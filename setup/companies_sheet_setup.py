# companies_sheet_setup.py
# One-time setup: Creates the "Companies" tab in your existing Job Tracker Google Sheet
# and populates it with the initial 40 companies.
#
# Required environment variables (set these before running):
#   GOOGLE_SPREADSHEET_ID    - your Google Sheet ID
#   GOOGLE_CREDENTIALS_PATH  - path to your google_credentials.json file
#
# Command: py -3.12 companies_sheet_setup.py
# Run this ONCE. After that, add companies manually in Google Sheets.

import gspread
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ---------- CONFIG ----------
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
SHEET_NAME = "Companies"

if not SPREADSHEET_ID:
    print("ERROR: GOOGLE_SPREADSHEET_ID environment variable is not set.")
    print("Set it with: setx GOOGLE_SPREADSHEET_ID \"your-spreadsheet-id\"")
    sys.exit(1)

# ---------- COMPANY DATA ----------
# Format: [company_name, career_url, ats_type, board_token, category, scope_tags, active, notes]
#
# ats_type: greenhouse / lever / ashby / smartrecruiters
# board_token: the identifier used in the ATS API URL
#   - Greenhouse: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
#   - Lever: https://api.lever.co/v0/postings/{board_token}
#   - Ashby: https://api.ashbyhq.com/posting-api/job-board/{board_token} (official REST API)
#   - SmartRecruiters: https://api.smartrecruiters.com/v1/companies/{board_token}/postings

