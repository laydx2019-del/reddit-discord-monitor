Reddit-to-Discord Post Monitor
A small, self-hosted, commercial-use Reddit monitoring application for a video-game and electronics resale business. It monitors up to five public subreddits for new submissions and forwards the title and Reddit permalink to a private Discord channel for manual review. It does not purchase products, message Redditors, vote, comment, or post to Reddit.
Status and API access
Prototype; Reddit API approval required. This project does not claim that Reddit has approved its use. The owner must obtain explicit authorization for the intended commercial use and comply with any applicable Reddit API terms, fees, rate limits, and data handling requirements before running it. This app uses Reddit's external OAuth Data API via PRAW; it is not a Devvit app. No credentials are included.
Architecture
- Python 3.12 + PRAW (read-only OAuth)
- Docker Compose on a privately managed Linux server
- SQLite to remember post IDs and avoid duplicate notifications
- Discord webhook for private alerts (title and original Reddit link)
- One check per subreddit per polling cycle (default 60 seconds), with PRAW's API rate-limit handling
- First run records recent posts without sending them, to avoid a backlog
Setup (after approval)
1. Create an approved Reddit OAuth application and obtain its client ID and secret. Use the authentication flow and credentials Reddit authorizes for your application.
2. In Discord: Channel Settings → Integrations → Webhooks → New Webhook. Copy its URL.
3. Copy .env.example to .env and set the credentials, webhook URL, username in the user agent, and comma-separated subreddit names.
4. Run docker compose up -d --build.
5. Follow logs using docker compose logs -f reddit-monitor.
6. Stop using docker compose down (data volume is retained).
Never commit .env, API secrets, or webhook URLs to GitHub.
Configuration
Variable	Description
REDDIT_CLIENT_ID	Approved OAuth app client ID
REDDIT_CLIENT_SECRET	OAuth app secret, if issued for your authorized app type
REDDIT_USER_AGENT	Unique, descriptive app identifier including your Reddit username
DISCORD_WEBHOOK_URL	Private Discord webhook URL
SUBREDDITS	Comma-separated names, up to five
POLL_INTERVAL_SECONDS	Polling interval; minimum 60 seconds
DB_PATH	SQLite database path


Limitations and compliance
- Polling is not a real-time push feed. Posts deleted before polling or displaced from the latest 100 posts may be missed.
- Access to private or restricted communities is not assumed.
- Reddit's rate limits and commercial-use approval terms govern actual operation. Reduce polling frequency if necessary.
- Discord webhook errors are retried, but a webhook delivery followed by a database write failure can cause a duplicate.
- This prototype does not implement Reddit deletion-event reconciliation for already-posted Discord messages. Before production use, confirm whether your authorized use and applicable Reddit data/deletion rules require additional deletion handling.
- The bot does not scrape HTML pages or circumvent access restrictions.
- Posts are shown as titles and links, not full-text archives.
Planned improvements
Automated tests, better logging and monitoring, graceful recovery from API failures, and deletion handling if required by Reddit's approval conditions.
