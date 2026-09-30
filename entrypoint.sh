#!/bin/sh
set -e

# Ensure the SQLite/Knowledge/Image dirs exist and are writable by appuser (uid 1000)
# before any non-root process writes to them. Root-only prep.
mkdir -p /app/data
mkdir -p /app/data/knowledge
mkdir -p /app/data/image

# Ownership: prefer chown; fall back to chmod 777 so any user can write regardless
# of whether the mount is root-owned or appuser-owned (handles both Railway and local).
if chown -R 1000:1000 /app/data 2>/dev/null; then
  :
else
  chmod -R 777 /app/data 2>/dev/null || true
fi

# Provision the admin-dashboard credential (ADMIN_USER / ADMIN_PASSWORD).
# Must run BEFORE supervisord so the upstream app's first-boot seed
# (hard-coded admin/admin) is skipped — see admin_bootstrap.py.
# No-op (and non-fatal) when the vars are unset — the app keeps upstream defaults.
# The script also chowns the SQLite file to appuser (uid 1000) when it created it,
# so the Go app can write the rest of its tables.
if [ -f /admin_bootstrap.py ]; then
  python3 /admin_bootstrap.py || echo "[entrypoint] admin bootstrap reported a non-fatal issue (see above)"
fi

# Run the original supervisord; it still forks MuseBot + MuseBotAdmin as `user=appuser`.
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf -n
