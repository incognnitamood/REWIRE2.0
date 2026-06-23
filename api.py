"""REWIRE — FastAPI inference backend.

Serves the trained RepurposingGAT for drug-repurposing queries and exposes the
PPI graph for frontend network visualization.

Endpoints:
    GET  /                     health/info
    GET  /stats                network + dataset summary
    GET  /diseases             the 8 disease cluster names
    POST /rank                 rank drugs by similarity to a disease centroid
    GET  /drug/{name}/graph    target nodes + 1-hop neighborhood for viz

Heavy artifacts (PPI graph, GAT weights, drug embeddings) are loaded once at
startup and cached, so per-request work is just centroid + cosine math.
"""

import math
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# NOTE: torch must be imported before numpy/pandas. On Windows, importing the
# MKL-backed numpy/pandas first can poison the DLL search so torch's c10.dll
# fails to initialize (WinError 1114). Loading torch first avoids the clash.
import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from gat_model import RepurposingGAT                       # noqa: E402
from ppi_graph import build_graph, simulate_binding        # noqa: E402
import train_gat as tg                        # noqa: E402  (cluster maps + helpers)

OUTPUT_DIR = ROOT / "outputs"
DATA_DIR = ROOT / "data" / "processed"
DRUG_FILE = DATA_DIR / "canonical_drug_targets.csv"
CHEM_FILE = DATA_DIR / "drug_chemistry.csv"
KNOWN_FILE = DATA_DIR / "known_indications.csv"
EXTERNAL_FILE = DATA_DIR / "external_drug_targets.csv"
MATRIX_FILE = OUTPUT_DIR / "drug_rsv_matrix.npy"
NAMES_FILE = OUTPUT_DIR / "drug_names.txt"
MODEL_FILE = OUTPUT_DIR / "rewire_gat.pth"

# Default binding inhibition used by the attenuation view when a target's
# affinity is unknown (per the feature spec).
DEFAULT_INHIBITION = 0.5

# ChEMBL live-lookup config (Feature 3 dynamic search per DYNAMIC_SEARCH.md).
# When a drug is absent from both the local dataset and the static fallback
# table, we query the public ChEMBL REST API for its mechanism-of-action
# targets and feed those into the exact same scoring pipeline.
CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_TIMEOUT = 20                  # seconds per HTTP call
CHEMBL_DEFAULT_AFFINITY_NM = 100.0   # used when no activity value is available

# Cache populated at startup.
CTX: dict = {}


