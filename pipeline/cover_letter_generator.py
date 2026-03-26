# Cover Letter Generator - Script 4
# Reads scored_jobs.csv, selects top 40 jobs, submits to Claude Batch API
#
# Required environment variables:
#   ANTHROPIC_API_KEY  - your Anthropic API key
#   BASE_PATH          - folder where CSV files are read from and saved to
#
# Output: pending_batch.json in BASE_PATH (used by cover_letter_retriever.py)

import subprocess
import sys

# Auto-install required packages
for pkg in ["anthropic", "python-docx"]:
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

import os
import csv
import json
import random
from datetime import datetime
from anthropic import Anthropic

# ============================================================
# CONFIGURATION
# ============================================================

BASE_PATH = os.environ.get("BASE_PATH", os.getcwd())
SCORED_JOBS_FILE = os.path.join(BASE_PATH, "scored_jobs.csv")
COVER_LETTER_HISTORY = os.path.join(BASE_PATH, "cover_letters_history.csv")
PENDING_BATCH_FILE = os.path.join(BASE_PATH, "pending_batch.json")
DAILY_CAP = 40
MAX_JD_LENGTH = 3000

SCOPE_KEYWORDS = {
    1: {
        "name": "Business x GenAI",
        "terms": [
            "ai strategy", "genai consultant", "ai transformation",
            "digital transformation ai", "ai business consultant",
            "ai change management", "ai implementation manager"
        ]
    },
    2: {
        "name": "BI and Strategy Analytics",
        "terms": [
            "business intelligence analyst", "bi analyst",
            "data analyst strategy", "business intelligence consultant",
            "analytics manager", "strategy analyst", "insights analyst"
        ]
    },
    3: {
        "name": "Chief of Staff",
        "terms": [
            "chief of staff", "founder associate", "founders associate",
            "ceo office", "head of staff", "business operations associate",
            "strategic operations"
        ]
    },
    4: {
        "name": "Tech x Business Consulting",
        "terms": [
            "technology consultant", "digital consultant",
            "management consultant technology", "it strategy consultant",
            "business technology analyst", "digital strategy consultant",
            "transformation consultant"
        ]
    }
}

# ============================================================
# SYSTEM PROMPT (identical for all jobs -- gets cached by Anthropic)
# COST SAVINGS: Because this prompt is the same for every request
# in the batch, Anthropic caches it automatically. You only pay
# full price for it once, then all other requests use the cached
# version at a discount. This is why the system prompt is long
# and the user prompt is short -- not the other way around.
# DO NOT put job-specific info in the system prompt.
# DO NOT put CV/rules info in the user prompt.
#
# CUSTOMIZE THIS: Replace the candidate profile, achievement list,
# and scope profiles below with your own background.
# ============================================================

