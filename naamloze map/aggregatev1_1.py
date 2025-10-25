#!/usr/bin/env python3
"""
v3.6.4 STRICT — Dedup fix.
- Normalize Seller keys (strip + upper) for comparisons.
- De-duplicate Admin_Aggregates on normalized Seller.
- Only add dummy rows for truly missing normalized sellers.
"""

import argparse, os, sys, re
import pandas as pd
import numpy as np
from datetime import date

def log(msg, enabled):
    if enabled:
        print(msg, file=sys.stderr)

def detect_delimiter(sample, candidates=None):
    if candidates is None: candidates=[",",";","\t","|"]
    counts={d: sample.count(d) for d in candidates}
    return max(counts, key=counts.get)

def load_table(path, encoding=None, verbose=False, sheet_name=None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        with open(path,"rb") as fh: raw=fh.read(4096)
        guessed=None
        for enc in [encoding,"utf-8-sig","utf-8","latin-1"]:
            if not enc: continue
            try:
                sample = raw.decode(enc, errors="replace"); guessed=enc; break
            except Exception: continue
        if not guessed:
            guessed="utf-8-sig"; sample=raw.decode(guessed, errors="replace")
        delim = detect_delimiter(sample)
        log(f"[csv] {os.path.basename(path)} encoding={guessed}, delimiter={repr(delim)}", verbose)
        df = pd.read_csv(path, encoding=guessed, sep=delim)
        return df, "Sheet1"
    elif ext in [".xlsx",".xlsm",".xls"]:
        if sheet_name:
            df = pd.read_excel(path, sheet_name=sheet_name); return df, sheet_name
        xls = pd.ExcelFile(path); sh = xls.sheet_names[0]
        df = pd.read_excel(path, sheet_name=sh); return df, sh
    else:
        raise RuntimeError(f"Unsupported extension: {ext}")

def smart_to_float(s):
    if pd.isna(s): return np.nan
    t = str(s).strip().replace("€","").replace(" ","")
    if t == "": return np.nan
    has_dot = "." in t; has_comma = "," in t
    if has_dot and has_comma:
        last_dot=t.rfind("."); last_comma=t.rfind(",")
        if last_comma>last_dot: t=t.replace(".","").replace(",",".")
        else: t=t.replace(",","")
    elif has_comma and not has_dot:
        t=t.replace(",",".")
    t = re.sub(r"[^0-9\.\-]","",t)
    try: return float(t)
    except ValueError: return np.nan

def excel_letter_to_index(letter):
    s = str(letter).strip().upper()
    total = 0
    for ch in s:
        if not ('A' <= ch <= 'Z'): raise ValueError(f"Invalid column letter: {letter}")
        total = total*26 + (ord(ch)-ord('A')+1)
    return total-1

def resolve_main_columns(df, seller_col, seller_name_col, fee_col, labels_col):
    cols=[str(c).strip() for c in df.columns]; low=[c.lower() for c in cols]
    def find_all_then_any(preds):
        for i,c in enumerate(low):
            if all(p in c for p in preds): return cols[i]
        for i,c in enumerate(low):
            if any(p in c for p in preds): return cols[i]
        return None
    if not seller_col: seller_col = find_all_then_any(["seller"])
    if not seller_name_col: seller_name_col = (find_all_then_any(["seller","name"]) or find_all_then_any(["seller name"]) or find_all_then_any(["name"]))
    if not fee_col: fee_col = (find_all_then_any(["fulfilment","fee"]) or find_all_then_any(["fulfillment","fee"]) or find_all_then_any(["fulfil","fee"]) or find_all_then_any(["fulfill","fee"]))
    if not labels_col: labels_col = (find_all_then_any(["number","labels"]) or find_all_then_any(["labels"]))
    missing=[n for n in [("Seller",seller_col),("Fulfilment Fee",fee_col),("Number of Labels",labels_col)] if n[1] is None]
    if missing: raise RuntimeError("Missing required columns in main input: "+", ".join(k for k,_ in missing))
    return seller_col, seller_name_col, fee_col, labels_col

def aggregate_main(df, seller_col, seller_name_col, fee_col, labels_col):
    df=df.copy(); df.columns=[str(c).strip() for c in df.columns]
    df[fee_col]=df[fee_col].apply(smart_to_float)
    df[labels_col]=pd.to_numeric(df[labels_col], errors="coerce")
    df["__has_labels__"]=df[labels_col].fillna(0)>0
    df_labels=df.loc[df["__has_labels__"]].copy()
    issues_mask = df_labels[fee_col].isna() | (df_labels[fee_col]==0)
    issues = df_labels.loc[issues_mask].copy()
    by_seller=None
    if len(issues)>0:
        issues["__Row__"]=issues.index.astype(int)+2
        by_seller=(issues.groupby([seller_col], dropna=False)
                   .agg(**{"Seller Name":(seller_name_col, lambda s: s.dropna().iloc[0] if seller_name_col and not s.dropna().empty else None),
                           "Issue Rows":(fee_col,"size"),
                           "Total Labels Affected":(labels_col,"sum")})
                   .reset_index().rename(columns={seller_col:"Seller"})
                   .sort_values("Issue Rows",ascending=False))
    df_ok = df_labels.loc[~issues_mask].copy()
    df_ok["__row_total__"]=df_ok[fee_col]*df_ok[labels_col]
    totals=(df_ok.groupby(seller_col, dropna=False)
            .agg(**{"Seller Name":(seller_name_col, lambda s: s.dropna().iloc[0] if seller_name_col and not s.dropna().empty else None),
                    "Total Labels":(labels_col,"sum"),
                    "Fulfilment Fee Total":("__row_total__","sum"),
                    "Row Count":("__row_total__","size")})
            .reset_index().rename(columns={seller_col:"Seller"})
            .sort_values("Fulfilment Fee Total", ascending=False, na_position="last"))
    return totals, df_ok, (issues if len(issues)>0 else None), by_seller

def resolve_admin(df, seller_letter=None, storage_letter=None, pim_letter=None, seller_col=None, storage_col=None, pim_col=None):
    cols=[str(c).strip() for c in df.columns]
    def from_letter(letter):
        if not letter: return None
        idx = excel_letter_to_index(letter)
        if idx >= len(cols): raise RuntimeError(f"Column letter {letter} out of range")
        return cols[idx]
    seller = seller_col or from_letter(seller_letter) or cols[0]
    storage = storage_col or from_letter(storage_letter) or (cols[6] if len(cols)>=7 else None)
    pim = pim_col or from_letter(pim_letter) or (cols[8] if len(cols)>=9 else None)
    return seller, storage, pim

def detect_admin_name_column(df):
    for c in df.columns:
        cl = str(c).lower()
        if "name" in cl or "naam" in cl:
            return c
    return None

def aggregate_admin(df, admin_seller_col, storage_col, pim_col):
    d=df.copy(); d.columns=[str(c).strip() for c in d.columns]
    if storage_col and storage_col not in d.columns: d[storage_col]=0.0
    if pim_col and pim_col not in d.columns: d[pim_col]=0.0
    if storage_col: d[storage_col]=d[storage_col].apply(smart_to_float)
    if pim_col: d[pim_col]=d[pim_col].apply(smart_to_float)
    use=[c for c in [storage_col,pim_col] if c]
    grp=(d.groupby(admin_seller_col, dropna=False)[use].sum(min_count=1).reset_index()
         .rename(columns={admin_seller_col:"Seller"}))
    if storage_col: grp.rename(columns={storage_col:"Storage Cost"}, inplace=True)
    if pim_col: grp.rename(columns={pim_col:"PIM Cost"}, inplace=True)
    if "Storage Cost" not in grp.columns: grp["Storage Cost"]=0.0
    if "PIM Cost" not in grp.columns: grp["PIM Cost"]=0.0
    return grp

def append_total_row(df):
    out = df.copy()
    numeric_cols = out.select_dtypes(include=[np.number]).columns
    total_vals = out[numeric_cols].sum(numeric_only=True)
    total_row = {c: "" for c in out.columns}
    if "Seller" in out.columns:
        total_row["Seller"] = "TOTAL"
    for c in numeric_cols:
        total_row[c] = total_vals.get(c, np.nan)
    out = pd.concat([out, pd.DataFrame([total_row])], ignore_index=True)
    return out


def load_admin_table_fixed(path, encoding=None, verbose=False, sheet_name=None):
    """Read admin costs starting with header on Excel row 3 (0-based header=2)."""
    ext = os.path.splitext(path)[1].lower()
    hdr = 2  # header on row 3
    if ext == ".csv":
        with open(path, "rb") as fh:
            raw = fh.read(4096)
        guessed = None
        for enc in [encoding, "utf-8-sig", "utf-8", "latin-1"]:
            if not enc:
                continue
            try:
                raw.decode(enc, errors="replace")
                guessed = enc
                break
            except Exception:
                continue
        if not guessed:
            guessed = "utf-8-sig"
        # quick delimiter guess
        sample = raw.decode(guessed, errors="replace")
        delim_counts = {d: sample.count(d) for d in [",", ";", "\t", "|"]}
        delim = max(delim_counts, key=delim_counts.get)
        if verbose:
            print(f"[csv-admin] {os.path.basename(path)} encoding={guessed}, delimiter={repr(delim)}, header=2", file=sys.stderr)
        return pd.read_csv(path, encoding=guessed, sep=delim, header=hdr), "Sheet1"
    elif ext in [".xlsx", ".xlsm", ".xls"]:
        sh = sheet_name or pd.ExcelFile(path).sheet_names[0]
        if verbose:
            print(f"[xlsx-admin] sheet={sh}, header=2", file=sys.stderr)
        return pd.read_excel(path, sheet_name=sh, header=hdr), sh
    else:
        raise RuntimeError(f"Unsupported admin extension: {ext}")


def main():
    ap = argparse.ArgumentParser(description="v3.6.4 strict: dedup on dummy add")
    ap.add_argument("--input", required=True)
    ap.add_argument("--admin", required=True)
    ap.add_argument("--template", default=None)
    ap.add_argument("--output", required=True)
    ap.add_argument("--sheet-name", default=None)
    ap.add_argument("--seller-col", default=None)
    ap.add_argument("--seller-name-col", default=None)
    ap.add_argument("--fee-col", default=None)
    ap.add_argument("--labels-col", default=None)
    ap.add_argument("--admin-sheet", default=None)
    ap.add_argument("--seller-letter", default=None)
    ap.add_argument("--storage-letter", default=None)
    ap.add_argument("--pim-letter", default=None)
    ap.add_argument("--admin-seller-col", default=None)
    ap.add_argument("--storage-col", default=None)
    ap.add_argument("--pim-col", default=None)
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("--encoding", default=None)
    ap.add_argument("--allow-issues", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    # Load inputs
    main_df, _ = load_table(args.input, encoding=args.encoding, verbose=args.verbose, sheet_name=args.sheet_name)
    admin_df, _ = load_admin_table_fixed(args.admin, encoding=args.encoding, verbose=args.verbose, sheet_name=args.admin_sheet)

    # Main aggregate + issues
    seller_col, seller_name_col, fee_col, labels_col = resolve_main_columns(main_df, args.seller_col, args.seller_name_col, args.fee_col, args.labels_col)
    totals, rows_used, issues_rows, issues_summary = aggregate_main(main_df, seller_col, seller_name_col, fee_col, labels_col)

    # Admin aggregate
    a_seller, a_storage, a_pim = resolve_admin(admin_df, args.seller_letter, args.storage_letter, args.pim_letter, args.admin_seller_col, args.storage_col, args.pim_col)
    admin_agg = aggregate_admin(admin_df, a_seller, a_storage, a_pim)

    # Admin name map
    admin_name_col = detect_admin_name_column(admin_df)
    admin_name_map = {}
    if admin_name_col is not None and admin_name_col in admin_df.columns:
        tmp = admin_df[[a_seller, admin_name_col]].copy()
        tmp[a_seller] = tmp[a_seller].astype(str).str.strip()
        tmp[admin_name_col] = tmp[admin_name_col].astype(str).str.strip()
        admin_name_map = pd.Series(tmp[admin_name_col].values, index=tmp[a_seller]).to_dict()
    # Main name map
    name_map_main = pd.Series(totals["Seller Name"].values, index=totals["Seller"].astype(str).str.strip()).to_dict()

    # Build Admin_Aggregates full with union and de-dup
    admin_agg = admin_agg.copy()
    admin_agg["Seller"] = admin_agg["Seller"].astype(str).str.strip()
    admin_agg["__KEY__"] = admin_agg["Seller"].str.upper()
    # keep first occurrence per normalized key
    admin_agg = admin_agg.drop_duplicates(subset="__KEY__", keep="first")
    totals_keys = totals["Seller"].astype(str).str.strip()
    all_sellers = pd.Index(sorted(set(admin_agg["Seller"]).union(set(totals_keys))))
    admin_agg_full = (admin_agg.set_index("Seller")
                      .reindex(all_sellers)
                      .fillna({"Storage Cost":0.0, "PIM Cost":0.0})
                      .reset_index().rename(columns={"index":"Seller"}))
    admin_agg_full["Seller Name"] = admin_agg_full["Seller"].map(admin_name_map).fillna(admin_agg_full["Seller"].map(name_map_main))
    for col in ["Storage Cost","PIM Cost"]:
        if col not in admin_agg_full.columns: admin_agg_full[col]=0.0
    admin_agg_full = admin_agg_full[["Seller","Seller Name","Storage Cost","PIM Cost"]]

    # VLOOKUP mapping
    totals = totals.copy()
    key_totals = totals["Seller"].astype(str).str.strip()
    key_admin  = admin_agg_full["Seller"].astype(str).str.strip()
    storage_map = pd.Series(admin_agg_full["Storage Cost"].values, index=key_admin).to_dict()
    pim_map     = pd.Series(admin_agg_full["PIM Cost"].values, index=key_admin).to_dict()
    totals["Storage Cost"] = key_totals.map(storage_map).fillna(0.0)
    totals["PIM Cost"]     = key_totals.map(pim_map).fillna(0.0)
    totals["Grand Total"]  = totals["Fulfilment Fee Total"].fillna(0.0) + totals["Storage Cost"] + totals["PIM Cost"]

    # Dummy rows for truly missing normalized sellers
    norm_totals = set(key_totals.str.upper())
    norm_admin  = set(key_admin.str.upper())
    missing_norm = norm_admin - norm_totals
    if missing_norm:
        # map normalized key -> original Seller
        admin_map_norm_to_seller = dict(zip(key_admin.str.upper(), key_admin))
        to_add = [admin_map_norm_to_seller[k] for k in missing_norm if k in admin_map_norm_to_seller and admin_map_norm_to_seller[k] not in set(totals["Seller"])]
        if to_add:
            dummy_rows = admin_agg_full.loc[admin_agg_full["Seller"].isin(to_add), ["Seller","Seller Name","Storage Cost","PIM Cost"]].copy()
            dummy_rows["Total Labels"] = 0
            dummy_rows["Fulfilment Fee Total"] = 0.0
            dummy_rows["Row Count"] = 0
            dummy_rows["Grand Total"] = dummy_rows["Storage Cost"] + dummy_rows["PIM Cost"]
            wanted_cols = ["Seller","Seller Name","Total Labels","Fulfilment Fee Total","Row Count","Storage Cost","PIM Cost","Grand Total"]
            for c in wanted_cols:
                if c not in dummy_rows.columns:
                    dummy_rows[c] = "" if c in ["Seller","Seller Name"] else 0.0
            dummy_rows = dummy_rows[wanted_cols]
            totals = pd.concat([totals, dummy_rows], ignore_index=True)

    # Final TOTAL row
    totals_with_total = totals.copy()
    numeric_cols = totals_with_total.select_dtypes(include=[np.number]).columns
    total_row = {c: "" for c in totals_with_total.columns}
    total_row["Seller"] = "TOTAL"
    for c in numeric_cols:
        total_row[c] = totals_with_total[c].sum(numeric_only=True)
    totals_with_total = pd.concat([totals_with_total, pd.DataFrame([total_row])], ignore_index=True)

    # Write output
    with pd.ExcelWriter(args.output, engine="xlsxwriter") as writer:
        rows_used.to_excel(writer, index=False, sheet_name="Rows_Used")
        admin_agg_full.to_excel(writer, index=False, sheet_name="Admin_Aggregates")
        totals_with_total.to_excel(writer, index=False, sheet_name="Totals_by_Seller")
        if issues_rows is not None:
            issues_rows.to_excel(writer, index=False, sheet_name="Data_Issues")
            issues_summary.to_excel(writer, index=False, sheet_name="Issue_Summary_By_Seller")

    if issues_rows is not None and not args.allow_issues:
        log("[result] Issues detected. Totals written; fix data or rerun with --allow-issues.", args.verbose)
        sys.exit(2)

    log(f"[write] Excel: {args.output}", args.verbose)

if __name__ == "__main__":
    main()
