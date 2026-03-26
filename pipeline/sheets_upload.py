# Google Sheets Job Tracker — Daily Upload Script
#
# Required environment variables:
#   GOOGLE_SPREADSHEET_ID    - your Google Sheet ID
#   GOOGLE_CREDENTIALS_PATH  - path to your google_credentials.json file
#   BASE_PATH                - folder where scored_jobs.csv and cover letter history are
#
# Run with: py -3.12 sheets_upload.py
#
# What this does:
#   1. Reads scored_jobs.csv (from job_scorer.py)
#   2. Reads cover_letters_history.csv (from cover_letter_retriever.py)
#   3. Matches cover letters to scored jobs
#   4. Uploads NEW jobs to the Google Sheet (skips jobs already in the sheet)
#   5. Updates the Stats sheet with today's summary
#
# Run this AFTER:
#   - job_scorer.py (creates scored_jobs.csv)
#   - cover_letter_retriever.py (creates cover_letters_history.csv) — optional
#
# Safe to run multiple times — it only adds NEW jobs (deduplicates by URL).

import gspread
from google.oauth2.service_account import Credentials
import csv
import os
import sys
from datetime import datetime, date

# ============================================================
# CONFIGURATION
# ============================================================

SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")
BASE_PATH = os.environ.get("BASE_PATH", os.getcwd())
SCORED_JOBS_FILE = os.path.join(BASE_PATH, "scored_jobs.csv")
COVER_LETTERS_HISTORY = os.path.join(BASE_PATH, "cover_letters_history.csv")

if not SPREADSHEET_ID:
    print("\n[ERROR] GOOGLE_SPREADSHEET_ID environment variable is not set.")
    print("Set it with: setx GOOGLE_SPREADSHEET_ID \"your-spreadsheet-id\"")
    sys.exit(1)

if not os.path.exists(CREDENTIALS_FILE):
    print(f"\n[ERROR] Credentials file not found at: {CREDENTIALS_FILE}")
    print("Set GOOGLE_CREDENTIALS_PATH to the path of your google_credentials.json file.")
    sys.exit(1)

# ============================================================
# DO NOT EDIT BELOW THIS LINE
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Column order must match the sheet headers from sheets_setup.py
SHEET_COLUMNS = [
    "job_id", "title", "company", "url", "source", "scope", "score",
    "label", "model", "cover_letter", "gap_analysis", "status",
    "date_scraped", "date_applied", "notes"
]


