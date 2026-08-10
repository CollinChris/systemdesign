# system-design-app

Sends you one system design fact or quiz question a day as a Telegram
notification, each linked to its source article for further reading. Runs
once and exits — intended to be triggered daily by Windows Task Scheduler,
not run as a background service.

## Setup

```
uv sync
cp .env.example .env
```

Fill in `.env`:

1. **Create a Telegram bot**: message [@BotFather](https://t.me/BotFather) on
   Telegram, send `/newbot`, and follow the prompts. Copy the token it gives
   you into `TELEGRAM_BOT_TOKEN`.
2. **Find your chat id**: send any message to your new bot, then visit
   `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and read
   `message.chat.id` from the JSON response (or ask
   [@userinfobot](https://t.me/userinfobot)). Put it in `TELEGRAM_CHAT_ID`.
3. **Optional — `ANTHROPIC_API_KEY`**: if set, the app automatically
   generates and appends new fact/quiz entries to `data/content_bank.json`
   via the Anthropic API whenever fewer than 3 unsent entries remain. Leave
   it blank to rely solely on the curated content bank.

## Running manually

```
uv run system-design-app
```

Sends one notification and exits. Run it again and a different (unsent)
entry is picked; once every entry has been sent, the pool reshuffles and
cycles again.

## Growing the content bank

`data/content_bank.json` is a plain JSON file — add your own fact/quiz
entries by hand at any time, following the existing schema (`id`, `type`,
`text`/`question`+`answer`, `source_url`, `source_excerpt`). IDs must be
unique and are never reused.

## Scheduling with Windows Task Scheduler

1. Open Task Scheduler → **Create Task**.
2. **Action** → **Start a program**:
   - Program: full path to `uv.exe`. On this machine that's
     `C:\Users\Admin\AppData\Roaming\Python\Python312\Scripts\uv.exe`
     (`uv` isn't on PATH here — find it elsewhere with `where.exe uv` or
     `python -m site --user-base` + `\Scripts`).
   - Arguments: `run system-design-app`
   - Start in: this project's directory (so `.env` and `data/` resolve
     correctly), e.g. `C:\Users\<you>\Downloads\selfprojects\system_design_app`
3. **Trigger**: Daily, at whatever time you want your notification.
4. Choose "Run only when user is logged on" unless you've configured the
   task to run with stored credentials.

## Development

```
uv run black .
uv run ruff check .
uv run mypy src/
uv run pytest --cov
```