SYSTEM_PROMPT = """You are a cover letter writer for [Candidate Name], a professional based in [City], Germany, completing their [Degree] at [University] in [Year].

YOUR TASK: Write a tailored cover letter for the job provided. The cover letter must feel like the candidate wrote it themselves. Confident, specific, and direct. Not generic, not robotic, not overly formal.

STRUCTURE (exactly 5 paragraphs, no more, no less):

PARAGRAPH 1 (FIXED -- use this exact text every time, do not modify a single word):
There's a quote I really connect with: "Plant a tree whose shade you are not sure you might or might not sit under." I try to bring this mindset into any work I contribute to. For me, it means doing the work the right way, helping my team members, and building things that last and add value. This approach keeps me curious, pushes me to learn quickly, and helps me make a positive impact on the people and projects around me.

PARAGRAPH 2: Lead with your strongest, most relevant achievement for THIS specific job. Pick the one achievement from the candidate's list that most directly addresses what the job description asks for. Be specific with numbers and context. Write 3 to 5 sentences.

PARAGRAPH 3: Add a second achievement that complements paragraph 2, and connect it to something specific about the company or the role. Show that the candidate understands what this company needs and why their experience maps to their challenge. Write 3 to 5 sentences.

PARAGRAPH 4: Third achievement or deeper company connection. This paragraph should tie the candidate's experience together into a narrative of why they are the right person for THIS role at THIS company. If the job description gives clues about their challenges, pain points, or goals, reference them here. Write 3 to 5 sentences.

PARAGRAPH 5 (CLOSING): End with a forward-looking sentence about what the candidate would bring to the team. Make it specific to the role, not generic. Do not use phrases like "I look forward to hearing from you" or "I would welcome the opportunity to discuss." Write 2 to 3 sentences.

After paragraph 5, insert one blank line, then write:
Best regards
[Candidate Name]

GREETING LINE:
Every cover letter must begin with: Dear Hiring team at [Company Name],
Then a blank line before paragraph 1.

IMPORTANT: Do NOT insert blank lines between paragraphs 1 through 5. The only blank line in the entire cover letter body is between paragraph 5 and "Best regards". Paragraphs 1, 2, 3, 4, and 5 should flow continuously with no blank lines between them.

STYLE RULES (follow all of these strictly):

1. LENGTH: The entire cover letter (all 5 paragraphs combined, excluding greeting and sign-off) should be 400 to 500 words. Do not go below 400 words. Do not exceed 500 words for the body text.

2. TONE: Professional but human. Write like a sharp colleague, not a template. Confident without arrogance. No filler phrases like "I believe I would be a great fit" or "I am passionate about" or "I am excited to apply" or "I am thrilled" or "I am eager."

3. ACHIEVEMENTS: Include 2 to 3 specific, quantified achievements from the candidate's achievement list below that are directly relevant to THIS job. Do not list everything. Pick the ones that matter most for this role.

4. STRONGEST DIFFERENTIATOR RULE: Always include the candidate's single strongest differentiator (the one story that sets them apart most clearly) in at least one of paragraphs 2, 3, or 4. Frame it through the lens of the relevant scope.

5. COMPANY CONNECTION: Reference something specific about the company or role from the job description. Not generic flattery. If the JD mentions specific challenges, technologies, or goals, use them.

6. PUNCTUATION: Never use em dashes anywhere in the cover letter. Use commas, periods, or semicolons instead.

7. LANGUAGE: Do not mention language skills or language ability anywhere in the cover letter.

8. HONESTY: Only reference experiences, skills, and achievements that appear in the candidate's achievement list or CV content below. Never invent projects, companies, numbers, or skills.

9. FORMATTING: No bullet points. No bold text. No headers. Just clean paragraphs. Do not include a date or address block.

10. WORD CHOICE: Do not use "leverage," "synergy," "spearhead," "utilize," or "facilitate." Write in plain, direct English.

CANDIDATE'S ACHIEVEMENT LIST (replace with your own):
[Add your key achievements here with specific numbers and context]

ACADEMIC ACHIEVEMENTS (replace with your own):
[Add your academic achievements, grades, competitions, projects here]

4 SCOPE PROFILES (replace with your own career scopes):

SCOPE 1 -- [Your Scope 1 Name]:
CV version: [CV filename]
Angle: [Describe the narrative angle and key achievements to emphasize for this scope]

SCOPE 2 -- [Your Scope 2 Name]:
CV version: [CV filename]
Angle: [Describe the narrative angle and key achievements to emphasize for this scope]

SCOPE 3 -- [Your Scope 3 Name]:
CV version: [CV filename]
Angle: [Describe the narrative angle and key achievements to emphasize for this scope]

SCOPE 4 -- [Your Scope 4 Name]:
CV version: [CV filename]
Angle: [Describe the narrative angle and key achievements to emphasize for this scope]

OUTPUT FORMAT:
Return ONLY the cover letter. Start with "Dear Hiring team at [Company Name]," and end with "[Candidate Name]". Nothing else before or after. No commentary, no notes, no explanations."""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def detect_scope(job):
    """Determine which scope a job belongs to based on its search term or title."""
    search_query = job.get("search_query", "").lower().strip()
    if search_query:
        for scope_num, scope_info in SCOPE_KEYWORDS.items():
            for term in scope_info["terms"]:
                if term in search_query:
                    return scope_num

    title = job.get("title", "").lower()
    if any(kw in title for kw in ["ai ", "genai", "artificial intelligence", "machine learning",
                                    "ml ", "llm", "rag", "generative"]):
        return 1
    if any(kw in title for kw in ["business intelligence", " bi ", "data analyst", "analytics",
                                    "power bi", "dashboard", "insights"]):
        return 2
    if any(kw in title for kw in ["chief of staff", "founder associate", "founders associate",
                                    "ceo office", "head of staff", "business operations"]):
        return 3
    if any(kw in title for kw in ["consultant", "consulting", "advisory", "advisor"]):
        return 4

    desc = job.get("description", "").lower()
    if any(kw in desc for kw in ["ai strategy", "genai", "llm", "rag", "artificial intelligence"]):
        return 1
    if any(kw in desc for kw in ["business intelligence", "power bi", "dashboard", "kpi"]):
        return 2
    if any(kw in desc for kw in ["chief of staff", "founder associate", "ceo office"]):
        return 3
    if any(kw in desc for kw in ["consulting", "client-facing", "advisory"]):
        return 4

    return 1