def load_scored_jobs():
    """Load scored_jobs.csv and return list of job dicts."""
    if not os.path.exists(SCORED_JOBS_FILE):
        print(f"\n[ERROR] scored_jobs.csv not found at: {SCORED_JOBS_FILE}")
        print("Run job_scorer.py first to create this file.")
        sys.exit(1)

    jobs = []
    with open(SCORED_JOBS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            jobs.append(row)

    print(f"Loaded {len(jobs)} scored jobs from scored_jobs.csv")
    return jobs


def load_cover_letters():
    """Load cover_letters_history.csv and return dict of url -> cover letter info."""
    cover_letters = {}
    if not os.path.exists(COVER_LETTERS_HISTORY):
        print("No cover_letters_history.csv found (not an error — cover letters are optional)")
        return cover_letters

    with open(COVER_LETTERS_HISTORY, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("job_url", "").strip()
            if url:
                cover_letters[url] = {
                    "model": row.get("model", ""),
                    "docx_path": row.get("docx_path", ""),
                    "scope": row.get("scope_match", row.get("scope", "")),
                }

    print(f"Loaded {len(cover_letters)} cover letters from history")
    return cover_letters


def get_existing_urls(ws):
    """Get all URLs already in the sheet to avoid duplicates."""
    try:
        url_col = ws.col_values(4)  # Column D = URL (1-based index 4)
        existing = set(url.strip() for url in url_col[1:] if url.strip())
        return existing
    except Exception:
        return set()


def determine_source(row):
    """Figure out the job source from available CSV columns."""
    source = row.get("source", "").strip()
    if source:
        return source

    url = row.get("job_url", row.get("url", "")).strip().lower()
    if "linkedin.com" in url:
        return "LinkedIn"
    elif "indeed.com" in url:
        return "Indeed"
    elif "arbeitnow.com" in url:
        return "Arbeitnow"
    else:
        return "Unknown"


def determine_scope(row, cover_letters):
    """Get the scope from cover letter history or from the scored job data."""
    url = row.get("job_url", row.get("url", "")).strip()

    if url in cover_letters and cover_letters[url].get("scope"):
        return cover_letters[url]["scope"]

    scope = row.get("scope_match", row.get("scope", "")).strip()
    if scope:
        return scope

    return ""


def build_row(row, job_counter, cover_letters, today_str):
    """Convert a scored job CSV row into a Google Sheet row."""
    url = row.get("job_url", row.get("url", "")).strip()
    title = row.get("title", "").strip()
    company = row.get("company", "").strip()
    score_str = row.get("score", "0").strip()
    gap = row.get("gaps", row.get("gap_analysis", row.get("reason", ""))).strip()

    try:
        score = int(float(score_str))
    except (ValueError, TypeError):
        score = 0

    if score >= 70:
        label = "apply"
    elif score >= 50:
        label = "maybe"
    else:
        label = "skip"

    cl_info = cover_letters.get(url, {})
    model = cl_info.get("model", "")
    cover_letter_path = cl_info.get("docx_path", "")

    if cover_letter_path:
        cover_letter_name = os.path.basename(cover_letter_path)
    else:
        cover_letter_name = ""

    source = determine_source(row)
    scope = determine_scope(row, cover_letters)

    # Generate a short job ID: MMDD + counter (e.g., 0323-001)
    job_id = f"{today_str.replace('-', '')[4:8]}-{job_counter:03d}"

    sheet_row = [
        job_id,             # A: job_id
        title,              # B: title
        company,            # C: company
        url,                # D: url
        source,             # E: source
        scope,              # F: scope
        score,              # G: score (number for conditional formatting)
        label,              # H: label
        model,              # I: model
        cover_letter_name,  # J: cover_letter
        gap,                # K: gap_analysis
        "new",              # L: status (always starts as "new")
        today_str,          # M: date_scraped
        "",                 # N: date_applied (empty — fill manually)
        ""                  # O: notes (empty — fill manually)
    ]

    return sheet_row


def update_stats(spreadsheet, today_str, total_new, apply_count, maybe_count, skip_count, cl_count):
    """Add a row to the Stats sheet with today's summary."""
    try:
        stats_ws = spreadsheet.worksheet("Stats")

        existing = stats_ws.col_values(1)
        next_row = len(existing) + 1

        stats_row = [
            today_str,
            total_new,
            apply_count,
            maybe_count,
            skip_count,
            cl_count,
            0  # applications_sent starts at 0, fill manually
        ]

        stats_ws.update(f"A{next_row}:G{next_row}", [stats_row])
        print(f"\nStats updated: {total_new} new jobs ({apply_count} apply, {maybe_count} maybe, {skip_count} skip)")
    except Exception as e:
        print(f"\n[WARNING] Could not update Stats sheet: {e}")
        print("This is not critical — your jobs are still uploaded.")


def main():
    # --- Connect ---
    print("\nConnecting to Google Sheets...")
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        ws = spreadsheet.worksheet("Jobs")
        print(f"Connected to: {spreadsheet.title}")
    except Exception as e:
        print(f"\n[ERROR] Could not connect: {e}")
        sys.exit(1)

    # --- Load data ---
    scored_jobs = load_scored_jobs()
    cover_letters = load_cover_letters()

    # --- Deduplicate against sheet ---
    print("\nChecking for duplicates...")
    existing_urls = get_existing_urls(ws)
    print(f"Found {len(existing_urls)} jobs already in the sheet")

    new_jobs = []
    for job in scored_jobs:
        url = job.get("job_url", job.get("url", "")).strip()
        if url and url not in existing_urls:
            new_jobs.append(job)

    if not new_jobs:
        print("\nNo new jobs to upload. Everything in scored_jobs.csv is already in the sheet.")
        print("Run the scrapers + scorer first to get new jobs.")
        return

    print(f"\n{len(new_jobs)} new jobs to upload ({len(scored_jobs) - len(new_jobs)} duplicates skipped)")

    # --- Build rows ---
    today_str = date.today().strftime("%Y-%m-%d")

    try:
        existing_ids = ws.col_values(1)[1:]  # Column A, skip header
        if existing_ids:
            last_id = existing_ids[-1]
            last_counter = int(last_id.split("-")[1])
        else:
            last_counter = 0
    except Exception:
        last_counter = 0

    rows_to_add = []
    apply_count = 0
    maybe_count = 0
    skip_count = 0

    for i, job in enumerate(new_jobs):
        job_counter = last_counter + i + 1
        row = build_row(job, job_counter, cover_letters, today_str)
        rows_to_add.append(row)

        label = row[7]
        if label == "apply":
            apply_count += 1
        elif label == "maybe":
            maybe_count += 1
        else:
            skip_count += 1

    # --- Upload in batches of 100 ---
    print(f"\nUploading {len(rows_to_add)} jobs...")

    all_values = ws.col_values(1)
    next_row = len(all_values) + 1

    batch_size = 100
    uploaded = 0

    for start in range(0, len(rows_to_add), batch_size):
        batch = rows_to_add[start:start + batch_size]
        end_row = next_row + len(batch) - 1
        end_col = chr(ord("A") + len(SHEET_COLUMNS) - 1)  # "O"

        range_str = f"A{next_row}:{end_col}{end_row}"
        ws.update(range_str, batch, value_input_option="USER_ENTERED")

        uploaded += len(batch)
        next_row = end_row + 1
        print(f"  Uploaded {uploaded}/{len(rows_to_add)} jobs...")

    cl_count = sum(1 for row in rows_to_add if row[9])  # cover_letter column

    update_stats(spreadsheet, today_str, len(rows_to_add), apply_count, maybe_count, skip_count, cl_count)

    # --- Summary ---
    print("\n" + "=" * 50)
    print("UPLOAD COMPLETE!")
    print("=" * 50)
    print(f"\n  New jobs added:      {len(rows_to_add)}")
    print(f"  Apply (70+):         {apply_count}")
    print(f"  Maybe (50-69):       {maybe_count}")
    print(f"  Skip (<50):          {skip_count}")
    print(f"  With cover letters:  {cl_count}")
    print(f"  Duplicates skipped:  {len(scored_jobs) - len(new_jobs)}")
    print(f"\nOpen your sheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
    print("\nDuring your morning routine:")
    print("  1. Sort by score (column G, highest first)")
    print("  2. Apply to jobs with cover letters ready")
    print("  3. Change status dropdown from 'new' to 'applied'")
    print("  4. Fill in 'date_applied' column")


if __name__ == "__main__":
    main()
