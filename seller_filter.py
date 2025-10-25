#!/usr/bin/env python3
"""
Seller Filter Program
Filters center.csv file by seller and provides download functionality.
"""

import argparse
import pandas as pd
import os
import sys
from datetime import datetime
import uuid

def log(msg, enabled=True):
    """Simple logging function"""
    if enabled:
        print(msg, file=sys.stderr)

def load_center_data(file_path):
    """Load the center.csv file"""
    try:
        # Try different separators and encodings
        for sep in [';', ',', '\t']:
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(file_path, sep=sep, encoding=encoding)
                    log(f"Successfully loaded {len(df)} rows using separator '{sep}' and encoding '{encoding}'")
                    return df
                except Exception as e:
                    continue
        
        # If all attempts fail, raise an error
        raise RuntimeError("Could not load CSV file with any separator/encoding combination")
        
    except Exception as e:
        raise RuntimeError(f"Failed to load center data: {e}")

def get_unique_sellers(df):
    """Get list of unique sellers from the data"""
    # Check for seller columns (Seller Id, Seller Name, or similar)
    seller_cols = [col for col in df.columns if 'seller' in col.lower()]
    
    if not seller_cols:
        raise RuntimeError("No seller columns found in the data")
    
    # Prefer Seller Name over Seller Id if both exist
    seller_col = None
    if 'Seller Name' in seller_cols:
        seller_col = 'Seller Name'
    elif 'Seller Id' in seller_cols:
        seller_col = 'Seller Id'
    else:
        seller_col = seller_cols[0]
    
    log(f"Using seller column: {seller_col}")
    
    # Get unique sellers (excluding NaN values)
    unique_sellers = df[seller_col].dropna().unique()
    unique_sellers = sorted([str(s) for s in unique_sellers if str(s).strip()])
    
    return unique_sellers, seller_col

def filter_by_seller(df, seller_value, seller_col):
    """Filter dataframe by seller"""
    # Handle both string and numeric seller values
    if isinstance(seller_value, str):
        # Try to convert to int if possible
        try:
            seller_value_int = int(seller_value)
            filtered_df = df[df[seller_col] == seller_value_int]
        except ValueError:
            # Keep as string
            filtered_df = df[df[seller_col] == seller_value]
    else:
        filtered_df = df[df[seller_col] == seller_value]
    
    return filtered_df

def save_filtered_data(df, output_path, seller_value):
    """Save filtered data to Excel format"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save as Excel file
        df.to_excel(output_path, index=False, sheet_name='Seller Data')
        log(f"Saved {len(df)} rows to {output_path}")
        return True
    except Exception as e:
        log(f"Error saving file: {e}")
        return False

def interactive_mode(file_path):
    """Interactive mode for selecting and filtering sellers"""
    log("Loading center data...")
    df = load_center_data(file_path)
    
    log("Getting unique sellers...")
    unique_sellers, seller_col = get_unique_sellers(df)
    
    if not unique_sellers:
        log("No sellers found in the data")
        return
    
    log(f"\nFound {len(unique_sellers)} unique sellers:")
    for i, seller in enumerate(unique_sellers, 1):
        log(f"{i:3d}. {seller}")
    
    while True:
        try:
            choice = input(f"\nSelect seller (1-{len(unique_sellers)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                log("Goodbye!")
                break
            
            seller_index = int(choice) - 1
            if 0 <= seller_index < len(unique_sellers):
                selected_seller = unique_sellers[seller_index]
                log(f"\nSelected seller: {selected_seller}")
                
                # Filter data
                filtered_df = filter_by_seller(df, selected_seller, seller_col)
                log(f"Found {len(filtered_df)} records for seller '{selected_seller}'")
                
                if len(filtered_df) == 0:
                    log("No records found for this seller")
                    continue
                
                # Generate output filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_seller_name = "".join(c for c in selected_seller if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_seller_name = safe_seller_name.replace(' ', '_')
                output_filename = f"seller_{safe_seller_name}_{timestamp}.xlsx"
                output_path = os.path.join("outputs", output_filename)
                
                # Save filtered data
                if save_filtered_data(filtered_df, output_path, selected_seller):
                    log(f"✅ Filtered data saved to: {output_path}")
                    
                    # Show summary
                    log(f"\nSummary for seller '{selected_seller}':")
                    log(f"  - Total records: {len(filtered_df)}")
                    
                    # Show some key columns if they exist
                    key_cols = ['OrderDate', 'Date', 'Carrier', 'Sales Channel', 'Fulfillment Fee']
                    available_cols = [col for col in key_cols if col in filtered_df.columns]
                    
                    if available_cols:
                        log(f"  - Sample data:")
                        sample_df = filtered_df[available_cols].head(3)
                        for _, row in sample_df.iterrows():
                            log(f"    {dict(row)}")
                else:
                    log("❌ Failed to save filtered data")
                
            else:
                log(f"Invalid choice. Please enter a number between 1 and {len(unique_sellers)}")
                
        except ValueError:
            log("Invalid input. Please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            log("\nGoodbye!")
            break

def command_line_mode(file_path, seller_value, output_path=None):
    """Command line mode for filtering by specific seller"""
    log("Loading center data...")
    df = load_center_data(file_path)
    
    log("Getting unique sellers...")
    unique_sellers, seller_col = get_unique_sellers(df)
    
    # Filter data
    filtered_df = filter_by_seller(df, seller_value, seller_col)
    log(f"Found {len(filtered_df)} records for seller '{seller_value}'")
    
    if len(filtered_df) == 0:
        log(f"No records found for seller '{seller_value}'")
        log(f"Available sellers: {', '.join(unique_sellers[:10])}{'...' if len(unique_sellers) > 10 else ''}")
        return False
    
    # Generate output path if not provided
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_seller_name = "".join(c for c in str(seller_value) if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_seller_name = safe_seller_name.replace(' ', '_')
        output_filename = f"seller_{safe_seller_name}_{timestamp}.xlsx"
        output_path = os.path.join("outputs", output_filename)
    
    # Save filtered data
    if save_filtered_data(filtered_df, output_path, seller_value):
        log(f"✅ Filtered data saved to: {output_path}")
        
        # Show summary
        log(f"\nSummary for seller '{seller_value}':")
        log(f"  - Total records: {len(filtered_df)}")
        
        return True
    else:
        log("❌ Failed to save filtered data")
        return False

def main():
    parser = argparse.ArgumentParser(description="Filter center.csv by seller and export to Excel")
    parser.add_argument("--input", default="center.csv", help="Input CSV file (default: center.csv)")
    parser.add_argument("--seller", help="Seller ID or name to filter by (if not provided, interactive mode)")
    parser.add_argument("--output", help="Output Excel file path (auto-generated if not provided)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        log(f"Error: Input file '{args.input}' not found")
        return 1
    
    # Create outputs directory
    os.makedirs("outputs", exist_ok=True)
    
    try:
        if args.seller:
            # Command line mode
            success = command_line_mode(args.input, args.seller, args.output)
            return 0 if success else 1
        else:
            # Interactive mode
            interactive_mode(args.input)
            return 0
            
    except Exception as e:
        log(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