def _load_context():
    """Build the PPI graph, load the trained GAT, and embed all 141 drugs."""
    # --- RSV matrix + names ------------------------------------------------
    rsv = np.load(MATRIX_FILE).astype(np.float64)
    drug_names = [n for n in NAMES_FILE.read_text(encoding="utf-8").splitlines()
                  if n]
    rsv_std = (rsv - rsv.mean(0)) / (rsv.std(0) + 1e-12)
    rsv_tensor = torch.tensor(rsv_std, dtype=torch.float32)

    # --- drug -> target genes ---------------------------------------------
    df = pd.read_csv(DRUG_FILE)
    drug_targets = {name: list(grp["gene_symbol"])
                    for name, grp in df.groupby("drug_name", sort=False)}
    all_targets = set(df["gene_symbol"])

    # drug -> [(gene, affinity_nm | None)] for the edge-attenuation view.
    drug_target_rows: dict = {}
    for row in df.itertuples(index=False):
        aff = None if pd.isna(row.affinity_nm) else float(row.affinity_nm)
        drug_target_rows.setdefault(row.drug_name, []).append(
            (row.gene_symbol, aff))

    # --- PPI graph -> PyG Data --------------------------------------------
    G0 = build_graph()
    data, node_index = tg.build_pyg_graph(G0, all_targets)

    # --- per-drug target pooling index (aligned to drug_names) ------------
    target_index, target_batch = [], []
    for i, name in enumerate(drug_names):
        ids = [node_index[g] for g in drug_targets.get(name, [])
               if g in node_index] or [0]
        target_index += ids
        target_batch += [i] * len(ids)
    target_index = torch.tensor(target_index, dtype=torch.long)
    target_batch = torch.tensor(target_batch, dtype=torch.long)

    # --- disease label per drug (name or None) ---------------------------
    labels = [tg.assign_disease(drug_targets.get(n, [])) for n in drug_names]

    # --- load trained model + embed all drugs once -----------------------
    model = RepurposingGAT(in_dim=data.num_node_features, hidden_dim=16,
                           rsv_dim=rsv_tensor.shape[1], dropout=0.5)
    model.load_state_dict(torch.load(MODEL_FILE, map_location="cpu",
                                     weights_only=True))
    model.eval()
    with torch.no_grad():
        emb = model(data.x, data.edge_index, target_index, target_batch,
                    rsv_tensor).cpu().numpy()

    # --- chemistry / ground-truth / external-fallback tables -------------
    chemistry = _load_chemistry()
    known_indications = _load_known_indications()
    external_targets = _load_external_targets()
    disease_profiles = _build_disease_profiles(known_indications, chemistry)

    CTX.update(
        G0=G0,
        node_index=node_index,
        drug_names=drug_names,
        name_lookup={n.lower(): n for n in drug_names},
        drug_index={n: i for i, n in enumerate(drug_names)},
        drug_targets=drug_targets,
        drug_target_rows=drug_target_rows,
        labels=labels,
        embeddings=emb,
        n_proteins=G0.number_of_nodes(),
        n_edges=G0.number_of_edges(),
        # live-inference artifacts (Feature 3)
        model=model,
        data=data,
        rsv_mean=rsv.mean(axis=0),
        rsv_col_std=rsv.std(axis=0),
        rsv_baseline=None,            # computed lazily on first /infer
        # chemistry / clinical artifacts (Features 2 & 4)
        chemistry=chemistry,
        chem_lookup={n.lower(): n for n in chemistry},
        known_indications=known_indications,
        external_targets=external_targets,
        disease_profiles=disease_profiles,
        # volatile in-memory cache for live ChEMBL lookups (never persisted)
        chembl_cache={},
    )


def _load_chemistry():
    """drug_name -> {drug_class, scaffold_family, functional_groups, smiles}."""
    cdf = pd.read_csv(CHEM_FILE)
    out = {}
    for r in cdf.itertuples(index=False):
        groups = [g.strip() for g in str(r.functional_groups).split(";")
                  if g.strip()]
        out[r.drug_name] = {
            "drug_class": r.drug_class,
            "scaffold_family": r.scaffold_family,
            "functional_groups": groups,
            "smiles": "" if pd.isna(r.smiles) else str(r.smiles),
        }
    return out


def _load_known_indications():
    """disease_name -> [{drug_name, evidence_level}, ...] (ground truth)."""
    kdf = pd.read_csv(KNOWN_FILE)
    out: dict = {}
    for r in kdf.itertuples(index=False):
        out.setdefault(r.disease_name, []).append(
            {"drug_name": r.drug_name, "evidence_level": r.evidence_level})
    return out


def _load_external_targets():
    """lower(drug_name) -> [(gene_symbol, affinity_nm), ...] fallback table."""
    if not EXTERNAL_FILE.exists():
        return {}
    edf = pd.read_csv(EXTERNAL_FILE)
    out: dict = {}
    for r in edf.itertuples(index=False):
        out.setdefault(r.drug_name.lower(), []).append(
            (r.gene_symbol, float(r.affinity_nm)))
    return out


def _build_disease_profiles(known, chemistry):
    """disease_name -> set of functional groups typical of its known drugs."""
    profiles = {}
    for disease, drugs in known.items():
        groups = set()
        for item in drugs:
            info = chemistry.get(item["drug_name"])
            if info:
                groups.update(info["functional_groups"])
        profiles[disease] = groups
    return profiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_context()
    yield
    CTX.clear()


