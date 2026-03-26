# job_scorer.py - Score filtered jobs using DeepSeek V3.2 API
# ============================================================
# Reads filtered_jobs.csv, scores each job against your CV,
# and outputs scored_jobs.csv sorted by score (highest first).
#
# Required environment variables:
#   DEEPSEEK_API_KEY   - your DeepSeek API key
#   BASE_PATH          - folder where CSV files are read from and saved to
#
# Usage:  py -3.12 job_scorer.py
# First:  py -3.12 -m pip install openai
#
# IMPORTANT: You must set your DeepSeek API key before running.
# Open Command Prompt and run:
#     setx DEEPSEEK_API_KEY "sk-your-key-here"
# Then CLOSE and REOPEN Command Prompt before running the script.

import os
import sys
import csv
import json
import time
import re
from pathlib import Path

# Force UTF-8 output so special characters in job titles don't crash on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Check for API key early ──────────────────────────────────────────────────
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
if not API_KEY:
    print("=" * 60)
    print("ERROR: DEEPSEEK_API_KEY not found!")
    print()
    print("To fix this, open Command Prompt and run:")
    print('  setx DEEPSEEK_API_KEY "sk-your-key-here"')
    print()
    print("Then CLOSE and REOPEN Command Prompt, and run this script again.")
    print("=" * 60)
    sys.exit(1)

# ── Check for openai package ────────────────────────────────────────────────
try:
    from openai import OpenAI
except ImportError:
    print("=" * 60)
    print("ERROR: openai package not installed!")
    print()
    print("To fix this, run:")
    print("  py -3.12 -m pip install openai")
    print()
    print("Then run this script again.")
    print("=" * 60)
    sys.exit(1)

# ── Configuration ────────────────────────────────────────────────────────────
BASE_PATH = Path(os.environ.get("BASE_PATH", os.getcwd()))
INPUT_FILE = BASE_PATH / "filtered_jobs.csv"
OUTPUT_FILE = BASE_PATH / "scored_jobs.csv"
ALREADY_SCORED_FILE = BASE_PATH / "scored_jobs_history.csv"

# DeepSeek settings
MODEL = "deepseek-chat"  # This is DeepSeek V3.2 (non-thinking mode)
BASE_URL = "https://api.deepseek.com"
TEMPERATURE = 0.1  # Low = more consistent scoring
MAX_OUTPUT_TOKENS = 500  # Enough for JSON response
REQUEST_TIMEOUT = 60  # seconds — skip if no response after this

# Rate limiting (DeepSeek allows ~60 requests/minute on free tier)
DELAY_BETWEEN_REQUESTS = 1.2  # seconds — safe margin
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds

# ── Candidate CV (system prompt — cached by DeepSeek after first request) ────
# DeepSeek automatically caches identical prompt prefixes.
# Since this system prompt is the same for EVERY job, it gets cached after
# the first request, reducing input cost by ~90% for all subsequent requests.
#
# CUSTOMIZE THIS: Replace the candidate profile below with your own CV details.

