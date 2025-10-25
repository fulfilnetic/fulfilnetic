#!/usr/bin/env python3
"""
Aggregate Fulfilment Fee by Seller.

Now supports CSV input:
- If --input points to a .csv, the program will first save an .xlsx copy,
  then continue the normal flow on that .xlsx.

Usage:
  python aggregate_fulfilment_fees.py \
    --input "/path/to/file.csv" \
    --output "/path/to/output.xlsx" \
    --verbose

Optional:
  --sheet-name "YourSheet"        # for Excel inputs
  --seller-col "Seller"
  --seller-name-col "Seller Name"
  --fee-col "Fulfilment Fee"
  --csv                            # also write a CSV beside the Excel
  --encoding "utf-8-sig"          # CSV encoding
  --verbose                        # print progress info
"""

import argparse
import os
import sys
import re
import pandas as pd
import numpy as np

def log(msg, enabled):
    if enabled:
        print(msg, file=sys.stderr)

def detect_delimiter(sample, candidates=None):
    if candidates is None:
        candidates = [",", ";", "\t", "|"]
    counts = {d: sample.count(d) for d in candidates}
    # pick the delimiter with max occurrences
    return max(counts, key=counts.get)

def load_input(input_path, encoding=None, verbose=False, sheet_name=None):
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".csv":
        # Read first 4096 bytes to guess delimiter
        with open(input_path, "rb") as fh:
            raw = fh.read(4096)
        # try bytes decode
        guessed = None
        for enc in [encoding, "utf-8-sig", "utf-8", "latin-1"]:
            if not enc:
                continue
            try:
                sample = raw.decode(enc, errors="replace")
                guessed = enc
                break
            except Exception:
                continue
        if not guessed:
            # fallback utf-8-sig
            guessed = "utf-8-sig"
            sample = raw.decode(guessed, errors="replace")

        delim = detect_delimiter(sample)
        log(f"[csv] encoding={guessed}, delimiter={repr(delim)}", verbose)

        df = pd.read_csv(input_path, encoding=guessed, sep=delim)
        # Save as xlsx first
        xlsx_copy = os.path.splitext(input_path)[0] + ".xlsx"
        with pd.ExcelWriter(xlsx_copy, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
        log(f"[csv] written xlsx copy: {xlsx_copy}", verbose)
        # Return the DataFrame and metadata pretending it's from Excel
        return df, "Sheet1", xlsx_copy

    elif ext in [".xlsx", ".xlsm", ".xls"]:
        xls = pd.ExcelFile(input_path)
        if sheet_name:
            df = pd.read_excel(input_path, sheet_name=sheet_name)
            return df, sheet_name, input_path
        else:
            # leave sheet detection to later
            return None, None, input_path
    else:
        raise RuntimeError(f"Unsupported input extension: {ext}")

def detect_sheet_and_columns_from_excel(xlsx_path, verbose=False):
    """
    Find the first sheet that contains columns for seller, seller name, and fulfilment fee.
    Returns: (sheet_name, seller_col, seller_name_col, fee_col, df)
    """
    xls = pd.ExcelFile(xlsx_path)
    for sh in xls.sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sh)
        cols = [str(c).strip() for c in df.columns]
        low = [c.lower() for c in cols]

        seller_idx = None
        seller_name_idx = None
        fee_idx = None

        for i, c in enumerate(low):
            if 'seller' in c and seller_idx is None:
                seller_idx = i
            if ('seller' in c and 'name' in c) or c.strip() == 'seller name':
                if seller_name_idx is None:
                    seller_name_idx = i
            if (('fulfil' in c or 'fulfill' in c) and 'fee' in c) or c.strip() in ['fulfilment fee', 'fulfillment fee']:
                if fee_idx is None:
                    fee_idx = i

        # If no seller_name col, fall back to any "name" column
        if seller_name_idx is None:
            for i, c in enumerate(low):
                if 'name' in c:
                    seller_name_idx = i
                    break

        if seller_idx is not None and fee_idx is not None:
            # Map back to original-cased names
            df.columns = cols
            seller_col = cols[seller_idx]
            seller_name_col = cols[seller_name_idx] if seller_name_idx is not None else None
            fee_col = cols[fee_idx]
            log(f"[detect] Using sheet '{sh}' with columns -> Seller: '{seller_col}', Seller Name: '{seller_name_col}', Fee: '{fee_col}'", verbose)
            return sh, seller_col, seller_name_col, fee_col, df

    raise RuntimeError("No sheet with Seller, Seller Name, and Fulfilment Fee columns detected. Provide --sheet-name and column args explicitly.")

