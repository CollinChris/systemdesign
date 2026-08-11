# system-design-app

Sends you one system design fact or quiz question a day as a Telegram
notification, each linked to its source article for further reading. Runs
once and exits — intended to be triggered daily by a scheduler (GitHub
Actions by default; Windows Task Scheduler or cron also work for local
runs), not run as a background service.

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

## Scheduling with GitHub Actions (recommended)

`.github/workflows/daily-notification.yml` runs the app on a schedule in
GitHub's cloud, so your own machine doesn't need to be on or logged in.

1. Push this repo to GitHub (if not already).
2. Add repo secrets under **Settings → Secrets and variables → Actions**:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and optionally
   `ANTHROPIC_API_KEY` — same values as your `.env`. Or via the CLI:
   ```
   gh secret set TELEGRAM_BOT_TOKEN
   gh secret set TELEGRAM_CHAT_ID
   gh secret set ANTHROPIC_API_KEY   # optional
   ```
3. That's it — the workflow fires daily at `0 5 * * *` UTC (1:00 PM
   Asia/Singapore) via its `schedule` trigger, and can also be run on
   demand from the Actions tab (`workflow_dispatch`).

Since GitHub Actions runners are ephemeral, `data/state.json` (send
history) and `data/content_bank.json` (grows via the optional Anthropic
top-up) are committed back to the repo by the workflow after each run —
that's why `data/state.json` is tracked in git rather than ignored.

To change the time: edit the `cron` line in the workflow file. GitHub
Actions schedules are always UTC and don't observe daylight saving, so
recompute the UTC offset if your local time zone does.

## Scheduling locally instead

If you'd rather run it on your own machine on a schedule (no GitHub
required), use Windows Task Scheduler or cron.

### Windows Task Scheduler

A `run_daily.bat` is included in the project root — it `cd`s into its own
folder before running `uv`, so "Start in" is handled automatically no
matter where the project lives.

**Via the command line** (run once, in a Windows terminal, from the
project directory):

```
schtasks /create /tn "SystemDesignApp Daily" /tr "C:\Users\Admin\Downloads\selfprojects\system_design_app\run_daily.bat" /sc daily /st 13:00
```

Adjust the path if the project lives elsewhere. This registers a task
that fires every day at 1:00 PM and runs only while you're logged on
(the schtasks default).

**Or via the GUI**:

1. Open Task Scheduler → **Create Task**.
2. **Action** → **Start a program**:
   - Program: full path to `run_daily.bat`, e.g.
     `C:\Users\Admin\Downloads\selfprojects\system_design_app\run_daily.bat`
3. **Trigger**: Daily, at 1:00 PM.
4. Choose "Run only when user is logged on" unless you've configured the
   task to run with stored credentials.

If you'd rather point Task Scheduler straight at `uv.exe` instead of the
batch file:
   - Program: full path to `uv.exe`. On this machine that's
     `C:\Users\Admin\AppData\Roaming\Python\Python312\Scripts\uv.exe`
     (`uv` isn't on PATH here — find it elsewhere with `where.exe uv` or
     `python -m site --user-base` + `\Scripts`).
   - Arguments: `run system-design-app`
   - Start in: this project's directory (so `.env` and `data/` resolve
     correctly), e.g. `C:\Users\<you>\Downloads\selfprojects\system_design_app`

### cron (Linux/macOS)

```
crontab -e
```

Add a line (adjust paths for your machine — find `uv`'s path with
`which uv`):

```
0 13 * * * cd /path/to/system_design_app && /path/to/uv run system-design-app >> /path/to/system_design_app/logs/cron.log 2>&1
```

This only fires while the machine is on and awake at that time.

## Development

```
uv run black .
uv run ruff check .
uv run mypy src/
uv run pytest --cov
```
