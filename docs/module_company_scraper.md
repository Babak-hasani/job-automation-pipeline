# Module: Company Website Scraper

## RELATIONSHIP TO CORE SYSTEM
This module extends the core job automation pipeline. It adds a 4th scraper source (company career pages) alongside Indeed, LinkedIn, and Arbeitnow.

**Dependencies on core system:**
- Google Sheet: set via `GOOGLE_SPREADSHEET_ID` environment variable (shared with core pipeline — this module uses the "Companies" tab)
- Google credentials: set via `GOOGLE_CREDENTIALS_PATH` environment variable (same service account as core pipeline)
- CSV output format: matches `raw_jobs*.csv` pattern that `job_filter.py` auto-detects
- n8n workflow: runs as 4th parallel scraper node in "Job Pipeline"
- All downstream scripts (filter, scorer, cover letters, sheets upload) work unchanged — they process company-scraped jobs identically to Indeed/LinkedIn/Arbeitnow jobs

**No changes needed to any existing scripts.** The company scraper outputs `raw_jobs_companies.csv` and `job_filter.py` picks it up automatically.

---

## STATUS: COMPLETE (Phase A)

Phase A (API-based, 32 active companies): **FULLY WORKING — 0 errors, 0 NOT_FOUND**
Phase B (browser-based, up to 30 corporates): Planned for later

**Last confirmed run: 2026-03-26**
- 32 active companies scraped
- 1,305 relevant jobs found
- 0 board token failures

---

## WHAT'S BEEN BUILT

### Scripts

**Script: `setup/companies_sheet_setup.py`** — One-time Google Sheet setup
- Creates "Companies" tab in the existing Job Tracker spreadsheet
- Populates with all 40 companies (32 active, 8 disabled — all tokens confirmed)
- Run ONCE (only needed if Companies tab is deleted or corrupted)
- Command: `py -3.12 setup/companies_sheet_setup.py`

**Script: `scrapers/company_scraper.py`** — Daily company career page scraper
- Reads company list from Google Sheet "Companies" tab
- Scrapes each company's career page via their ATS public API
- Filters results by Germany location + keyword relevance
- Output: `raw_jobs_companies.csv` in `BASE_PATH` folder (same format as other scrapers)
- Run time: ~2 minutes for 32 companies
- Command: `py -3.12 scrapers/company_scraper.py`
- **No browser needed** — all API-based, zero blocking risk, zero cost

### Google Sheet "Companies" Tab — 8 columns (A-H)

| Column | Field | Description |
|---|---|---|
| A | company_name | e.g., "Celonis" |
| B | career_url | The company's careers page URL (for human reference) |
| C | ats_type | greenhouse / lever / ashby / smartrecruiters |
| D | board_token | The identifier used in the ATS API URL for that company |
| E | category | AI Startup / Corporate / International / Consulting |
| F | scope_tags | Which of your target scopes this company maps to |
| G | active | YES / NO — set to NO to pause a company without deleting |
| H | notes | Free text (includes verification status) |

**To add a new company:** Fill in one row in the Google Sheet. Set active=YES. The scraper picks it up on next run.

**To find a board_token for a new company:**
- Go to the company's careers page and click any job
- The URL reveals the ATS and token:
  - `boards.greenhouse.io/{token}/jobs/...` → Greenhouse
  - `job-boards.greenhouse.io/{token}/jobs/...` → Greenhouse (EU)
  - `job-boards.eu.greenhouse.io/{token}/jobs/...` → Greenhouse (EU)
  - `jobs.lever.co/{token}/...` → Lever
  - `jobs.ashbyhq.com/{token}/...` → Ashby
  - `careers.smartrecruiters.com/{token}/...` → SmartRecruiters
  - `jobs.smartrecruiters.com/{token}/...` → SmartRecruiters
- If the job opens as a popup on the company's own domain with no ATS URL visible → unsupported, set active=NO

---

## ATS API DETAILS

All APIs are free, public, and require no authentication.

| ATS | Endpoint | Returns |
|---|---|---|
| Greenhouse | `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | JSON with title, location, description, URL |
| Lever | `GET https://api.lever.co/v0/postings/{token}?mode=json` | JSON with title, location, description, URL |
| Ashby | `GET https://api.ashbyhq.com/posting-api/job-board/{token}` | JSON with title, location, description, URL (official REST API) |
| SmartRecruiters | `GET https://api.smartrecruiters.com/v1/companies/{token}/postings` | JSON with title, location, URL (limited descriptions) |

**Key differences by ATS:**
- Greenhouse and Lever return full job descriptions
- Ashby returns full descriptions via official REST API (`api.ashbyhq.com`) — NOT the old GraphQL endpoint
- SmartRecruiters returns limited description data — jobs still get scored but may score lower
- Ashby tokens are case-sensitive (e.g. `DeepL` not `deepl`, `AlephAlpha` not `alephalpha`)

---

## CONFIRMED COMPANY LIST (40 companies — 32 active, 8 disabled)

### 1. AI/Tech Startups & Scaleups

