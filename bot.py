import logging
import os
import signal
import sqlite3
import time
from datetime import datetime, timezone

import praw
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('reddit-discord-monitor')

SUBREDDITS = [s.strip().removeprefix('r/') for s in os.environ.get('SUBREDDITS', 'hardwareswap,GameSale,gameswap').split(',') if s.strip()]
INTERVAL = max(60, int(os.environ.get('POLL_INTERVAL_SECONDS', '60')))
WEBHOOK = os.environ['DISCORD_WEBHOOK_URL']
DB_PATH = os.environ.get('DB_PATH', '/data/posts.sqlite3')
USER_AGENT = os.environ.get('REDDIT_USER_AGENT', 'linux:reddit-discord-monitor:0.1 (by u/yourusername)')
STOP = False


def stop(*_):
    global STOP
    STOP = True


def db_connect():
    connection = sqlite3.connect(DB_PATH)
    connection.execute('CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, created_utc REAL NOT NULL, seen_at TEXT NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS initialized (subreddit TEXT PRIMARY KEY)')
    connection.commit()
    return connection


def notify(post):
    payload = {
        'username': 'Reddit Post Monitor',
        'allowed_mentions': {'parse': []},
        'embeds': [{
            'title': post.title[:256],
            'url': 'https://www.reddit.com' + post.permalink,
            'description': f'New post in r/{post.subreddit.display_name}',
            'timestamp': datetime.fromtimestamp(post.created_utc, timezone.utc).isoformat(),
        }],
    }
    for attempt in range(5):
        response = requests.post(WEBHOOK, json=payload, timeout=20)
        if response.status_code in (200, 204):
            return True
        if response.status_code == 429:
            wait = min(120, max(1, float(response.json().get('retry_after', 5))))
            log.warning('Discord rate limited; waiting %.1fs', wait)
            time.sleep(wait)
            continue
        if response.status_code >= 500:
            time.sleep(min(30, 2 ** attempt))
            continue
        log.error('Discord webhook failed: HTTP %s', response.status_code)
        return False
    return False


def main():
    if not SUBREDDITS or len(SUBREDDITS) > 5:
        raise ValueError('Configure between 1 and 5 subreddits')
    reddit = praw.Reddit(
        client_id=os.environ['REDDIT_CLIENT_ID'],
        client_secret=os.environ['REDDIT_CLIENT_SECRET'],
        user_agent=USER_AGENT,
        check_for_async=False,
    )
    connection = db_connect()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info('Monitoring %s every %ss', ', '.join(SUBREDDITS), INTERVAL)
    while not STOP:
        started = time.monotonic()
        for subreddit in SUBREDDITS:
            if STOP:
                break
            try:
                posts = list(reddit.subreddit(subreddit).new(limit=100))
                first_run = connection.execute('SELECT 1 FROM initialized WHERE subreddit=?', (subreddit,)).fetchone() is None
                for post in reversed(posts):
                    if connection.execute('SELECT 1 FROM seen WHERE id=?', (post.id,)).fetchone():
                        continue
                    if not first_run and not notify(post):
                        log.warning('Notification not delivered; will retry on next poll: %s', post.id)
                        continue
                    connection.execute('INSERT OR IGNORE INTO seen VALUES (?, ?, ?)', (post.id, post.created_utc, datetime.now(timezone.utc).isoformat()))
                    connection.commit()
                if first_run:
                    connection.execute('INSERT OR IGNORE INTO initialized VALUES (?)', (subreddit,))
                    connection.commit()
                    log.info('Initialized r/%s without sending historical posts', subreddit)
            except Exception:
                log.exception('Failed to poll r/%s; will retry', subreddit)
        # Limit local history. Reddit's deletion requirements may require additional handling.
        connection.execute("DELETE FROM seen WHERE seen_at < datetime('now', '-30 days')")
        connection.commit()
        while not STOP and time.monotonic() - started < INTERVAL:
            time.sleep(1)
    connection.close()


if __name__ == '__main__':
    main()
