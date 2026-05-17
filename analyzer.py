from groq import Groq
import pandas as pd
import json
import os
import time
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import track

load_dotenv()
console = Console()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

EXTRACTION_PROMPT = """You are a market research analyst specializing in identifying business opportunities from user complaints.

Analyze this Reddit post and extract structured intelligence.

POST TITLE: {title}
POST BODY: {body}
SUBREDDIT: r/{subreddit}
ENGAGEMENT: {score} upvotes, {comments} comments

Return ONLY a valid JSON object with these exact keys:
{{
  "is_genuine_pain_point": true or false,
  "pain_point_summary": "1 sentence describing the core problem",
  "pain_category": "one of: workflow / tooling / pricing / onboarding / integration / support / missing_feature / process / other",
  "target_user": "who experiences this pain (e.g. solo SaaS founders, product managers at startups)",
  "emotional_intensity": a number from 1 to 10,
  "urgency": a number from 1 to 10,
  "frequency_signal": "one of: isolated / occasional / common / widespread",
  "existing_solutions_mentioned": ["list any tools or solutions they mentioned, or empty array"],
  "gap_in_existing_solutions": "what is missing from current solutions",
  "product_opportunity": "1-2 sentence idea for a product or feature that solves this",
  "monetization_angle": "how you would charge for this",
  "willingness_to_pay_signal": "one of: low / medium / high / very_high",
  "key_quote": "most impactful quote from the post, max 120 chars"
}}

Return ONLY the JSON. No explanation, no markdown, no code blocks."""


def analyze_post(row):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=900,
            temperature=0.2,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(
                    title=row["title"],
                    body=str(row["body"])[:600],
                    subreddit=row["subreddit"],
                    score=row["score"],
                    comments=row["num_comments"]
                )
            }]
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code blocks if model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return result

    except json.JSONDecodeError as e:
        return {"is_genuine_pain_point": False, "error": f"JSON parse failed: {e}"}
    except Exception as e:
        return {"is_genuine_pain_point": False, "error": str(e)}


def run_analyzer(input_file="raw_pain_points.csv", sample_size=100):
    console.print("\n[bold cyan]Claude AI Pain Point Analyzer[/bold cyan]")
    console.print(f"[dim]Analyzing top {sample_size} posts with Claude Haiku...[/dim]\n")

    if not os.path.exists(input_file):
        console.print(f"[red]File not found: {input_file}. Run scraper.py first.[/red]")
        return None

    df = pd.read_csv(input_file)
    if df.empty:
        console.print("[red]No data to analyze.[/red]")
        return None

    df_sample = df.head(sample_size).copy()
    results = []

    for _, row in track(df_sample.iterrows(), total=len(df_sample), description="Analyzing with Claude..."):
        analysis = analyze_post(row)

        if analysis.get("is_genuine_pain_point", False):
            combined = {**row.to_dict(), **analysis}
            results.append(combined)

        time.sleep(0.25)

    if not results:
        console.print("[red]No genuine pain points detected. Try expanding keywords in scraper.py.[/red]")
        return None

    results_df = pd.DataFrame(results)

    wtp_map = {"very_high": 10, "high": 7.5, "medium": 5, "low": 2.5}
    results_df["wtp_score"] = results_df["willingness_to_pay_signal"].map(wtp_map).fillna(5)
    results_df["engagement_score"] = results_df["engagement"].fillna(0).clip(0, 1000) / 100

    results_df["opportunity_score"] = (
        results_df["emotional_intensity"].fillna(5) * 0.25 +
        results_df["urgency"].fillna(5) * 0.25 +
        results_df["engagement_score"] * 0.25 +
        results_df["wtp_score"] * 0.25
    ).round(2)

    results_df = results_df.sort_values("opportunity_score", ascending=False)
    results_df.to_csv("analyzed_pain_points.csv", index=False)

    console.print(f"\n[bold green]Analysis complete![/bold green]")
    console.print(f"  Posts analyzed:            {len(df_sample)}")
    console.print(f"  Genuine pain points found: [bold]{len(results_df)}[/bold]")
    console.print(f"  Cost:                      FREE (Groq)\n")

    console.print("[bold yellow]TOP 5 OPPORTUNITIES:[/bold yellow]\n")
    for i, (_, row) in enumerate(results_df.head(5).iterrows(), 1):
        console.print(f"[bold]{i}. {row.get('pain_point_summary', 'N/A')}[/bold]")
        console.print(f"   r/{row['subreddit']} | Opportunity Score: {row['opportunity_score']}/10")
        console.print(f"   Intensity: {row.get('emotional_intensity', 'N/A')}/10 | WTP: {row.get('willingness_to_pay_signal', 'N/A')}")
        console.print(f"   Idea: {row.get('product_opportunity', 'N/A')}")
        console.print(f"   Quote: \"{row.get('key_quote', 'N/A')}\"\n")

    return results_df


if __name__ == "__main__":
    run_analyzer(sample_size=100)
