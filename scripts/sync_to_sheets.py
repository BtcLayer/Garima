import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Configuration
CSV_FILE = "storage/dashboard_upload.csv"
JSON_KEYFILE = "service_account.json"
SHEET_NAME = "My Trading Dashboard" # Make sure this matches your Sheet title!

def sync_to_sheets():
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: {CSV_FILE} not found.")
        return

    try:
        # Define the scope
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Authenticate
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEYFILE, scope)
        client = gspread.authorize(creds)

        # Open the sheet
        sheet = client.open(SHEET_NAME).sheet1

        # Load CSV data
        df = pd.read_csv(CSV_FILE).fillna("")
        
        # Clear existing data and update with new data (including headers)
        data = [df.columns.values.tolist()] + df.values.tolist()
        sheet.clear()
        sheet.update('A1', data)

        print("-" * 30)
        print(f"✅ Success! Google Sheet '{SHEET_NAME}' has been updated.")
        print(f"📊 Rows uploaded: {len(df)}")
        print("-" * 30)

    except Exception as e:
        print(f"❌ Google Sheets Sync Failed: {e}")

if __name__ == "__main__":
    sync_to_sheets()