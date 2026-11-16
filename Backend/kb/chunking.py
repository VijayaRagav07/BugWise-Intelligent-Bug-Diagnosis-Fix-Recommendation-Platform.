import json
import re
import uuid
import pandas as pd
from pathlib import Path

RAW_FILE = Path(__file__).resolve().parent.parent / "data" / "raw" / "eclipse_bug_records_22-07-2022-csv.txt"
CHUNKS_OUT = Path(__file__).resolve().parent.parent / "data" / "processed" / "processed_chunks.json"

MAX_BUGS_FOR_CPU = 5000  # Optimal sample size: indexes in ~15 seconds on CPU

def clean_text(val) -> str:
    if pd.isna(val) or val is None:
        return ""
    text = str(val).strip()
    return "" if text.lower() in {"nan", "none", "---", "unspecified"} else text

def extract_exceptions(text: str) -> list[str]:
    matches = re.findall(r'\b([a-zA-Z0-9_$.]+(?:Exception|Error|Fault))\b', text)
    return sorted(list(set(matches)))

def run_chunking():
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Place eclipse_bug_records_22-07-2022-csv.txt at: {RAW_FILE}")

    # Exact column indices verified from sample row:
    # 0=bug_id, 7=product, 8=component, 11=op_sys, 13=resolution, 14=dup_id, 17=priority, 18=severity, 25=short_desc
    res_col_idx = 13
    summary_col_idx = 25

    valid_rows = []
    reader = pd.read_csv(
        RAW_FILE,
        sep=";",
        header=None,
        dtype=str,
        on_bad_lines="skip",
        chunksize=50000
    )

    for df_part in reader:
        df_part = df_part[df_part[0] != "bug_id"]
        res_series = df_part[res_col_idx].astype(str).str.strip()
        summary_series = df_part[summary_col_idx].astype(str).str.strip()

        filtered = df_part[
            res_series.isin(["FIXED", "DUPLICATE"]) &
            (summary_series.str.len() >= 15) &
            (summary_series.str.lower() != "nan")
        ].copy()
        valid_rows.append(filtered)

        if sum(len(x) for x in valid_rows) >= MAX_BUGS_FOR_CPU * 3:
            break

    df_clean = pd.concat(valid_rows, ignore_index=True)
    df_clean["bug_id_num"] = pd.to_numeric(df_clean[0], errors="coerce")
    df_sample = df_clean.sort_values("bug_id_num", ascending=False).head(MAX_BUGS_FOR_CPU)

    print(f"Filtered to {len(df_sample)} high-signal FIXED/DUPLICATE Eclipse bugs.")

    chunks = []
    for _, row in df_sample.iterrows():
        bug_id = clean_text(row[0])
        product = clean_text(row[7]) or "Eclipse"
        component = clean_text(row[8]) or "General"
        os_name = clean_text(row[11]) or "All"
        resolution = clean_text(row[13])
        dup_id = clean_text(row[14])
        priority = clean_text(row[17]) or "P3"
        severity = clean_text(row[18]) or "normal"
        summary = clean_text(row[25])

        if not summary:
            continue

        exceptions = extract_exceptions(summary)
        rich_content = (
            f"Product: {product} | Component: {component} | Severity: {severity} ({priority}) | OS: {os_name} | Resolution: {resolution}\n"
            f"Bug Summary: {summary}"
        )
        if resolution == "DUPLICATE" and dup_id.isdigit():
            rich_content += f"\nDuplicate Of: ECLIPSE-{dup_id}"

        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "source_dataset": "ECLIPSE_BUGZILLA_MENDELEY_2022",
            "original_bug_id": f"ECLIPSE-{bug_id}",
            "chunk_type": "DESCRIPTION",
            "content": rich_content,
            "product": product,
            "component": component,
            "severity": severity,
            "priority": priority,
            "resolution": resolution,
            "duplicate_of": f"ECLIPSE-{dup_id}" if dup_id.isdigit() else None,
            "exception_types": exceptions
        })

    CHUNKS_OUT.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_OUT.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"Success! Saved {len(chunks)} clean chunks -> {CHUNKS_OUT}")

if __name__ == "__main__":
    run_chunking()