def load_cover_letter_history():
    """Load URLs of jobs that already have cover letters."""
    if not os.path.exists(COVER_LETTER_HISTORY):
        return set()
    history = set()
    with open(COVER_LETTER_HISTORY, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("job_url", "").strip()
            if url:
                history.add(url)
    return history


def load_scored_jobs():
    """Load jobs from scored_jobs.csv."""
    if not os.path.exists(SCORED_JOBS_FILE):
        print(f"\nERROR: {SCORED_JOBS_FILE} not found!")
        print("Run the job scorer first: py -3.12 job_scorer.py")
        sys.exit(1)
    jobs = []
    with open(SCORED_JOBS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            jobs.append(row)
    if not jobs:
        print("\nERROR: scored_jobs.csv is empty! No jobs to process.")
        sys.exit(1)
    return jobs


def select_top_jobs(jobs, history):
    """Select top 40 jobs using tiebreaker rules."""
    new_jobs = [j for j in jobs if j.get("job_url", j.get("url", "")).strip() not in history]

    if not new_jobs:
        print("\nNo new jobs to process! All scored jobs already have cover letters.")
        print("Run the scrapers and scorer to get fresh jobs.")
        sys.exit(0)

    for job in new_jobs:
        job["_scope"] = detect_scope(job)
        job["_scope_name"] = SCOPE_KEYWORDS[job["_scope"]]["name"]
        try:
            job["_score"] = int(float(job.get("score", "0")))
        except (ValueError, TypeError):
            job["_score"] = 0
        desc = job.get("description", "").strip()
        job["_has_description"] = 1 if len(desc) > 100 else 0
        job["_random"] = random.random()

    new_jobs.sort(key=lambda j: (
        -j["_score"],
        -j["_has_description"],
        j["_scope"],
        j["_random"]
    ))

    selected = new_jobs[:DAILY_CAP]
    return selected


def build_user_prompt(job):
    """Build the user message for a specific job."""
    scope_num = job["_scope"]
    scope_name = job["_scope_name"]
    title = job.get("title", "Unknown Title")
    company = job.get("company", "Unknown Company")
    description = job.get("description", "")
    if len(description) > MAX_JD_LENGTH:
        description = description[:MAX_JD_LENGTH] + "..."

    prompt = f"""Write a cover letter for the candidate using SCOPE {scope_num}: {scope_name}

Job Title: {title}
Company: {company}

Job Description:
{description}"""

    return prompt


# ============================================================
# MAIN SCRIPT
# ============================================================

def main():
    print("=" * 60)
    print("COVER LETTER GENERATOR")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nERROR: ANTHROPIC_API_KEY not found!")
        print("Set it with: setx ANTHROPIC_API_KEY \"sk-ant-...\"")
        print("Then restart Command Prompt and try again.")
        sys.exit(1)

    print(f"\nAPI key found: {api_key[:12]}...")

    print("\nLoading scored jobs...")
    jobs = load_scored_jobs()
    print(f"  Found {len(jobs)} scored jobs")

    print("Loading cover letter history...")
    history = load_cover_letter_history()
    print(f"  Found {len(history)} jobs with existing cover letters")

    print(f"\nSelecting top {DAILY_CAP} jobs...")
    selected = select_top_jobs(jobs, history)
    print(f"  Selected {len(selected)} jobs for cover letters")

    apply_jobs = [j for j in selected if j["_score"] >= 70]
    maybe_jobs = [j for j in selected if j["_score"] < 70]

    scope_counts = {}
    for j in selected:
        s = j["_scope_name"]
        scope_counts[s] = scope_counts.get(s, 0) + 1

    print(f"\n  Score breakdown:")
    print(f"    Apply (70+): {len(apply_jobs)} jobs -> Claude Sonnet 4.6")
    print(f"    Maybe (<70): {len(maybe_jobs)} jobs -> Claude Haiku 4.5")

    print(f"\n  Scope breakdown:")
    for scope_name, count in sorted(scope_counts.items()):
        print(f"    {scope_name}: {count} jobs")

    print(f"\n  Top 10 jobs:")
    for j in selected[:10]:
        model_tag = "S" if j["_score"] >= 70 else "H"
        print(f"    [{j['_score']}{model_tag}] {j.get('title', '?')} @ {j.get('company', '?')} ({j['_scope_name']})")

    print(f"\n{'=' * 60}")
    print(f"Ready to submit {len(selected)} cover letter requests to Claude Batch API.")

    sonnet_count = len(apply_jobs)
    haiku_count = len(maybe_jobs)
    est_cost = (sonnet_count * 0.015) + (haiku_count * 0.005)
    print(f"Estimated cost: ${est_cost:.4f} ({sonnet_count} Sonnet + {haiku_count} Haiku, Batch API)")
    print(f"{'=' * 60}")

    if "--auto" in sys.argv:
        print("\n[AUTO MODE] Skipping confirmation, submitting batch...")
    else:
        confirm = input("\nType 'yes' to submit batch, anything else to cancel: ").strip().lower()
        if confirm != "yes":
            print("Cancelled. No batch submitted.")
            sys.exit(0)

    print("\nBuilding batch requests...")
    requests = []

    for i, job in enumerate(selected):
        if job["_score"] >= 70:
            model = "claude-sonnet-4-20250514"
        else:
            model = "claude-haiku-4-5-20251001"

        custom_id = f"cover_letter_{i}_{job['_scope']}_{job['_score']}"

        request = {
            "custom_id": custom_id,
            "params": {
                "model": model,
                "max_tokens": 1500,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": build_user_prompt(job)
                    }
                ]
            }
        }
        requests.append(request)

    print(f"\nSubmitting batch of {len(requests)} requests to Anthropic...")

    client = Anthropic()

    try:
        batch = client.messages.batches.create(requests=requests)

        print(f"\nBatch submitted successfully!")
        print(f"  Batch ID: {batch.id}")
        print(f"  Status: {batch.processing_status}")

        batch_info = {
            "batch_id": batch.id,
            "submitted_at": datetime.now().isoformat(),
            "total_jobs": len(selected),
            "sonnet_count": sonnet_count,
            "haiku_count": haiku_count,
            "estimated_cost": est_cost,
            "jobs": []
        }

        for i, job in enumerate(selected):
            job_url = job.get("job_url", job.get("url", ""))
            model_tag = "S" if job["_score"] >= 70 else "H"
            batch_info["jobs"].append({
                "custom_id": f"cover_letter_{i}_{job['_scope']}_{job['_score']}",
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "url": job_url,
                "scope": job["_scope"],
                "scope_name": job["_scope_name"],
                "score": job["_score"],
                "model_tag": model_tag,
                "model": "claude-sonnet-4-20250514" if job["_score"] >= 70 else "claude-haiku-4-5-20251001"
            })

        with open(PENDING_BATCH_FILE, "w", encoding="utf-8") as f:
            json.dump(batch_info, f, indent=2)

        print(f"\n  Batch info saved to: {PENDING_BATCH_FILE}")
        print(f"\n{'=' * 60}")
        print("NEXT STEPS:")
        print("  1. Wait for batch to complete (usually a few hours, max 24 hours)")
        print("  2. Run the retriever script:")
        print("     py -3.12 cover_letter_retriever.py")
        print(f"{'=' * 60}")

    except Exception as e:
        print(f"\nERROR submitting batch: {e}")
        print("\nPossible causes:")
        print("  - Invalid API key (check ANTHROPIC_API_KEY)")
        print("  - Insufficient credits (check console.anthropic.com)")
        print("  - Network issue (check internet connection)")
        sys.exit(1)


if __name__ == "__main__":
    main()