| Company | ATS | Token | Active | Notes |
|---|---|---|---|---|
| Celonis | greenhouse | celonis | YES | Confirmed |
| DeepL | ashby | DeepL | YES | Confirmed. Case-sensitive token. |
| Personio | greenhouse | personio | NO | Uses own Personio ATS — unsupported |
| N26 | greenhouse | n26 | YES | Confirmed |
| Trade Republic | greenhouse | TradeRepublic | NO | Custom popup career page — no public API |
| Scalable Capital | smartrecruiters | ScalableGmbH | YES | Confirmed |
| FlixBus (Flix) | greenhouse | flix | YES | Confirmed |
| Contentful | greenhouse | contentful | YES | Confirmed |
| Staffbase | greenhouse | staffbase | YES | Confirmed |
| Helsing | greenhouse | helsing | YES | Confirmed |
| FINN | lever | finn | YES | Confirmed |
| Parloa | greenhouse | parloa | YES | Confirmed (eu.greenhouse.io) |
| Aleph Alpha | ashby | AlephAlpha | YES | Confirmed. Case-sensitive token. |
| Merantix | lever | merantix | NO | Uses Personio ATS — unsupported |
| commercetools | greenhouse | commercetools | YES | Confirmed |
| Taxfix | ashby | taxfix.com | YES | Confirmed. Token includes .com suffix. |
| Enpal | smartrecruiters | EnpalBV | YES | Confirmed |
| Omio | smartrecruiters | Omio1 | YES | Confirmed |

### 2. Large German Corporates

| Company | ATS | Token | Active | Notes |
|---|---|---|---|---|
| Bosch | smartrecruiters | BoschGroup | YES | Confirmed |
| Continental | smartrecruiters | Continental | YES | Confirmed |
| Zalando | greenhouse | zalando | NO | Custom popup career page — no public API |
| Delivery Hero | smartrecruiters | DeliveryHero | YES | Confirmed |
| HelloFresh | greenhouse | hellofresh | YES | Confirmed |
| TeamViewer | smartrecruiters | TeamViewer | YES | Confirmed |
| trivago | greenhouse | trivago | YES | Confirmed |
| AUTO1 Group | lever | auto1 | NO | Custom career site — no public ATS API |

### 3. International Companies with German Offices

| Company | ATS | Token | Active | Notes |
|---|---|---|---|---|
| Datadog | greenhouse | datadog | YES | Confirmed |
| Mistral AI | lever | mistral | YES | Confirmed |
| MongoDB | greenhouse | mongodb | YES | Confirmed |
| HubSpot | greenhouse | hubspot | YES | Confirmed |
| Notion | ashby | notion | YES | Confirmed |
| Stripe | ashby | stripe | NO | Custom career site — no public ATS API |
| Miro | greenhouse | realtimeboardglobal | YES | Confirmed. Miro's legal name is RealtimeBoard. |
| GitLab | greenhouse | gitlab | YES | Confirmed |
| Figma | greenhouse | figma | YES | Confirmed |
| Cloudflare | greenhouse | cloudflare | YES | Confirmed |

### 4. Consulting Firms

| Company | ATS | Token | Active | Notes |
|---|---|---|---|---|
| Thoughtworks | smartrecruiters | ThoughtWorks | YES | Confirmed |
| Capgemini Invent | greenhouse | capgeminideutschlandgmbh | YES | Confirmed (eu.greenhouse.io) |
| Simon-Kucher | ashby | simon-kucher | NO | Uses Cornerstone OnDemand (csod) — unsupported |
| Publicis Sapient | lever | publicissapient | NO | Uses iCIMS — unsupported |

---

## KEYWORD STRATEGY

The scraper uses **24 broad keywords** (not the 28 specific Indeed/LinkedIn terms). Rationale: companies are already pre-filtered by relevance when we chose them. Broader keywords catch more role title variations. DeepSeek scoring handles fine-grained relevance.

**Keywords:** ai, strategy, digital, transformation, intelligence, analytics, data, consultant, operations, product, chief of staff, founder, business, advisor, manager, program, project, associate, automation, innovation, change management, stakeholder, implementation, deployment

**Location filter keywords:** germany, deutschland, munich, münchen, berlin, hamburg, frankfurt, stuttgart, cologne, köln, düsseldorf, dusseldorf, hannover, hanover, bonn, heidelberg, chemnitz, göppingen, remote, emea, europe, eu, dach

---

## N8N INTEGRATION

Added as the 4th parallel scraper in the existing "Job Pipeline" workflow:

```
                    ┌→ 1. Scrape Indeed ────┐
                    │→ 2. Scrape LinkedIn ──│
Start Pipeline ────→→ 3. Scrape Arbeitnow ─→→ Merge (Append) → Filter → Score → Cover Letters → Sheets
                    └→ 4. Scrape Companies ─┘
```

**Node config:**
- Name: "4. Scrape Companies"
- Type: Execute Command
- Command: `py -3.12 scrapers/company_scraper.py`
- Execute Once: ON
- Connected from: Start Pipeline trigger
- Connected to: Merge (Append) node

