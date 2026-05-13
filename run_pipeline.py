"""
Pain Point Intelligence System — Full Pipeline
Run this single file to scrape, analyze, and generate your report.
"""

import os
import sys
from rich.console import Console
from rich.panel import Panel
from datetime import datetime

console = Console()

def check_env():
    """Verify all required env vars are present"""
    required = [
        "GROQ_API_KEY"
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        console.print(f"\n[bold red]Missing environment variables: {', '.join(missing)}[/bold red]")
        console.print("[yellow]Please fill in your .env file before running.[/yellow]")
        console.print("[dim]See .env.example for guidance.[/dim]\n")
        sys.exit(1)

def main():
    from dotenv import load_dotenv
    load_dotenv()
    check_env()

    console.print(Panel.fit(
        "[bold magenta]PAIN POINT INTELLIGENCE SYSTEM[/bold magenta]\n"
        "[dim]SaaS & Startup Edition - Powered by Reddit + Groq AI[/dim]",
        border_style="magenta"
    ))
    console.print(f"[dim]Started at {datetime.now().strftime('%H:%M:%S')}[/dim]\n")

    # Phase 1: Scrape
    console.rule("[bold blue]PHASE 1 — Reddit Scraping[/bold blue]")
    from scraper import run_scraper
    df_raw = run_scraper()

    if df_raw is None or df_raw.empty:
        console.print("[red]Scraping returned no data. Check credentials and try again.[/red]")
        sys.exit(1)

    # Phase 2: Analyze
    console.rule("[bold blue]PHASE 2 — AI Analysis (Claude)[/bold blue]")
    from analyzer import run_analyzer
    df_analyzed = run_analyzer(sample_size=100)

    if df_analyzed is None or df_analyzed.empty:
        console.print("[red]Analysis returned no results. Check API key and data quality.[/red]")
        sys.exit(1)

    # Phase 3: Report
    console.rule("[bold blue]PHASE 3 — Report Generation[/bold blue]")
    from report_generator import generate_report
    result = generate_report()

    if result:
        _, report_file = result
        console.print(Panel.fit(
            f"[bold green]PIPELINE COMPLETE![/bold green]\n\n"
            f"[white]Files generated:[/white]\n"
            f"  raw_pain_points.csv\n"
            f"  analyzed_pain_points.csv\n"
            f"  {report_file}\n\n"
            f"[bold yellow]NOW: Post your top 3 findings on Twitter/Reddit[/bold yellow]\n"
            f"[dim]Ask: 'Would you pay $49/mo for this weekly?' [/dim]",
            border_style="green"
        ))

if __name__ == "__main__":
    main()
