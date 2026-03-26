# job-automation-pipeline

**A fully automated job application pipeline — AI scoring, tailored cover letters, and Google Sheets tracking, running end-to-end via n8n.**

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Last Updated](https://img.shields.io/badge/Last%20Updated-March%202026-lightgrey)

---

## The Problem

Searching for jobs manually is a full-time job in itself. You spend hours scrolling job boards, most postings are irrelevant, and by the time you've found something worth applying to, you've barely got energy left to write a decent cover letter — let alone 30 of them.

I was targeting mid-level roles across 4 different career tracks simultaneously (AI strategy, BI & analytics, Chief of Staff, consulting) in Germany. That meant 4 different CVs, 4 different cover letter angles, and hundreds of postings to sift through daily. Doing it manually wasn't just slow — it wasn't scalable.

So I built this instead.

---

## What It Does

- **Surfaces 1,300+ relevant job postings every morning**, pre-scored and ready to review — scraped from Indeed, LinkedIn, Arbeitnow, and 32 company career pages directly
- **Scores every job against your CV** using AI, so you know in seconds which are worth your time (and which aren't)
- **Generates a tailored cover letter for each top job** automatically — a better letter than most people write manually, every single time
- **Tracks everything in a Google Sheets dashboard** — one place to see your pipeline, statuses, scores, and gaps
- **Runs the entire pipeline with one click** via n8n workflow automation — press go in the evening, wake up to everything ready

---

## Architecture

```
Indeed ───────────────────────────────────────────────────────────────────┐
LinkedIn ─────────────────────────────────────────────────────────────────┤
Arbeitnow ────────────────────────────────────────────────────────────────┼──→ Filter ──→ DeepSeek Score ──→ Claude Cover Letters ──→ Google Sheets
32 Company Career Pages (Greenhouse / Lever / Ashby / SmartRecruiters) ──┘
```

All 4 sources scrape in parallel. Results merge, get filtered, scored by AI, and cover letters are generated — all automatically. You wake up to a prioritized list and a folder of ready-to-send letters.

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Scraping (job boards) | Python + [JobSpy](https://github.com/Bunsly/JobSpy) | Handles Indeed + LinkedIn without login |
| Scraping (company pages) | Python + ATS public APIs | Free, fast, no browser needed, zero blocking risk |
| Workflow automation | [n8n](https://n8n.io) | Open source, self-hosted, parallel execution |
| Job scoring | [DeepSeek V3.2](https://api.deepseek.com) API | 7–18x cheaper than GPT-4 for structured tasks. Real cost: $0.04 per run of ~300 jobs |
| Cover letter generation | [Claude Sonnet 4.6 + Haiku 4.5](https://anthropic.com) via Batch API | Sonnet quality for top matches, Haiku for volume. 50% cost saving via Batch API |
| Job tracking | Google Sheets API | Accessible anywhere, easy to update manually |
| Output format | `.docx` (cover letters), `.csv` (intermediate data) | ATS-compatible for cover letters |

---

## Key Features

### Multi-Source Scraping
Four scrapers run in parallel via n8n:
- **Indeed** — 28 search terms across 4 career tracks, 50 results each
- **LinkedIn** — same 28 terms, with human-like delays to avoid blocking
- **Arbeitnow** — free public API, up to 1,000 German job market postings
- **32 Company Career Pages** — direct ATS API integration (see below)

All sources auto-merge and deduplicate before filtering.

### ATS API Integration (the good part)
Instead of scraping company career pages with a browser (slow, fragile, gets blocked), this pipeline integrates directly with the underlying Applicant Tracking Systems that companies use to post jobs. Four platforms are supported:

| ATS | Companies using it (sample) |
|---|---|
| Greenhouse | Celonis, Datadog, MongoDB, HubSpot, GitLab, Figma, Cloudflare, HelloFresh, FlixBus, Miro + more |
| Lever | Mistral AI, FINN |
| Ashby | DeepL, Aleph Alpha, Notion |
| SmartRecruiters | Bosch, Delivery Hero, Scalable Capital, TeamViewer, Enpal |

All APIs are free, public, and require no authentication. One new company takes 2 minutes to add (just fill one row in the Google Sheet).

### AI Scoring — Two Layers
Every job gets scored 0–100 against your CV, with two layers of logic:

**Layer 1 — LLM judgment (DeepSeek V3.2):** Weighted scoring across role level fit (30%), skills match (25%), experience relevance (20%), language (15%), location (10%).

**Layer 2 — Python hard overrides:** Certain rules can't be trusted to an LLM alone. If a job description is in German, the score is forced to 0 in Python — regardless of what the LLM outputs. Same for wrong-field roles (nursing, accounting, etc.) and 10+ years experience requirements. This two-layer approach ensures the scoring is reliable, not just plausible.

Output: `apply` (70+), `maybe` (50–69), `skip` (<50) — plus a `gaps` field listing the 1–2 key reasons you might not get the role. That gaps field goes straight into column K of the Google Sheet.

### Intelligent Cover Letter Generation
Cover letters are generated using two Claude models, tiered by job score:
- **Sonnet 4.6** → top jobs (score 70+). Best quality for roles worth the extra cost.
- **Haiku 4.5** → remaining jobs (score 50–69). Fast and good enough for volume applications.

All letters go through the **Anthropic Batch API** (50% discount) — submitted the evening before, ready by morning. Each letter is scope-targeted: AI strategy jobs get a different angle than BI jobs or Chief of Staff jobs.

The daily cap is 40 cover letters, which accounts for ~5–10 jobs that turn out to be German or irrelevant upon manual review. Target: 30–35 real applications per day.

### Google Sheets Job Tracker
Every scored job lands in a Google Sheet with 15 columns:

| Column | What it shows |
|---|---|
| Score | 0–100, colour-coded (green / yellow / red) |
| Label | apply / maybe / skip |
| Scope | Which career track this job maps to |
| Gap Analysis | 1–2 key gaps from AI scoring |
| Cover Letter | Filename of the generated .docx |
| Status | new / applied / skipped / rejected / interview / offer |
| Source | Indeed / LinkedIn / Arbeitnow / [Company] Careers |

Sort by score, click the URL, Simplify autofills the form, attach the cover letter, submit. That's the morning routine.

### Cost Efficiency
This is a production system with real cost data:

| Item | Actual Cost |
|---|---|
| DeepSeek scoring (300 jobs/run) | $0.04 per run |
| Claude cover letters (40/day) | ~$0.26/day |
| Everything else (n8n, JobSpy, Sheets API, Arbeitnow) | Free |
| **Total monthly** | **~$8–9/month** |

The DeepSeek cost is low because of prompt caching: the CV and scoring rules are sent as the system prompt (identical every request and cached), while the job description is the user message (different every request). Cache hit rate confirmed at 80%+.

---

## Full Pipeline — Step by Step

1. **Trigger** — You click "Execute workflow" in n8n. Takes 5 seconds.
2. **Scrape** — All 4 scrapers run in parallel (~30–40 minutes, mostly LinkedIn delays)
3. **Filter** — Merges all sources, deduplicates, removes irrelevant titles and German-language jobs
4. **Score** — DeepSeek scores every remaining job against your CV (~5–15 minutes)
5. **Cover Letters** — Top 40 jobs submitted to Claude Batch API (completes in background overnight)
6. **Sheets Upload** — Everything synced to Google Sheets
7. **Morning** — Run `cover_letter_retriever.py` to download letters, re-sync sheet, start applying

The pipeline is fire-and-forget. You trigger it once in the evening, walk away, and come back to a prioritised, ready-to-apply list.

---

## Setup Guide

### Prerequisites
- Python 3.12
- Node.js (for n8n)
- A [DeepSeek API account](https://platform.deepseek.com) (free 5M tokens on signup)
- An [Anthropic API account](https://console.anthropic.com) ($5 free credits on signup)
- A Google Cloud project with Sheets API + Drive API enabled (free)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/job-automation-pipeline.git
cd job-automation-pipeline
```

### 2. Install Python dependencies

```bash
pip install python-jobspy openai anthropic python-docx gspread requests beautifulsoup4
```

### 3. Set environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here
GOOGLE_CREDENTIALS_PATH=path/to/your/google_credentials.json
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
BASE_PATH=path/to/your/working/directory
```

On Windows, set these as system environment variables instead:
```cmd
setx DEEPSEEK_API_KEY "sk-your-key-here"
setx ANTHROPIC_API_KEY "sk-ant-your-key-here"
setx GOOGLE_SPREADSHEET_ID "your-spreadsheet-id"
setx GOOGLE_CREDENTIALS_PATH "C:\path\to\google_credentials.json"
setx BASE_PATH "C:\Users\YourName\Desktop"
```
Then close and reopen your terminal for them to take effect.

### 4. Set up Google Sheets

1. Go to [Google Cloud Console](https://console.cloud.google.com), create a project
2. Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account**, download the JSON key, save it as `google_credentials.json`
4. Create a new Google Sheet, share it with the service account email (Editor role)
5. Copy the Spreadsheet ID from the URL into your `GOOGLE_SPREADSHEET_ID` env var

Run the one-time setup scripts:
```bash
python setup/sheets_setup.py
python setup/companies_sheet_setup.py
```

### 5. Add your CV content

Open `pipeline/job_scorer.py` and `pipeline/cover_letter_generator.py` — find the `CV_TEXT` and `COVER_LETTER_PROMPT` sections and replace the placeholder content with your own CV and cover letter instructions.

### 6. Install and configure n8n

```bash
npx n8n start
```

Go to `http://localhost:5678` → Settings → Import → upload `n8n/job_pipeline_workflow.json`

Update the file paths in each Execute Command node to match your system.

### 7. Run the pipeline

In n8n: open "Job Pipeline" → click **Execute workflow**

Or run scripts individually in order:
```bash
python scrapers/jobspy_scraper.py
python scrapers/linkedin_scraper.py
python scrapers/arbeitnow_scraper.py
python scrapers/company_scraper.py
python pipeline/job_filter.py
python pipeline/job_scorer.py
python pipeline/cover_letter_generator.py --auto
python pipeline/sheets_upload.py
```

---

## Configuration

### Adding a new company to scrape

1. Open the "Companies" tab in your Google Sheet
2. Add one row: company name, careers URL, ATS type, board token, category, scope tags, active=YES
3. That's it — the scraper reads the sheet on every run

**Finding a company's ATS token:**
- Go to their careers page, click any job
- The URL reveals the ATS and token: `boards.greenhouse.io/{token}/jobs/...` → Greenhouse token is `{token}`
- Same pattern for Lever (`job-boards.lever.co/{token}`), Ashby (`jobs.ashbyhq.com/{token}`), SmartRecruiters

### Adjusting scoring
Edit the scoring prompt in `pipeline/job_scorer.py`. The two-layer system (LLM scoring + Python overrides) is documented in the script comments.

### Changing search terms
Edit the `SEARCH_TERMS` list in `scrapers/jobspy_scraper.py` and `scrapers/linkedin_scraper.py`.

### Changing cover letter style
Edit the `COVER_LETTER_PROMPT` in `pipeline/cover_letter_generator.py`. The system supports multiple scope angles — one prompt per career track.

---

## Project Structure

```
job-automation-pipeline/
├── README.md                          ← you are here
├── .env.example                       ← environment variable template
├── .gitignore                         ← excludes credentials and output files
├── LICENSE                            ← MIT
│
├── scrapers/
│   ├── jobspy_scraper.py              ← Indeed scraper (28 search terms)
│   ├── linkedin_scraper.py            ← LinkedIn scraper (human-like delays)
│   ├── arbeitnow_scraper.py           ← Arbeitnow free API scraper
│   └── company_scraper.py             ← 32 company ATS API scraper
│
├── pipeline/
│   ├── job_filter.py                  ← merge, deduplicate, filter all sources
│   ├── job_scorer.py                  ← DeepSeek V3.2 scoring + Python overrides
│   ├── cover_letter_generator.py      ← Claude Batch API submission
│   ├── cover_letter_retriever.py      ← download completed cover letters
│   └── sheets_upload.py               ← Google Sheets sync
│
├── setup/
│   ├── sheets_setup.py                ← one-time Jobs tab setup
│   └── companies_sheet_setup.py       ← one-time Companies tab setup
│
├── n8n/
│   └── job_pipeline_workflow.json     ← importable n8n workflow
│
└── docs/
    ├── project_context.md             ← full system documentation
    └── module_company_scraper.md      ← company scraper module docs
```

---

## Cost Breakdown

| Item | Cost | Notes |
|---|---|---|
| DeepSeek V3.2 scoring | ~$0.50–1.00/month | $0.04/run confirmed. 80%+ cache hit rate on system prompt. |
| Claude cover letters | ~$7.80/month | 40 letters/day, Sonnet + Haiku mix, Batch API (50% discount) |
| n8n | Free | Self-hosted, open source |
| JobSpy (Indeed + LinkedIn) | Free | Open source Python library |
| Arbeitnow API | Free | Public API, no auth required |
| Company ATS APIs | Free | All 4 ATS platforms have public job listing APIs |
| Google Sheets API | Free | Within free quota |
| **Total** | **~$8–9/month** | For ~30–35 applications/day |

---

## Roadmap

- **Phase B — Browser-based corporate scraping** — Workday and SAP SuccessFactors don't have public APIs. Adding Playwright-based scraping for Siemens, BMW, SAP, Mercedes-Benz and similar large German corporates (~30 additional companies)
- **Cold Outreach Automation** — Automated personalised outreach to hiring managers at target companies, triggered by job postings in the pipeline
- **Schedule Trigger** — Auto-run the pipeline at a fixed time each evening (currently manual trigger by preference)

---

## About

I'm Babak Hasani — I sit at the intersection of business strategy and GenAI execution. I've spent 6+ years across digital transformation, business intelligence, strategy consulting, and a startup exit (3.2x return), and I'm currently finishing a Master in Management at TU Munich.

I built this pipeline because the alternative — applying to jobs manually at scale across 4 career tracks simultaneously — wasn't a real option. This is how I approach problems: identify the bottleneck, figure out whether technology can solve it, and build the thing.

**Connect:** [linkedin.com/in/babak-hasani](https://www.linkedin.com/in/babak-hasani/)

---

## License

MIT — use it, fork it, adapt it. If you build something with it, I'd love to hear about it.
