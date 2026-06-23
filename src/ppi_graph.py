"""REWIRE — PPI graph construction and drug-binding perturbation.

`build_graph()` loads the protein-protein interaction edge list into the
baseline graph G0.  `simulate_binding()` produces a *perturbed* copy of a graph
given a set of drug targets and their binding affinities.

Design contract:
    G0 is the pristine reference network.  It must NEVER be mutated.  Every
    perturbation operates on an independent deep copy, so callers can build G0
    once and reuse it across all 50 drugs in parallel without contamination.
"""

import copy
import math
from pathlib import Path

import networkx as nx
import pandas as pd

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PPI_FILE = DATA_DIR / "ppi_genes.csv"

WEIGHT_CUTOFF = 700      # keep only high-confidence interactions
WEIGHT_SCALE = 1000.0    # normalize STRING-style scores into (0, 1]

# Perturbation tunables -----------------------------------------------------
# Binding strength is mapped from affinity (nM) to a pKd-like scale and then
# squashed into [0, 1].  The strength drives an *additive* reduction of the
# edge weights incident to the bound target node.  An additive (rather than
# multiplicative) reduction is deliberate: it changes the *shape* of the local
# weight distribution, so the entropy metric in compute_rsv.py is non-trivial.
PKD_MIN = 4.0            # ~ affinity of 100,000 nM  -> strength 0
PKD_MAX = 11.0           # ~ affinity of 0.01 nM     -> strength 1
MAX_REDUCTION = 0.5      # largest additive weight drop for a maximal binder
WEIGHT_FLOOR = 0.05      # never let a perturbed edge weight vanish entirely


def build_graph():
    """Load the PPI edge list into the baseline NetworkX graph G0.

    Edges with weight < WEIGHT_CUTOFF are dropped; surviving weights are
    normalized by WEIGHT_SCALE into (0, 1].  Returns an undirected graph with a
    float ``weight`` attribute on every edge.
    """
    df = pd.read_csv(PPI_FILE)
    df = df[df["weight"] >= WEIGHT_CUTOFF].copy()
    df["weight"] = df["weight"].astype(float) / WEIGHT_SCALE

    G0 = nx.from_pandas_edgelist(df, "gene1", "gene2", edge_attr="weight")
    return G0


def affinity_to_strength(affinity_nm: float) -> float:
    """Map a binding affinity in nanomolar to a strength in [0, 1].

    Lower nM means tighter binding.  We convert to a pKd-like value
    (pKd = 9 - log10(affinity_nm)) and min-max squash it against a fixed
    reference window so the mapping is deterministic and independent of the
    particular drug set.
    """
    affinity_nm = max(float(affinity_nm), 1e-6)  # guard against 0 / negatives
    pkd = 9.0 - math.log10(affinity_nm)
    strength = (pkd - PKD_MIN) / (PKD_MAX - PKD_MIN)
    return min(1.0, max(0.0, strength))


def simulate_binding(G, targets_df: pd.DataFrame):
    """Return a perturbed deep copy of ``G`` reflecting drug binding.

    For every target gene present in the graph, the edges incident to that node
    are weakened by an additive amount proportional to the drug's binding
    strength (derived from ``affinity_nm``).  This models an inhibitor
    sequestering the target and degrading its local interactions.

    ``G`` (typically G0) is never modified — we always operate on a deep copy.
    """
    Gd = copy.deepcopy(G)

    for row in targets_df.itertuples(index=False):
        gene = row.gene_symbol
        if gene not in Gd:
            continue

        strength = affinity_to_strength(row.affinity_nm)
        reduction = MAX_REDUCTION * strength

        for neighbor in Gd.neighbors(gene):
            old_w = Gd[gene][neighbor]["weight"]
            Gd[gene][neighbor]["weight"] = max(old_w - reduction, WEIGHT_FLOOR)

    return Gd


if __name__ == "__main__":
    # Smoke test: build G0 and report basic structure without mutating it.
    G0 = build_graph()
    print(f"G0: {G0.number_of_nodes():,} nodes, {G0.number_of_edges():,} edges")

    drugs = pd.read_csv(DATA_DIR / "canonical_drug_targets.csv")
    sample = drugs.head(1)
    Gd = simulate_binding(G0, sample)
    gene = sample.iloc[0]["gene_symbol"]
    if gene in G0:
        before = [G0[gene][n]["weight"] for n in G0.neighbors(gene)]
        after = [Gd[gene][n]["weight"] for n in Gd.neighbors(gene)]
        print(f"target {gene}: mean weight {sum(before)/len(before):.4f} "
              f"-> {sum(after)/len(after):.4f}  (G0 unchanged)")
