# Copilot Instructions for SwiftlyTTS (updated)

Below are concise, actionable notes to help an AI coding agent be productive in this repository.

## Big picture
- SwiftlyTTS is a Discord TTS bot (Python) + Next.js web UI. Core responsibilities:
	- `bot.py`: entrypoint, loads `cogs/`, schedules background tasks, reads `config.yml`, and uses `lib/postgres.py` and `lib/VOICEVOXlib.py`.
	- `cogs/`: command implementations grouped (e.g. `voice/`, `system/`). Extensions are loaded dynamically by `bot.py` using AutoShardedBot.
	- `lib/VOICEVOXlib.py`: VOICEVOX HTTP client. Supports multiple VOICEVOX URLs via `VOICEVOX_URL` (comma-separated) and reloads `.env` at runtime.
	- `lib/postgres.py`: asyncpg-based DB wrapper. `initialize()` creates required tables and performs a simple migration for `user_voice.speaker_id`.
	- `web/`: Next.js (app router). Server-side API routes live under `web/app/api/`.

## Critical env vars & files (search these)
- `.env` / `.env.example` (root) — required for local dev and runtime. Key names used:
	- DISCORD_TOKEN, SHARD_COUNT, DEBUG
	- DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
	- VOICEVOX_URL (comma-separated list; default: http://localhost:50021)
	- PROMETHEUS_URL (used by web API: `web/app/api/prometheus/range/route.ts`)
	- NEXTAUTH_SECRET, DISCORD_CLIENT_ID / SECRET (web `web/lib/auth.ts`)
- `config.yml` — bot command prefix (used by `bot.py`).

## Run / build workflows (developer commands)
- Python (bot):
	- Install: `pip install -r requirements.txt` (Windows: `requirements.win.txt`).
	- Run: `python bot.py` (ensure `.env` present and VOICEVOX + Postgres accessible).
	- Note: On Windows the code sets WindowsSelectorEventLoopPolicy in `bot.py`.
- Web (Next.js):
	- Install: `cd web && npm install`
	- Dev: `cd web && npm run dev`
	- Build: `cd web && npm run build` (CI uses this; a successful build was run in workspace history).

## Integration & runtime patterns to preserve
- VOICEVOX URL rotation: `VOICEVOXlib` reads `VOICEVOX_URL` from env and tries each URL; agent changes should preserve the retry/round-robin semantics and the fact it reloads `.env` dynamically.
- DB migrations: `PostgresDB.initialize()` is idempotent and creates tables on startup. Small column migrations are handled there — prefer in-code, non-destructive migrations rather than assuming external migration tooling.
- Cog loading: `bot.py` walks `./cogs` and constructs module strings (replace os.sep with '.') — keep that string building logic if moving files.

## Observatory & metrics
- `lib/VOICEVOXlib.py` exposes a Prometheus Gauge named `voice_generation_seconds_per_minute`.
- Web frontend calls Prometheus via `PROMETHEUS_URL`; ensure URL is valid (route will return a helpful JSON error if not).

## Project-specific conventions
- Keep bot responsibilities inside `cogs/` modules (each file is a discord.py extension loaded by `bot.load_extension`).
- Use `lib/postgres.py` for all DB access (it provides helper methods like `upsert_dictionary`, `insert_guild_count`, etc.).
- `VOICEVOXlib` returns either saved tmp file paths (`synthesize`) or (base_url, bytes) (`synthesize_bytes`) — pay attention to both return shapes.

## Files to inspect when changing behavior
- `bot.py` (startup, event loop, cog loading, task scheduling)
- `lib/VOICEVOXlib.py` (VOICEVOX interaction, tmp file handling, metrics)
- `lib/postgres.py` (schema creation, helper DB methods)
- `README.md` and `.env.example` (runtime config examples)
- `pterodactyl-egg.json` (env var definitions for hosted deployments)

## Safety / quick checks before edits
- Don't assume database schema migrations exist — inspect `PostgresDB.initialize()`.
- Preserve `.env` names and defaults when introducing config changes (the web and bot read envs independently).

If any section is unclear or you want me to expand examples (e.g., show the cog-loading code snippet or VOICEVOX retry flow), tell me which area to expand and I'll iterate.