**How company jobs flow through the pipeline:**
- `company_scraper.py` outputs `raw_jobs_companies.csv` to `BASE_PATH`
- `job_filter.py` auto-detects all `raw_jobs*.csv` files and merges them
- Company jobs enter the same pipeline as Indeed/LinkedIn/Arbeitnow jobs
- Source column in Google Sheet shows e.g. `Celonis Careers` instead of `Indeed`
- No changes needed to any downstream scripts

---

## PHASE B — FUTURE (not built yet)

**What:** Add browser-based scraping for large corporates using Workday and SAP SuccessFactors (Siemens, BMW, SAP, Mercedes-Benz, Deutsche Bank, etc.)

**Why it's separate:** These ATS platforms don't have public APIs. They require a headless browser (Playwright) to load the page, enter search terms, and parse results. Slower, more brittle, higher maintenance.

**Target:** Up to 30 Tier 2 companies
**Total with Phase A:** Up to 80 Tier 1 (API) + up to 30 Tier 2 (browser) = 110 companies max

**Required tools for Phase B:**
- Playwright: `py -3.12 -m pip install playwright` then `py -3.12 -m playwright install chromium`
- Will add Tier 2 scraper functions to `company_scraper.py` (same script, new functions)
- Cost: $0 (Playwright is free and open source)

---

## TECHNICAL DECISIONS (module-specific)

| Decision | Choice | Reason |
|---|---|---|
| ATS approach (Phase A) | API-only (Greenhouse, Lever, Ashby, SmartRecruiters) | Free, fast (~1 sec/company), zero blocking risk, no browser needed |
| ATS approach (Phase B) | Browser-based (Playwright) for Workday/SuccessFactors | No public API available. Slower but works on any site. |
| Company list storage | Google Sheet "Companies" tab in existing spreadsheet | Dynamic — add companies anytime. Scraper reads sheet each run. Same credentials as core pipeline. |
| Keywords | 24 broad terms (vs. 28 specific terms for Indeed/LinkedIn) | Companies are pre-selected for relevance. Broader catches more title variations. Scorer handles fine-grained filtering. |
| Location filtering | Python keyword matching after fetching all jobs | Not all APIs support location filtering. Local filtering is reliable and consistent across all 4 ATS types. |
| Ashby API | Official REST API (`api.ashbyhq.com/posting-api/job-board/{token}`) | Old GraphQL endpoint (`jobs.ashbyhq.com/api/non-user-graphql`) was unreliable — returned null for valid tokens. Official REST API works correctly. |
| Ashby token casing | Exact case as shown in `jobs.ashbyhq.com/{token}` URL | Ashby tokens are case-sensitive. `DeepL` ≠ `deepl`. Always verify from the actual URL. |
| Disabled companies | Set active=NO in sheet (don't delete) | Keeps the record. Easy to re-enable if they switch ATS. |
| Output format | Same `raw_jobs*.csv` format as other scrapers | Zero changes needed to filter, scorer, cover letter, or sheets upload scripts. |
| Phase A company count | 32 active out of 40 initial | 8 disabled due to unsupported ATS or custom popup career pages. |

---

## COST

| Item | Cost |
|---|---|
| Phase A (API-based scraping) | $0 — all public APIs, no auth, no paid services |
| Phase B (browser-based, future) | $0 — Playwright is free and open source |
| Google Sheets API | Free (within quota) |

---

## BUGS AND FIXES (module-specific)

16. **Ashby GraphQL endpoint unreliable:** Old scraper used `jobs.ashbyhq.com/api/non-user-graphql` which returned `null` for valid tokens, causing false NOT_FOUND. Fix: switched to official REST API `api.ashbyhq.com/posting-api/job-board/{token}` (documented by Ashby, updated March 2025).
17. **Ashby tokens are case-sensitive:** `DeepL` works, `deepl` does not. `AlephAlpha` works, `alephalpha` does not. Always copy token exactly from `jobs.ashbyhq.com/{token}` URL.
18. **Taxfix token has .com suffix:** Token is `taxfix.com` (not `taxfix`). Taxfix embeds Ashby on their own domain so the token isn't visible in the standard URL.
19. **Miro's Greenhouse token is not "miro":** Legal company name is RealtimeBoard. Correct token: `realtimeboardglobal`.
20. **Capgemini token is long:** Token is `capgeminideutschlandgmbh`. Uses EU Greenhouse endpoint.
21. **Trade Republic and Zalando use custom popup career pages:** Jobs open as modal popups on their own domain — no ATS URL exposed, no public API available. Both disabled.
22. **Enpal switched from Lever to SmartRecruiters:** Old token `enpal` on Lever fails. New: SmartRecruiters with token `EnpalBV`.
23. **Aleph Alpha switched from Lever to Ashby:** Old token `alephalpha` on Lever fails. New: Ashby with token `AlephAlpha`.
24. **Personio, Merantix use Personio's own ATS:** Not supported (no public API). Both disabled.
25. **Simon-Kucher uses Cornerstone (csod):** Not supported. Disabled.
26. **Publicis Sapient uses iCIMS:** Not supported. Disabled.
27. **Stripe and AUTO1 Group use custom career sites:** No public ATS API available. Both disabled.
