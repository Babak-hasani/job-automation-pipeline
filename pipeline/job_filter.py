"""
SCRIPT 2 — Job Filter
Reads and merges results from all scrapers:
  - raw_jobs.csv (Script 1 — Indeed)
  - raw_jobs_linkedin.csv (Script 1b — LinkedIn, optional)
  - raw_jobs_arbeitnow.csv (Script 1c — Arbeitnow, optional)
  - raw_jobs_companies.csv (Script 1d — Company career pages, optional)

Applies filters and saves clean results.
You can re-run this as many times as you want without re-scraping.

Required environment variables:
    BASE_PATH   - folder where CSV files are read from and saved to

Usage:
    py -3.12 job_filter.py

Output:
    filtered_jobs.csv in BASE_PATH folder
"""

import pandas as pd
from datetime import datetime
import os
import glob

# ============================================================
# CONFIGURATION — Tweak these settings and re-run instantly
# ============================================================

# File paths
BASE_PATH = os.environ.get("BASE_PATH", os.getcwd())
OUTPUT_FILE = os.path.join(BASE_PATH, "filtered_jobs.csv")

# Minimum job description length in characters
# 800 characters = roughly half a page of text
MIN_DESCRIPTION_LENGTH = 800

# Title keywords to EXCLUDE (too senior, too junior, or irrelevant fields)
# These are checked as substrings, case-insensitive
EXCLUDE_TITLES = [
    # Too junior
    "intern",
    "werkstudent",
    "working student",
    "praktikant",
    "praktikum",

    # Too senior
    "senior director",
    "vice president",
    "vp ",
    " vp",
    "principal",
    "partner",
    "c-level",
    "cto",
    "cfo",
    "ceo",

    # Engineering / technical roles (not your profile)
    "engineer",
    "engineering",
    "techniker",
    "technician",
    "architect",
    "developer",
    "devops",
    "sysadmin",
    "system administrator",

    # Finance / accounting roles
    "accountant",
    "accounting",
    "controller",
    "controlling",
    "bookkeep",
    "lohnbuchhal",
    "revenue accountant",
    "tax ",
    "audit",

    # Medical / pharma / health
    "nurse",
    "doctor",
    "clinical",
    "medical",
    "pharma",
    "health manager",
    "health assistant",
    "animal health",
    "krankentransport",
    "therapist",

    # Operations / logistics / manual
    "warehouse",
    "production associate",
    "driver",
    "mechanic",
    "electrician",
    "logistics specialist",
    "supply chain",
    "procurement",

    # Design / creative (not your profile)
    "ui/ux",
    "ux designer",
    "ui designer",
    "graphic design",
    "art director",

    # Admin / assistant roles
    "assistant",
    "assistenz",
    "secretary",
    "receptionist",
    "office manager",

    # Construction / trades
    "holzbau",
    "medientechnik",
    "construction",
    "bauingenieur",
    "bauleiter",

    # Other irrelevant
    "cook",
    "guard",
    "security specialist",
    "facility",
    "janitor",
    "cleaner",
]

# German language markers — if a job description contains these,
# it is written in German and gets removed (Layer 1 filter).
# The LLM scoring step (Layer 2) will catch any remaining edge cases later.
# LinkedIn jobs skip this filter since they have no descriptions.
GERMAN_MARKERS = [
    # Common German JD section headers
    "aufgaben",
    "qualifikation",
    "ihr profil",
    "wir bieten",
    "ihre aufgaben",
    "anforderungen",
    "was wir bieten",
    "dein profil",
    "deine aufgaben",
    "was du mitbringst",
    "was sie mitbringen",
    "was sie erwartet",
    "das erwartet dich",
    "das bringst du mit",
    "über uns",
    "wir suchen",
    "stellenbeschreibung",
    "ihre vorteile",
    "deine vorteile",
    "bewerbung",
    "jetzt bewerben",
    "arbeitgeber",
    "berufserfahrung",
    "festanstellung",
    "vollzeit",
    "teilzeit",
    "unbefristet",
]

