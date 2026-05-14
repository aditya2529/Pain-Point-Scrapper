"""
Load and serve pain-point data from the CSV produced by the analyzer.
"""

import os
import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "analyzed_pain_points.csv"


def load_pain_points():
    """Load analyzed pain points from CSV."""
    if not CSV_PATH.exists():
        return []

    df = pd.read_csv(CSV_PATH)
    df = df.sort_values("opportunity_score", ascending=False)

    # Convert to list of dicts, cleaning NaN
    records = df.fillna("").to_dict("records")

    cleaned = []
    for r in records:
        cleaned.append({
            "id": str(r.get("id", "")),
            "title": str(r.get("title", "")),
            "subreddit": str(r.get("subreddit", "")),
            "score": int(r.get("score", 0)) if r.get("score") else 0,
            "num_comments": int(r.get("num_comments", 0)) if r.get("num_comments") else 0,
            "url": str(r.get("url", "")),
            "opportunity_score": float(r.get("opportunity_score", 0)) if r.get("opportunity_score") else 0,
            "pain_point_summary": str(r.get("pain_point_summary", "")),
            "pain_category": str(r.get("pain_category", "other")),
            "target_user": str(r.get("target_user", "")),
            "emotional_intensity": int(r.get("emotional_intensity", 5)) if r.get("emotional_intensity") else 5,
            "urgency": int(r.get("urgency", 5)) if r.get("urgency") else 5,
            "frequency_signal": str(r.get("frequency_signal", "")),
            "gap_in_existing_solutions": str(r.get("gap_in_existing_solutions", "")),
            "product_opportunity": str(r.get("product_opportunity", "")),
            "monetization_angle": str(r.get("monetization_angle", "")),
            "willingness_to_pay_signal": str(r.get("willingness_to_pay_signal", "medium")),
            "key_quote": str(r.get("key_quote", ""))
        })

    return cleaned


def get_pain_points_for_plan(plan: str = "free"):
    """Return all pain points — tool is now 100% free."""
    return load_pain_points()


def get_stats():
    """Return aggregate stats for the dashboard."""
    points = load_pain_points()
    if not points:
        return {
            "total_pain_points": 0,
            "subreddits": [],
            "categories": {},
            "avg_score": 0,
            "top_score": 0
        }

    subreddits = list(set(p["subreddit"] for p in points))
    categories = {}
    for p in points:
        cat = p.get("pain_category", "other")
        categories[cat] = categories.get(cat, 0) + 1

    scores = [p["opportunity_score"] for p in points if p["opportunity_score"]]

    return {
        "total_pain_points": len(points),
        "subreddits": subreddits,
        "categories": categories,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "top_score": max(scores) if scores else 0
    }
