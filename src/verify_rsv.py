"""Verify the regenerated RSV outputs.

Confirms that:
    1. outputs/drug_rsv_matrix.npy has shape exactly (141, 4).
    2. outputs/drug_names.txt holds exactly 141 names, row-aligned to the matrix.
    3. The matrix contains no NaN or infinity values.

Exits 0 only if every check passes.
"""

import sys
from pathlib import Path

import numpy as np

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
MATRIX_FILE = OUTPUT_DIR / "drug_rsv_matrix.npy"
NAMES_FILE = OUTPUT_DIR / "drug_names.txt"

EXPECTED_SHAPE = (141, 4)
EXPECTED_DRUGS = 141


def main() -> int:
    matrix = np.load(MATRIX_FILE)
    names = [n for n in NAMES_FILE.read_text(encoding="utf-8").splitlines() if n]

    print(f"Verifying RSV outputs in {OUTPUT_DIR}")
    print("-" * 60)

    check_shape = matrix.shape == EXPECTED_SHAPE
    print(f"[1] matrix shape == {EXPECTED_SHAPE}   : "
          f"{'PASS' if check_shape else 'FAIL'} (got {matrix.shape})")

    check_names = len(names) == EXPECTED_DRUGS and len(names) == matrix.shape[0]
    print(f"[2] len(drug_names) == {EXPECTED_DRUGS}     : "
          f"{'PASS' if check_names else 'FAIL'} "
          f"(got {len(names)}; matrix rows {matrix.shape[0]})")

    n_nan = int(np.isnan(matrix).sum())
    n_inf = int(np.isinf(matrix).sum())
    check_finite = n_nan == 0 and n_inf == 0
    print(f"[3] no NaN / inf values        : "
          f"{'PASS' if check_finite else 'FAIL'} "
          f"({n_nan} NaN, {n_inf} inf)")

    print("-" * 60)
    if check_shape and check_names and check_finite:
        print("RSV VERIFICATION SUCCESSFUL")
        return 0
    print("RSV VERIFICATION FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
