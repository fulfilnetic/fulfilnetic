#!/usr/bin/env python3
"""
Teamleader Invoice Converter
Converts aggregated fulfillment data to Teamleader import format for billing customers.
"""

import argparse
import pandas as pd
import numpy as np
from datetime import date, datetime
import os
import sys

def log(msg, enabled):
    if enabled:
        print(msg, file=sys.stderr)

def load_aggregated_data(input_file, sheet_name="Totals_by_Seller"):
    """Load the aggregated data from aggregatev1.py output"""
    try:
        df = pd.read_excel(input_file, sheet_name=sheet_name)
        log(f"Loaded {len(df)} rows from {sheet_name}", True)
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to load aggregated data: {e}")

def create_teamleader_invoice_data(df, invoice_date=None, start_invoice_number=1):
    """
    Convert aggregated fulfillment data to Teamleader format
    Creates separate lines for each service type (Fulfillment Fee, Storage Costs, PIM Costs)
    
    Teamleader columns:
    1. Naam van de klant (Customer name)
    2. Datum (Date) - YYYY-MM-DD format
    3. Bedrijfsentiteit (Company entity)
    4. Nummer (Number) - same for all services of same customer
    5. Betaald (Paid)
    6. Totale Prijs met btw (Ter controle) (Total price with VAT for control)
    7. Permanent (Permanent)
    8. Betalingstermijn (Payment term)
    9. Opmerkingen (Remarks)
    10. Naam item (Service name: Fulfillment Fee, Opslagkosten, PIM Costs)
    11. Prijs item excl. Btw (Exact price from aggregated data)
    12. Btw-tarief item (VAT rate item)
    13. Aantal items (Number of items)
    14. Tussentitel item (Subtotal item)
    15. Velden om te matchen met bedrijven (Company matching fields)
    16. Velden om te matchen met Projecten (Project matching fields)
    """
    
    if invoice_date is None:
        invoice_date = date.today()
    
    # Filter out TOTAL row if present
    df_clean = df[df['Seller'] != 'TOTAL'].copy()
    
    teamleader_data = []
    invoice_counter = start_invoice_number
    
    for _, row in df_clean.iterrows():
        seller_name = row.get('Seller Name', row.get('Seller', ''))
        seller_id = row.get('Seller', '')
        
        # Skip rows with zero or missing totals
        grand_total = row.get('Grand Total', 0)
        if pd.isna(grand_total) or grand_total == 0:
            continue
        
        # Create sequential invoice number (same for all services of this customer)
        invoice_number = invoice_counter
        invoice_counter += 1
        
        # Get exact prices from aggregated data
        fulfillment_fee = row.get('Fulfilment Fee Total', 0)
        storage_cost = row.get('Storage Cost', 0)
        pim_cost = row.get('PIM Cost', 0)
        
        # Create separate lines for each service that has a value > 0
        services = []
        
        if not pd.isna(fulfillment_fee) and fulfillment_fee > 0:
            services.append({
                'name': 'Fulfilment Fee',
                'price': fulfillment_fee
            })
        
        if not pd.isna(storage_cost) and storage_cost > 0:
            services.append({
                'name': 'Opslagkosten',
                'price': storage_cost
            })
        
        if not pd.isna(pim_cost) and pim_cost > 0:
            services.append({
                'name': 'PIM-kosten',
                'price': pim_cost
            })
        
        # If no services found, skip this customer
        if not services:
            continue
        
        # Create a line for each service
        for service in services:
            teamleader_row = {
                'Naam van de klant': seller_name,
                'Datum': invoice_date.strftime('%Y-%m-%d'),  # YYYY-MM-DD format
                'Bedrijfsentiteit': '',  # Column C - always empty
                'Nummer': invoice_number,  # Same invoice number for all services of this customer
                'Betaald': 0,  # Column E - always 0
                'Totale Prijs met btw (Ter controle)': '',  # Column F - always empty
                'Permanent': 1,  # Column G - always 1
                'Betalingstermijn': 7,  # Column H - always 7
                'Opmerkingen': '',  # Column I - always empty
                'Naam item': service['name'],  # Column J - service name
                'Prijs item excl. Btw': round(service['price'], 2),  # Column K - exact price from data
                'Btw-tarief item': 21,  # Column L - always 21
                'Aantal items': 1,  # Column M - always 1
                'Tussentitel item': '',  # Column N - always empty
                'Velden om te matchen met bedrijven [Extern ID / Bedrijf[Custom Field: 1 lijn tekst]]': '',  # Column O - always empty
                'Velden om te matchen met Projecten [Project Nummer / Project Custom Field: 1 lijn tekst]]': ''  # Column P - always empty
            }
            
            teamleader_data.append(teamleader_row)
    
    return pd.DataFrame(teamleader_data)

def main():
    parser = argparse.ArgumentParser(description="Convert aggregated fulfillment data to Teamleader import format")
    parser.add_argument("--input", required=True, help="Input Excel file from aggregatev1.py")
    parser.add_argument("--output", default="import_teamleader.xlsx", help="Output Excel file for Teamleader")
    parser.add_argument("--sheet-name", default="Totals_by_Seller", help="Sheet name to read from input file")
    parser.add_argument("--invoice-date", help="Invoice date (YYYY-MM-DD format)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Get invoice date from user
    if args.invoice_date:
        try:
            invoice_date = datetime.strptime(args.invoice_date, '%Y-%m-%d').date()
        except ValueError:
            raise RuntimeError("Invalid date format. Use YYYY-MM-DD")
    else:
        while True:
            date_input = input("Enter invoice date (YYYY-MM-DD format): ").strip()
            try:
                invoice_date = datetime.strptime(date_input, '%Y-%m-%d').date()
                break
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD format.")
    
    # Get starting invoice number from user
    while True:
        try:
            start_number = int(input("Enter starting invoice number: ").strip())
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Load aggregated data
    df = load_aggregated_data(args.input, args.sheet_name)
    
    # Create Teamleader data (separate lines for each service)
    teamleader_df = create_teamleader_invoice_data(df, invoice_date, start_number)
    log("Created invoices with separate lines for each service", args.verbose)
    
    # Write output
    teamleader_df.to_excel(args.output, index=False, sheet_name="Teamleader Import")
    
    log(f"Created Teamleader import file: {args.output}", args.verbose)
    log(f"Generated {len(teamleader_df)} invoice lines for {teamleader_df['Naam van de klant'].nunique()} customers", args.verbose)
    
    # Show summary
    if args.verbose:
        print("\nSummary:")
        print(f"Total customers: {teamleader_df['Naam van de klant'].nunique()}")
        print(f"Total invoice lines: {len(teamleader_df)}")
        print(f"VAT rate: 21% (fixed)")
        print(f"Payment term: 7 days (fixed)")

if __name__ == "__main__":
    main()
