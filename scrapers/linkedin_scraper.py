"""
SCRIPT 1b — LinkedIn Scraper (OPTIONAL but recommended)
Scrapes LinkedIn with all 28 search terms, using long random delays
to look like a real human browsing jobs.

Takes ~25-40 minutes. Run it in the background while you work.

Your LinkedIn account is NOT at risk — JobSpy does not log into LinkedIn.
TIP: Don't have LinkedIn open in Chrome while this runs.

Required environment variables:
    BASE_PATH   - folder where output CSV will be saved

Usage:
    py -3.12 linkedin_scraper.py

Output:
    raw_jobs_linkedin.csv in BASE_PATH folder
"""

from jobspy import scrape_jobs
import pandas as pd
from datetime import datetime
import os
import time
import random

# ============================================================
# CONFIGURATION
# ============================================================

LOCATION = "Germany"
RESULTS_PER_TERM = 15       # Moderate volume per term
HOURS_OLD = 24

# Delays to look human (in seconds)
MIN_DELAY = 30              # Minimum seconds between searches
MAX_DELAY = 90              # Maximum seconds between searches
MIN_SCOPE_PAUSE = 120       # Minimum seconds pause between scopes (2 min)
MAX_SCOPE_PAUSE = 300       # Maximum seconds pause between scopes (5 min)

# Safety: stop if LinkedIn seems to be blocking
MAX_CONSECUTIVE_EMPTY = 3   # Stop if 3 searches in a row return 0 results

# Where to save results
BASE_PATH = os.environ.get("BASE_PATH", os.getcwd())
OUTPUT_FILE = os.path.join(BASE_PATH, "raw_jobs_linkedin.csv")

# All 28 search terms across 4 scopes (same as the main scraper)
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

def scrape_linkedin():
    """Scrape LinkedIn with human-like delays between searches."""
    all_jobs = []
    total_terms = sum(len(terms) for terms in SCOPES.values())
    current = 0
    consecutive_empty = 0
    scope_names = list(SCOPES.keys())

    # Randomize the order of scopes each run
    random.shuffle(scope_names)

    for scope_idx, scope_name in enumerate(scope_names):
        search_terms = list(SCOPES[scope_name])

        # Randomize order of terms within each scope
        random.shuffle(search_terms)

        # Pause between scopes (not before the first one)
        if scope_idx > 0:
            pause = random.uniform(MIN_SCOPE_PAUSE, MAX_SCOPE_PAUSE)
            print(f"\n    Pausing {pause:.0f} seconds between scopes (like changing search focus)...")
            time.sleep(pause)

        print(f"\n--- Scope: {scope_name} ({len(search_terms)} terms) ---")

        for term in search_terms:
            current += 1

            # Random delay between searches (not before the very first one)
            if current > 1:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                print(f"    Waiting {delay:.0f} seconds...")
                time.sleep(delay)

            print(f"[{current}/{total_terms}] LinkedIn: '{term}'...")

            try:
                jobs = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=term,
                    location=LOCATION,
                    results_wanted=RESULTS_PER_TERM,
                    hours_old=HOURS_OLD,
                )

                jobs["scope"] = scope_name
                jobs["search_term_used"] = term

                if len(jobs) == 0:
                    consecutive_empty += 1
                    print(f"    WARNING: 0 results (consecutive empty: {consecutive_empty}/{MAX_CONSECUTIVE_EMPTY})")

                    if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                        print()
                        print("!" * 60)
                        print(f"SAFETY STOP: {MAX_CONSECUTIVE_EMPTY} consecutive empty results.")
                        print("LinkedIn may be rate limiting. Stopping LinkedIn scraper.")
                        print("Your Indeed results are unaffected — just run job_filter.py.")
                        print("Try again tomorrow.")
                        print("!" * 60)
                        break
                else:
                    consecutive_empty = 0  # Reset counter on success
                    all_jobs.append(jobs)
                    print(f"    Found {len(jobs)} jobs")

            except Exception as e:
                consecutive_empty += 1
                print(f"    ERROR: {e}")
                print(f"    (consecutive failures: {consecutive_empty}/{MAX_CONSECUTIVE_EMPTY})")

                if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                    print()
                    print("!" * 60)
                    print(f"SAFETY STOP: {MAX_CONSECUTIVE_EMPTY} consecutive errors.")
                    print("LinkedIn is blocking. Stopping.")
                    print("!" * 60)
                    break
                continue

        # Check if we hit the safety stop
        if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
            break

    if not all_jobs:
        print("\nNo LinkedIn jobs found. This is OK — run job_filter.py with Indeed results only.")
        return pd.DataFrame()

    combined = pd.concat(all_jobs, ignore_index=True)
    return combined


def main():
    start_time = datetime.now()

    total_terms = sum(len(t) for t in SCOPES.values())
    est_min = int(total_terms * (MIN_DELAY + MAX_DELAY) / 2 / 60)
    est_max = int(total_terms * (MIN_DELAY + MAX_DELAY) / 2 / 60) + 10

    print("=" * 60)
    print("SCRIPT 1b — LINKEDIN SCRAPER")
    print(f"Date: {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Location: {LOCATION}")
    print(f"Search terms: {total_terms} (all 4 scopes)")
    print(f"Results per term: {RESULTS_PER_TERM}")
    print(f"Delay between searches: {MIN_DELAY}-{MAX_DELAY} seconds")
    print(f"Pause between scopes: {MIN_SCOPE_PAUSE//60}-{MAX_SCOPE_PAUSE//60} minutes")
    print(f"Estimated total time: ~{est_min}-{est_max} minutes")
    print()
    print("NOTE: Your LinkedIn account is safe — this does not log in.")
    print("TIP: Don't have LinkedIn open in Chrome while this runs.")
    print("You can work on other things while this runs in the background.")
    print("=" * 60)

    jobs = scrape_linkedin()

    if jobs.empty:
        print("\nNo results saved. Exiting.")
        return

    jobs.to_csv(OUTPUT_FILE, index=False)

    elapsed = datetime.now() - start_time
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)

    print()
    print("=" * 60)
    print(f"LINKEDIN SCRAPING COMPLETE")
    print(f"Total LinkedIn jobs: {len(jobs)}")
    print()
    print("Breakdown by scope:")
    for scope_name in SCOPES:
        count = len(jobs[jobs["scope"] == scope_name])
        if count > 0:
            print(f"  {scope_name}: {count} jobs")
    print()
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"Time taken: {minutes} min {seconds} sec")
    print()
    print("Next step: run arbeitnow_scraper.py (optional), then job_filter.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
