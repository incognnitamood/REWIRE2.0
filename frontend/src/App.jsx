import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Pill,
  Atom,
  Share2,
  ListOrdered,
  Network,
  FlaskConical,
  AlertTriangle,
  Sparkles,
  Waypoints,
  Beaker,
  ShieldCheck,
} from 'lucide-react'

import Sidebar from './components/Sidebar'
import StatCard from './components/StatCard'
import ControlPanel from './components/ControlPanel'
import RankedTable from './components/RankedTable'
import NetworkGraph from './components/NetworkGraph'
import DrugChemicalProfile from './components/DrugChemicalProfile'
import EdgeAttenuationTable from './components/EdgeAttenuationTable'
import ChemicalSimilarity from './components/ChemicalSimilarity'
import ClinicalVerification from './components/ClinicalVerification'
import GlobalSearch from './components/GlobalSearch'
import { getStats, rankDrugs, getDrugGraph } from './lib/api'
import { cn, labelFor } from './lib/utils'

const fmt = (n) => (n == null ? '—' : n.toLocaleString('en-US'))

const TABS = [
  { id: 'ranked', label: 'Ranked Candidates', icon: ListOrdered },
  { id: 'network', label: 'Network Topology', icon: Network },
  { id: 'attenuation', label: 'Edge Attenuation', icon: Waypoints },
  { id: 'chemistry', label: 'Chemical Profile', icon: Beaker },
  { id: 'clinical', label: 'Clinical Verification', icon: ShieldCheck },
]