COMPANIES = [
    # ===== 1. AI/TECH STARTUPS & SCALEUPS IN GERMANY =====
    ["Celonis", "https://www.celonis.com/careers/", "greenhouse", "celonis", "AI Startup", "GenAI, BI, Consulting", "YES", "Process mining + AI. Munich HQ. Confirmed."],
    ["DeepL", "https://www.deepl.com/en/careers/", "ashby", "DeepL", "AI Startup", "GenAI, BI", "YES", "AI translation. Cologne. Confirmed Ashby."],
    ["Personio", "https://www.personio.com/about-personio/careers/", "greenhouse", "personio", "AI Startup", "CoS, BI, Consulting", "NO", "Uses own Personio ATS - not supported. Disabled."],
    ["N26", "https://n26.com/en/careers", "greenhouse", "n26", "AI Startup", "BI, CoS, GenAI", "YES", "Neobank. Berlin. Confirmed Greenhouse."],
    ["Trade Republic", "https://traderepublic.com/careers", "greenhouse", "TradeRepublic", "AI Startup", "CoS, BI", "NO", "Custom popup career page - no public ATS API. Disabled."],
    ["Scalable Capital", "https://www.scalable.capital/en/careers", "smartrecruiters", "ScalableGmbH", "AI Startup", "BI, CoS", "YES", "Fintech. Munich. Confirmed SmartRecruiters."],
    ["FlixBus (Flix)", "https://www.flixbus.com/company/jobs", "greenhouse", "flix", "AI Startup", "BI, Consulting, CoS", "YES", "Mobility unicorn. Munich. Confirmed Greenhouse."],
    ["Contentful", "https://www.contentful.com/careers/", "greenhouse", "contentful", "AI Startup", "Consulting, GenAI", "YES", "CMS platform. Berlin. Confirmed Greenhouse."],
    ["Staffbase", "https://staffbase.com/en/career", "greenhouse", "staffbase", "AI Startup", "GenAI, CoS", "YES", "Employee comms + AI. Chemnitz. Confirmed Greenhouse."],
    ["Helsing", "https://helsing.ai/careers", "greenhouse", "helsing", "AI Startup", "GenAI, CoS", "YES", "Defense AI. Munich. Confirmed Greenhouse (long jobId format)."],
    ["FINN", "https://www.finn.auto/careers", "lever", "finn", "AI Startup", "CoS, BI", "YES", "Car subscription. Munich. Confirmed Lever."],
    ["Parloa", "https://www.parloa.com/careers/", "greenhouse", "parloa", "AI Startup", "GenAI, Consulting", "YES", "Conversational AI. Berlin. Confirmed Greenhouse (eu.greenhouse.io)."],
    ["Aleph Alpha", "https://aleph-alpha.com/careers/", "ashby", "AlephAlpha", "AI Startup", "GenAI, Consulting", "YES", "Enterprise AI. Heidelberg. Confirmed Ashby. Token is AlephAlpha."],
    ["Merantix", "https://merantix.com/careers/", "lever", "merantix", "AI Startup", "GenAI, CoS", "NO", "Uses Personio - not supported. Disabled."],
    ["commercetools", "https://commercetools.com/careers", "greenhouse", "commercetools", "AI Startup", "Consulting, BI", "YES", "Commerce platform. Munich. Confirmed Greenhouse."],
    ["Taxfix", "https://taxfix.de/en/careers/", "ashby", "taxfix.com", "AI Startup", "CoS, BI", "YES", "Fintech. Berlin. Confirmed Ashby. Token is taxfix.com (with .com)."],
    ["Enpal", "https://www.enpal.de/karriere", "smartrecruiters", "EnpalBV", "AI Startup", "CoS, BI", "YES", "Green energy unicorn. Berlin. Confirmed SmartRecruiters."],
    ["Omio", "https://www.omio.com/careers", "smartrecruiters", "Omio1", "AI Startup", "BI, GenAI", "YES", "Travel tech. Berlin. Confirmed SmartRecruiters."],

    # ===== 2. LARGE GERMAN CORPORATES =====
    ["Bosch", "https://www.bosch.com/careers/", "smartrecruiters", "BoschGroup", "Corporate", "GenAI, BI, Consulting", "YES", "Stuttgart. Confirmed SmartRecruiters."],
    ["Continental", "https://www.continental.com/en/career/", "smartrecruiters", "Continental", "Corporate", "BI, Consulting", "YES", "Auto + tech. Hannover. Confirmed SmartRecruiters."],
    ["Zalando", "https://jobs.zalando.com/en/", "greenhouse", "zalando", "Corporate", "BI, GenAI, CoS", "NO", "Custom popup career page - no public ATS API. Disabled."],
    ["Delivery Hero", "https://careers.deliveryhero.com/", "smartrecruiters", "DeliveryHero", "Corporate", "BI, CoS", "YES", "Food delivery. Berlin. Confirmed SmartRecruiters."],
    ["HelloFresh", "https://www.hellofreshgroup.com/en/careers/", "greenhouse", "hellofresh", "Corporate", "BI, CoS", "YES", "Food tech. Berlin. Confirmed Greenhouse."],
    ["TeamViewer", "https://www.teamviewer.com/en/careers/", "smartrecruiters", "TeamViewer", "Corporate", "GenAI, Consulting", "YES", "Near Stuttgart. Confirmed SmartRecruiters."],
    ["trivago", "https://company.trivago.com/careers/", "greenhouse", "trivago", "Corporate", "BI, GenAI", "YES", "Travel tech. Duesseldorf. Confirmed Greenhouse."],
    ["AUTO1 Group", "https://www.auto1-group.com/careers/", "lever", "auto1", "Corporate", "BI, CoS", "NO", "Uses own career site - no public ATS API. Disabled."],

    # ===== 3. INTERNATIONAL COMPANIES WITH GERMAN OFFICES =====
    ["Datadog", "https://www.datadoghq.com/careers/", "greenhouse", "datadog", "International", "Consulting, GenAI", "YES", "Observability. Berlin office. Confirmed Greenhouse."],
    ["Mistral AI", "https://mistral.ai/careers/", "lever", "mistral", "International", "GenAI, Consulting", "YES", "French AI leader. Munich office. Confirmed Lever."],
    ["MongoDB", "https://www.mongodb.com/company/careers", "greenhouse", "mongodb", "International", "Consulting, GenAI", "YES", "Database + AI. Munich office. Confirmed Greenhouse."],
    ["HubSpot", "https://www.hubspot.com/careers", "greenhouse", "hubspot", "International", "Consulting, BI", "YES", "CRM/marketing. Berlin office. Confirmed Greenhouse."],
    ["Notion", "https://www.notion.so/careers", "ashby", "notion", "International", "GenAI, CoS", "YES", "Productivity + AI. Berlin office. Confirmed Ashby."],
    ["Stripe", "https://stripe.com/jobs", "ashby", "stripe", "International", "CoS, BI", "NO", "Uses own career site - no public ATS API. Disabled."],
    ["Miro", "https://miro.com/careers/", "greenhouse", "miro", "International", "GenAI, Consulting", "YES", "Collaboration + AI. Berlin office. Confirmed Greenhouse."],
    ["GitLab", "https://about.gitlab.com/jobs/", "greenhouse", "gitlab", "International", "GenAI, Consulting", "YES", "DevOps + AI. Remote-first, hires in DE. Confirmed Greenhouse."],
    ["Figma", "https://www.figma.com/careers/", "greenhouse", "figma", "International", "GenAI, CoS", "YES", "Design tool + AI. Berlin office. Confirmed Greenhouse."],
    ["Cloudflare", "https://www.cloudflare.com/careers/", "greenhouse", "cloudflare", "International", "Consulting, GenAI", "YES", "Infrastructure + AI. Munich office. Confirmed Greenhouse."],

    # ===== 4. CONSULTING FIRMS =====
    ["Thoughtworks", "https://www.thoughtworks.com/careers", "smartrecruiters", "ThoughtWorks", "Consulting", "Consulting, GenAI", "YES", "Tech consulting. Multiple DE offices. Confirmed SmartRecruiters."],
    ["Capgemini Invent", "https://www.capgemini.com/careers/", "greenhouse", "capgeminideutschlandgmbh", "Consulting", "Consulting, GenAI", "YES", "Digital + AI consulting. Confirmed Greenhouse (eu.greenhouse.io)."],
    ["Simon-Kucher", "https://www.simon-kucher.com/en/careers", "ashby", "simon-kucher", "Consulting", "Consulting, BI", "NO", "Uses Cornerstone OnDemand (csod) - not supported. Disabled."],
    ["Publicis Sapient", "https://www.publicissapient.com/careers", "lever", "publicissapient", "Consulting", "Consulting, GenAI", "NO", "Uses iCIMS - not supported. Disabled."],
]

