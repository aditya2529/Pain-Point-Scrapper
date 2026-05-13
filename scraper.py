"""
Reddit scraper using public JSON API — zero auth needed.
No API keys, no PRAW, no captcha. Works instantly.
"""

import requests
import pandas as pd
import time
import os
from rich.console import Console
from rich.progress import track
from datetime import datetime

console = Console()

# Headers to mimic a real browser (Reddit blocks empty user-agents)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PainPointResearcher/1.0"
}

# Target subreddits
SUBREDDITS = [
    "SaaS",
    "startups",
    "Entrepreneur",
    "indiehackers",
    "webdev",
    "smallbusiness",
    "ProductManagement",
    "digitalnomad",
    "passive_income"
]

# Pain signal keywords
PAIN_KEYWORDS = [
    "frustrated", "annoying", "hate", "broken", "terrible",
    "impossible", "waste of time", "why can't", "nobody solves",
    "problem with", "issue with", "struggling with", "can't figure out",
    "anyone else", "am I the only one", "drives me crazy",
    "wish there was", "there should be", "why doesn't",
    "looking for a tool", "need help with", "can't find",
    "overpriced", "too expensive", "no good solution",
    "manual process", "takes forever", "so painful",
    "horrible", "nightmare", "useless", "disappointing",
    "fails", "buggy", "slow", "crashes", "unreliable",
    "no way to", "is it possible to", "how do i even",
    "killing me", "worst", "awful", "terrible experience",
    "rant", "venting", "advice needed", "help needed",
    "sick of", "fed up", "giving up on", "alternatives to"
]

def has_pain_signal(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in PAIN_KEYWORDS)

def fetch_subreddit(subreddit, category="hot", limit=100):
    """Fetch posts from Reddit public JSON API"""
    url = f"https://www.reddit.com/r/{subreddit}/{category}.json?limit={limit}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)

        if resp.status_code == 429:
            console.print(f"  [yellow]Rate limited on r/{subreddit}, waiting 5s...[/yellow]")
            time.sleep(5)
            resp = requests.get(url, headers=HEADERS, timeout=10)

        if resp.status_code != 200:
            console.print(f"  [red]Failed r/{subreddit} ({category}): HTTP {resp.status_code}[/red]")
            return []

        data = resp.json()
        posts = []

        for post in data["data"]["children"]:
            p = post["data"]

            # Skip pinned/stickied posts
            if p.get("stickied", False):
                continue

            title = p.get("title", "")
            body  = p.get("selftext", "")
            full_text = f"{title} {body}"

            # Filter for pain signals
            if not has_pain_signal(full_text):
                continue

            # Skip very short posts
            if len(full_text.strip()) < 60:
                continue

            # Skip deleted/removed
            if body in ["[deleted]", "[removed]"]:
                continue

            posts.append({
                "id":           p.get("id", ""),
                "subreddit":    subreddit,
                "title":        title,
                "body":         body[:1000],
                "full_text":    full_text[:1500],
                "score":        p.get("score", 0),
                "num_comments": p.get("num_comments", 0),
                "url":          f"https://reddit.com{p.get('permalink', '')}",
                "created_utc":  datetime.fromtimestamp(
                                    p.get("created_utc", 0)
                                ).strftime("%Y-%m-%d"),
                "category":     category
            })

        return posts

    except Exception as e:
        console.print(f"  [red]Error on r/{subreddit}: {e}[/red]")
        return []


def run_scraper():
    console.print("\n[bold cyan]Reddit Public JSON Scraper[/bold cyan]")
    console.print("[dim]No API key needed — using Reddit's public endpoints[/dim]\n")

    all_posts = []

    for sub in track(SUBREDDITS, description="Scraping subreddits..."):
        sub_posts = []
        for category in ["hot", "new", "top"]:
            posts = fetch_subreddit(sub, category=category, limit=75)
            sub_posts.extend(posts)
            time.sleep(1.2)  # Polite rate limiting

        console.print(f"  [green]done[/green] r/{sub}: {len(sub_posts)} pain-signal posts")
        all_posts.extend(sub_posts)

    if not all_posts:
        console.print("[red]No posts collected. Check your internet connection.[/red]")
        return pd.DataFrame()

    df = pd.DataFrame(all_posts)
    df = df.drop_duplicates(subset=["id"])
    df["engagement"] = df["score"] + (df["num_comments"] * 2)
    df = df.sort_values("engagement", ascending=False)

    df.to_csv("raw_pain_points.csv", index=False)

    console.print(f"\n[bold green]Done! {len(df)} unique pain posts saved to raw_pain_points.csv[/bold green]")
    console.print(f"[dim]Top post: {df.iloc[0]['title'][:80]}[/dim]\n")

    return df


if __name__ == "__main__":
    df = run_scraper()
    if not df.empty:
        print(df[["subreddit", "title", "score", "num_comments"]].head(20).to_string())
