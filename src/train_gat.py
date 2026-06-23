"""REWIRE — train the RepurposingGAT on disease-cluster supervision.

Pipeline:
    1. Load the 141x4 RSV matrix and the row-aligned drug names.
    2. Build the PPI graph (ppi_graph.build_graph) as a single PyG Data object,
       with node features [normalized log-degree, is_drug_target].
    3. Map every drug to a disease cluster from its target gene(s).
    4. Embed all drugs with the GAT (target-node pooling + RSV fusion).
    5. Optimize a CosineEmbeddingLoss over drug pairs: same disease -> +1
       (pull together), different disease -> -1 (push apart).
    6. Save the trained weights to outputs/rewire_gat.pth.

Disease-cluster gene sets are disjoint, following the spec's family hints so
that each labelled drug belongs to exactly one cluster.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch_geometric.data import Data

from gat_model import RepurposingGAT
from ppi_graph import build_graph

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"
DATA_DIR = ROOT / "data" / "processed"
DRUG_FILE = DATA_DIR / "canonical_drug_targets.csv"
MATRIX_FILE = OUTPUT_DIR / "drug_rsv_matrix.npy"
NAMES_FILE = OUTPUT_DIR / "drug_names.txt"
MODEL_OUT = OUTPUT_DIR / "rewire_gat.pth"

SEED = 42
EPOCHS = 100
LR = 0.01
WEIGHT_DECAY = 1e-3

# Disjoint gene -> disease assignment (one cluster per gene). Built from the
# spec's hints, extended with same-family targets present in the dataset.
DISEASE_GENES = {
    "Hypertension":          {"ACE", "AGTR1", "ADRB1", "CACNA1C", "CACNA1D"},
    "Alzheimers":            {"ACHE", "GRIN1", "GRIN2A", "CHRM1"},
    "Leukemia":              {"ABL1", "SRC", "KIT", "FLT3", "FGFR1", "PDGFRA",
                              "ALK"},
    "Type2_Diabetes":        {"DPP4", "SLC5A2", "ABCC8", "MGAM", "PPARG",
                              "ACACB"},
    "Rheumatoid_Arthritis":  {"JAK1", "JAK3", "DHODH", "IMPDH1"},
    "Breast_Cancer":         {"ERBB2", "ESR1", "CYP19A1", "CDK4", "CDK6",
                              "PIK3CA", "PIK3CD"},
    "Parkinsons":            {"DDC", "COMT", "MAOB", "DRD2", "DRD3"},
    "Crohns":                {"ITGA4", "IL12B", "TLR9", "S1PR1", "NR3C1",
                              "PTGS1", "PTGS2", "SAA1"},
}
DISEASE_NAMES = list(DISEASE_GENES.keys())
GENE_TO_DISEASE = {g: d for d, genes in DISEASE_GENES.items() for g in genes}


def build_pyg_graph(G0, target_genes):
    """Convert the PPI graph into a PyG Data object with node features.

    Returns (data, node_index) where node_index maps gene symbol -> row id.
    """
    nodes = sorted(G0.nodes())
    node_index = {n: i for i, n in enumerate(nodes)}

    # Undirected edges -> both directions for message passing.
    src, dst = [], []
    for u, v in G0.edges():
        iu, iv = node_index[u], node_index[v]
        src += [iu, iv]
        dst += [iv, iu]
    edge_index = torch.tensor([src, dst], dtype=torch.long)

    deg = np.array([G0.degree(n) for n in nodes], dtype=np.float64)
    log_deg = np.log1p(deg)
    log_deg = (log_deg - log_deg.mean()) / (log_deg.std() + 1e-9)
    is_target = np.array([1.0 if n in target_genes else 0.0 for n in nodes])
    x = torch.tensor(np.stack([log_deg, is_target], axis=1),
                     dtype=torch.float32)

    return Data(x=x, edge_index=edge_index), node_index


def assign_disease(genes):
    """Assign a drug (given its target genes) to a single disease cluster.

    If targets map to several diseases, the most frequent one wins (ties broken
    by cluster order). Returns the disease name or None if no target matches.
    """
    hits = [GENE_TO_DISEASE[g] for g in genes if g in GENE_TO_DISEASE]
    if not hits:
        return None
    # majority vote; ties broken by cluster order (earliest wins).
    return max(DISEASE_NAMES,
               key=lambda d: (hits.count(d), -DISEASE_NAMES.index(d)))


def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    # --- 1. Load RSV matrix + names ------------------------------------
    rsv = np.load(MATRIX_FILE).astype(np.float64)
    drug_names = [n for n in NAMES_FILE.read_text(encoding="utf-8").splitlines()
                  if n]
    assert rsv.shape[0] == len(drug_names), "RSV / names length mismatch"
    n_drugs = len(drug_names)
    print(f"Loaded RSV matrix {rsv.shape} for {n_drugs} drugs")

    # Standardize RSV columns so all four metrics (which span ~8 orders of
    # magnitude) contribute to the fused embedding.
    rsv_std = (rsv - rsv.mean(0)) / (rsv.std(0) + 1e-12)
    rsv_tensor = torch.tensor(rsv_std, dtype=torch.float32)

    # --- 2. Drug -> target genes ---------------------------------------
    df = pd.read_csv(DRUG_FILE)
    drug_targets = {name: list(grp["gene_symbol"])
                    for name, grp in df.groupby("drug_name", sort=False)}
    all_targets = set(df["gene_symbol"])

    # --- 3. PPI -> PyG Data --------------------------------------------
    print("Building PPI graph -> PyG Data ...")
    G0 = build_graph()
    data, node_index = build_pyg_graph(G0, all_targets)
    print(f"  PyG graph: {data.num_nodes:,} nodes, "
          f"{data.edge_index.shape[1]:,} directed edges, "
          f"{data.num_node_features} node features")

    # --- target-node pooling index, aligned to drug_names order --------
    target_index, target_batch = [], []
    missing = []
    for i, name in enumerate(drug_names):
        genes = drug_targets.get(name, [])
        node_ids = [node_index[g] for g in genes if g in node_index]
        if not node_ids:
            missing.append(name)
            node_ids = [0]  # placeholder so every drug has a pooled vector
        target_index += node_ids
        target_batch += [i] * len(node_ids)
    if missing:
        print(f"  WARNING: {len(missing)} drug(s) had no target in graph: "
              f"{missing}")
    target_index = torch.tensor(target_index, dtype=torch.long)
    target_batch = torch.tensor(target_batch, dtype=torch.long)

    # --- 4. Disease cluster labels -------------------------------------
    labels = np.array([
        DISEASE_NAMES.index(d) if (d := assign_disease(drug_targets.get(n, [])))
        is not None else -1
        for n in drug_names
    ])
    labelled = np.where(labels >= 0)[0]
    print(f"Disease-cluster coverage: {len(labelled)}/{n_drugs} drugs labelled")
    for di, dname in enumerate(DISEASE_NAMES):
        cnt = int((labels == di).sum())
        print(f"  {dname:<22} {cnt} drug(s)")

    # --- pair construction for CosineEmbeddingLoss ---------------------
    pair_i, pair_j, pair_y = [], [], []
    for a_pos in range(len(labelled)):
        for b_pos in range(a_pos + 1, len(labelled)):
            i, j = int(labelled[a_pos]), int(labelled[b_pos])
            pair_i.append(i)
            pair_j.append(j)
            pair_y.append(1.0 if labels[i] == labels[j] else -1.0)
    pair_i = torch.tensor(pair_i, dtype=torch.long)
    pair_j = torch.tensor(pair_j, dtype=torch.long)
    pair_y = torch.tensor(pair_y, dtype=torch.float32)
    n_pos = int((pair_y > 0).sum())
    print(f"Training pairs: {len(pair_y)} "
          f"({n_pos} same-disease, {len(pair_y) - n_pos} different)")

    # --- 5. Model / optimizer / loss -----------------------------------
    model = RepurposingGAT(in_dim=data.num_node_features, hidden_dim=16,
                           rsv_dim=rsv_tensor.shape[1], dropout=0.5)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR,
                                 weight_decay=WEIGHT_DECAY)
    criterion = nn.CosineEmbeddingLoss()

    print(f"\nTraining for {EPOCHS} epochs (Adam lr={LR}, wd={WEIGHT_DECAY}) ...")
    model.train()
    for epoch in range(1, EPOCHS + 1):
        optimizer.zero_grad()
        z = model(data.x, data.edge_index, target_index, target_batch,
                  rsv_tensor)
        loss = criterion(z[pair_i], z[pair_j], pair_y)
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0 or epoch == 1:
            print(f"  epoch {epoch:3d}/{EPOCHS}   loss = {loss.item():.4f}")

    # --- 6. Save -------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), MODEL_OUT)
    print(f"\nSaved trained GAT weights -> {MODEL_OUT}")


if __name__ == "__main__":
    main()
