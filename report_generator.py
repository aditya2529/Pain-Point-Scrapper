from groq import Groq
import pandas as pd
import os
from dotenv import load_dotenv
from rich.console import Console
from collections import Counter
from datetime import datetime

load_dotenv()
console = Console()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_report(input_file="analyzed_pain_points.csv"):
    console.print("\n[bold cyan]Generating Intelligence Report...[/bold cyan]\n")

    if not os.path.exists(input_file):
        console.print(f"[red]File not found: {input_file}. Run analyzer.py first.[/red]")
        return None

    df = pd.read_csv(input_file)
    df = df.sort_values("opportunity_score", ascending=False)

    category_counts = Counter(df["pain_category"].dropna())
    top_categories = category_counts.most_common(6)
    top_10 = df.head(10)

    # Generate AI narrative
    pain_points_text = "\n".join([
        f"- {p['pain_point_summary']} "
        f"(Category: {p['pain_category']}, "
        f"Intensity: {p['emotional_intensity']}/10, "
        f"WTP: {p['willingness_to_pay_signal']}, "
        f"Opportunity: {p['product_opportunity']})"
        for _, p in top_10.iterrows()
    ])

    console.print("[dim]Asking Claude to write executive summary...[/dim]")

    narrative = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1800,
        temperature=0.4,
        messages=[{
            "role": "user",
            "content": f"""You are a sharp market research analyst briefing a startup founder.

Based on these pain points discovered from Reddit analysis of SaaS/Startup communities:

{pain_points_text}

Write a punchy 4-paragraph executive summary:
1. The dominant theme — what single frustration cuts across most of these?
2. The #1 highest-opportunity product idea with clear reasoning (be specific, not vague)
3. One contrarian or surprising insight that most founders would miss
4. The one thing a solo founder could build in 30 days to capture some of this market

Be brutally honest. No fluff. No generic "build a SaaS" advice. Write like a YC partner who has 2 minutes."""
        }]
    ).choices[0].message.content

    # Build report
    now = datetime.now().strftime("%B %d, %Y")
    report_lines = []

    report_lines.append("=" * 70)
    report_lines.append("  PAIN POINT INTELLIGENCE REPORT — SaaS & Startup Edition")
    report_lines.append(f"  {now}  |  Based on {len(df)} analyzed posts from Reddit")
    report_lines.append("=" * 70)

    report_lines.append("\n[ EXECUTIVE SUMMARY ]\n")
    report_lines.append(narrative)

    report_lines.append("\n\n[ TOP PAIN CATEGORIES ]\n")
    for category, count in top_categories:
        bar = "#" * min(count, 30)
        report_lines.append(f"  {category:<22} {bar} ({count})")

    report_lines.append("\n\n[ TOP 10 OPPORTUNITIES — RANKED BY SCORE ]\n")

    for i, (_, p) in enumerate(top_10.iterrows(), 1):
        wtp_emoji = {
            "very_high": "[$$$$]",
            "high":      "[$$$] ",
            "medium":    "[$$]  ",
            "low":       "[$]   "
        }.get(str(p.get("willingness_to_pay_signal", "medium")).strip(), "[$]   ")

        report_lines.append(f"{'-'*68}")
        report_lines.append(f"  #{i}  Score: {p['opportunity_score']}/10  |  r/{p['subreddit']}")
        report_lines.append(f"{'-'*68}")
        report_lines.append(f"  PAIN:    {p['pain_point_summary']}")
        report_lines.append(f"  WHO:     {p['target_user']}")
        report_lines.append(f"  EMOTION: {p['emotional_intensity']}/10  |  URGENCY: {p['urgency']}/10  |  WTP: {wtp_emoji} {p['willingness_to_pay_signal']}")
        report_lines.append(f"  FREQ:    {p.get('frequency_signal', 'N/A')}")
        report_lines.append(f"")
        report_lines.append(f"  PRODUCT IDEA:")
        report_lines.append(f"  {p['product_opportunity']}")
        report_lines.append(f"")
        report_lines.append(f"  MONETIZATION: {p.get('monetization_angle', 'N/A')}")
        report_lines.append(f"  GAP:          {p.get('gap_in_existing_solutions', 'N/A')}")
        report_lines.append(f"")
        report_lines.append(f"  QUOTE: \"{p.get('key_quote', 'N/A')}\"")
        report_lines.append(f"  LINK:  {p.get('url', 'N/A')}")
        report_lines.append("")

    report_lines.append("=" * 70)
    report_lines.append("  NEXT ACTIONS FOR THE FOUNDER")
    report_lines.append("=" * 70)
    report_lines.append("""
  1. Pick the pain point that resonates most with your background
  2. Click the Reddit link — read every comment in that thread
  3. Find 5-10 commenters who expressed the same frustration
  4. DM them: "I'm researching this exact problem. 15-min call?
     I'll share my findings with you for free."
  5. After 5 calls: if 3+ people say "I'd pay for a solution"
     you have a business. Start building.
  6. Post this report on Twitter with your top 3 findings
     First line: "I analyzed 400+ Reddit posts about SaaS pain.
     Here's what I found (thread)"
""")
    report_lines.append("=" * 70)
    report_lines.append("  Generated by Pain Point Intelligence System")
    report_lines.append("  Would your audience pay $49/mo for weekly reports like this?")
    report_lines.append("=" * 70)

    full_report = "\n".join(report_lines)

    # Save
    report_file = f"pain_point_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(full_report)

    console.print(full_report)
    console.print(f"\n[bold green]Report saved to: {report_file}[/bold green]")

    return full_report, report_file


if __name__ == "__main__":
    generate_report()
