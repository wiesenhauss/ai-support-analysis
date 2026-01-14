#!/usr/bin/env python3
"""
Check CSV column names to diagnose import issues.
Usage: python check_csv_columns.py path/to/your/file.csv
"""

import sys
import pandas as pd

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_csv_columns.py path/to/your/file.csv")
        print("\nOr drag and drop a CSV file onto this script")
        input("\nPress Enter to exit...")
        return
    
    csv_path = sys.argv[1]
    print(f"\nAnalyzing: {csv_path}\n")
    
    try:
        df = pd.read_csv(csv_path, nrows=100)  # Just read first 100 rows for speed
        
        print("=" * 60)
        print("ALL COLUMN NAMES IN CSV:")
        print("=" * 60)
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:3}. '{col}'")
        
        print("\n" + "=" * 60)
        print("COLUMNS THAT MIGHT BE CSAT-RELATED:")
        print("=" * 60)
        csat_keywords = ['csat', 'satisfaction', 'rating', 'score', 'survey']
        found_csat = []
        for col in df.columns:
            if any(kw in col.lower() for kw in csat_keywords):
                # Show sample values
                sample_values = df[col].dropna().head(5).tolist()
                found_csat.append((col, sample_values))
                print(f"\n  Column: '{col}'")
                print(f"  Sample values: {sample_values}")
        
        if not found_csat:
            print("\n  ⚠️  No CSAT-related columns found!")
            print("  The CSV might not have CSAT data, or it uses a different column name.")
        
        print("\n" + "=" * 60)
        print("RECOMMENDATION:")
        print("=" * 60)
        
        # Check for the expected column
        expected_names = ['CSAT Rating', 'csat_rating', 'CSAT_Rating', 'CSAT']
        found_expected = None
        for name in expected_names:
            if name in df.columns:
                found_expected = name
                break
            for col in df.columns:
                if col.lower() == name.lower():
                    found_expected = col
                    break
        
        if found_expected:
            print(f"  ✓ Found expected column: '{found_expected}'")
            sample = df[found_expected].dropna().head(10).tolist()
            print(f"  Sample values: {sample}")
        else:
            print("  ⚠️  Could not find 'CSAT Rating' column!")
            if found_csat:
                print(f"\n  The closest match is: '{found_csat[0][0]}'")
                print(f"  Please let me know this column name so I can add it to the import mapping.")
            
    except Exception as e:
        print(f"Error reading CSV: {e}")

if __name__ == "__main__":
    main()