app = FastAPI(title="REWIRE API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class RankRequest(BaseModel):
    disease_name: str
    top_k: int = 10


class InferRequest(BaseModel):
    drug_name: str
    disease_name: str


# ---------------------------------------------------------------------------
# Shared scoring helpers
# ---------------------------------------------------------------------------
def _disease_centroid(disease_name: str):
    """Mean embedding of the drugs labelled for ``disease_name`` (+ members)."""
    labels = CTX["labels"]
    emb = CTX["embeddings"]
    members = [i for i, lab in enumerate(labels) if lab == disease_name]
    if not members:
        return None, members
    return emb[members].mean(axis=0), members


def _cosine_to_centroid(vec, centroid):
    """Cosine similarity between a single embedding and the centroid."""
    c = centroid / (np.linalg.norm(centroid) + 1e-12)
    v = vec / (np.linalg.norm(vec) + 1e-12)
    return float(v @ c)


def _rank_for_disease(disease_name: str, top_k: int):
    """Centroid + cosine ranking of every drug against a disease cluster."""
    drug_names = CTX["drug_names"]
    labels = CTX["labels"]
    emb = CTX["embeddings"]

    centroid, members = _disease_centroid(disease_name)
    if centroid is None:
        raise HTTPException(
            status_code=404,
            detail=f"No labelled drugs for '{disease_name}'",
        )

    c = centroid / (np.linalg.norm(centroid) + 1e-12)
    z = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12)
    sims = z @ c

    order = np.argsort(-sims)[:top_k]
    results = [
        {
            "rank": rnk,
            "drug_name": drug_names[i],
            "similarity_score": round(float(sims[i]), 6),
            "known_indication": labels[i] == disease_name,
        }
        for rnk, i in enumerate(order, start=1)
    ]
    return {"disease_name": disease_name,
            "n_known_drugs": len(members),
            "results": results}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"service": "REWIRE", "status": "ok",
            "endpoints": [
                "/stats", "/diseases", "/rank", "/drug/{name}/graph",
                "/drug/{name}/attenuation", "/drug/{name}/chemistry",
                "/infer", "/disease/{name}/verification",
            ]}


@app.get("/stats")
def stats():
    return {
        "proteins": CTX["n_proteins"],
        "edges": CTX["n_edges"],
        "drugs": len(CTX["drug_names"]),
        "disease_clusters": len(tg.DISEASE_NAMES),
        "diseases": tg.DISEASE_NAMES,
    }


@app.get("/diseases")
def diseases():
    return {"diseases": tg.DISEASE_NAMES}


@app.post("/rank")
def rank(req: RankRequest):
    if req.disease_name not in tg.DISEASE_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown disease '{req.disease_name}'. "
                   f"Valid: {tg.DISEASE_NAMES}",
        )
    if req.top_k < 1:
        raise HTTPException(status_code=422, detail="top_k must be >= 1")

    return _rank_for_disease(req.disease_name, req.top_k)


@app.get("/drug/{name}/graph")
def drug_graph(name: str):
    canonical = CTX["name_lookup"].get(name.lower())
    if canonical is None:
        raise HTTPException(status_code=404, detail=f"Unknown drug '{name}'")

    G0 = CTX["G0"]
    targets = [g for g in CTX["drug_targets"].get(canonical, []) if g in G0]
    if not targets:
        return {"drug": canonical, "nodes": [], "links": []}

    target_set = set(targets)
    node_set = set(targets)
    for t in targets:
        node_set.update(G0.neighbors(t))

    nodes = [
        {"id": n, "group": "target" if n in target_set else "neighbor"}
        for n in node_set
    ]
    # Induced subgraph edges (target<->neighbor and neighbor<->neighbor).
    links = [
        {"source": u, "target": v, "weight": round(float(d["weight"]), 4)}
        for u, v, d in G0.subgraph(node_set).edges(data=True)
    ]
    return {"drug": canonical, "nodes": nodes, "links": links}


