#!/usr/bin/env python3
"""
Prepare the MuseBot admin dashboard credential on first boot.

Background
----------
The upstream MuseBot admin app (admin/db/db.go) seeds a hard-coded default
credential on every fresh DB:

  INSERT INTO admin_users VALUES (1, 'admin', '21232f297a57a5a743894a0e4a801fc3', ...);

The hash `21232f297a57a5a743894a0e4a801fc3` is MD5("admin"). Login compares
MD5(input) against this column (see admin/db/user.go GetUserByUsername).

This script runs as root in the container, before supervisord starts.
If ADMIN_USER / ADMIN_PASSWORD are set, it pre-provisions the admin_users
table so the upstream Go init sees "table exists" and skips its INSERT,
leaving exactly the credentials we requested in the DB.

Scope
-----
* SQLite (DB_TYPE=sqlite3): fully supported.
* MySQL (DB_TYPE=mysql): not supported here (no mysql client in the image) —
  we log a warning and let the app keep upstream's admin/admin. You can still
  change the password from the admin UI after first login.

Idempotency
-----------
* Runs on every container start.
* Upserts at most one row for the requested username (idempotent).
* If the requested username is NOT `admin`, also deletes the default
  `admin/admin` row so the known-bad credential doesn't linger.
* Never deletes other (UI-created) users — that would erase accounts on each restart.
"""
import hashlib
import os
import sqlite3
import sys
import time


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def log(msg: str) -> None:
    print(f"[bootstrap] {msg}", file=sys.stderr, flush=True)


def main() -> int:
    db_type = (os.environ.get("DB_TYPE") or "sqlite3").strip().lower()
    db_conf = (os.environ.get("DB_CONF") or "/app/data/muse_bot.db").strip()
    user    = (os.environ.get("ADMIN_USER") or "").strip()
    pw      = os.environ.get("ADMIN_PASSWORD") or ""

    # Not our job if the user opted out of setting credentials; upstream default stays.
    if not user or not pw:
        log("ADMIN_USER / ADMIN_PASSWORD not set — upstream default (admin/admin) stays in effect.")
        log("Set them in the Railway dashboard to override the default dashboard credentials.")
        return 0

    if len(pw) < 6:
        log(f"WARNING: ADMIN_PASSWORD is only {len(pw)} characters — a stronger password is strongly recommended.")

    if db_type != "sqlite3":
        log(f"DB_TYPE={db_type} detected — admin-credentials bootstrap only supports sqlite3 in this wrapper.")
        log("Upstream will still seed admin/admin into your MySQL database on first start.")
        log("Change it from the admin UI after first login (admin -> users -> edit).")
        return 1

    d = os.path.dirname(db_conf) or "."
    try:
        os.makedirs(d, exist_ok=True)
        if os.path.isdir(d) and os.geteuid() == 0:
            try:
                os.chown(d, 1000, 1000)
            except OSError:
                os.chmod(d, 0o777)
    except OSError as e:
        log(f"failed to mkdir {d}: {e}")
        return 1

    try:
        con = sqlite3.connect(db_conf, timeout=10)
    except sqlite3.Error as e:
        log(f"failed to open SQLite DB {db_conf}: {e}")
        return 2

    # The app runs as appuser (uid 1000). If we created the SQLite file as root,
    # hand ownership so the Go process can CREATE bot tables and write WAL/journals.
    if os.path.exists(db_conf) and os.geteuid() == 0:
        try:
            os.chown(db_conf, 1000, 1000)
        except OSError:
            try:
                os.chmod(db_conf, 0o666)
            except OSError:
                pass

    cur = con.cursor()
    try:
        # Match the DDL emitted by the upstream admin app (admin/db/db.go sqlite3CreateTableSQL).
        # `IF NOT EXISTS` means: our CREATE here is the source of truth; upstream will skip.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(255) NOT NULL DEFAULT '',
                password VARCHAR(100) NOT NULL DEFAULT '',
                create_time int(10) NOT NULL DEFAULT '0',
                update_time int(10) NOT NULL DEFAULT '0'
            );
            """
        )
        # The upstream admin app also creates a `bot` table. Create it too so the
        # app's own `CREATE TABLE` (no IF NOT EXISTS for sqlite) is skipped cleanly.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address VARCHAR(255) NOT NULL DEFAULT '',
                name VARCHAR(255) NOT NULL DEFAULT '',
                key_file TEXT NOT NULL,
                crt_file TEXT NOT NULL,
                ca_file TEXT NOT NULL,
                command TEXT NOT NULL,
                create_time int(11) NOT NULL DEFAULT '0',
                update_time int(11) NOT NULL DEFAULT '0',
                is_deleted int(10) NOT NULL DEFAULT '0'
            );
            """
        )

        now = int(time.time())
        new_hash = md5_hex(pw)

        action = None
        cur.execute("SELECT id FROM admin_users WHERE username = ?", (user,))
        row = cur.fetchone()
        if row is not None:
            cur.execute(
                "UPDATE admin_users SET password = ?, update_time = ? WHERE id = ?",
                (new_hash, now, row[0]),
            )
            action = f"updated row id={row[0]}"

        if action is None:
            # Try to repurpose the upstream default row (id=1, username='admin') so
            # we end up with exactly one user instead of two.
            cur.execute("SELECT id, username FROM admin_users WHERE id = 1")
            drow = cur.fetchone()
            if drow is not None and drow[1] == "admin" and user == "admin":
                cur.execute(
                    "UPDATE admin_users SET password = ?, update_time = ? WHERE id = 1",
                    (new_hash, now),
                )
                action = "repurposed default row id=1"
            else:
                cur.execute(
                    "INSERT INTO admin_users (username, password, create_time, update_time) VALUES (?, ?, ?, ?)",
                    (user, new_hash, now, now),
                )
                action = "inserted new row"

        # Remove the upstream default admin/admin row when it's not the one we provisioned,
        # so the known-bad credential cannot be used after a first login.
        if user != "admin":
            cur.execute("DELETE FROM admin_users WHERE username = 'admin'")
            action += "; removed default 'admin' row"

        con.commit()
    except sqlite3.Error as e:
        con.rollback()
        log(f"sqlite error: {e}")
        return 3
    finally:
        con.close()

    log(f"OK — {action}. Dashboard login: username={user} password=<value of ADMIN_PASSWORD>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
