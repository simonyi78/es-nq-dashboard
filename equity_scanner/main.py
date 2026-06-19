"""Orchestrator: screens equities, checks Google Trends interest, scores setups,
builds a PDF analyst report, and posts results to Discord.

Reads the ticker universe from tickers.txt, runs equity_filter.screen_universe()
to find $200M-$2B caps in a 50-day consolidation base, layers in Google Trends
data (scanner.fetch_trends), computes a Lift-Off Potential Score and analyst
write-up per candidate (scoring.py), builds a PDF report (report.py), and POSTs
a markdown summary table + the PDF to the webhook URL in DISCORD_WEBHOOK_URL.
"""

import asyncio
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

from equity_filter import fetch_universe, screen_universe
from scanner import fetch_trends
from scoring import compute_score, format_market_cap, generate_industry_section, generate_writeup
from report import build_report

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
DISCORD_CHUNK_SIZE = 1900  # stay under Discord's 2000-char message limit


def build_markdown_table(rows: list[dict], scores: list[dict]) -> str:
    if not rows:
        return "_No matches today._"

    headers = ["Ticker", "Mkt Cap", "Price", "50D Range %", "Trend", "Trend Chg %", "Score", "Rating"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row, score_info in zip(rows, scores):
        trend_latest = row.get("trend_latest")
        trend_change_pct = row.get("trend_change_pct")
        cells = [
            row["ticker"],
            format_market_cap(row["market_cap"]),
            f"${row['price']:.2f}",
            f"{row['range_50d_pct']:.1f}%",
            f"{trend_latest:.0f}" if trend_latest is not None else "-",
            f"{trend_change_pct:+.1f}%" if trend_change_pct is not None else "-",
            f"{score_info['score']:.1f}",
            score_info["rating"],
        ]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def post_to_discord(content: str, file_path: str | None = None) -> None:
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL not set; printing output instead:\n")
        print(content)
        if file_path:
            print(f"\n(PDF report saved to {file_path})")
        return

    if file_path:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/pdf")}
            payload = {"payload_json": json.dumps({"content": content})}
            resp = requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
            resp.raise_for_status()
        return

    for i in range(0, len(content), DISCORD_CHUNK_SIZE):
        chunk = content[i : i + DISCORD_CHUNK_SIZE]
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": f"```{chunk}```"})
        resp.raise_for_status()


async def run() -> None:
    tickers = fetch_universe()
    print(f"Screening {len(tickers)} live candidates for $200M-$2B caps in a 50-day base...")

    candidates = screen_universe(tickers)
    print(f"Found {len(candidates)} candidate(s).")

    scores = []
    writeups = []
    industry_sections = []

    if candidates:
        trends = await fetch_trends([c["name"] for c in candidates])
        trend_by_name = {t["keyword"]: t for t in trends}
        for c in candidates:
            trend = trend_by_name.get(c["name"], {})
            c["trend_latest"] = trend.get("latest")
            c["trend_change_pct"] = trend.get("change_pct")

        for c in candidates:
            score_info = compute_score(c)
            scores.append(score_info)
            writeups.append(generate_writeup(c, score_info))
            industry_sections.append(generate_industry_section(c, candidates))

    table = build_markdown_table(candidates, scores)
    message = f"**Equity Scanner - {len(candidates)} match(es)**\n\n{table}"

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"scan_{datetime.now():%Y%m%d_%H%M%S}.pdf")
    build_report(candidates, scores, writeups, industry_sections, report_path)
    print(f"PDF report written to {report_path}")

    post_to_discord(message, file_path=report_path)


if __name__ == "__main__":
    asyncio.run(run())