SYSTEM_PROMPT = """You are a job-matching expert. You will score how well a candidate matches a job posting.

## CANDIDATE PROFILE

**Location:** [Your city], Germany (open to relocation within Germany)
**Language:** English fluent. Does NOT speak German — cannot work in German-language roles.
**Education:** [Your degree], [Your university], graduating [year]
**Experience:** [X] years total

### Work History:
1. **[Job Title]** | [Company] ([years])
   - [Key achievement with metric]
   - [Key achievement with metric]

2. **[Job Title]** | [Company] ([years])
   - [Key achievement with metric]
   - [Key achievement with metric]

### Technical Skills:
[List your technical skills here]

### Soft Skills:
[List your soft skills here]

### Target Career Scopes:
- **Scope 1:** [description]
- **Scope 2:** [description]
- **Scope 3:** [description]
- **Scope 4:** [description]

## SCORING INSTRUCTIONS

You will receive a job posting. Score it 0-100 based on how well the candidate matches.

**Scoring criteria (weighted):**
- Role level fit (30%): Mid-level, associate, early manager = good. Junior/intern or Director/VP/C-suite = bad.
- Skills match (25%): How many required skills does the candidate have?
- Experience relevance (20%): How relevant is their background to this role?
- Language compatibility (15%): If the job requires German (spoken/written/native), score 0.
- Location fit (10%): Germany-based or remote-friendly = good. Other countries = bad.

**Critical rules:**
- If the job description is primarily in German → score 0, set german_language to true
- If the job explicitly requires "German fluent/native/C1/C2" or "Deutsch" as a requirement → score 0, set german_language to true
- If the job requires 10+ years experience → cap score at 30
- If the job is clearly for a different field (nursing, accounting, mechanical engineering, etc.) → score 0
- Senior roles (8+ years) are OK, cap at 70 unless it's a perfect match
- Director/VP/Head of = cap at 40

**Respond with ONLY valid JSON (no markdown, no code fences, no explanation):**
{
  "score": <0-100>,
  "scope": "<best_matching_scope: genai | bi_analytics | chief_of_staff | consulting | none>",
  "german_language": <true if German required, false otherwise>,
  "match_reasons": "<2-3 bullet points on why this matches, max 150 chars total>",
  "gaps": "<1-2 key gaps or missing requirements, max 100 chars total>",
  "recommendation": "<apply | maybe | skip>"
}

Where recommendation is:
- "apply" = score >= 70, strong match
- "maybe" = score 50-69, worth reviewing
- "skip" = score < 50, not a good fit"""


# ── Helper: build user message for a job ─────────────────────────────────────
def build_user_message(job: dict) -> str:
    """Build the user message for a single job."""
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    location = job.get("location", "Unknown")
    description = job.get("description", "").strip()
    source = job.get("source", "unknown")

    # LinkedIn jobs have no description — flag this
    if not description or len(description) < 50:
        return (
            f"## JOB POSTING (title + company only — no description available)\n\n"
            f"**Title:** {title}\n"
            f"**Company:** {company}\n"
            f"**Location:** {location}\n"
            f"**Source:** {source}\n\n"
            f"Score based on title and company only. "
            f"Be generous since we can't see full requirements — if the title sounds "
            f"relevant, score 50-65 range. If title is clearly irrelevant, score 0-20."
        )
    else:
        # Truncate very long descriptions to save tokens (keep first ~3000 chars)
        if len(description) > 3000:
            description = description[:3000] + "\n\n[... description truncated for length ...]"

        return (
            f"## JOB POSTING\n\n"
            f"**Title:** {title}\n"
            f"**Company:** {company}\n"
            f"**Location:** {location}\n"
            f"**Source:** {source}\n\n"
            f"**Description:**\n{description}"
        )


# ── Helper: parse JSON from DeepSeek response ───────────────────────────────
def parse_score_response(text: str) -> dict:
    """Parse the JSON response from DeepSeek, handling edge cases."""
    # Remove markdown code fences if present
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return None
        else:
            return None

    # Validate required fields
    required = ["score", "scope", "german_language", "match_reasons", "gaps", "recommendation"]
    for field in required:
        if field not in data:
            return None

    # Ensure score is numeric and in range
    try:
        data["score"] = max(0, min(100, int(float(data["score"]))))
    except (ValueError, TypeError):
        data["score"] = 0

    return data


# ── Helper: load already-scored job URLs to skip duplicates ──────────────────
def load_scored_urls() -> set:
    """Load URLs of jobs that have already been scored (from history file)."""
    urls = set()

    # Check both output file and history file
    for filepath in [OUTPUT_FILE, ALREADY_SCORED_FILE]:
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get("job_url", "").strip()
                        if url:
                            urls.add(url)
            except Exception:
                pass

    return urls


