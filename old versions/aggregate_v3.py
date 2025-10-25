#!/usr/bin/env python3
"""
Aggregate Fulfilment + Storage + PIM per Seller and build a Teamleader-style upload.

Inputs
------
--input        : Main CSV/XLSX with Fulfilment Fee + Number of Labels per row (by Seller)
--admin        : Excel with Storage (col G) and PIM (col I) costs by Seller
--template     : Teamleader template Excel (optional; first sheet columns are mirrored)
--output       : Output Excel

Behavior
--------
1) Validates rows: keep only rows with labels > 0.
2) Issues = labels > 0 but Fulfilment Fee is NaN or 0.
3) Per-row total = Fulfilment Fee * Number of Labels.
4) Aggregate per Seller (+ Seller Name): Fulfilment total, Total Labels, Row Count.
5) From --admin, detect 'Seller' and the two cost columns:
   - Prefer explicit --admin-seller-col/--storage-col/--pim-col names.
   - Else detect by header keywords.
   - Else fallback to zero-based positions 6 (G) and 8 (I) if available.
   Sums by Seller.
6) Merge Storage and PIM into totals. Compute Grand Total.
7) Write sheets:
   - Rows_Used
   - Totals_by_Seller (Fulfilment, Storage, PIM, Grand Total)
   - Admin_Aggregates (what was pulled from admin file)
   - If issues exist: Data_Issues + Issue_Summary_By_Seller
   - If --template given: Teamleader_Upload matching the template's first sheet columns
     (heuristic fill; unmapped columns remain blank).

Exit codes
----------
0 = OK (or issues allowed with --allow-issues)
2 = Issues found and --allow-issues not set

CLI example
-----------
python aggregate_fulfilment_fees_v3.py \
  --input "main.csv" \
  --admin "ChannelDock  Administration.xlsx" \
  --template "Import-template-teamleader-oktober.xlsx" \
  --output "merged_output.xlsx" \
  --verbose
"""

import argparse
import os
import sys
import re
import pandas as pd
import numpy as np
from datetime import date

def log(msg, enabled):
    if enabled:
        print(msg, file=sys.stderr)

def detect_delimiter(sample, candidates=None):
    if candidates is None:
        candidates = [",", ";", "\t", "|"]
    counts = {d: sample.count(d) for d in candidates}
    return max(counts, key=counts.get)

