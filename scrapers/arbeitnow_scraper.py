"""
SCRIPT 1c — Arbeitnow Scraper (OPTIONAL but recommended)
Fetches English-language jobs in Germany from Arbeitnow's free API.
No scraping needed — this is an official, public API. Zero blocking risk.

Takes ~10-30 seconds. Very fast.

Required environment variables:
    BASE_PATH   - folder where output CSV will be saved

Usage:
    py -3.12 arbeitnow_scraper.py

Output:
    raw_jobs_arbeitnow.csv in BASE_PATH folder
"""

import re
import os
import time
from datetime import datetime, timedelta

import requests
import pandas as pd

# ============================================================
# CONFIGURATION
# ============================================================

# Where to save results
BASE_PATH = os.environ.get("BASE_PATH", os.getcwd())
OUTPUT_FILE = os.path.join(BASE_PATH, "raw_jobs_arbeitnow.csv")

# Arbeitnow API base URL (free, no API key needed)
API_URL = "https://www.arbeitnow.com/api/job-board-api"

# How many pages to fetch (100 jobs per page)
MAX_PAGES = 10  # Up to 1000 jobs total

# Only keep jobs posted within this many days
MAX_DAYS_OLD = 7


# ============================================================
# SCRAPING LOGIC — No need to edit below this line
# ============================================================

# Keywords to match against job titles (at least one must match)
# These cover all 4 scopes
RELEVANT_KEYWORDS = [
    # Scope 1: Business x GenAI
    "ai ", "artificial intelligence", "genai", "gen ai",
    "digital transformation", "change management",
    "machine learning", "automation",

    # Scope 2: BI & Strategy Analytics
    "business intelligence", " bi ", "data analyst",
    "analytics", "strategy", "insights",

    # Scope 3: Chief of Staff
    "chief of staff", "founder", "coo", "operations",

    # Scope 4: Tech x Business Consulting
    "consultant", "consulting", "advisory",
    "transformation", "technology",

    # General matches
    "product manager", "project manager",
    "business analyst", "strategist",
]


def fetch_all_jobs():
    """Fetch jobs from Arbeitnow API with pagination."""
    all_jobs = []

    for page in range(1, MAX_PAGES + 1):
        print(f"  Fetching page {page}...")

        try:
            response = requests.get(
                API_URL,
                params={"page": page},
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            jobs = data.get("data", [])
            if not jobs:
                print(f"  No more jobs on page {page}. Stopping.")
                break

            all_jobs.extend(jobs)
            print(f"  Got {len(jobs)} jobs (total so far: {len(all_jobs)})")

            # Small delay between pages to be polite
            time.sleep(1)

        except Exception as e:
            print(f"  ERROR on page {page}: {e}")
            break

    return all_jobs


def filter_relevant_jobs(jobs):
    """Filter to only keep jobs relevant to your 4 scopes."""
    cutoff_date = datetime.now() - timedelta(days=MAX_DAYS_OLD)

    relevant = []
    for job in jobs:
        title = (job.get("title") or "").lower()
        description = (job.get("description") or "").lower()

        # Check if the job is recent enough
        created_at = job.get("created_at")
        if created_at:
            job_date = datetime.fromtimestamp(created_at)
            if job_date < cutoff_date:
                continue

        # Check if title or description matches any relevant keyword
        combined = title + " " + description
        if any(kw in combined for kw in RELEVANT_KEYWORDS):
            relevant.append(job)

    return relevant


def convert_to_dataframe(jobs):
    """Convert Arbeitnow API format to match the same CSV format as the other scrapers."""
    rows = []
    for job in jobs:
        # Determine scope based on which keywords matched
        title = (job.get("title") or "").lower()
        description = (job.get("description") or "").lower()
        combined = title + " " + description

        scope = "Unknown"
        if any(kw in combined for kw in ["ai ", "genai", "gen ai", "artificial intelligence", "digital transformation", "machine learning", "automation", "change management"]):
            scope = "Business x GenAI"
        elif any(kw in combined for kw in ["business intelligence", " bi ", "data analyst", "analytics", "strategy", "insights", "strategist"]):
            scope = "BI & Strategy Analytics"
        elif any(kw in combined for kw in ["chief of staff", "founder", "coo"]):
            scope = "Chief of Staff"
        elif any(kw in combined for kw in ["consultant", "consulting", "advisory", "transformation"]):
            scope = "Tech x Business Consulting"

        # Convert timestamp to date
        created_at = job.get("created_at")
        date_posted = ""
        if created_at:
            date_posted = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d")

        # Strip HTML from description
        desc = job.get("description", "")
        desc_clean = re.sub(r'<[^>]+>', ' ', desc)
        desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()

        rows.append({
            "site": "arbeitnow",
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": job.get("location", ""),
            "job_url": job.get("url", ""),
            "description": desc_clean,
            "date_posted": date_posted,
            "is_remote": job.get("remote", False),
            "scope": scope,
            "search_term_used": "arbeitnow_api",
        })

    return pd.DataFrame(rows)


def main():
    start_time = datetime.now()

    print("=" * 60)
    print("SCRIPT 1c — ARBEITNOW SCRAPER")
    print(f"Date: {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Source: Arbeitnow.com (free API, English jobs in Germany)")
    print(f"Max pages: {MAX_PAGES} (100 jobs per page)")
    print(f"Max age: {MAX_DAYS_OLD} days")
    print("=" * 60)
    print()

    # Step 1: Fetch all jobs from API
    print("Fetching jobs from Arbeitnow API...")
    all_jobs = fetch_all_jobs()
    print(f"\nTotal jobs fetched: {len(all_jobs)}")

    if not all_jobs:
        print("No jobs found. Exiting.")
        return

    # Step 2: Filter to relevant jobs
    print("\nFiltering for relevant jobs...")
    relevant = filter_relevant_jobs(all_jobs)
    print(f"Relevant to your scopes: {len(relevant)} out of {len(all_jobs)}")

    if not relevant:
        print("No relevant jobs found. Exiting.")
        return

    # Step 3: Convert to DataFrame
    df = convert_to_dataframe(relevant)

    # Step 4: Save
    df.to_csv(OUTPUT_FILE, index=False)

    elapsed = datetime.now() - start_time
    seconds = int(elapsed.total_seconds())

    print()
    print("=" * 60)
    print(f"ARBEITNOW SCRAPING COMPLETE")
    print(f"Total relevant jobs: {len(df)}")
    print()
    print("Breakdown by scope:")
    for scope in df["scope"].unique():
        count = len(df[df["scope"] == scope])
        print(f"  {scope}: {count} jobs")
    print()
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"Time taken: {seconds} seconds")
    print()
    print("Next step: run job_filter.py to merge and filter all results.")
    print("=" * 60)


if __name__ == "__main__":
    main()
