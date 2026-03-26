# Google Sheets Job Tracker — One-Time Setup Script
#
# Required environment variables:
#   GOOGLE_SPREADSHEET_ID    - your Google Sheet ID
#   GOOGLE_CREDENTIALS_PATH  - path to your google_credentials.json file
#
# Run ONCE with: py -3.12 sheets_setup.py
# This creates the headers and formatting in your Google Sheet.

import gspread
from google.oauth2.service_account import Credentials
import sys
import os

# ============================================================
# CONFIGURATION
# ============================================================

SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")

if not SPREADSHEET_ID:
    print("\n[ERROR] GOOGLE_SPREADSHEET_ID environment variable is not set.")
    print("Set it with: setx GOOGLE_SPREADSHEET_ID \"your-spreadsheet-id\"")
    print("Then close and reopen Command Prompt and run this script again.")
    sys.exit(1)

# ============================================================
# DO NOT EDIT BELOW THIS LINE
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def main():
    # --- Validate credentials file exists ---
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n[ERROR] Credentials file not found at: {CREDENTIALS_FILE}")
        print("Make sure GOOGLE_CREDENTIALS_PATH points to your google_credentials.json file.")
        sys.exit(1)

    # --- Connect to Google Sheets ---
    print("\nConnecting to Google Sheets...")
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        print(f"Connected to: {spreadsheet.title}")
    except Exception as e:
        print(f"\n[ERROR] Could not connect to Google Sheets: {e}")
        print("\nCommon fixes:")
        print("1. Make sure you shared the Google Sheet with the service account email")
        print("2. Make sure the Spreadsheet ID is correct")
        print("3. Make sure Google Sheets API and Google Drive API are enabled")
        sys.exit(1)

    # --- Set up the "Jobs" sheet ---
    print("\nSetting up the Jobs sheet...")

    # Rename the default Sheet1 to "Jobs" (or create it)
    try:
        ws = spreadsheet.sheet1
        ws.update_title("Jobs")
    except Exception:
        try:
            ws = spreadsheet.add_worksheet(title="Jobs", rows=1000, cols=20)
        except Exception:
            ws = spreadsheet.worksheet("Jobs")

    # Define headers
    headers = [
        "job_id",           # A: Auto-generated unique ID
        "title",            # B: Job title
        "company",          # C: Company name
        "url",              # D: Job posting URL
        "source",           # E: Indeed / LinkedIn / Arbeitnow / [Company] Careers
        "scope",            # F: GenAI / BI / CoS / Consulting
        "score",            # G: DeepSeek score (0-100)
        "label",            # H: apply / maybe / skip
        "model",            # I: Sonnet / Haiku (cover letter model)
        "cover_letter",     # J: Cover letter filename
        "gap_analysis",     # K: Key gaps from scoring
        "status",           # L: new / applied / skipped / rejected / interview
        "date_scraped",     # M: When the job was first found
        "date_applied",     # N: When you applied (filled manually)
        "notes"             # O: Manual notes
    ]

    # Write headers to row 1
    ws.update("A1:O1", [headers])
    print(f"Headers written: {len(headers)} columns (A through O)")

    # --- Format the header row ---
    print("Formatting header row...")

    # Bold white text on dark blue background for header row
    ws.format("A1:O1", {
        "backgroundColor": {"red": 0.15, "green": 0.3, "blue": 0.53},
        "textFormat": {
            "bold": True,
            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
            "fontSize": 10
        },
        "horizontalAlignment": "CENTER"
    })

    # Freeze the header row so it stays visible when scrolling
    ws.freeze(rows=1)

    # --- Set column widths ---
    print("Setting column widths...")

    column_widths = [
        (0, 80),    # A: job_id
        (1, 280),   # B: title
        (2, 180),   # C: company
        (3, 100),   # D: url
        (4, 90),    # E: source
        (5, 100),   # F: scope
        (6, 60),    # G: score
        (7, 70),    # H: label
        (8, 70),    # I: model
        (9, 200),   # J: cover_letter
        (10, 250),  # K: gap_analysis
        (11, 100),  # L: status
        (12, 100),  # M: date_scraped
        (13, 100),  # N: date_applied
        (14, 200),  # O: notes
    ]

    requests_body = []
    for col_index, width in column_widths:
        requests_body.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": ws.id,
                    "dimension": "COLUMNS",
                    "startIndex": col_index,
                    "endIndex": col_index + 1
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize"
            }
        })

    # --- Add conditional formatting for score column ---
    # Green for 70+ (apply), Yellow for 50-69 (maybe), Red for below 50 (skip)
    score_col_index = 6  # Column G (0-based)

    requests_body.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": ws.id, "startColumnIndex": score_col_index, "endColumnIndex": score_col_index + 1, "startRowIndex": 1}],
                "booleanRule": {
                    "condition": {"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": "70"}]},
                    "format": {"backgroundColor": {"red": 0.72, "green": 0.88, "blue": 0.62}}
                }
            },
            "index": 0
        }
    })

    requests_body.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": ws.id, "startColumnIndex": score_col_index, "endColumnIndex": score_col_index + 1, "startRowIndex": 1}],
                "booleanRule": {
                    "condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "50"}, {"userEnteredValue": "69"}]},
                    "format": {"backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.6}}
                }
            },
            "index": 1
        }
    })

    requests_body.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": ws.id, "startColumnIndex": score_col_index, "endColumnIndex": score_col_index + 1, "startRowIndex": 1}],
                "booleanRule": {
                    "condition": {"type": "NUMBER_LESS", "values": [{"userEnteredValue": "50"}]},
                    "format": {"backgroundColor": {"red": 0.96, "green": 0.7, "blue": 0.67}}
                }
            },
            "index": 2
        }
    })

    # --- Add conditional formatting for status column ---
    status_col_index = 11  # Column L (0-based)

    status_colors = {
        "applied":   {"red": 0.72, "green": 0.88, "blue": 0.62},
        "interview": {"red": 0.55, "green": 0.78, "blue": 0.95},
        "skipped":   {"red": 0.85, "green": 0.85, "blue": 0.85},
        "rejected":  {"red": 0.96, "green": 0.7, "blue": 0.67},
    }

    for status_text, color in status_colors.items():
        requests_body.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": ws.id, "startColumnIndex": status_col_index, "endColumnIndex": status_col_index + 1, "startRowIndex": 1}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": status_text}]},
                        "format": {"backgroundColor": color}
                    }
                },
                "index": 0
            }
        })

    # --- Add data validation dropdown for status column ---
    requests_body.append({
        "setDataValidation": {
            "range": {"sheetId": ws.id, "startColumnIndex": status_col_index, "endColumnIndex": status_col_index + 1, "startRowIndex": 1, "endRowIndex": 1000},
            "rule": {
                "condition": {
                    "type": "ONE_OF_LIST",
                    "values": [
                        {"userEnteredValue": "new"},
                        {"userEnteredValue": "applied"},
                        {"userEnteredValue": "skipped"},
                        {"userEnteredValue": "rejected"},
                        {"userEnteredValue": "interview"},
                        {"userEnteredValue": "offer"}
                    ]
                },
                "showCustomUi": True,
                "strict": False
            }
        }
    })

    # Execute all formatting requests in one batch
    if requests_body:
        spreadsheet.batch_update({"requests": requests_body})

    # --- Create a "Stats" sheet for daily summary ---
    print("Creating Stats sheet...")
    try:
        stats_ws = spreadsheet.add_worksheet(title="Stats", rows=100, cols=10)
    except Exception:
        stats_ws = spreadsheet.worksheet("Stats")

    stats_headers = ["date", "total_jobs", "apply_count", "maybe_count", "skip_count", "cover_letters_generated", "applications_sent"]
    stats_ws.update("A1:G1", [stats_headers])
    stats_ws.format("A1:G1", {
        "backgroundColor": {"red": 0.15, "green": 0.3, "blue": 0.53},
        "textFormat": {
            "bold": True,
            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
            "fontSize": 10
        },
        "horizontalAlignment": "CENTER"
    })
    stats_ws.freeze(rows=1)

    # --- Done ---
    print("\n" + "=" * 50)
    print("SETUP COMPLETE!")
    print("=" * 50)
    print(f"\nYour Google Sheet is ready: {spreadsheet.title}")
    print("\nWhat was created:")
    print("  - 'Jobs' sheet with 15 columns (A-O)")
    print("  - Frozen header row (stays visible when scrolling)")
    print("  - Score column: green (70+), yellow (50-69), red (<50)")
    print("  - Status column: dropdown with color coding")
    print("  - 'Stats' sheet for daily summary tracking")
    print(f"\nSheet URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
    print("\nNext: Run sheets_upload.py to push your scored jobs into this sheet.")


if __name__ == "__main__":
    main()