# ---------- MAIN ----------
def main():
    print("=" * 60)
    print("COMPANIES SHEET SETUP")
    print("=" * 60)

    # Connect to Google Sheets
    print("\nConnecting to Google Sheets...")
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        print(f"Connected to: {spreadsheet.title}")
    except Exception as e:
        print(f"ERROR connecting to Google Sheets: {e}")
        print("Make sure GOOGLE_CREDENTIALS_PATH points to your google_credentials.json file.")
        return

    # Check if "Companies" tab already exists
    existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
    if SHEET_NAME in existing_sheets:
        print(f"\nWARNING: '{SHEET_NAME}' tab already exists!")
        response = input("Do you want to DELETE it and recreate? (yes/no): ").strip().lower()
        if response != "yes":
            print("Cancelled. No changes made.")
            return
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        spreadsheet.del_worksheet(worksheet)
        print(f"Deleted existing '{SHEET_NAME}' tab.")

    # Create the "Companies" tab
    print(f"\nCreating '{SHEET_NAME}' tab...")
    worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=200, cols=8)

    # Set headers
    headers = ["company_name", "career_url", "ats_type", "board_token", "category", "scope_tags", "active", "notes"]
    worksheet.update(range_name="A1:H1", values=[headers])

    # Populate company data
    print(f"Adding {len(COMPANIES)} companies...")
    if COMPANIES:
        range_name = f"A2:H{len(COMPANIES) + 1}"
        worksheet.update(range_name=range_name, values=COMPANIES)

    # Format headers (bold)
    worksheet.format("A1:H1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
    })

    active_count = sum(1 for c in COMPANIES if c[6] == "YES")
    disabled_count = sum(1 for c in COMPANIES if c[6] == "NO")

    print(f"\nDone! '{SHEET_NAME}' tab created with {len(COMPANIES)} companies.")
    print(f"  Active (will be scraped): {active_count}")
    print(f"  Disabled (unsupported ATS): {disabled_count}")
    print(f"\nTo add a new company later, just fill in a new row in the Companies tab.")
    print(f"Set column G (active) to 'YES' for the scraper to pick it up.")

if __name__ == "__main__":
    main()