# ---------------------------------------------------------------------------
# Feature 1 — Edge Weight Attenuation View (network perturbation)
# ---------------------------------------------------------------------------
@app.get("/drug/{name}/attenuation")
def drug_attenuation(name: str):
    """Top-20 PPI edges most weakened by a drug binding its target proteins.

    For each target, binding_inhibition = 1 / (1 + affinity_nM) (default 0.5 if
    affinity is unknown). Every edge incident to a target is attenuated:
    new_weight = original_weight * (1 - binding_inhibition). Edges touching two
    targets take the stronger inhibition (most significant change).
    """
    canonical = CTX["name_lookup"].get(name.lower())
    if canonical is None:
        raise HTTPException(status_code=404, detail=f"Unknown drug '{name}'")

    G0 = CTX["G0"]

    # target gene -> binding inhibition (max over duplicate rows for that gene)
    inhibition: dict = {}
    for gene, aff in CTX["drug_target_rows"].get(canonical, []):
        if gene not in G0:
            continue
        inh = DEFAULT_INHIBITION if aff is None else 1.0 / (1.0 + aff)
        inhibition[gene] = max(inhibition.get(gene, 0.0), inh)

    if not inhibition:
        return {"drug": canonical, "n_targets": 0, "edges": []}

    # Collect incident edges, deduped by unordered pair, strongest inhibition.
    edge_inh: dict = {}
    for gene, inh in inhibition.items():
        for nbr in G0.neighbors(gene):
            key = frozenset((gene, nbr))
            old_w = float(G0[gene][nbr]["weight"])
            prev = edge_inh.get(key)
            if prev is None or inh > prev[3]:
                edge_inh[key] = (gene, nbr, old_w, inh)

    rows = []
    for gene, nbr, old_w, inh in edge_inh.values():
        new_w = old_w * (1.0 - inh)
        pct = (new_w - old_w) / old_w * 100.0 if old_w > 0 else 0.0
        rows.append({
            "protein_a": gene,
            "protein_b": nbr,
            "original_weight": round(old_w, 4),
            "new_weight": round(new_w, 4),
            "pct_change": round(pct, 2),
        })

    # Most significant negative change first (ascending % change).
    rows.sort(key=lambda r: r["pct_change"])
    return {
        "drug": canonical,
        "n_targets": len(inhibition),
        "targets": sorted(inhibition),
        "edges": rows[:20],
    }


# ---------------------------------------------------------------------------
# Feature 2 — Chemical Composition & Structural Similarity View
# ---------------------------------------------------------------------------
def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


@app.get("/drug/{name}/chemistry")
def drug_chemistry(name: str):
    """Chemical profile + Top-5 structural neighbours + disease-profile scores."""
    chemistry = CTX["chemistry"]
    canonical = CTX["chem_lookup"].get(name.lower())
    if canonical is None:
        raise HTTPException(
            status_code=404,
            detail=f"No chemical profile available for '{name}'",
        )

    info = chemistry[canonical]
    groups = set(info["functional_groups"])

    # Top-5 structurally similar drugs by Jaccard of functional-group sets.
    sims = []
    for other, oinfo in chemistry.items():
        if other == canonical:
            continue
        score = _jaccard(groups, set(oinfo["functional_groups"]))
        sims.append({
            "drug_name": other,
            "drug_class": oinfo["drug_class"],
            "jaccard_score": round(score, 4),
        })
    sims.sort(key=lambda x: x["jaccard_score"], reverse=True)
    top5 = sims[:5]

    # Disease-profile match: fraction of the drug's groups characteristic of
    # each disease's known-drug profile (overlap coefficient over the drug).
    disease_scores = []
    for disease in tg.DISEASE_NAMES:
        profile = CTX["disease_profiles"].get(disease, set())
        score = (len(groups & profile) / len(groups)) if groups else 0.0
        disease_scores.append({
            "disease": disease,
            "score": round(score, 4),
        })
    disease_scores.sort(key=lambda x: x["score"], reverse=True)

    return {
        "drug_name": canonical,
        "drug_class": info["drug_class"],
        "scaffold_family": info["scaffold_family"],
        "functional_groups": info["functional_groups"],
        "smiles": info["smiles"],
        "similar_drugs": top5,
        "disease_profiles": disease_scores,
    }


# ---------------------------------------------------------------------------
# Feature 3 — On-the-Fly Drug Inference (volatile, live execution)
# ---------------------------------------------------------------------------
def _ensure_rsv_baseline():
    """Lazily compute G0's expensive RSV baseline (betweenness/Louvain/Fiedler).

    Cached in CTX after the first call so subsequent live inferences are fast.
    """
    if CTX.get("rsv_baseline") is not None:
        return CTX["rsv_baseline"]
    import compute_rsv as crsv                              # noqa: E402
    baseline = crsv.precompute_baseline(CTX["G0"])
    CTX["rsv_baseline"] = baseline
    return baseline