export default function App() {
  const [stats, setStats] = useState(null)
  const [statsError, setStatsError] = useState(false)

  const [activeDisease, setActiveDisease] = useState('Leukemia')
  const [topK, setTopK] = useState(10)

  const [results, setResults] = useState(null)
  const [rankLoading, setRankLoading] = useState(false)
  const [rankError, setRankError] = useState(null)

  const [activeTab, setActiveTab] = useState('ranked')
  const [selectedDrug, setSelectedDrug] = useState(null)
  const [graphData, setGraphData] = useState(null)
  const [graphLoading, setGraphLoading] = useState(false)

  // Fetch global stats once on mount.
  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setStatsError(true))
  }, [])

  const handleRun = async () => {
    if (!activeDisease) return
    setRankLoading(true)
    setRankError(null)
    setActiveTab('ranked')
    try {
      const data = await rankDrugs(activeDisease, topK)
      setResults(data)
    } catch {
      setRankError('Could not reach the REWIRE API. Is the backend running on :8077?')
      setResults(null)
    } finally {
      setRankLoading(false)
    }
  }

  const handleSelectDrug = async (name) => {
    // Selecting a drug reveals its chemical profile in the Ranked tab and
    // preloads its PPI network so the Network tab is ready instantly.
    setSelectedDrug(name)
    setGraphLoading(true)
    try {
      const data = await getDrugGraph(name)
      setGraphData(data)
    } catch {
      setGraphData({ nodes: [], links: [] })
    } finally {
      setGraphLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar activeDisease={activeDisease} onSelect={setActiveDisease} />

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-8 py-8">
          {/* Header */}
          <motion.header
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mb-7"
          >
            <div className="mb-1 inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600 ring-1 ring-inset ring-indigo-600/10">
              <FlaskConical className="h-3.5 w-3.5" />
              Computational Drug Repurposing
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
              Repurposing Dashboard
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Graph-attention network medicine over the human protein interactome.
            </p>
          </motion.header>

          {/* Stat cards */}
          {statsError ? (
            <div className="mb-7 flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              Unable to load stats from the API. Start the backend with{' '}
              <code className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs">
                uvicorn api:app --port 8077
              </code>
            </div>
          ) : (
            <div className="mb-7 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatCard
                icon={Pill}
                label="Unique Drugs"
                value={fmt(stats?.drugs)}
                tone="indigo"
                index={0}
              />
              <StatCard
                icon={Atom}
                label="Proteins"
                value={fmt(stats?.proteins)}
                tone="violet"
                index={1}
              />
              <StatCard
                icon={Share2}
                label="Interactions"
                value={fmt(stats?.edges)}
                tone="emerald"
                index={2}
              />
            </div>
          )}

          {/* Control panel */}
          <div className="mb-5">
            <ControlPanel
              activeDisease={activeDisease}
              topK={topK}
              onTopKChange={setTopK}
              onRun={handleRun}
              loading={rankLoading}
            />
          </div>

          {/* Global drug search — on-the-fly live inference (Feature 3) */}
          <div className="mb-7">
            <GlobalSearch activeDisease={activeDisease} />
          </div>

          {/* Tabs */}
          <div className="mb-4 flex items-center gap-1 rounded-xl bg-slate-100 p-1">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.id
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'relative flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
                    isActive ? 'text-slate-900' : 'text-slate-500 hover:text-slate-700',
                  )}
                >
                  {isActive && (
                    <motion.span
                      layoutId="active-tab"
                      transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                      className="absolute inset-0 rounded-lg bg-white shadow-sm"
                    />
                  )}
                  <Icon className="relative z-10 h-4 w-4" />
                  <span className="relative z-10">{tab.label}</span>
                </button>
              )
            })}
          </div>

          {/* Tab content */}
          <AnimatePresence mode="wait">
            {activeTab === 'ranked' && (
              <motion.div
                key="ranked"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                {rankError ? (
                  <div className="flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                    <AlertTriangle className="h-5 w-5 shrink-0" />
                    {rankError}
                  </div>
                ) : rankLoading ? (
                  <RankedSkeleton />
                ) : results?.results?.length ? (
                  <>
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm text-slate-500">
                        Ranking{' '}
                        <span className="font-semibold text-slate-700">
                          {labelFor(results.disease_name)}
                        </span>{' '}
                        · {results.n_known_drugs} known drugs in cluster
                      </p>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">
                        <Sparkles className="h-3.5 w-3.5" />
                        {results.results.filter((r) => !r.known_indication).length}{' '}
                        novel candidates
                      </span>
                    </div>
                    <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                      <div className={selectedDrug ? 'xl:col-span-2' : 'xl:col-span-3'}>
                        <RankedTable
                          results={results.results}
                          onSelectDrug={handleSelectDrug}
                          selectedDrug={selectedDrug}
                        />
                      </div>
                      <AnimatePresence mode="wait">
                        {selectedDrug && (
                          <div key={selectedDrug} className="xl:sticky xl:top-6 xl:self-start">
                            <DrugChemicalProfile
                              drugName={selectedDrug}
                              onViewNetwork={() => setActiveTab('network')}
                            />
                          </div>
                        )}
                      </AnimatePresence>
                    </div>
                  </>
                ) : (
                  <EmptyState
                    icon={ListOrdered}
                    title="No results yet"
                    text="Pick a disease and hit Run AI Repurposing to rank candidate drugs."
                  />
                )}
              </motion.div>
            )}

            {activeTab === 'network' && (
              <motion.div
                key="network"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <NetworkGraph
                  drug={selectedDrug}
                  data={graphData}
                  loading={graphLoading}
                />
              </motion.div>
            )}

            {activeTab === 'attenuation' && (
              <motion.div
                key="attenuation"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <EdgeAttenuationTable drug={selectedDrug} />
              </motion.div>
            )}

            {activeTab === 'chemistry' && (
              <motion.div
                key="chemistry"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <ChemicalSimilarity
                  drug={selectedDrug}
                  onSelectDrug={handleSelectDrug}
                />
              </motion.div>
            )}

            {activeTab === 'clinical' && (
              <motion.div
                key="clinical"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25 }}
              >
                <ClinicalVerification disease={activeDisease} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}

function EmptyState({ icon: Icon, title, text }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
        <Icon className="h-6 w-6" />
      </span>
      <p className="text-base font-semibold text-slate-700">{title}</p>
      <p className="max-w-sm text-sm text-slate-400">{text}</p>
    </div>
  )
}

function RankedSkeleton() {
  return (
    <div className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 rounded-lg px-2 py-3"
        >
          <div className="h-7 w-7 animate-pulse rounded-lg bg-slate-100" />
          <div className="h-4 w-32 animate-pulse rounded bg-slate-100" />
          <div className="h-2 w-40 animate-pulse rounded-full bg-slate-100" />
          <div className="ml-auto h-6 w-28 animate-pulse rounded-full bg-slate-100" />
        </div>
      ))}
    </div>
  )
}
