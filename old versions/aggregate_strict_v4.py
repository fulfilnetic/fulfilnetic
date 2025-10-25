#!/usr/bin/env python3
"""
v3.3a STRICT — Auto-detect admin sheet + totals row + diagnostics.

Enhancements:
- Scans ALL sheets in the admin workbook. Picks the sheet with best Storage/PIM signal.
- Manual overrides still supported: --admin-sheet, --seller-letter/--storage-letter/--pim-letter.
- Writes Admin_Detect_Report with per-sheet signals and chosen columns.
- Strict seller join. Adds TOTAL row. Join_Diagnostics included.

Usage:
  python aggregate_fulfilment_fees_v3_3a_strict_autosheet.py \
    --input main.csv --admin storage.xlsx --output merged.xlsx \
    --verbose
  # Optional overrides:
  # --admin-sheet "Sheet2" --seller-letter B --storage-letter G --pim-letter I
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

def load_excel_all_sheets(path):
    xls = pd.ExcelFile(path)
    dfs = {}
    for sh in xls.sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=sh)
            df.columns = [str(c).strip() for c in df.columns]
            dfs[sh] = df
        except Exception:
            continue
    return dfs

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
                   .reset_index().rename(columns={seller_col:"Seller"}).sort_values("Issue Rows",ascending=False))
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

def resolve_admin_columns_by_letters(df, seller_letter=None, storage_letter=None, pim_letter=None):
    cols=[str(c).strip() for c in df.columns]
    seller_col=storage_col=pim_col=None
    if seller_letter:
        idx = excel_letter_to_index(seller_letter); 
        if idx >= len(cols): raise RuntimeError(f"--seller-letter {seller_letter} out of range")
        seller_col = cols[idx]
    if storage_letter:
        idx = excel_letter_to_index(storage_letter); 
        if idx >= len(cols): raise RuntimeError(f"--storage-letter {storage_letter} out of range")
        storage_col = cols[idx]
    if pim_letter:
        idx = excel_letter_to_index(pim_letter); 
        if idx >= len(cols): raise RuntimeError(f"--pim-letter {pim_letter} out of range")
        pim_col = cols[idx]
    return seller_col, storage_col, pim_col

def score_admin_sheet(df):
    # Score presence of likely cost headers and numeric-like values
    cols = [str(c).lower() for c in df.columns]
    header_score = sum(1 for c in cols if ("storage" in c or "pim" in c))
    # numeric signal: count of cells with currency-like strings
    numeric_signal = 0
    sample = df.head(100)
    for c in df.columns:
        s = sample[c].astype(str).str.contains(r"[0-9]", regex=True, na=False).sum()
        numeric_signal += s
    return header_score, numeric_signal

def aggregate_admin_dataframe(df, admin_seller_col, storage_col, pim_col):
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

def admin_autodetect_and_aggregate(path, admin_sheet_override=None, seller_letter=None, storage_letter=None, pim_letter=None):
    xls = pd.ExcelFile(path)
    report_rows=[]
    best = None
    best_name=None
    dfs={}
    for sh in xls.sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=sh)
        except Exception:
            continue
        df.columns=[str(c).strip() for c in df.columns]
        header_score, numeric_signal = score_admin_sheet(df)
        report_rows.append({"Sheet": sh, "HeaderScore(Storage/PIM)": header_score, "NumericSignal(0-100rows)": numeric_signal, "Columns": ", ".join(map(str, df.columns[:20]))})
        dfs[sh]=df
    report = pd.DataFrame(report_rows).sort_values(["HeaderScore(Storage/PIM)","NumericSignal(0-100rows)"], ascending=[False, False])
    # pick sheet: override or best by score then by first
    if admin_sheet_override and admin_sheet_override in dfs:
        best_name = admin_sheet_override
    else:
        best_name = report.iloc[0]["Sheet"] if not report.empty else xls.sheet_names[0]
    df_best = dfs[best_name]

    # Resolve columns
    sel_col_l, stor_col_l, pim_col_l = resolve_admin_columns_by_letters(df_best, seller_letter, storage_letter, pim_letter)
    # If letters not provided, fall back to heuristics
    cols=[str(c).strip() for c in df_best.columns]; low=[c.lower() for c in cols]
    def find_any(preds):
        for i,c in enumerate(low):
            if any(p in c for p in preds): return cols[i]
        return None
    admin_seller_col = sel_col_l or find_any(["seller","customer","client","company","debiteur","klant","name"]) or cols[0]
    storage_col = stor_col_l or find_any(["storage"]) or (cols[6] if len(cols)>=7 else None)
    pim_col = pim_col_l or find_any(["pim"]) or (cols[8] if len(cols)>=9 else None)

    agg = aggregate_admin_dataframe(df_best, admin_seller_col, storage_col, pim_col)
    chosen_info = pd.DataFrame([{
        "ChosenSheet": best_name,
        "SellerCol": admin_seller_col,
        "StorageCol": storage_col,
        "PIMCol": pim_col
    }])
    return agg, report, chosen_info

def merge_strict(totals, admin_agg):
    totals["Seller"]=totals["Seller"].astype(str).str.strip()
    admin_agg["Seller"]=admin_agg["Seller"].astype(str).str.strip()
    return totals.merge(admin_agg, on="Seller", how="left")

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

def build_teamleader_upload(tl_template_path, totals_merged, seller_name_col_guess="Seller Name"):
    xls=pd.ExcelFile(tl_template_path)
    df_t=pd.read_excel(tl_template_path, sheet_name=xls.sheet_names[0], nrows=0)
    cols=list(df_t.columns); out=pd.DataFrame(columns=cols); today=date.today().isoformat()
    def pick_amount(row): return row.get("Grand Total", np.nan)
    def pick_name(row): return row.get(seller_name_col_guess) or row.get("Seller")
    for _,r in totals_merged.iterrows():
        if r.get("Seller")=="TOTAL":
            continue
        new={}
        for c in cols:
            lc=str(c).lower()
            if any(k in lc for k in ["amount","total","prijs","bedrag","waarde"]): new[c]=pick_amount(r)
            elif any(k in lc for k in ["description","omschrijving","note","notitie"]): new[c]="Fulfilment + Storage + PIM"
            elif any(k in lc for k in ["date","datum"]): new[c]=today
            elif any(k in lc for k in ["currency","valuta"]): new[c]="EUR"
            elif any(k in lc for k in ["company","customer","client","seller","account","firm","organisatie","bedrijf","debiteur"]): new[c]=pick_name(r)
            else: new[c]=""
        out=pd.concat([out,pd.DataFrame([new])], ignore_index=True)
    return out

def main():
    ap = argparse.ArgumentParser(description="v3.3a strict: auto-detect admin sheet + totals row + diagnostics")
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
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("--encoding", default=None)
    ap.add_argument("--allow-issues", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    main_df, _ = load_table(args.input, encoding=args.encoding, verbose=args.verbose, sheet_name=args.sheet_name)
    seller_col, seller_name_col, fee_col, labels_col = resolve_main_columns(main_df, args.seller_col, args.seller_name_col, args.fee_col, args.labels_col)
    totals, rows_used, issues_rows, issues_summary = aggregate_main(main_df, seller_col, seller_name_col, fee_col, labels_col)

    # Admin: auto-detect best sheet unless user overrides
    admin_agg, admin_report, admin_choice = admin_autodetect_and_aggregate(
        args.admin,
        admin_sheet_override=args.admin_sheet,
        seller_letter=args.seller_letter,
        storage_letter=args.storage_letter,
        pim_letter=args.pim_letter,
    )

    # Join diagnostics
    left_keys = totals["Seller"].astype(str).str.strip().unique()
    right_keys = admin_agg["Seller"].astype(str).str.strip().unique()
    missing_in_admin = sorted(list(set(left_keys) - set(right_keys)))
    missing_in_totals = sorted(list(set(right_keys) - set(left_keys)))
    diag_df = pd.DataFrame({
        "Seller in Totals not in Admin": pd.Series(missing_in_admin),
        "Seller in Admin not in Totals": pd.Series(missing_in_totals),
    })

    merged = merge_strict(totals, admin_agg)
    if "Storage Cost" not in merged.columns: merged["Storage Cost"]=0.0
    if "PIM Cost" not in merged.columns: merged["PIM Cost"]=0.0
    merged["Storage Cost"]=merged["Storage Cost"].fillna(0.0)
    merged["PIM Cost"]=merged["PIM Cost"].fillna(0.0)
    merged["Grand Total"]=merged["Fulfilment Fee Total"].fillna(0.0)+merged["Storage Cost"]+merged["PIM Cost"]

    merged_with_total = append_total_row(merged)

    tl_upload=None
    if args.template and os.path.exists(args.template):
        tl_upload = build_teamleader_upload(args.template, merged_with_total, seller_name_col_guess="Seller Name")

    with pd.ExcelWriter(args.output, engine="xlsxwriter") as writer:
        rows_used.to_excel(writer, index=False, sheet_name="Rows_Used")
        merged_with_total.to_excel(writer, index=False, sheet_name="Totals_by_Seller")
        admin_agg.to_excel(writer, index=False, sheet_name="Admin_Aggregates")
        diag_df.to_excel(writer, index=False, sheet_name="Join_Diagnostics")
        admin_report.to_excel(writer, index=False, sheet_name="Admin_Detect_Report")
        admin_choice.to_excel(writer, index=False, sheet_name="Admin_Chosen")
        if issues_rows is not None:
            issues_rows.to_excel(writer, index=False, sheet_name="Data_Issues")
            issues_summary.to_excel(writer, index=False, sheet_name="Issue_Summary_By_Seller")
        if tl_upload is not None:
            tl_upload.to_excel(writer, index=False, sheet_name="Teamleader_Upload")
        if args.csv:
            merged_with_total.to_csv(os.path.splitext(args.output)[0]+"_totals.csv", index=False)

    if issues_rows is not None and not args.allow_issues:
        log("[result] Issues detected. Totals written; fix data or rerun with --allow-issues.", args.verbose)
        sys.exit(2)

    log(f"[write] Excel: {args.output}", args.verbose)

if __name__ == "__main__":
    main()
