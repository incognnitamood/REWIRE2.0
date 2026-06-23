import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Beaker,
  Dna,
  ImageOff,
  Loader2,
  Layers,
  Tag,
  MousePointerClick,
} from 'lucide-react'
import { getChemistry } from '../lib/api'
import { labelFor } from '../lib/utils'

// A small deterministic palette so each functional group gets a stable,
// color-coded pill across renders.
const PILL_PALETTE = [
  'bg-indigo-50 text-indigo-700 ring-indigo-600/15',
  'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
  'bg-amber-50 text-amber-700 ring-amber-600/15',
  'bg-rose-50 text-rose-700 ring-rose-600/15',
  'bg-violet-50 text-violet-700 ring-violet-600/15',
  'bg-sky-50 text-sky-700 ring-sky-600/15',
  'bg-teal-50 text-teal-700 ring-teal-600/15',
  'bg-fuchsia-50 text-fuchsia-700 ring-fuchsia-600/15',
]

function pillClass(label) {
  let h = 0
  for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) >>> 0
  return PILL_PALETTE[h % PILL_PALETTE.length]
}

export default function ChemicalSimilarity({ drug, onSelectDrug }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [imgError, setImgError] = useState(false)

  useEffect(() => {
    setImgError(false)
    if (!drug) {
      setData(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getChemistry(drug)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setError('No chemical profile available.'))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [drug])

  if (!drug) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white/60 px-6 py-16 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
          <MousePointerClick className="h-6 w-6" />
        </span>
        <p className="max-w-md text-sm text-slate-400">
          Select a drug in the Ranked Candidates table to inspect its chemical
          composition and structural similarity to other drugs.
        </p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex h-72 flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white text-slate-400 shadow-sm">
        <Loader2 className="h-7 w-7 animate-spin text-indigo-500" />
        <p className="text-sm font-medium">Loading chemical profile…</p>
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

  const imgUrl = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(
    drug,
  )}/PNG`

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      {/* LEFT — structure + composition */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm lg:col-span-1"
      >
        <div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-4">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 text-white shadow-md shadow-indigo-500/30">
            <Beaker className="h-4 w-4" strokeWidth={2.4} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-slate-900">{drug}</p>
            <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
              2D Structure
            </p>
          </div>
        </div>

        {/* 2D molecular image */}
        <div className="px-5 pt-5">
          <div className="flex h-48 items-center justify-center rounded-xl border border-slate-200 bg-slate-50/70 p-3">
            {imgError ? (
              <div className="flex flex-col items-center gap-2 text-slate-400">
                <ImageOff className="h-7 w-7" />
                <p className="text-xs font-medium">2D structure unavailable</p>
              </div>
            ) : (
              <img
                src={imgUrl}
                alt={`2D structure of ${drug}`}
                loading="lazy"
                onError={() => setImgError(true)}
                className="max-h-full max-w-full object-contain mix-blend-multiply"
              />
            )}
          </div>
          <p className="mt-1.5 text-center text-[10px] text-slate-400">
            Source: PubChem PUG REST
          </p>
        </div>

        {/* Metadata badges */}
        <div className="space-y-3 px-5 pb-5 pt-4">
          <div className="flex items-center gap-2">
            <Tag className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Drug Class
            </span>
            <span className="ml-auto rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-600/15">
              {data.drug_class}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Layers className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Scaffold Family
            </span>
            <span className="ml-auto rounded-md bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700 ring-1 ring-inset ring-violet-600/15">
              {data.scaffold_family}
            </span>
          </div>

          <div className="pt-1">
            <div className="mb-2 flex items-center gap-2">
              <Dna className="h-4 w-4 text-indigo-500" strokeWidth={2.4} />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Functional Groups
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {data.functional_groups.map((g) => (
                <span
                  key={g}
                  className={`rounded-full px-3 py-1 text-xs font-medium capitalize ring-1 ring-inset ${pillClass(
                    g,
                  )}`}
                >
                  {g}
                </span>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* RIGHT — disease profile chart + similar drugs */}
      <div className="space-y-5 lg:col-span-2">
        {/* Disease composition similarity */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <h4 className="mb-1 text-sm font-bold text-slate-800">
            Composition Similarity to Disease Pathway Profiles
          </h4>
          <p className="mb-4 text-xs text-slate-400">
            How much of {drug}'s functional-group makeup matches the typical
            chemistry of drugs treating each disease.
          </p>
          <div className="space-y-3">
            {data.disease_profiles.map((d, i) => {
              const pct = Math.round(d.score * 100)
              return (
                <div key={d.disease} className="flex items-center gap-3">
                  <span className="w-40 shrink-0 truncate text-xs font-medium text-slate-600">
                    {labelFor(d.disease)}
                  </span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.6, delay: i * 0.05, ease: 'easeOut' }}
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-blue-500"
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right font-mono text-xs font-semibold tabular-nums text-slate-600">
                    {pct}%
                  </span>
                </div>
              )
            })}
          </div>
        </motion.div>

        {/* Top-5 structurally similar drugs */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
        >
          <div className="border-b border-slate-100 px-5 py-4">
            <h4 className="text-sm font-bold text-slate-800">
              Top 5 Structurally Similar Drugs
            </h4>
            <p className="text-xs text-slate-400">
              Ranked by Jaccard similarity of functional groups
            </p>
          </div>
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70">
                <th className="px-5 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Drug
                </th>
                <th className="px-5 py-2.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Class
                </th>
                <th className="px-5 py-2.5 text-right text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Jaccard
                </th>
              </tr>
            </thead>
            <tbody>
              {data.similar_drugs.map((s) => (
                <tr
                  key={s.drug_name}
                  onClick={() => onSelectDrug?.(s.drug_name)}
                  className="cursor-pointer border-b border-slate-100 last:border-0 transition-colors hover:bg-indigo-50/40"
                >
                  <td className="px-5 py-3 text-sm font-semibold text-slate-900">
                    {s.drug_name}
                  </td>
                  <td className="px-5 py-3 text-xs text-slate-500">
                    {s.drug_class}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <span className="inline-flex items-center gap-2">
                      <span className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-slate-100 sm:block">
                        <span
                          className="block h-full rounded-full bg-gradient-to-r from-emerald-400 to-teal-500"
                          style={{ width: `${Math.round(s.jaccard_score * 100)}%` }}
                        />
                      </span>
                      <span className="font-mono text-xs font-semibold tabular-nums text-slate-600">
                        {s.jaccard_score.toFixed(3)}
                      </span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      </div>
    </div>
  )
}
