#!/usr/bin/env python3
"""
Debug script to check CSAT values in the database.
Run this to diagnose why CSAT chart might be showing 0%.
"""

from data_store import get_data_store

def main():
    print("=" * 60)
    print("CSAT Database Debug Report")
    print("=" * 60)
    
    try:
        data_store = get_data_store()
        
        # Get basic stats
        stats = data_store.get_database_stats()
        print(f"\nDatabase: {stats['db_path']}")
        print(f"Total tickets: {stats['total_tickets']:,}")
        print(f"Total batches: {stats['total_batches']}")
        
        # Get CSAT debug info
        debug_info = data_store.debug_csat_values()
        
        print(f"\n--- CSAT Value Analysis ---")
        print(f"Unique CSAT values found: {len(debug_info['unique_values'])}")
        print(f"Tickets matching 'good': {debug_info['good_matches']:,}")
        print(f"Tickets matching 'bad': {debug_info['bad_matches']:,}")
        print(f"Total rated: {debug_info['total_rated']:,}")
        
        print(f"\n--- All unique CSAT values ---")
        for value, count in sorted(debug_info['unique_values'].items(), key=lambda x: -x[1]):
            print(f"  {value}: {count:,}")
        
        # Analysis
        print(f"\n--- Diagnosis ---")
        if debug_info['total_rated'] == 0:
            print("⚠️  NO CSAT RATINGS FOUND IN DATABASE!")
            print("\nPossible causes:")
            print("1. The 'CSAT Rating' column was not found during import")
            print("2. All CSAT values in your CSV files are empty/null")
            print("3. The CSAT column has a different name than expected")
            print("\nSolution: Delete existing batches and re-import your CSV files")
            print("The import now recognizes more column name variations.")
        else:
            satisfaction_rate = debug_info['good_matches'] / debug_info['total_rated'] * 100
            print(f"✓ Found {debug_info['total_rated']:,} rated tickets")
            print(f"✓ Expected satisfaction rate: {satisfaction_rate:.1f}%")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
