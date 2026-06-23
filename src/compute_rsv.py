"""REWIRE — Rewiring Sensitivity Vector (RSV) calculator.

For each drug we perturb the baseline PPI network G0 around the drug's targets
(see ``ppi_graph.simulate_binding``) and measure how much the network's global
structure shifts.  The shift is summarized as a 4-dimensional RSV:

    1. Betweenness Shift   — L1 distance between betweenness-centrality vectors
                             (nx.betweenness_centrality, k=100, seed=42).
    2. Community Change    — 1 - NMI between Louvain partitions (python-louvain).
    3. Spectral Gap Delta  — |ΔFiedler|, the change in the second-smallest
                             Laplacian eigenvalue (scipy eigsh, k=2).
    4. Entropy Delta       — change in Shannon entropy of the edge weights
                             incident to the drug's target nodes.

The three global metrics (betweenness, community, Fiedler) are expensive, so
G0's baseline values are computed ONCE up front.  The drugs are then scored in
parallel with a ProcessPoolExecutor: each worker process rebuilds G0 once (via
an initializer) and reuses the precomputed baselines, so only the small
per-drug perturbation work is repeated.

Input is the cleaned, validated canonical_drug_targets.csv (143 rows / 141
distinct drugs).  Rows are grouped by drug name, so multi-target drugs such as
Ponatinib (FGFR1, ABL1) and Sorafenib (RAF1, KIT) yield a single RSV vector
each — exactly 141 vectors in total.

Outputs:
    outputs/drug_rsv_matrix.npy   — float64 array, shape (n_drugs, 4)
    outputs/drug_names.txt        — drug names, one per line, row-aligned
"""

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import community as community_louvain
import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse.linalg import eigsh
from sklearn.metrics import normalized_mutual_info_score
from tqdm import tqdm

from ppi_graph import build_graph, simulate_binding

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"
DRUG_FILE = DATA_DIR / "canonical_drug_targets.csv"

RSV_DIM = 4
BETWEENNESS_K = 100
BETWEENNESS_SEED = 42
LOUVAIN_SEED = 42
FIEDLER_TOL = 1e-3          # plenty precise: perturbation signal >> solver noise
FIEDLER_MAXITER = 5000

# ---------------------------------------------------------------------------
# Per-process globals, populated by the pool initializer (and in __main__).
# ---------------------------------------------------------------------------
_G0 = None             # baseline graph (rebuilt once per worker process)
_NODE_ORDER = None     # fixed node ordering for vector alignment
_CC_NODES = None       # nodes of the largest connected component (for Fiedler)
_BC0 = None            # baseline betweenness vector  (aligned to _NODE_ORDER)
_LABELS0 = None        # baseline Louvain labels      (aligned to _NODE_ORDER)
_FIEDLER0 = None       # baseline Fiedler eigenvalue


# ---------------------------------------------------------------------------
# Metric primitives
# ---------------------------------------------------------------------------
def betweenness_vector(G, node_order):
    """Approximate betweenness centrality as a vector aligned to node_order."""
    bc = nx.betweenness_centrality(
        G, k=BETWEENNESS_K, seed=BETWEENNESS_SEED, weight="weight"
    )
    return np.array([bc[n] for n in node_order], dtype=np.float64)


def community_labels(G, node_order):
    """Louvain community labels as an integer vector aligned to node_order."""
    partition = community_louvain.best_partition(
        G, weight="weight", random_state=LOUVAIN_SEED
    )
    return np.array([partition[n] for n in node_order], dtype=np.int64)


def fiedler_value(G, cc_nodes):
    """Second-smallest Laplacian eigenvalue (algebraic connectivity).

    Computed on the largest connected component via Lanczos (eigsh, k=2,
    which='SA') — accurate and far cheaper in memory than shift-invert, which
    matters under heavy process parallelism.
    """
    L = nx.laplacian_matrix(
        G.subgraph(cc_nodes), nodelist=cc_nodes, weight="weight"
    ).astype(np.float64).tocsr()
    vals = eigsh(
        L, k=2, which="SA", tol=FIEDLER_TOL, maxiter=FIEDLER_MAXITER,
        return_eigenvectors=False,
    )
    return float(np.sort(vals)[1])


def target_entropy(G, genes):
    """Summed Shannon entropy (bits) of edge weights incident to ``genes``."""
    total = 0.0
    for gene in genes:
        if gene not in G:
            continue
        weights = np.array(
            [G[gene][nbr]["weight"] for nbr in G.neighbors(gene)],
            dtype=np.float64,
        )
        s = weights.sum()
        if s <= 0 or weights.size == 0:
            continue
        p = weights / s
        total += float(-np.sum(p * np.log2(p)))
    return total


