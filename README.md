# Deploy and Host

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.com/deploy/musebot)

**MuseBot Lite** — [MuseBot](https://github.com/yincongcyincong/MuseBot) (1.6k★, MIT, Go 1.24) — is a lightweight open-source AI Secretary that speaks **8 messaging platforms from a single Go binary**: Telegram, Discord, Slack, Lark/Feishu, DingDing, Work WeChat (企业微信), QQ (OneBot), and personal WeChat — with **LLM tool-calling (MCP)**, **RAG over your documents**, **cron-triggered briefings**, **streaming replies**, **image/voice/video generation**, and a built-in **admin dashboard**.

This Lite template ships the whole system in **one container** (the official `jackyin0822/musebot:v1.0.41` image plus a small Railway-volume compatibility shim): the bot server on **:36060**, the admin dashboard on **:18080**, the SQLite database, the RAG knowledge directory, and every generated media file all live on **one persistent volume** — no companion database service required, and every conversation survives redeploys.

- 8 messaging platforms from one binary — pick one or wire up several at the same time (fill the matching tokens)
- LLM-agnostic: DeepSeek, OpenAI, Gemini, OpenRouter, OrcaRouter, 302.AI, Volc, Aliyun, chatAnyWhere, or any OpenAI-compatible endpoint — set `TYPE` + matching token
- **RAG**: drop markdown/PDF/text into `KNOWLEDGE_PATH` and the bot grounds replies in *your* documents
- **Cron**: schedule "good morning" briefings or any LLM prompt on a crontab expression via the admin API
- **MCP tools**: point `MCP_CONF_PATH` at an MCP server and MuseBot exposes its tools to the LLM as function calls
- **Voice in / voice + image + video out** on Volc / Gemini / OpenAI / Aliyun / 302.AI engines
- **Admin dashboard** at :18080 (`/dashboard`) — manage users, tokens, records, RAG, cron, MCP, logs, and restart the bot remotely

## Why Deploy

MuseBot is one of only a handful of self-hosted AI Secretary projects that covers the Chinese IM ecosystem (WeChat / Work WeChat / Feishu / DingDing / QQ) *and* the Western stack (Telegram / Discord / Slack) **in the same binary**, with **MCP tool-calling + RAG + cron + streaming** in one Go process — and it is the **only one on Railway's template list today** (0 existing templates)

Shipping it as a single-container Railway template means:

- **One click** — no companion Postgres to spin up (SQLite by default), no Helm chart, no 4-container orchestration; two processes (bot + admin) live in one container under supervisord
- **Persistence** — one Railway volume covers the SQLite database, the RAG knowledge corpus, generated images, and the bot's message log; a redeploy never loses state
- **Any LLM** — DeepSeek, OpenAI, Gemini, OpenRouter, OrcaRouter, 302.AI, Volc, Aliyun, chatAnyWhere, or your own OpenAI-compatible endpoint (set `TYPE` + `*_TOKEN`)
- **Multi-platform** — fill as many of `TELEGRAM_BOT_TOKEN` / `DISCORD_BOT_TOKEN` / `SLACK_*` / `LARK_*` / `DING_*` / `COM_WECHAT_*` / `WECHAT_*` / `QQ_*` as you need; empty ones are idle
- **Proxy-friendly** — `LLM_PROXY` and `ROBOT_PROXY` let you route blocked providers (LLM) or region-restricted bot APIs (Telegram/Discord) through an egress proxy from the same container

## Required inputs

Two things are **mandatory** for a working bot — everything else is optional and disabled by default:

| Variable | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` (or one of the other platform tokens) | [Telegram @BotFather](https://t.me/BotFather) → New bot, or your Discord / Slack / Feishu / Ding / WeChat / QQ console |
| One LLM token matching `TYPE` (e.g. `DEEPSEEK_TOKEN` for `TYPE=deepseek`) | Provider dashboard (see "## About Hosting") |

Everything else — `BOT_NAME`, `CHARACTER`, `TOKEN_PER_USER`, RAG paths, `*_PROXY`, MCP config, whitelist IDs — has sensible defaults or is off until you set it.

## Source Repository

[https://github.com/yincongcyincong/MuseBot](https://github.com/yincongcyincong/MuseBot) · image: `jackyin0822/musebot:v1.0.41` · template repo: [https://github.com/mc9max/musebot](https://github.com/mc9max/musebot)

The template ships a minimal `Dockerfile` that starts from the official `jackyin0822/musebot:v1.0.41` image and adds a 20-line `entrypoint.sh` that runs as root just long enough to `mkdir -p /app/data` and chown it to `appuser` before `exec`'ing the original supervisord — fixing the "unable to open database file: no such file or directory" crash the official image hits on a fresh Railway volume (the image does not ship `/app/data`, and its apps run as uid 1000 against a root-owned mount).

## About Hosting

| Item | Value |
|---|---|
| Runtime | Go 1.24 single binary + admin server, both under supervisord |
| Image | `jackyin0822/musebot:v1.0.41` (~228 MB compressed) + 2 files of wrapper code |
| Container user | `appuser` (uid 1000) — the wrapper entrypoint is root for the ~1 s chown step only |
| Persistence | one Railway volume at `/app/data` (SQLite DB + RAG corpus + generated media) |
| LLM providers | DeepSeek, OpenAI, Gemini, OpenRouter/OrcaRouter, 302.AI, Volc, Aliyun, chatAnyWhere, or any OpenAI-compatible endpoint — pick one via `TYPE` |
| Messaging platforms | Telegram, Discord, Slack, Lark/Feishu, DingDing, Work WeChat, QQ (OneBot), personal WeChat |
| Admin surface | `/dashboard` on port 18080 (users, tokens, RAG, cron, MCP, logs, restart) |
| Cost profile | Hobby $3 / 256 MB or 512 MB instance is comfortable; no companion services |
| Egress | LLM + bot APIs over outbound HTTPS; optional `LLM_PROXY` / `ROBOT_PROXY` for region-restricted endpoints |

## Ports

- **36060** — main bot HTTP API (`/pong`, `/communicate`, `/com/wechat`, `/wechat`, `/qq`, `/onebot`, `/rag/*`, `/cron/*`, `/mcp/*`, `/user/*`, `/log`, `/restart`, `/stop`)
- **18080** — admin dashboard (`/dashboard`) — manage users, tokens, records, RAG, cron, MCP, logs, restart the bot remotely

## Dependencies for MuseBot Lite

- **Go 1.24** — already compiled into the official `jackyin0822/musebot:v1.0.41` image; no Go toolchain required on Railway
- **SQLite** — embedded; no companion database service required (MySQL also supported via `DB_TYPE` + `DB_CONF`, but SQLite on a volume is the zero-config default)
- **ffmpeg / ffprobe** — bundled in the official image for audio + video transcode; no host packages required
- **Optional egress proxy** — an HTTP(S) proxy (e.g. a SOCKS/HTTP bridge) if `TYPE` points at a region-restricted LLM API **or** if the bot needs to reach Telegram/Discord from a region where they are blocked. Leave blank if you're in a normal region on Railway.

### Deployment Dependencies

None. MuseBot Lite ships everything required in one container:

- **No companion database** — SQLite by default, or bring your own MySQL/Postgres if you want cross-instance sharing.
- **No companion vector store** — RAG runs against the local vector DB on the volume by default (`VECTOR_DB_TYPE=local`); upgrade to Qdrant / Chroma / Weaviate / Milvus optionally without changing the app.
- **No companion web server** — the bot's own HTTP server (Gin) on 36060 is the app; the optional admin dashboard is a second process in the same container on 18080.
- **No companion MCP sidecar** — MCP endpoints are registered at boot via `MCP_CONF_PATH`, and the LLM calls them over stdio or HTTP directly.
- **One persistent volume** — `/app/data` holds the SQLite file, RAG knowledge corpus, and generated media.

## Common Use Cases

- **Multilingual personal secretary** — one bot on Telegram + Discord + Feishu + Work WeChat answering from your RAG documents (drop `~/work/notes.md` into `/app/data/knowledge`) at 8am with a cron schedule
- **Small-team AI assistant** — per-user token budget (`TOKEN_PER_USER`), per-group whitelist (`ALLOWED_USER_IDS`, `ALLOWED_GROUP_IDS`), shared context, streaming replies
- **MCP-powered automation** — point your Beszel / Kopia / marketing-agent MCP servers into `MCP_CONF_PATH` and let MuseBot's LLM call them via function calls from any of the 8 platforms
- **LLM relay test-bench** — flip between DeepSeek / Gemini / OpenAI / OpenRouter / OrcaRouter live via the `/conf/update` admin API to compare providers on the same chat history

## License

[MIT](https://github.com/yincongcyincong/MuseBot/blob/main/LICENSE) (upstream MuseBot); this template repository is MIT.

MuseBot is not affiliated with, endorsed by, or sponsored by any LLM vendor, messaging platform, or Railway.com.
