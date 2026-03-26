"""
SCRIPT 1 — Job Scraper (Indeed)
Scrapes Indeed across 4 career scopes.
Saves raw results to a CSV file for Script 2 to filter.

Required environment variables:
    BASE_PATH   - folder where output CSV will be saved

Usage:
    py -3.12 jobspy_scraper.py

Output:
    raw_jobs.csv in BASE_PATH folder
"""

from jobspy import scrape_jobs
import pandas as pd
from datetime import datetime
import os

# ============================================================
# CONFIGURATION — Edit these settings to match your preferences
# ============================================================

LOCATION = "Germany"
COUNTRY_INDEED = "Germany"
RESULTS_PER_TERM = 50
HOURS_OLD = 24
SOURCES = ["indeed"]

# Where to save the raw results
BASE_PATH = os.environ.get("BASE_PATH", os.getcwd())
OUTPUT_FILE = os.path.join(BASE_PATH, "raw_jobs.csv")

# Your 4 career scopes and their search terms (28 total)
SCOPES = {
    "Business x GenAI": [
        "AI Strategy",
        "GenAI Consultant",
        "AI Transformation",
        "Digital Transformation AI",
        "AI Business Consultant",
        "AI Change Management",
        "AI Implementation Manager",
    ],
    "BI & Strategy Analytics": [
        "Business Intelligence Analyst",
        "BI Analyst",
        "Data Analyst Strategy",
        "Business Intelligence Consultant",
        "Analytics Manager",
        "Strategy Analyst",
        "Insights Analyst",
    ],
    "Chief of Staff": [
        "Chief of Staff",
        "Founder Associate",
        "Founders Associate",
        "CEO Office",
        "Head of Staff",
        "Business Operations Associate",
        "Strategic Operations",
    ],
    "Tech x Business Consulting": [
        "Technology Consultant",
        "Digital Consultant",
        "Management Consultant Technology",
        "IT Strategy Consultant",
        "Business Technology Analyst",
        "Digital Strategy Consultant",
        "Transformation Consultant",
    ],
}


# ============================================================
# SCRAPING LOGIC — No need to edit below this line
# ============================================================

def scrape_all_scopes():
    """Scrape all search terms across all scopes."""
    all_jobs = []
    total_terms = sum(len(terms) for terms in SCOPES.values())
    current = 0

    for scope_name, search_terms in SCOPES.items():
        print(f"\n--- Scope: {scope_name} ({len(search_terms)} terms) ---")

        for term in search_terms:
            current += 1
            print(f"[{current}/{total_terms}] Scraping: '{term}'...")

            try:
                jobs = scrape_jobs(
                    site_name=SOURCES,
                    search_term=term,
                    location=LOCATION,
                    results_wanted=RESULTS_PER_TERM,
                    hours_old=HOURS_OLD,
                    country_indeed=COUNTRY_INDEED,
                )

                jobs["scope"] = scope_name
                jobs["search_term_used"] = term

                all_jobs.append(jobs)
                print(f"    Found {len(jobs)} jobs")

            except Exception as e:
                print(f"    ERROR scraping '{term}': {e}")
                continue

    if not all_jobs:
        print("\nNo jobs found across any search terms.")
        return pd.DataFrame()

    combined = pd.concat(all_jobs, ignore_index=True)
    return combined


def main():
    start_time = datetime.now()

    print("=" * 60)
    print("SCRIPT 1 — JOB SCRAPER (Indeed)")
    print(f"Date: {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Location: {LOCATION}")
    print(f"Sources: {', '.join(SOURCES)}")
    print(f"Scopes: {len(SCOPES)} scopes, {sum(len(t) for t in SCOPES.values())} search terms")
    print(f"Results per term: {RESULTS_PER_TERM}")
    print("=" * 60)

    jobs = scrape_all_scopes()

    if jobs.empty:
        print("\nNo jobs found. Exiting.")
        return

    jobs.to_csv(OUTPUT_FILE, index=False)

    elapsed = datetime.now() - start_time
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)

    print()
    print("=" * 60)
    print(f"SCRAPING COMPLETE")
    print(f"Total raw jobs: {len(jobs)}")
    print()
    print("Breakdown by scope:")
    for scope_name in SCOPES:
        count = len(jobs[jobs["scope"] == scope_name])
        print(f"  {scope_name}: {count} jobs")
    print()
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"Time taken: {minutes} min {seconds} sec")
    print()
    print("Next step: run linkedin_scraper.py, then arbeitnow_scraper.py,")
    print("then job_filter.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