def load_table(path, encoding=None, verbose=False, sheet_name=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        with open(path, "rb") as fh:
            raw = fh.read(4096)
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
        log(f"[csv] {os.path.basename(path)} encoding={guessed}, delimiter={repr(delim)}", verbose)
        df = pd.read_csv(path, encoding=guessed, sep=delim)
        return df, "Sheet1"
    elif ext in [".xlsx", ".xlsm", ".xls"]:
        if sheet_name:
            df = pd.read_excel(path, sheet_name=sheet_name)
            return df, sheet_name
        else:
            xls = pd.ExcelFile(path)
            df = pd.read_excel(path, sheet_name=xls.sheet_names[0])
            return df, xls.sheet_names[0]
    else:
        raise RuntimeError(f"Unsupported extension: {ext}")

def smart_to_float(s):
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

def resolve_main_columns(df, seller_col, seller_name_col, fee_col, labels_col):
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
        labels_col = (find_all_then_any(['number','labels']) or find_all_then_any(['labels']))
    missing = [n for n in [('Seller', seller_col), ('Fulfilment Fee', fee_col), ('Number of Labels', labels_col)] if n[1] is None]
    if missing:
        raise RuntimeError("Missing required columns in main input: " + ", ".join(f"{k}" for k,_ in missing))
    return seller_col, seller_name_col, fee_col, labels_col

def aggregate_main(df, seller_col, seller_name_col, fee_col, labels_col, verbose=False):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df[fee_col] = df[fee_col].apply(smart_to_float)
    df[labels_col] = pd.to_numeric(df[labels_col], errors="coerce")
    df["__has_labels__"] = df[labels_col].fillna(0) > 0
    df_labels = df.loc[df["__has_labels__"]].copy()
    issues_mask = df_labels[fee_col].isna() | (df_labels[fee_col] == 0)
    issues = df_labels.loc[issues_mask].copy()
    by_seller = None
    if len(issues) > 0:
        issues["__Row__"] = issues.index.astype(int) + 2
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

def resolve_admin_columns(df, admin_seller_col, storage_col, pim_col):
    cols = [str(c).strip() for c in df.columns]
    low = [c.lower() for c in cols]
    def find_any(preds):
        for i, c in enumerate(low):
            if any(p in c for p in preds):
                return cols[i]
        return None
    if not admin_seller_col:
        admin_seller_col = find_any(['seller','customer','client','company','debiteur','klant','name'])
    if not storage_col:
        storage_col = find_any(['storage'])
    if not pim_col:
        pim_col = find_any(['pim'])
    # fallback by position: G and I -> 6 and 8 zero-based if exist
    if storage_col is None and len(cols) >= 7:
        storage_col = cols[6]
    if pim_col is None and len(cols) >= 9:
        pim_col = cols[8]
    if admin_seller_col is None:
        raise RuntimeError("Could not detect seller column in admin file. Provide --admin-seller-col.")
    return admin_seller_col, storage_col, pim_col

def aggregate_admin(df, admin_seller_col, storage_col, pim_col):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if storage_col not in df.columns or pim_col not in df.columns:
        # Create cols if missing
        if storage_col not in df.columns:
            df[storage_col] = 0.0
        if pim_col not in df.columns:
            df[pim_col] = 0.0
    df[storage_col] = df[storage_col].apply(smart_to_float)
    df[pim_col] = df[pim_col].apply(smart_to_float)
    grp = (
        df.groupby(admin_seller_col, dropna=False)[[storage_col, pim_col]]
        .sum(min_count=1)
        .reset_index()
        .rename(columns={admin_seller_col: "Seller", storage_col: "Storage Cost", pim_col: "PIM Cost"})
    )
    grp = clean_frame(grp)
    return grp

def build_teamleader_upload(tl_template_path, totals_merged, seller_name_col_guess="Seller Name"):
    # Mirror first sheet columns
    xls = pd.ExcelFile(tl_template_path)
    df_t = pd.read_excel(tl_template_path, sheet_name=xls.sheet_names[0], nrows=0)
    cols = list(df_t.columns)
    # Construct a new DF with same columns, fill heuristically
    out = pd.DataFrame(columns=cols)
    # Values we can provide
    today = date.today().isoformat()
    # Decide fields
    def pick_amount(row):
        return row.get("Grand Total", np.nan)
    def pick_name(row):
        # prefer Seller Name then Seller
        return row.get(seller_name_col_guess) or row.get("Seller")
    for _, r in totals_merged.iterrows():
        new = {}
        for c in cols:
            lc = str(c).lower()
            if any(k in lc for k in ["amount","total","prijs","bedrag","waarde"]):
                new[c] = pick_amount(r)
            elif any(k in lc for k in ["description","omschrijving","note","notitie"]):
                new[c] = "Fulfilment + Storage + PIM"
            elif any(k in lc for k in ["date","datum"]):
                new[c] = today
            elif any(k in lc for k in ["currency","valuta"]):
                new[c] = "EUR"
            elif any(k in lc for k in ["company","customer","client","seller","account","firm","organisatie","bedrijf","debiteur"]):
                new[c] = pick_name(r)
            else:
                new[c] = ""
        out = pd.concat([out, pd.DataFrame([new])], ignore_index=True)
    return clean_frame(out)

def main():
    ap = argparse.ArgumentParser(description="Aggregate Fulfilment + Storage + PIM per Seller and build Teamleader upload.")
    ap.add_argument("--input", required=True, help="Path to main CSV/XLSX")
    ap.add_argument("--admin", required=True, help="Path to admin Excel with Storage (G) and PIM (I)")
    ap.add_argument("--template", default=None, help="Path to Teamleader template (optional)")
    ap.add_argument("--output", required=True, help="Path to output Excel")
    ap.add_argument("--sheet-name", default=None, help="Sheet name for Excel main input")
    ap.add_argument("--seller-col", default=None)
    ap.add_argument("--seller-name-col", default=None)
    ap.add_argument("--fee-col", default=None)
    ap.add_argument("--labels-col", default=None)
    ap.add_argument("--admin-sheet", default=None)
    ap.add_argument("--admin-seller-col", default=None)
    ap.add_argument("--storage-col", default=None)
    ap.add_argument("--pim-col", default=None)
    ap.add_argument("--csv", action="store_true", help="Also write a CSV of Totals_by_Seller")
    ap.add_argument("--encoding", default=None, help="CSV encoding hint for main input")
    ap.add_argument("--allow-issues", action="store_true", help="Return success even if issues exist")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    # Load main and admin
    main_df, _ = load_table(args.input, encoding=args.encoding, verbose=args.verbose, sheet_name=args.sheet_name)
    admin_df, _ = load_table(args.admin, verbose=args.verbose, sheet_name=args.admin_sheet)

    # Resolve and aggregate main
    seller_col, seller_name_col, fee_col, labels_col = resolve_main_columns(main_df, args.seller_col, args.seller_name_col, args.fee_col, args.labels_col)
    totals, rows_used, issues_rows, issues_summary = aggregate_main(main_df, seller_col, seller_name_col, fee_col, labels_col, verbose=args.verbose)

    # Resolve and aggregate admin
    admin_seller_col, storage_col, pim_col = resolve_admin_columns(admin_df, args.admin_seller_col, args.storage_col, args.pim_col)
    admin_agg = aggregate_admin(admin_df, admin_seller_col, storage_col, pim_col)

    # Merge totals with admin aggregates
    merged = totals.merge(admin_agg, on="Seller", how="left")
    for col in ["Storage Cost","PIM Cost"]:
        if col not in merged.columns:
            merged[col] = 0.0
    merged["Storage Cost"] = merged["Storage Cost"].fillna(0.0)
    merged["PIM Cost"] = merged["PIM Cost"].fillna(0.0)
    merged["Grand Total"] = merged["Fulfilment Fee Total"].fillna(0.0) + merged["Storage Cost"] + merged["PIM Cost"]
    merged = clean_frame(merged)

    # Optional Teamleader upload
    tl_upload = None
    if args.template and os.path.exists(args.template):
        tl_upload = build_teamleader_upload(args.template, merged, seller_name_col_guess="Seller Name")

    # Write output
    with pd.ExcelWriter(args.output, engine="xlsxwriter") as writer:
        rows_used.to_excel(writer, index=False, sheet_name="Rows_Used")
        merged.to_excel(writer, index=False, sheet_name="Totals_by_Seller")
        admin_agg.to_excel(writer, index=False, sheet_name="Admin_Aggregates")
        if issues_rows is not None:
            issues_rows.to_excel(writer, index=False, sheet_name="Data_Issues")
            issues_summary.to_excel(writer, index=False, sheet_name="Issue_Summary_By_Seller")
        if tl_upload is not None:
            tl_upload.to_excel(writer, index=False, sheet_name="Teamleader_Upload")
        if args.csv:
            merged.to_csv(os.path.splitext(args.output)[0] + "_totals.csv", index=False)

    if issues_rows is not None and not args.allow_issues:
        log("[result] Issues detected. Totals written; fix data or rerun with --allow-issues.", args.verbose)
        sys.exit(2)

    log(f"[write] Excel: {args.output}", args.verbose)

if __name__ == "__main__":
    main()
