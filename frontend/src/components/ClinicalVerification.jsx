import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Loader2,
  Stethoscope,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react'
import { getVerification } from '../lib/api'
import { cn, labelFor } from '../lib/utils'

// Color-coded evidence badges for ground-truth treatments.
function EvidenceBadge({ level }) {
  const tone =
    level === 'Approved'
      ? 'bg-emerald-50 text-emerald-700 ring-emerald-600/20'
      : level === 'Off-label'
        ? 'bg-amber-50 text-amber-700 ring-amber-600/20'
        : 'bg-sky-50 text-sky-700 ring-sky-600/20'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset',
        tone,
      )}
    >
      {level}
    </span>
  )
}

export default function ClinicalVerification({ disease }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!disease) return
    let cancelled = false
    setLoading(true)
    setError(null)
    getVerification(disease)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError('Could not load verification data.'))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [disease])

  if (loading) {
    return (
      <div className="flex h-72 flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white text-slate-400 shadow-sm">
        <Loader2 className="h-7 w-7 animate-spin text-indigo-500" />
        <p className="text-sm font-medium">Comparing against clinical ground truth…</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-400 shadow-sm">
        {error || 'No data.'}
      </div>
    )
  }

  const diseaseLabel = labelFor(data.disease_name)
  const hasOverlap = data.n_overlap > 0
  const summary = hasOverlap
    ? `${data.n_overlap} of ${data.n_known} clinically established drugs for ${diseaseLabel} appear in our top 10 computed ranking — validating the model's approach.`
    : `No overlap detected between known clinical treatments and our top 10 computed predictions for ${diseaseLabel}. Model coverage or predictive accuracy here may be limited.`

  return (
    <div className="space-y-5">
      {/* Split view */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* LEFT — clinical ground truth */}
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50">
              <Stethoscope className="h-4 w-4 text-emerald-600" />
            </span>
            <div>
              <p className="text-sm font-bold text-slate-900">Currently Used Clinically</p>
              <p className="text-xs text-slate-400">
                Ground-truth treatments for {diseaseLabel}
              </p>
            </div>
          </div>
          <ul>
            {data.known_treatments.map((k, i) => (
              <motion.li
                key={k.drug_name}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.03 }}
                className={cn(
                  'flex items-center justify-between border-b border-slate-100 px-5 py-3 last:border-0',
                  k.overlap && 'bg-emerald-50/60',
                )}
              >
                <span className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                  {k.overlap && (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  )}
                  {k.drug_name}
                </span>
                <EvidenceBadge level={k.evidence_level} />
              </motion.li>
            ))}
          </ul>
        </div>

        {/* RIGHT — model computed ranking */}
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50">
              <Cpu className="h-4 w-4 text-indigo-600" />
            </span>
            <div>
              <p className="text-sm font-bold text-slate-900">Model Computed Ranking</p>
              <p className="text-xs text-slate-400">Top 10 predictions for {diseaseLabel}</p>
            </div>
          </div>
          <ul>
            {data.computed_ranking.map((r, i) => (
              <motion.li
                key={r.drug_name}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.03 }}
                className={cn(
                  'flex items-center justify-between border-b border-slate-100 px-5 py-3 last:border-0',
                  r.overlap && 'bg-emerald-50/60',
                )}
              >
                <span className="flex items-center gap-3">
                  <span
                    className={cn(
                      'flex h-6 w-6 items-center justify-center rounded-md text-[11px] font-bold',
                      r.overlap
                        ? 'bg-emerald-500 text-white'
                        : 'bg-slate-100 text-slate-500',
                    )}
                  >
                    {r.rank}
                  </span>
                  <span className="text-sm font-semibold text-slate-800">
                    {r.drug_name}
                  </span>
                  {r.overlap && (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  )}
                </span>
                <span className="font-mono text-xs font-semibold tabular-nums text-slate-500">
                  {r.similarity_score.toFixed(3)}
                </span>
              </motion.li>
            ))}
          </ul>
        </div>
      </div>

      {/* Auto-summary */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className={cn(
          'flex items-start gap-3 rounded-2xl border p-4 text-sm',
          hasOverlap
            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
            : 'border-amber-200 bg-amber-50 text-amber-800',
        )}
      >
        {hasOverlap ? (
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
        ) : (
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
        )}
        <p className="font-medium leading-relaxed">{summary}</p>
      </motion.div>
    </div>
  )
}
