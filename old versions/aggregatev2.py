#!/usr/bin/env python3
"""
Aggregate Fulfilment Fee by Seller with Labels validation.

Outputs:
- Always writes:
  - "Rows_Used" (clean rows used in totals)
  - "Totals_by_Seller" (sum of fee * labels per Seller, with Seller Name)
- If issues exist (labels > 0 but fee missing or zero), also writes:
  - "Data_Issues"
  - "Issue_Summary_By_Seller"

Exit codes:
- 0  -> success (no issues) or issues allowed with --allow-issues
- 2  -> issues found and --allow-issues NOT provided

Usage:
  python aggregate_fulfilment_fees_v2.py --input "in.csv" --output "out.xlsx" [--allow-issues] [--verbose]
Options:
  --seller-col, --seller-name-col, --fee-col, --labels-col
  --encoding (CSV), --sheet-name (Excel), --csv (also write totals CSV), --verbose
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
    return max(counts, key=counts.get)

def load_input(input_path, encoding=None, verbose=False, sheet_name=None):
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".csv":
        with open(input_path, "rb") as fh:
            raw = fh.read(4096)

        # choose encoding
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
            guessed = "utf-8-sig"
            sample = raw.decode(guessed, errors="replace")

        delim = detect_delimiter(sample)
        log(f"[csv] encoding={guessed}, delimiter={repr(delim)}", verbose)

        df = pd.read_csv(input_path, encoding=guessed, sep=delim)
        # Also create an .xlsx copy for auditability
        xlsx_copy = os.path.splitext(input_path)[0] + ".xlsx"
        with pd.ExcelWriter(xlsx_copy, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
        log(f"[csv] written xlsx copy: {xlsx_copy}", verbose)
        return df, "Sheet1", xlsx_copy

    elif ext in [".xlsx", ".xlsm", ".xls"]:
        if sheet_name:
            df = pd.read_excel(input_path, sheet_name=sheet_name)
            return df, sheet_name, input_path
        else:
            return None, None, input_path
    else:
        raise RuntimeError(f"Unsupported input extension: {ext}")

def detect_sheet_and_columns_from_excel(xlsx_path, verbose=False):
    xls = pd.ExcelFile(xlsx_path)
    for sh in xls.sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sh)
        cols = [str(c).strip() for c in df.columns]
        low = [c.lower() for c in cols]

        seller_idx = seller_name_idx = fee_idx = labels_idx = None

        for i, c in enumerate(low):
            if 'seller' in c and seller_idx is None:
                seller_idx = i
            if ('seller' in c and 'name' in c) or c.strip() == 'seller name':
                if seller_name_idx is None:
                    seller_name_idx = i
            if (('fulfil' in c or 'fulfill' in c) and 'fee' in c) or c.strip() in ['fulfilment fee', 'fulfillment fee']:
                if fee_idx is None:
                    fee_idx = i
            if ('number of labels' in c) or ('labels' in c and 'number' in c):
                if labels_idx is None:
                    labels_idx = i

        if seller_name_idx is None:
            for i, c in enumerate(low):
                if 'name' in c:
                    seller_name_idx = i
                    break

        if (seller_idx is not None) and (fee_idx is not None) and (labels_idx is not None):
            df.columns = cols
            seller_col = cols[seller_idx]
            seller_name_col = cols[seller_name_idx] if seller_name_idx is not None else None
            fee_col = cols[fee_idx]
            labels_col = cols[labels_idx]
            log(f"[detect] sheet='{sh}' -> Seller='{seller_col}', Seller Name='{seller_name_col}', Fee='{fee_col}', Labels='{labels_col}'", verbose)
            return sh, seller_col, seller_name_col, fee_col, labels_col, df

    raise RuntimeError("Could not auto-detect columns: need Seller, Fulfilment Fee, Number of Labels. Provide --sheet-name and column args.")

def smart_to_float(s):
    if pd.isna(s):
        return np.nan
    t = str(s).strip().replace("€", "").replace(" ", "")
    if t == "":
        return np.nan

    has_dot = "." in t
    has_comma = "," in t

    # infer decimal separator when both present
    if has_dot and has_comma:
        last_dot = t.rfind(".")
        last_comma = t.rfind(",")
        if last_comma > last_dot:
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif has_comma and not has_dot:
        t = t.replace(",", ".")
    # else keep as is

    t = re.sub(r"[^0-9\.\-]", "", t)
    try:
        return float(t)
    except ValueError:
        return np.nan

_ILLEGAL = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")

def clean_illegal(obj):
    if isinstance(obj, str):
        return _ILLEGAL.sub("", obj)
    return obj

def clean_frame(df):
    obj = df.select_dtypes(include=["object"])
    if not obj.empty:
        df[obj.columns] = obj.apply(lambda s: s.map(clean_illegal))
    return df

def resolve_columns(df, seller_col, seller_name_col, fee_col, labels_col):
    cols = [str(c).strip() for c in df.columns]
    low = [c.lower() for c in cols]

    def find_all_then_any(preds):
        for i, c in enumerate(low):
            if all(p in c for p in preds):
                return cols[i]
        for i, c in enumerate(low):
            if any(p in c for p in preds):
                return cols[i]
        return None

    if not seller_col:
        seller_col = find_all_then_any(['seller'])
    if not seller_name_col:
        seller_name_col = (find_all_then_any(['seller','name']) or
                           find_all_then_any(['seller name']) or
                           find_all_then_any(['name']))
    if not fee_col:
        fee_col = (find_all_then_any(['fulfilment','fee']) or
                   find_all_then_any(['fulfillment','fee']) or
                   find_all_then_any(['fulfil','fee']) or
                   find_all_then_any(['fulfill','fee']))
    if not labels_col:
        labels_col = (find_all_then_any(['number','labels']) or
                      find_all_then_any(['labels']))

    missing = [n for n in [('Seller', seller_col), ('Fulfilment Fee', fee_col), ('Number of Labels', labels_col)] if n[1] is None]
    if missing:
        raise RuntimeError("Missing required columns: " + ", ".join(f"{k}" for k,_ in missing))

    return seller_col, seller_name_col, fee_col, labels_col

def aggregate(df, seller_col, seller_name_col, fee_col, labels_col, allow_issues=False, verbose=False):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Parse numbers
    df[fee_col] = df[fee_col].apply(smart_to_float)
    df[labels_col] = pd.to_numeric(df[labels_col], errors="coerce")

    # Keep only rows with labels present and > 0
    df["__has_labels__"] = df[labels_col].fillna(0) > 0
    df_labels = df.loc[df["__has_labels__"]].copy()

    # Issues: labels > 0 but fee missing or zero
    issues_mask = df_labels[fee_col].isna() | (df_labels[fee_col] == 0)
    issues = df_labels.loc[issues_mask].copy()
    by_seller = None
    if len(issues) > 0:
        issues["__Row__"] = issues.index.astype(int) + 2  # approx excel row (header=1)
        by_seller = (
            issues.groupby([seller_col], dropna=False)
            .agg(
                **{
                    "Seller Name": (seller_name_col, lambda s: s.dropna().iloc[0] if seller_name_col and not s.dropna().empty else None),
                    "Issue Rows": (fee_col, "size"),
                    "Total Labels Affected": (labels_col, "sum"),
                }
            )
            .reset_index()
            .rename(columns={seller_col: "Seller"})
            .sort_values("Issue Rows", ascending=False)
        )
        issues = clean_frame(issues)
        by_seller = clean_frame(by_seller)

    # Compute totals on clean rows
    df_ok = df_labels.loc[~issues_mask].copy()
    df_ok["__row_total__"] = df_ok[fee_col] * df_ok[labels_col]

    totals = (
        df_ok.groupby(seller_col, dropna=False)
        .agg(
            **{
                "Seller Name": (seller_name_col, lambda s: s.dropna().iloc[0] if seller_name_col and not s.dropna().empty else None),
                "Total Labels": (labels_col, "sum"),
                "Fulfilment Fee Total": ("__row_total__", "sum"),
                "Row Count": ("__row_total__", "size"),
            }
        )
        .reset_index()
        .rename(columns={seller_col: "Seller"})
        .sort_values("Fulfilment Fee Total", ascending=False, na_position="last")
    )

    totals = clean_frame(totals)
    df_ok = clean_frame(df_ok)
    return totals, df_ok, issues if len(issues) > 0 else None, by_seller

def main():
    import pandas as pd
    ap = argparse.ArgumentParser(description="Aggregate Fulfilment Fee by Seller with Labels validation.")
    ap.add_argument("--input", required=True, help="Path to input Excel or CSV file")
    ap.add_argument("--output", required=True, help="Path to output Excel file")
    ap.add_argument("--sheet-name", default=None, help="Sheet name to read (Excel only)")
    ap.add_argument("--seller-col", default=None, help="Seller column name")
    ap.add_argument("--seller-name-col", default=None, help="Seller Name column name")
    ap.add_argument("--fee-col", default=None, help="Fulfilment Fee column name")
    ap.add_argument("--labels-col", default=None, help="Number of Labels column name")
    ap.add_argument("--csv", action="store_true", help="Also write CSV for the totals")
    ap.add_argument("--encoding", default=None, help="CSV encoding hint (e.g., utf-8-sig)")
    ap.add_argument("--allow-issues", action="store_true", help="Continue and return success even if issues exist")
    ap.add_argument("--verbose", action="store_true", help="Verbose logs to stderr")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input not found: {args.input}")

    df, detected_sheet, effective_input = load_input(args.input, encoding=args.encoding, verbose=args.verbose, sheet_name=args.sheet_name)

    if df is None:
        sh, seller_col_auto, seller_name_col_auto, fee_col_auto, labels_col_auto, df = detect_sheet_and_columns_from_excel(effective_input, verbose=args.verbose)
        sheet_to_use = sh
        seller_col = args.seller_col or seller_col_auto
        seller_name_col = args.seller_name_col or seller_name_col_auto
        fee_col = args.fee_col or fee_col_auto
        labels_col = args.labels_col or labels_col_auto
    else:
        sheet_to_use = detected_sheet or "Sheet1"
        seller_col, seller_name_col, fee_col, labels_col = resolve_columns(df, args.seller_col, args.seller_name_col, args.fee_col, args.labels_col)

    totals, df_clean, issues_rows, issues_summary = aggregate(df, seller_col, seller_name_col, fee_col, labels_col, allow_issues=args.allow_issues, verbose=args.verbose)

    # Write output
    with pd.ExcelWriter(args.output, engine="xlsxwriter") as writer:
        # Always write calculations
        df_clean.to_excel(writer, index=False, sheet_name="Rows_Used")
        totals.to_excel(writer, index=False, sheet_name="Totals_by_Seller")

        # If issues exist, also include the issue sheets
        if issues_rows is not None:
            issues_rows.to_excel(writer, index=False, sheet_name="Data_Issues")
            issues_summary.to_excel(writer, index=False, sheet_name="Issue_Summary_By_Seller")

        if args.csv:
            csv_path = os.path.splitext(args.output)[0] + "_totals.csv"
            totals.to_csv(csv_path, index=False)
            log(f"[write] CSV: {csv_path}", args.verbose)

    # Exit code: signal issues to automation if not allowed
    if issues_rows is not None and not args.allow_issues:
        log("[result] Issues detected. Totals written alongside issue sheets. Rerun with --allow-issues to return success.", args.verbose)
        sys.exit(2)

    log(f"[write] Excel: {args.output}", args.verbose)

if __name__ == "__main__":
    main()
