# MuseBot Lite — Railway one-click template
#
# Wraps jackyin0822/musebot:v1.0.41 to fix the Railway-volume issue:
#   - Official image runs apps as appuser (uid 1000) and does not ship /app/data
#   - A fresh Railway volume mounts root-owned; the SQLite open() fails with
#     "no such file or directory" as observed on live Railway deploys.
#
# This wrapper runs as root first, ensures /app/data (and the SQLite/Knowledge/Image
# subdirs) exist and are writable by appuser, then execs the original supervisord
# which still starts MuseBot + MuseBotAdmin as `user=appuser` per their config.

FROM jackyin0822/musebot:v1.0.41

USER root

COPY entrypoint.sh admin_bootstrap.py /tmp/bootstrap/
RUN cp /tmp/bootstrap/entrypoint.sh /entrypoint.sh && \
    cp /tmp/bootstrap/admin_bootstrap.py /admin_bootstrap.py && \
    chmod +x /entrypoint.sh && rm -rf /tmp/bootstrap

# Keep upstream EXPOSE 36060 (bot) and 18080 (admin dashboard).
EXPOSE 36060 18080

# Optional: let Railway healthcheck hit / (the admin SPA is on 18080; the domain
# targets 18080). The container-level HEALTHCHECK below still guards the bot on 36060.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS http://127.0.0.1:36060/pong || exit 1

ENTRYPOINT ["/entrypoint.sh"]
