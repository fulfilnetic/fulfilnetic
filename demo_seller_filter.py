#!/usr/bin/env python3
"""
Demo script for seller_filter.py
Shows how to use the seller filter program programmatically.
"""

import subprocess
import os
import sys

def run_command(cmd, description):
    """Run a command and show the output"""
    print(f"\n{'='*60}")
    print(f"DEMO: {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Return code: {result.returncode}")
    except Exception as e:
        print(f"Error running command: {e}")

def main():
    print("Seller Filter Program Demo")
    print("This demo shows how to use seller_filter.py to filter center.csv by seller")
    
    # Check if center.csv exists
    if not os.path.exists("center.csv"):
        print("Error: center.csv not found in current directory")
        print("Please make sure center.csv is in the same directory as this script")
        return 1
    
    # Demo 1: Show help
    run_command("python3 seller_filter.py --help", "Show help information")
    
    # Demo 2: Filter by seller ID
    run_command("python3 seller_filter.py --seller 4297 --verbose", "Filter by seller ID (4297)")
    
    # Demo 3: Filter by seller name
    run_command("python3 seller_filter.py --seller 'De online tandarts' --verbose", "Filter by seller name")
    
    # Demo 4: Filter with custom output file
    run_command("python3 seller_filter.py --seller 'Medies BV' --output outputs/custom_medies.xlsx --verbose", "Filter with custom output file")
    
    # Show generated files
    print(f"\n{'='*60}")
    print("GENERATED FILES")
    print(f"{'='*60}")
    
    outputs_dir = "outputs"
    if os.path.exists(outputs_dir):
        files = [f for f in os.listdir(outputs_dir) if f.startswith("seller_") and f.endswith(".xlsx")]
        if files:
            print("Generated seller filter Excel files:")
            for file in sorted(files):
                file_path = os.path.join(outputs_dir, file)
                file_size = os.path.getsize(file_path)
                print(f"  - {file} ({file_size:,} bytes)")
        else:
            print("No seller filter Excel files found")
    else:
        print("Outputs directory not found")
    
    print(f"\n{'='*60}")
    print("USAGE EXAMPLES")
    print(f"{'='*60}")
    print("1. Interactive mode (shows list of sellers to choose from):")
    print("   python3 seller_filter.py")
    print()
    print("2. Filter by seller ID:")
    print("   python3 seller_filter.py --seller 4297")
    print()
    print("3. Filter by seller name:")
    print("   python3 seller_filter.py --seller 'De online tandarts'")
    print()
    print("4. Filter with custom output file:")
    print("   python3 seller_filter.py --seller 'Medies BV' --output my_filtered_data.xlsx")
    print()
    print("5. Verbose output:")
    print("   python3 seller_filter.py --seller 4297 --verbose")
    print()
    print("6. Use different input file:")
    print("   python3 seller_filter.py --input my_data.csv --seller 1234")

if __name__ == "__main__":
    sys.exit(main())