# Title keywords to KEEP — at least one of these must appear
# Leave this list EMPTY to skip this filter (keep all titles that pass exclusion)
KEEP_TITLES = []

# Companies to BLACKLIST — skip jobs from these companies
# Add companies you have already rejected or do not want to work for
BLACKLIST_COMPANIES = []


# ============================================================
# FILTER LOGIC — No need to edit below this line
# ============================================================

def load_and_merge_all_sources():
    """Load and merge results from all available scrapers.
    Auto-detects all raw_jobs*.csv files in BASE_PATH."""
    dataframes = []

    # Auto-detect all raw_jobs*.csv files
    pattern = os.path.join(BASE_PATH, "raw_jobs*.csv")
    found_files = glob.glob(pattern)

    if not found_files:
        print(f"WARNING: No raw_jobs*.csv files found in {BASE_PATH}")
        print("Make sure you ran at least one scraper script first.")
        return pd.DataFrame()

    for filepath in sorted(found_files):
        filename = os.path.basename(filepath)
        try:
            df = pd.read_csv(filepath)
            print(f"Loaded {len(df)} jobs from {filename}")
            dataframes.append(df)
        except Exception as e:
            print(f"WARNING: Could not read {filename}: {e}")

    if not dataframes:
        print("\nERROR: No data files could be read.")
        return pd.DataFrame()

    combined = pd.concat(dataframes, ignore_index=True)
    print(f"\nCombined total: {len(combined)} raw jobs from {len(dataframes)} source(s)")
    return combined


def deduplicate(df):
    """Remove duplicate jobs based on job URL, then by title + company."""
    if df.empty:
        return df

    before = len(df)

    # First: exact URL duplicates
    df = df.drop_duplicates(subset=["job_url"], keep="first")
    after_url = len(df)
    print(f"[Filter 1a] URL dedup: {before} -> {after_url} (removed {before - after_url} exact URL duplicates)")

    # Second: same title + same company = likely the same job on different platforms
    before_title = len(df)
    df = df.drop_duplicates(subset=["title", "company"], keep="first")
    after_title = len(df)
    print(f"[Filter 1b] Title+Company dedup: {before_title} -> {after_title} (removed {before_title - after_title} cross-platform duplicates)")

    return df


def filter_by_title(df):
    """Filter out jobs with unwanted title keywords."""
    if df.empty:
        return df

    before = len(df)

    for keyword in EXCLUDE_TITLES:
        df = df[~df["title"].str.lower().str.contains(keyword, na=False)]

    excluded = before - len(df)
    print(f"[Filter 2] Title exclusion: {before} -> {len(df)} (removed {excluded} irrelevant titles)")

    if KEEP_TITLES:
        before_keep = len(df)
        mask = df["title"].str.lower().apply(
            lambda t: any(kw in t for kw in KEEP_TITLES) if pd.notna(t) else False
        )
        df = df[mask]
        removed = before_keep - len(df)
        print(f"[Filter 2b] Title inclusion: {before_keep} -> {len(df)} (removed {removed} missing required keywords)")

    return df


def filter_by_description(df):
    """Remove jobs with very short or empty descriptions.
    LinkedIn jobs are excluded from this filter because LinkedIn doesn't
    return descriptions in search results. Their descriptions will be
    reviewed manually during the morning routine.
    """
    if df.empty:
        return df

    before = len(df)

    # Split: LinkedIn jobs skip this filter, others must pass it
    linkedin_jobs = df[df["site"] == "linkedin"]
    other_jobs = df[df["site"] != "linkedin"]

    # Apply description filter only to non-LinkedIn jobs
    other_jobs = other_jobs[other_jobs["description"].str.len().fillna(0) >= MIN_DESCRIPTION_LENGTH]

    # Recombine
    df = pd.concat([other_jobs, linkedin_jobs], ignore_index=True)
    after = len(df)
    removed = before - after
    print(f"[Filter 3] Description length (min {MIN_DESCRIPTION_LENGTH} chars): {before} -> {after} (removed {removed} junk/vague)")
    print(f"           ({len(linkedin_jobs)} LinkedIn jobs kept without description — review manually)")
    return df


