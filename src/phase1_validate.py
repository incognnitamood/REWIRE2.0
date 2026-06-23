"""REWIRE Phase 1: validate the (expanded) canonical drug-targets file.

Runs three checks against data/processed/canonical_drug_targets.csv:
    1. Row count is exactly 143 (excluding the header).
    2. ``affinity_nm`` is strictly numeric (parseable as float) with no NaNs,
       empty strings, or non-numeric characters.
    3. No duplicate (drug_name, gene_symbol) target pairs.

The file is one row per drug-target pair. A handful of drugs are genuinely
multi-target (e.g. Ponatinib -> FGFR1/ABL1, Sorafenib -> RAF1/KIT), so a
repeated *drug name* is expected and valid; what must be unique is the
(drug, target) pair. The number of distinct drugs is reported for context.

Prints a per-check summary and, only if every check passes, emits
'DATA VALIDATION SUCCESSFUL'.
"""

import math
import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
DRUG_FILE = DATA_DIR / "canonical_drug_targets.csv"

EXPECTED_ROWS = 143


def _is_strict_float(raw: str) -> bool:
    """True only if ``raw`` is a clean, finite numeric string.

    Reading the column as text means pandas hasn't coerced anything yet, so we
    catch empty strings, stray characters, and NaN/inf spellings that
    ``float()`` would otherwise accept or that pandas would silently turn into
    NaN.
    """
    if raw is None:
        return False
    s = str(raw).strip()
    if s == "":
        return False
    try:
        val = float(s)
    except (ValueError, TypeError):
        return False
    return math.isfinite(val)  # rejects nan / inf / -inf


def main() -> int:
    # Read affinity_nm as raw text so we can detect non-numeric content
    # ourselves instead of letting pandas coerce it to NaN.
    df = pd.read_csv(DRUG_FILE, dtype={"affinity_nm": str})

    print(f"Validating: {DRUG_FILE}")
    print("-" * 60)

    # --- Check 1: exact row count --------------------------------------
    n_rows = len(df)
    check_rows = n_rows == EXPECTED_ROWS
    print(f"[1] Row count == {EXPECTED_ROWS:<4}        : "
          f"{'PASS' if check_rows else 'FAIL'} (found {n_rows})")

    # --- Check 2: affinity_nm strictly numeric -------------------------
    if "affinity_nm" not in df.columns:
        print("[2] affinity_nm numeric       : FAIL (column missing)")
        check_affinity = False
    else:
        raw = df["affinity_nm"]
        bad_mask = ~raw.apply(_is_strict_float)
        n_bad = int(bad_mask.sum())
        check_affinity = n_bad == 0
        print(f"[2] affinity_nm numeric       : "
              f"{'PASS' if check_affinity else 'FAIL'} "
              f"({n_bad} invalid value(s))")
        if n_bad:
            bad_rows = df.loc[bad_mask, ["drug_name", "affinity_nm"]]
            for _, r in bad_rows.head(10).iterrows():
                print(f"      - {r['drug_name']!r}: "
                      f"affinity_nm={r['affinity_nm']!r}")

    # --- Check 3: duplicate (drug_name, gene_symbol) pairs -------------
    # A repeated drug *name* is valid for multi-target drugs; the (drug,
    # target) PAIR is what must be unique.
    if {"drug_name", "gene_symbol"} - set(df.columns):
        print("[3] No duplicate drug-target  : FAIL (column missing)")
        check_dupes = False
    else:
        pair_dups = df[df.duplicated(subset=["drug_name", "gene_symbol"],
                                     keep=False)]
        n_dup_pairs = df.duplicated(subset=["drug_name", "gene_symbol"]).sum()
        check_dupes = n_dup_pairs == 0
        n_unique_drugs = df["drug_name"].nunique()
        print(f"[3] No dup (drug,target) pairs : "
              f"{'PASS' if check_dupes else 'FAIL'} "
              f"({int(n_dup_pairs)} duplicate pair(s); "
              f"{n_unique_drugs} distinct drugs)")
        for (name, gene), grp in pair_dups.groupby(["drug_name", "gene_symbol"]):
            print(f"      - {name!r} x {gene!r} appears {len(grp)} times")

    print("-" * 60)
    all_pass = check_rows and check_affinity and check_dupes
    if all_pass:
        print("DATA VALIDATION SUCCESSFUL")
        return 0
    print("DATA VALIDATION FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