def smart_to_float(s):
    """
    Robust numeric parsing for currency-like strings.
    Rules:
      - Strip currency symbols and spaces.
      - If both '.' and ',' exist, infer decimal by rightmost separator:
          e.g. '1.234,56' -> thousands '.', decimal ','  => 1234.56
                '1,234.56' -> thousands ',', decimal '.' => 1234.56
      - If only ',' exists -> treat as decimal comma.
      - If only '.' exists -> treat as decimal point.
    """
    if pd.isna(s):
        return np.nan
    t = str(s).strip().replace("€", "").replace(" ", "")
    if t == "":
        return np.nan

    has_dot = "." in t
    has_comma = "," in t

    if has_dot and has_comma:
        last_dot = t.rfind(".")
        last_comma = t.rfind(",")
        if last_comma > last_dot:
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif has_comma and not has_dot:
        t = t.replace(",", ".")
    # else: keep as-is

    t = re.sub(r"[^0-9\.\-]", "", t)
    try:
        return float(t)
    except ValueError:
        return np.nan

def aggregate(df, seller_col, seller_name_col, fee_col):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    # Validate required columns exist
    missing = [c for c in [seller_col, fee_col] if c and c not in df.columns]
    if missing:
        raise RuntimeError(f"Columns not found: {missing}. Available: {list(df.columns)}")
    if seller_name_col and seller_name_col not in df.columns:
        seller_name_col = None

    df[fee_col] = df[fee_col].apply(smart_to_float)

    agg = (
        df.groupby(seller_col, dropna=False)
        .agg(
            **{
                "Seller Name": (seller_name_col, lambda s: s.dropna().iloc[0] if seller_name_col and not s.dropna().empty else None),
                "Fulfilment Fee Total": (fee_col, "sum"),
                "Row Count": (fee_col, "size"),
            }
        )
        .reset_index()
        .rename(columns={seller_col: "Seller"})
        .sort_values("Fulfilment Fee Total", ascending=False, na_position="last")
    )
    return agg, df

def main():
    ap = argparse.ArgumentParser(description="Aggregate Fulfilment Fee by Seller.")
    ap.add_argument("--input", required=True, help="Path to input Excel or CSV file")
    ap.add_argument("--output", required=True, help="Path to output Excel file")
    ap.add_argument("--sheet-name", default=None, help="Sheet name to read (Excel only)")
    ap.add_argument("--seller-col", default=None, help="Seller column name")
    ap.add_argument("--seller-name-col", default=None, help="Seller Name column name")
    ap.add_argument("--fee-col", default=None, help="Fulfilment Fee column name")
    ap.add_argument("--csv", action="store_true", help="Also write CSV for the totals")
    ap.add_argument("--encoding", default=None, help="CSV encoding hint (e.g., utf-8-sig)")
    ap.add_argument("--verbose", action="store_true", help="Verbose logs to stderr")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input not found: {args.input}")

    # Load input
    df, detected_sheet, effective_input = load_input(args.input, encoding=args.encoding, verbose=args.verbose, sheet_name=args.sheet_name)
    seller_col = args.seller_col
    seller_name_col = args.seller_name_col
    fee_col = args.fee_col
    sheet_to_use = detected_sheet or args.sheet_name

    if df is None:
        # Excel path with no explicit sheet provided -> detect sheet + columns
        sh, seller_col_auto, seller_name_col_auto, fee_col_auto, df = detect_sheet_and_columns_from_excel(effective_input, verbose=args.verbose)
        sheet_to_use = sh
        seller_col = seller_col or seller_col_auto
        seller_name_col = seller_name_col or seller_name_col_auto
        fee_col = fee_col or fee_col_auto
    else:
        # DataFrame came from CSV or explicit sheet, so if columns not provided, try to auto-detect on this df
        cols = [str(c).strip() for c in df.columns]
        low = [c.lower() for c in cols]
        if not seller_col:
            seller_col = next((cols[i] for i, c in enumerate(low) if 'seller' in c), None)
        if not seller_name_col:
            seller_name_col = next((cols[i] for i, c in enumerate(low) if ('seller' in c and 'name' in c) or c == 'seller name'), None)
            if seller_name_col is None:
                seller_name_col = next((cols[i] for i, c in enumerate(low) if 'name' in c), None)
        if not fee_col:
            fee_col = next((cols[i] for i, c in enumerate(low) if (('fulfil' in c or 'fulfill' in c) and 'fee' in c) or c in ['fulfilment fee','fulfillment fee']), None)

    if not seller_col or not fee_col:
        raise RuntimeError("Could not resolve required columns. Provide --seller-col and --fee-col.")

    # Aggregate
    totals, df_clean = aggregate(df, seller_col, seller_name_col, fee_col)

    # Write output Excel
    with pd.ExcelWriter(args.output, engine="xlsxwriter") as writer:
        df_clean.to_excel(writer, index=False, sheet_name=(sheet_to_use or "Sheet1"))
        totals.to_excel(writer, index=False, sheet_name="Totals_by_Seller")

    if args.csv:
        csv_path = os.path.splitext(args.output)[0] + "_totals.csv"
        totals.to_csv(csv_path, index=False)
        log(f"[write] CSV: {csv_path}", args.verbose)

    log(f"[write] Excel: {args.output}", args.verbose)

if __name__ == "__main__":
    main()