def filter_by_company(df):
    """Remove jobs from blacklisted companies."""
    if df.empty or not BLACKLIST_COMPANIES:
        return df

    before = len(df)
    blacklist_lower = [c.lower() for c in BLACKLIST_COMPANIES]
    df = df[~df["company"].str.lower().isin(blacklist_lower)]
    after = len(df)
    removed = before - after
    print(f"[Filter 4] Company blacklist: {before} -> {after} (removed {removed} blacklisted)")
    return df


def filter_by_language(df):
    """Remove German-language job descriptions (Layer 1 — keyword-based).
    This catches ~85-90% of German JDs. The remaining edge cases will be
    caught by the LLM scoring step (Layer 2) which checks both language
    and German fluency requirements.
    LinkedIn jobs skip this filter since they have no descriptions.
    """
    if df.empty:
        return df

    before = len(df)

    # Split: LinkedIn jobs skip this filter
    linkedin_jobs = df[df["site"] == "linkedin"]
    other_jobs = df[df["site"] != "linkedin"]

    # Check each non-LinkedIn job's description for German markers
    def is_german(desc):
        if pd.isna(desc):
            return False
        desc_lower = str(desc).lower()
        # If 2 or more German markers appear, it's very likely a German JD
        matches = sum(1 for marker in GERMAN_MARKERS if marker in desc_lower)
        return matches >= 2

    german_mask = other_jobs["description"].apply(is_german)
    german_count = german_mask.sum()
    other_jobs = other_jobs[~german_mask]

    # Recombine
    df = pd.concat([other_jobs, linkedin_jobs], ignore_index=True)
    after = len(df)
    print(f"[Filter 5] German language (keyword check): {before} -> {after} (removed {german_count} German JDs)")
    print(f"           ({len(linkedin_jobs)} LinkedIn jobs kept — language checked manually)")
    print(f"           (Remaining edge cases caught by LLM scoring later)")
    return df


def print_summary(df):
    """Print a detailed summary of the filtered results."""
    print()
    print("=" * 60)
    print(f"FILTERING COMPLETE: {len(df)} jobs ready for scoring")
    print()

    print("Breakdown by scope:")
    if "scope" in df.columns:
        for scope in df["scope"].unique():
            count = len(df[df["scope"] == scope])
            print(f"  {scope}: {count} jobs")

    print()
    print("Breakdown by source:")
    if "site" in df.columns:
        for source in df["site"].unique():
            count = len(df[df["site"] == source])
            print(f"  {source}: {count} jobs")

    print()
    print("Top 10 companies:")
    if "company" in df.columns:
        top = df["company"].value_counts().head(10)
        for company, count in top.items():
            print(f"  {company}: {count} jobs")

    print()
    print(f"Saved to: {OUTPUT_FILE}")
    print("=" * 60)


def main():
    print("=" * 60)
    print("SCRIPT 2 — JOB FILTER")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Min description length: {MIN_DESCRIPTION_LENGTH} chars")
    print(f"Excluded title keywords: {len(EXCLUDE_TITLES)}")
    print(f"German language markers: {len(GERMAN_MARKERS)}")
    print(f"Blacklisted companies: {len(BLACKLIST_COMPANIES)}")
    print("=" * 60)
    print()

    # Step 1: Load and merge all sources
    jobs = load_and_merge_all_sources()
    if jobs.empty:
        return

    # Step 2: Deduplicate (by URL, then by title+company)
    print()
    jobs = deduplicate(jobs)

    # Step 3: Filter by title
    jobs = filter_by_title(jobs)

    # Step 4: Filter by description length
    jobs = filter_by_description(jobs)

    # Step 5: Filter by German language (Layer 1 — Python keywords)
    jobs = filter_by_language(jobs)

    # Step 6: Filter by company blacklist
    jobs = filter_by_company(jobs)

    # Step 7: Save filtered results
    jobs.to_csv(OUTPUT_FILE, index=False)

    # Step 8: Print summary
    print_summary(jobs)


if __name__ == "__main__":
    main()
