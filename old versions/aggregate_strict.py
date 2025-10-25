#!/usr/bin/env python3
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
                sample=raw.decode(enc, errors="replace"); guessed=enc; break
            except Exception: continue
        if not guessed:
            guessed="utf-8-sig"; sample=raw.decode(guessed, errors="replace")
        delim=detect_delimiter(sample)
        log(f"[csv] {os.path.basename(path)} encoding={guessed}, delimiter={repr(delim)}", verbose)
        df=pd.read_csv(path, encoding=guessed, sep=delim)
        return df, "Sheet1"
    elif ext in [".xlsx",".xlsm",".xls"]:
        if sheet_name:
            df=pd.read_excel(path, sheet_name=sheet_name); return df, sheet_name
        xls=pd.ExcelFile(path); sh=xls.sheet_names[0]
        df=pd.read_excel(path, sheet_name=sh); return df, sh
    else:
        raise RuntimeError(f"Unsupported extension: {ext}")

def smart_to_float(s):
    if pd.isna(s): return np.nan
    t=str(s).strip().replace("€","").replace(" ","")
    if t=="": return np.nan
    has_dot="." in t; has_comma="," in t
    if has_dot and has_comma:
        last_dot=t.rfind("."); last_comma=t.rfind(",")
        if last_comma>last_dot: t=t.replace(".","").replace(",",".")
        else: t=t.replace(",","")
    elif has_comma and not has_dot:
        t=t.replace(",",".")
    t=re.sub(r"[^0-9\.\-]","",t)
    try: return float(t)
    except ValueError: return np.nan

# Only use cleaning on internal issue tables to avoid visible char loss
_ILLEGAL = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")
def clean_illegal(obj):
    if isinstance(obj,str): return _ILLEGAL.sub("", obj)
    return obj
def clean_internal(df):
    obj=df.select_dtypes(include=["object"])
    if not obj.empty: df[obj.columns]=obj.apply(lambda s: s.map(clean_illegal))
    return df

def resolve_main_columns(df, seller_col, seller_name_col, fee_col, labels_col):
    cols=[str(c).strip() for c in df.columns]; low=[c.lower() for c in cols]
    def find_all_then_any(preds):
        for i,c in enumerate(low):
            if all(p in c for p in preds): return cols[i]
        for i,c in enumerate(low):
            if any(p in c for p in preds): return cols[i]
        return None
    if not seller_col: seller_col=find_all_then_any(["seller"])
    if not seller_name_col: seller_name_col=(find_all_then_any(["seller","name"]) or find_all_then_any(["seller name"]) or find_all_then_any(["name"]))
    if not fee_col: fee_col=(find_all_then_any(["fulfilment","fee"]) or find_all_then_any(["fulfillment","fee"]) or find_all_then_any(["fulfil","fee"]) or find_all_then_any(["fulfill","fee"]))
    if not labels_col: labels_col=(find_all_then_any(["number","labels"]) or find_all_then_any(["labels"]))
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
        issues=clean_internal(issues); by_seller=clean_internal(by_seller)
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

def resolve_admin_columns(df, admin_seller_col, storage_col, pim_col):
    cols=[str(c).strip() for c in df.columns]; low=[c.lower() for c in cols]
    def find_any(preds):
        for i,c in enumerate(low):
            if any(p in c for p in preds): return cols[i]
        return None
    if not admin_seller_col: admin_seller_col=find_any(["seller","customer","client","company","debiteur","klant","name"])
    if not storage_col: storage_col=find_any(["storage"])
    if not pim_col: pim_col=find_any(["pim"])
    if storage_col is None and len(cols)>=7: storage_col=cols[6]
    if pim_col is None and len(cols)>=9: pim_col=cols[8]
    if admin_seller_col is None: raise RuntimeError("Could not detect seller column in admin file. Provide --admin-seller-col.")
    return admin_seller_col, storage_col, pim_col

def aggregate_admin(df, admin_seller_col, storage_col, pim_col):
    df=df.copy(); df.columns=[str(c).strip() for c in df.columns]
    if storage_col not in df.columns: df[storage_col]=0.0
    if pim_col not in df.columns: df[pim_col]=0.0
    df[storage_col]=df[storage_col].apply(smart_to_float)
    df[pim_col]=df[pim_col].apply(smart_to_float)
    grp=(df.groupby(admin_seller_col, dropna=False)[[storage_col,pim_col]].sum(min_count=1).reset_index()
         .rename(columns={admin_seller_col:"Seller", storage_col:"Storage Cost", pim_col:"PIM Cost"}))
    return grp

def build_teamleader_upload(tl_template_path, totals_merged, seller_name_col_guess="Seller Name"):
    xls=pd.ExcelFile(tl_template_path)
    df_t=pd.read_excel(tl_template_path, sheet_name=xls.sheet_names[0], nrows=0)
    cols=list(df_t.columns); out=pd.DataFrame(columns=cols); today=date.today().isoformat()
    def pick_amount(row): return row.get("Grand Total", np.nan)
    def pick_name(row): return row.get(seller_name_col_guess) or row.get("Seller")
    for _,r in totals_merged.iterrows():
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

def merge_totals(totals, admin_agg):
    totals["Seller"]=totals["Seller"].astype(str).str.strip()
    admin_agg["Seller"]=admin_agg["Seller"].astype(str).str.strip()
    return totals.merge(admin_agg, on="Seller", how="left")

def main():
    ap=argparse.ArgumentParser(description="v3.2: preserve display text and build Teamleader upload")
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
    ap.add_argument("--admin-seller-col", default=None)
    ap.add_argument("--storage-col", default=None)
    ap.add_argument("--pim-col", default=None)
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("--encoding", default=None)
    ap.add_argument("--allow-issues", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args=ap.parse_args()

    main_df,_=load_table(args.input, encoding=args.encoding, verbose=args.verbose, sheet_name=args.sheet_name)
    admin_df,_=load_table(args.admin, verbose=args.verbose, sheet_name=args.admin_sheet)

    seller_col, seller_name_col, fee_col, labels_col = resolve_main_columns(main_df, args.seller_col, args.seller_name_col, args.fee_col, args.labels_col)
    totals, rows_used, issues_rows, issues_summary = aggregate_main(main_df, seller_col, seller_name_col, fee_col, labels_col)

    admin_seller_col, storage_col, pim_col = resolve_admin_columns(admin_df, args.admin_seller_col, args.storage_col, args.pim_col)
    admin_agg = aggregate_admin(admin_df, admin_seller_col, storage_col, pim_col)

    merged = merge_totals(totals, admin_agg)
    for col in ["Storage Cost","PIM Cost"]:
        if col not in merged.columns: merged[col]=0.0
    merged["Storage Cost"]=merged["Storage Cost"].fillna(0.0)
    merged["PIM Cost"]=merged["PIM Cost"].fillna(0.0)
    merged["Grand Total"]=merged["Fulfilment Fee Total"].fillna(0.0)+merged["Storage Cost"]+merged["PIM Cost"]

    tl_upload=None
    if args.template and os.path.exists(args.template):
        tl_upload=build_teamleader_upload(args.template, merged, seller_name_col_guess="Seller Name")

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
            merged.to_csv(os.path.splitext(args.output)[0]+"_totals.csv", index=False)

    if issues_rows is not None and not args.allow_issues:
        log("[result] Issues detected. Totals written; fix data or rerun with --allow-issues.", args.verbose)
        sys.exit(2)

    log(f"[write] Excel: {args.output}", args.verbose)

if __name__=="__main__":
    main()
