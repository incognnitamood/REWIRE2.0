import axios from 'axios'

// Global API configuration — points at the REWIRE FastAPI backend.
export const API_BASE_URL = 'http://127.0.0.1:8077'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

export const getStats = () => api.get('/stats').then((r) => r.data)

export const getDiseases = () => api.get('/diseases').then((r) => r.data)

export const rankDrugs = (disease_name, top_k) =>
  api.post('/rank', { disease_name, top_k }).then((r) => r.data)

export const getDrugGraph = (name) =>
  api.get(`/drug/${encodeURIComponent(name)}/graph`).then((r) => r.data)

// Feature 1 — edge-weight attenuation (network perturbation).
export const getAttenuation = (name) =>
  api.get(`/drug/${encodeURIComponent(name)}/attenuation`).then((r) => r.data)

// Feature 2 — chemical composition + structural similarity.
export const getChemistry = (name) =>
  api.get(`/drug/${encodeURIComponent(name)}/chemistry`).then((r) => r.data)

// Feature 3 — on-the-fly live inference (volatile, may take a moment).
// Off-database drugs run the full network-perturbation pipeline live (graph
// betweenness/Louvain/Fiedler on ~16k nodes), so allow a generous timeout.
export const inferDrug = (drug_name, disease_name) =>
  api
    .post('/infer', { drug_name, disease_name }, { timeout: 180000 })
    .then((r) => r.data)

// Feature 4 — clinical verification / comparative analysis.
export const getVerification = (disease_name) =>
  api
    .get(`/disease/${encodeURIComponent(disease_name)}/verification`)
    .then((r) => r.data)

export default api
