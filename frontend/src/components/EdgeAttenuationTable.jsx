import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Loader2, Waypoints, TrendingDown, MousePointerClick } from 'lucide-react'
import { getAttenuation } from '../lib/api'

// Feature 1 — Edge Weight Attenuation View.
// Shows the Top-20 PPI edges most weakened when a drug binds its target
// proteins, comparing the original and attenuated interaction weights.
export default function EdgeAttenuationTable({ drug }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!drug) {
      setData(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getAttenuation(drug)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError('Could not load attenuation data.'))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [drug])

  if (!drug) {
    return (
      <EmptyShell
        icon={MousePointerClick}
        text="Select a drug in the Ranked Candidates table to see how it attenuates the biological network around its target proteins."
      />
    )
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-50">
            <Waypoints className="h-4 w-4 text-rose-600" />
          </span>
          <div>
            <p className="text-sm font-bold text-slate-900">
              {drug} — Edge Weight Attenuation
            </p>
            <p className="text-xs text-slate-400">
              {data?.n_targets
                ? `Top ${data.edges.length} weakened interactions across ${data.n_targets} target protein(s)`
                : 'Network perturbation around drug-target proteins'}
            </p>
          </div>
        </div>
        {data?.edges?.length ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-600">
            <TrendingDown className="h-3.5 w-3.5" />
            Connections weakened
          </span>
        ) : null}
      </div>

      {loading ? (
        <div className="flex h-56 flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="h-7 w-7 animate-spin text-rose-500" />
          <p className="text-sm font-medium">Computing perturbation…</p>
        </div>
      ) : error ? (
        <div className="px-5 py-10 text-center text-sm text-rose-600">{error}</div>
      ) : !data?.edges?.length ? (
        <div className="px-5 py-10 text-center text-sm text-slate-400">
          No target proteins for {drug} are present in the interaction network,
          so no edges are attenuated.
        </div>
      ) : (
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/70">
              <Th>Protein A</Th>
              <Th>Protein B</Th>
              <Th className="text-right">Original Weight</Th>
              <Th className="text-right">New Weight</Th>
            </tr>
          </thead>
          <tbody>
            {data.edges.map((e, i) => (
              <motion.tr
                key={`${e.protein_a}-${e.protein_b}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: i * 0.02 }}
                className="border-b border-slate-100 last:border-0 hover:bg-rose-50/30"
              >
                <td className="px-5 py-3 font-mono text-sm font-semibold text-slate-700">
                  {e.protein_a}
                </td>
                <td className="px-5 py-3 font-mono text-sm text-slate-600">
                  {e.protein_b}
                </td>
                <td className="px-5 py-3 text-right font-mono text-sm tabular-nums text-slate-500">
                  {e.original_weight.toFixed(4)}
                </td>
                <td className="px-5 py-3 text-right font-mono text-sm tabular-nums text-slate-500">
                  {e.new_weight.toFixed(4)}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function Th({ children, className = '' }) {
  return (
    <th
      className={`px-5 py-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 ${className}`}
    >
      {children}
    </th>
  )
}

function EmptyShell({ icon: Icon, text }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
        <Icon className="h-6 w-6" />
      </span>
      <p className="max-w-md text-sm text-slate-400">{text}</p>
    </div>
  )
}
