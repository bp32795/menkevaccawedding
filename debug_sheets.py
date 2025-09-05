"""
Debug Google Sheets columns and data
This script helps debug the exact column structure in your Google Sheet
"""

import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_google_sheets_client, SPREADSHEET_ID

def debug_google_sheets():
    """Debug the Google Sheets structure and data"""
    load_dotenv()
    
    print("🔍 Debugging Google Sheets Structure")
    print("=" * 50)
    
    try:
        client = get_google_sheets_client()
        if not client:
            print("❌ Could not connect to Google Sheets")
            return
        
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # Get all values to see raw structure
        all_values = sheet.get_all_values()
        
        if not all_values:
            print("❌ No data found in sheet")
            return
        
        # Show headers
        headers = all_values[0]
        print("📋 Column Headers:")
        for i, header in enumerate(headers, 1):
            print(f"   Column {i}: '{header}'")
        
        print("\n📊 Sample Data (first 3 rows):")
        for i, row in enumerate(all_values[1:4], 2):  # Skip header, show first 3 data rows
            print(f"\n   Row {i}:")
            for j, value in enumerate(row):
                if j < len(headers):
                    print(f"     {headers[j]}: '{value}'")
        
        # Get records using get_all_records to see how gspread interprets it
        print("\n🔧 How gspread interprets the data:")
        records = sheet.get_all_records()
        
        if records:
            first_record = records[0]
            print("   First record keys:")
            for key in first_record.keys():
                print(f"     '{key}': '{first_record[key]}'")
        
        # Show column mapping for updates
        print("\n🎯 Column Mapping for Updates:")
        expected_columns = [
            "URL",
            "Priority", 
            "Image URL",
            "Price",
            "Bought?",
            "Item Title (if not entered, website will try to make one)",
            "Bought by"
        ]
        
        for i, expected in enumerate(expected_columns, 1):
            actual = headers[i-1] if i <= len(headers) else "MISSING"
            match = "✅" if expected == actual else "❌"
            print(f"   Column {i}: Expected '{expected}' → Actual '{actual}' {match}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    debug_google_sheets()