def _chembl_get(path: str):
    """GET a ChEMBL REST resource and return parsed JSON (raises on failure)."""
    import json as _json
    import urllib.request
    url = f"{CHEMBL_BASE}/{path}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "REWIRE/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=CHEMBL_TIMEOUT) as resp:
        return _json.loads(resp.read().decode("utf-8"))


def _chembl_lookup(drug_name: str):
    """Resolve a drug name to [(gene_symbol, affinity_nm), ...] via ChEMBL.

    Implements the DYNAMIC_SEARCH.md dynamic-lookup step: when a drug is absent
    from both the local dataset and the static fallback table, query the public
    ChEMBL API for its mechanism-of-action targets and map those to HGNC gene
    symbols. Only genes present in our PPI graph are kept (the pipeline can only
    perturb nodes it knows). Any network/parse error degrades gracefully to an
    empty list, which the caller surfaces as the 'insufficient data' message.
    """
    import urllib.parse
    node_index = CTX["node_index"]
    try:
        q = urllib.parse.quote(drug_name)
        # Prefer an exact preferred-name match; fall back to fuzzy search.
        mols = _chembl_get(
            f"molecule?pref_name__iexact={q}&format=json&limit=5"
        ).get("molecules", [])
        if not mols:
            mols = _chembl_get(
                f"molecule/search?q={q}&format=json&limit=8"
            ).get("molecules", [])
        if not mols:
            return []

        genes: dict = {}
        # Walk candidate molecules until one yields graph-resident targets.
        for mol in mols[:5]:
            cid = mol.get("molecule_chembl_id")
            if not cid:
                continue
            mechs = _chembl_get(
                f"mechanism?molecule_chembl_id={cid}&format=json"
            ).get("mechanisms", [])
            target_ids = list(dict.fromkeys(
                m.get("target_chembl_id") for m in mechs
                if m.get("target_chembl_id")))
            for tid in target_ids:
                try:
                    tgt = _chembl_get(f"target/{tid}?format=json")
                except Exception:
                    continue
                for comp in tgt.get("target_components", []):
                    for syn in comp.get("target_component_synonyms", []):
                        if syn.get("syn_type") == "GENE_SYMBOL":
                            g = syn.get("component_synonym")
                            if g and g in node_index:
                                genes.setdefault(g, CHEMBL_DEFAULT_AFFINITY_NM)
            if genes:
                break
        return list(genes.items())
    except Exception as exc:                       # noqa: BLE001
        # Network/parse failure -> graceful empty result, but log for triage.
        print(f"[chembl] lookup failed for {drug_name!r}: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return []


def _embed_new_drug(targets):
    """Embed an off-database drug by running the *exact* live pipeline.

    ``targets`` is a list of (gene_symbol, affinity_nm). We perturb G0 with
    ``simulate_binding``, compute the 4-D RSV with the same primitives as
    compute_rsv, standardize it against the trained matrix's column stats, then
    run the trained GAT forward to produce a single 16-D embedding.
    """
    import compute_rsv as crsv                              # noqa: E402
    from torch_geometric.nn import global_mean_pool         # noqa: E402

    G0 = CTX["G0"]
    baseline = _ensure_rsv_baseline()
    genes = [g for g, _ in targets]

    targets_df = pd.DataFrame(targets, columns=["gene_symbol", "affinity_nm"])
    Gd = simulate_binding(G0, targets_df)  # deep copy inside; G0 untouched

    bc_d = crsv.betweenness_vector(Gd, baseline["node_order"])
    betweenness_shift = float(np.abs(bc_d - baseline["bc0"]).sum())

    labels_d = crsv.community_labels(Gd, baseline["node_order"])
    from sklearn.metrics import normalized_mutual_info_score  # noqa: E402
    community_change = 1.0 - float(
        normalized_mutual_info_score(baseline["labels0"], labels_d))

    spectral_delta = abs(
        crsv.fiedler_value(Gd, baseline["cc_nodes"]) - baseline["fiedler0"])
    entropy_delta = abs(
        crsv.target_entropy(Gd, genes) - crsv.target_entropy(G0, genes))

    rsv = np.array([betweenness_shift, community_change,
                    spectral_delta, entropy_delta], dtype=np.float64)

    # Standardize with the trained matrix's per-column stats (same as startup).
    rsv_std = (rsv - CTX["rsv_mean"]) / (CTX["rsv_col_std"] + 1e-12)
    rsv_tensor = torch.tensor(rsv_std[None, :], dtype=torch.float32)

    node_index = CTX["node_index"]
    ids = [node_index[g] for g in genes if g in node_index] or [0]
    target_index = torch.tensor(ids, dtype=torch.long)
    target_batch = torch.zeros(len(ids), dtype=torch.long)

    model = CTX["model"]
    data = CTX["data"]
    model.eval()
    with torch.no_grad():
        emb = model(data.x, data.edge_index, target_index, target_batch,
                    rsv_tensor).cpu().numpy()
    return emb[0]


@app.post("/infer")
def infer(req: InferRequest):
    """Live relevance of any drug (in- or out-of-database) to a disease.

    Volatile: nothing is persisted. In-database drugs reuse their precomputed
    embedding; out-of-database drugs are looked up in the external fallback
    table and scored live through the same GAT pipeline.
    """
    if req.disease_name not in tg.DISEASE_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown disease '{req.disease_name}'. "
                   f"Valid: {tg.DISEASE_NAMES}",
        )

    drug = req.drug_name.strip()
    if not drug:
        raise HTTPException(status_code=422, detail="drug_name is required")

    centroid, _ = _disease_centroid(req.disease_name)
    if centroid is None:
        raise HTTPException(
            status_code=404,
            detail=f"No labelled drugs for '{req.disease_name}'")

    canonical = CTX["name_lookup"].get(drug.lower())
    if canonical is not None:
        # In-database: reuse the precomputed embedding (instant).
        vec = CTX["embeddings"][CTX["drug_index"][canonical]]
        score = _cosine_to_centroid(vec, centroid)
        return {
            "drug_name": canonical,
            "disease_name": req.disease_name,
            "relevance_score": round(score, 6),
            "in_database": True,
            "source": "precomputed",
            "targets": CTX["drug_targets"].get(canonical, []),
        }

    # Out-of-database: resolve targets dynamically (DYNAMIC_SEARCH.md).
    #   1) static local fallback table (fast, deterministic)
    #   2) live ChEMBL API lookup (any real drug), cached in-memory only.
    node_index = CTX["node_index"]
    rows = CTX["external_targets"].get(drug.lower())
    valid = [(g, a) for g, a in (rows or []) if g in node_index]
    source = "external_fallback"

    if not valid:
        cache = CTX["chembl_cache"]
        key = drug.lower()
        if key in cache:
            valid = cache[key]
        else:
            valid = _chembl_lookup(drug)
            cache[key] = valid          # volatile only — never written to disk
        source = "chembl_live"

    if not valid:
        raise HTTPException(
            status_code=404,
            detail=(f"Insufficient data available for {drug} — "
                    f"computational relevance cannot be evaluated."),
        )

    vec = _embed_new_drug(valid)
    score = _cosine_to_centroid(vec, centroid)
    return {
        "drug_name": drug,
        "disease_name": req.disease_name,
        "relevance_score": round(score, 6),
        "in_database": False,
        "source": source,
        "targets": [g for g, _ in valid],
    }


# ---------------------------------------------------------------------------
# Feature 4 — Clinical Verification Panel (comparative analysis)
# ---------------------------------------------------------------------------
@app.get("/disease/{name}/verification")
def disease_verification(name: str):
    """Ground-truth clinical drugs vs. the model's Top-10, with overlap flags."""
    if name not in tg.DISEASE_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown disease '{name}'. Valid: {tg.DISEASE_NAMES}",
        )

    known = CTX["known_indications"].get(name, [])
    ranked = _rank_for_disease(name, 10)["results"]

    known_names = {k["drug_name"] for k in known}
    ranked_names = {r["drug_name"] for r in ranked}
    overlap = sorted(known_names & ranked_names)

    known_out = [
        {**k, "overlap": k["drug_name"] in ranked_names} for k in known
    ]
    ranked_out = [
        {**r, "overlap": r["drug_name"] in known_names} for r in ranked
    ]

    return {
        "disease_name": name,
        "known_treatments": known_out,
        "computed_ranking": ranked_out,
        "overlap_drugs": overlap,
        "n_known": len(known_names),
        "n_overlap": len(overlap),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8077, reload=False)