# ── Helper: save one scored job to history file immediately ──────────────────
def save_to_history(scored_job: dict, fieldnames: list):
    """Save a single scored job to history file right after scoring.
    This way progress is never lost if the script is cancelled."""
    file_exists = ALREADY_SCORED_FILE.exists() and ALREADY_SCORED_FILE.stat().st_size > 0

    try:
        with open(ALREADY_SCORED_FILE, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerow(scored_job)
    except Exception:
        pass  # Silent fail — history is a convenience, not critical


# ── Output column definition ─────────────────────────────────────────────────
FIELDNAMES = [
    "score", "recommendation", "scope_match", "title", "company",
    "location", "job_url", "source", "german_language",
    "match_reasons", "gaps", "description", "date_scored"
]


# ── Main scoring function ───────────────────────────────────────────────────
def score_jobs():
    """Main function: read filtered jobs, score them, write results."""

    # Check input file exists
    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found!")
        print()
        print("Make sure you've run the scraper and filter scripts first:")
        print("  1. py -3.12 jobspy_scraper.py")
        print("  2. py -3.12 job_filter.py")
        sys.exit(1)

    # Read filtered jobs
    print(f"Reading jobs from {INPUT_FILE}...")
    jobs = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            jobs.append(row)

    print(f"  Found {len(jobs)} filtered jobs.")

    # Load already-scored URLs to skip duplicates
    scored_urls = load_scored_urls()
    if scored_urls:
        original_count = len(jobs)
        jobs = [j for j in jobs if j.get("job_url", "").strip() not in scored_urls]
        skipped = original_count - len(jobs)
        if skipped > 0:
            print(f"  Skipping {skipped} already-scored jobs.")

    if not jobs:
        print("\nNo new jobs to score! All jobs have already been scored.")
        print(f"Check {OUTPUT_FILE} for results.")
        return

    print(f"  Scoring {len(jobs)} new jobs...\n")

    # Initialize DeepSeek client with timeout
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=REQUEST_TIMEOUT,
    )

    # Score each job
    all_scored_jobs = []  # All jobs (including German) for history
    english_scored_jobs = []  # Only English jobs for results file
    errors = 0
    german_filtered = 0
    timed_out = 0

    for i, job in enumerate(jobs, 1):
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        source = job.get("source", "unknown")

        safe_title = title[:50].encode('utf-8', errors='replace').decode('utf-8')
        safe_company = company[:30].encode('utf-8', errors='replace').decode('utf-8')
        print(f"  [{i}/{len(jobs)}] {safe_title} @ {safe_company} ({source})", end=" ")

        user_message = build_user_message(job)

        # Retry logic
        result = None
        for attempt in range(MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_OUTPUT_TOKENS,
                    stream=False,
                )

                raw_text = response.choices[0].message.content
                result = parse_score_response(raw_text)

                if result is not None:
                    break
                else:
                    print(f"\n    ⚠ Bad JSON (attempt {attempt + 1}), retrying...", end=" ")
                    time.sleep(RETRY_DELAY)

            except Exception as e:
                error_msg = str(e)
                if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                    timed_out += 1
                    print(f"\n    ⚠ Timeout (attempt {attempt + 1}), retrying...", end=" ")
                    time.sleep(RETRY_DELAY)
                elif "rate" in error_msg.lower() or "429" in error_msg:
                    wait = RETRY_DELAY * (attempt + 1)
                    print(f"\n    ⚠ Rate limited, waiting {wait}s...", end=" ")
                    time.sleep(wait)
                elif "503" in error_msg or "502" in error_msg:
                    wait = RETRY_DELAY * (attempt + 1)
                    print(f"\n    ⚠ Server busy, waiting {wait}s...", end=" ")
                    time.sleep(wait)
                else:
                    print(f"\n    ✗ Error: {error_msg[:80]}", end=" ")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)

        # Process result
        scored_job = {**job}
        scored_job["date_scored"] = time.strftime("%Y-%m-%d")

        if result is None:
            print("-> FAILED (skipped)")
            errors += 1
            scored_job["score"] = -1
            scored_job["scope_match"] = "error"
            scored_job["german_language"] = ""
            scored_job["match_reasons"] = "API error - needs manual review"
            scored_job["gaps"] = ""
            scored_job["recommendation"] = "maybe"
            all_scored_jobs.append(scored_job)
            english_scored_jobs.append(scored_job)  # Keep errors in results for review
        else:
            score = result["score"]
            rec = result["recommendation"]

           # HARD OVERRIDE: If German is required, force score to 0
            is_german = str(result.get("german_language", False)).lower() == "true"
            if is_german:
                score = 0
                rec = "skip"
                german_filtered += 1
                print(f"-> GERMAN (score: 0)")
            else:
                emoji = "[Y]" if rec == "apply" else ("~" if rec == "maybe" else "[X]")
                print(f"-> {emoji} Score: {score} ({rec})")

            scored_job["score"] = score
            scored_job["scope_match"] = result["scope"]
            scored_job["german_language"] = str(is_german).lower()
            scored_job["match_reasons"] = result["match_reasons"]
            scored_job["gaps"] = result["gaps"]
            scored_job["recommendation"] = rec
            all_scored_jobs.append(scored_job)

            # Only add English jobs with score > 0 to the results file
            if not is_german and score > 0:
                english_scored_jobs.append(scored_job)

        # SAVE-AS-YOU-GO: Write to history immediately after each job
        save_to_history(scored_job, FIELDNAMES)

        # Rate limiting delay
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # ── Write results (English jobs only) ────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"SCORING COMPLETE")
    print(f"{'=' * 60}")

    # Sort by score (highest first), with errors at the bottom
    english_scored_jobs.sort(key=lambda x: (x["score"] if x["score"] >= 0 else -999), reverse=True)

    # Write scored_jobs.csv (English jobs only — no German clutter)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for job in english_scored_jobs:
            writer.writerow(job)

    # ── Summary stats ────────────────────────────────────────────────────────
    apply_count = sum(1 for j in english_scored_jobs if j.get("recommendation") == "apply")
    maybe_count = sum(1 for j in english_scored_jobs if j.get("recommendation") == "maybe")
    skip_count = sum(1 for j in english_scored_jobs if j.get("recommendation") == "skip")

    # Count zero-score English jobs that were removed
    zero_score_removed = len(all_scored_jobs) - german_filtered - len(english_scored_jobs) - errors

    print(f"  Total scored:      {len(all_scored_jobs)}")
    print(f"  German removed:    {german_filtered}")
    print(f"  Zero-score removed:{zero_score_removed}")
    print(f"  Results kept:      {len(english_scored_jobs)}")
    print(f"    ✓ APPLY (70+):   {apply_count}")
    print(f"    ~ MAYBE (50-69): {maybe_count}")
    print(f"    ✗ SKIP (<50):    {skip_count}")
    print(f"  Timeouts:          {timed_out}")
    print(f"  API errors:        {errors}")
    print()
    print(f"  Results saved to:  {OUTPUT_FILE}")
    print(f"  (German + zero-score jobs saved to history only — won't be re-scored)")

    # Show top 10 jobs
    top_jobs = [j for j in english_scored_jobs if j["score"] >= 50][:10]
    if top_jobs:
        print(f"\n{'=' * 60}")
        print(f"TOP MATCHES")
        print(f"{'=' * 60}")
        for j in top_jobs:
            score = j["score"]
            title = j["title"][:45]
            company = j["company"][:25]
            scope = j["scope_match"]
            print(f"  {score:>3}  {title:<45}  {company:<25}  [{scope}]")

    print(f"\nDone! Open {OUTPUT_FILE.name} to review your scored jobs.")


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("JOB SCORER — DeepSeek V3.2 API")
    print("=" * 60)
    print()

    # Quick cost estimate
    job_count = 0
    if INPUT_FILE.exists():
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            job_count = sum(1 for _ in reader)

        scored_urls = load_scored_urls()
        new_jobs = job_count - len([u for u in scored_urls if u])  # rough estimate
        new_jobs = max(0, new_jobs)

        if new_jobs > 0:
            # Rough cost estimate:
            # System prompt ~1500 tokens (cached after first: $0.028/M)
            # User message ~800 tokens avg (cache miss: $0.28/M)
            # Output ~200 tokens ($0.42/M)
            # First request: ~$0.001, subsequent: ~$0.0005 each
            est_cost = 0.001 + (new_jobs - 1) * 0.0005
            print(f"  {job_count} total filtered jobs, ~{new_jobs} new to score")
            print(f"  Estimated cost: ~${est_cost:.3f}")
            print(f"  Estimated time: ~{new_jobs * 1.5 / 60:.1f} minutes")
        else:
            print(f"  {job_count} filtered jobs found, checking for new ones...")
    else:
        print(f"  ⚠ {INPUT_FILE} not found — run the scraper & filter first!")
        sys.exit(1)

    print()
    print("Starting scoring automatically via n8n...")
    print()

    score_jobs()
