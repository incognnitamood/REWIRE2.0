import { motion } from 'framer-motion'
import { CheckCircle2, Sparkles, ChevronRight } from 'lucide-react'
import { cn } from '../lib/utils'

function StatusBadge({ known }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold',
        known
          ? 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20'
          : 'bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-600/20',
      )}
    >
      {known ? (
        <>
          <CheckCircle2 className="h-3.5 w-3.5" /> Known Indication
        </>
      ) : (
        <>
          <Sparkles className="h-3.5 w-3.5" /> Novel Candidate
        </>
      )}
    </span>
  )
}

function ScoreBar({ score }) {
  const pct = Math.max(0, Math.min(1, score)) * 100
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 w-full max-w-[160px] overflow-hidden rounded-full bg-slate-100">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-blue-500"
        />
      </div>
      <span className="font-mono text-xs font-semibold tabular-nums text-slate-600">
        {score.toFixed(3)}
      </span>
    </div>
  )
}

export default function RankedTable({ results, onSelectDrug, selectedDrug }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/70">
            <th className="px-5 py-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Rank
            </th>
            <th className="px-5 py-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Drug
            </th>
            <th className="px-5 py-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Similarity Score
            </th>
            <th className="px-5 py-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Status
            </th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody>
          {results.map((row, i) => (
            <motion.tr
              key={row.drug_name}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.04 }}
              onClick={() => onSelectDrug(row.drug_name)}
              className={cn(
                'group cursor-pointer border-b border-slate-100 last:border-0 transition-colors hover:bg-indigo-50/40',
                selectedDrug === row.drug_name && 'bg-indigo-50/70',
              )}
            >
              <td className="px-5 py-4">
                <span
                  className={cn(
                    'flex h-7 w-7 items-center justify-center rounded-lg text-xs font-bold',
                    row.rank <= 3
                      ? 'bg-gradient-to-br from-indigo-500 to-blue-600 text-white'
                      : 'bg-slate-100 text-slate-500',
                  )}
                >
                  {row.rank}
                </span>
              </td>
              <td className="px-5 py-4">
                <span className="font-semibold text-slate-900">{row.drug_name}</span>
              </td>
              <td className="px-5 py-4">
                <ScoreBar score={row.similarity_score} />
              </td>
              <td className="px-5 py-4">
                <StatusBadge known={row.known_indication} />
              </td>
              <td className="px-5 py-4 text-right">
                <ChevronRight className="ml-auto h-4 w-4 text-slate-300 transition-all group-hover:translate-x-0.5 group-hover:text-indigo-500" />
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