# ---------------------------------------------------------------------------
# Baseline precomputation (runs ONCE, in the main process)
# ---------------------------------------------------------------------------
def precompute_baseline(G0):
    """Compute G0's expensive global metrics a single time.

    Returns a dict of small, picklable artifacts that worker processes use as
    their reference baseline (the heavy graph itself is rebuilt per worker).
    """
    node_order = sorted(G0.nodes())
    cc_nodes = sorted(max(nx.connected_components(G0), key=len))

    print("  - betweenness centrality (k=100, seed=42) ...", flush=True)
    bc0 = betweenness_vector(G0, node_order)
    print("  - Louvain community partition ...", flush=True)
    labels0 = community_labels(G0, node_order)
    print("  - Fiedler eigenvalue (eigsh k=2) ...", flush=True)
    fiedler0 = fiedler_value(G0, cc_nodes)

    return {
        "node_order": node_order,
        "cc_nodes": cc_nodes,
        "bc0": bc0,
        "labels0": labels0,
        "fiedler0": fiedler0,
    }


# ---------------------------------------------------------------------------
# Parallel worker plumbing
# ---------------------------------------------------------------------------
def init_worker(baseline):
    """Pool initializer: rebuild G0 once per process and load the baseline."""
    global _G0, _NODE_ORDER, _CC_NODES, _BC0, _LABELS0, _FIEDLER0
    _G0 = build_graph()
    _NODE_ORDER = baseline["node_order"]
    _CC_NODES = baseline["cc_nodes"]
    _BC0 = baseline["bc0"]
    _LABELS0 = baseline["labels0"]
    _FIEDLER0 = baseline["fiedler0"]


def compute_drug_rsv(task):
    """Compute the 4-D RSV for a single drug. Runs inside a worker process."""
    drug_name, targets = task
    targets_df = pd.DataFrame(targets, columns=["gene_symbol", "affinity_nm"])
    genes = [g for g, _ in targets]

    Gd = simulate_binding(_G0, targets_df)  # deep copy inside; _G0 untouched

    bc_d = betweenness_vector(Gd, _NODE_ORDER)
    betweenness_shift = float(np.abs(bc_d - _BC0).sum())

    labels_d = community_labels(Gd, _NODE_ORDER)
    community_change = 1.0 - float(
        normalized_mutual_info_score(_LABELS0, labels_d)
    )

    spectral_delta = abs(fiedler_value(Gd, _CC_NODES) - _FIEDLER0)

    entropy_delta = abs(
        target_entropy(Gd, genes) - target_entropy(_G0, genes)
    )

    rsv = np.array(
        [betweenness_shift, community_change, spectral_delta, entropy_delta],
        dtype=np.float64,
    )
    return drug_name, rsv


def build_drug_tasks(drug_file):
    """Group the drug CSV into per-drug (name, [(gene, affinity_nm), ...])."""
    df = pd.read_csv(drug_file)
    tasks = []
    for drug_name, grp in df.groupby("drug_name", sort=False):
        targets = list(zip(grp["gene_symbol"], grp["affinity_nm"].astype(float)))
        tasks.append((drug_name, targets))
    return tasks


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Building baseline graph G0 ...", flush=True)
    G0 = build_graph()
    print(f"  G0: {G0.number_of_nodes():,} nodes, "
          f"{G0.number_of_edges():,} edges", flush=True)

    print("Precomputing heavy G0 baseline metrics (once) ...", flush=True)
    baseline = precompute_baseline(G0)
    print(f"  baseline Fiedler = {baseline['fiedler0']:.6e}", flush=True)
    del G0  # workers rebuild their own copy

    tasks = build_drug_tasks(DRUG_FILE)
    n_targets = sum(len(t[1]) for t in tasks)
    print(f"  grouped {n_targets} target rows into {len(tasks)} distinct "
          f"drug(s)", flush=True)
    n_workers = os.cpu_count()
    print(f"Scoring {len(tasks)} drugs across {n_workers} processes ...",
          flush=True)

    results = [None] * len(tasks)
    with ProcessPoolExecutor(
        max_workers=n_workers, initializer=init_worker, initargs=(baseline,)
    ) as executor:
        for i, (drug_name, rsv) in enumerate(
            tqdm(executor.map(compute_drug_rsv, tasks), total=len(tasks),
                 desc="RSV")
        ):
            results[i] = (drug_name, rsv)

    drug_names = [r[0] for r in results]
    matrix = np.vstack([r[1] for r in results])  # shape (n_drugs, 4)

    np.save(OUTPUT_DIR / "drug_rsv_matrix.npy", matrix)
    (OUTPUT_DIR / "drug_names.txt").write_text(
        "\n".join(drug_names) + "\n", encoding="utf-8"
    )

    print(f"\nSaved RSV matrix {matrix.shape} -> "
          f"{OUTPUT_DIR / 'drug_rsv_matrix.npy'}")
    print(f"Saved {len(drug_names)} drug names -> "
          f"{OUTPUT_DIR / 'drug_names.txt'}")
    print("\nRSV columns: [betweenness_shift, community_change, "
          "spectral_delta, entropy_delta]")
    with np.printoptions(precision=4, suppress=True):
        print("First 5 rows:")
        for name, row in zip(drug_names[:5], matrix[:5]):
            print(f"  {name:<16} {row}")


if __name__ == "__main__":
    main()
