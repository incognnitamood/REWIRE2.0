import { motion } from 'framer-motion'
import { Loader2, Sparkles } from 'lucide-react'
import { cn, labelFor } from '../lib/utils'

const TOP_K_OPTIONS = [5, 10, 20]

export default function ControlPanel({
  activeDisease,
  topK,
  onTopKChange,
  onRun,
  loading,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        {/* Target disease */}
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Target Disease
          </p>
          <p className="mt-1 text-lg font-bold text-slate-900">
            {activeDisease ? labelFor(activeDisease) : 'Select a disease'}
          </p>
        </div>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          {/* Top K pills */}
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Top K Candidates
            </p>
            <div className="inline-flex rounded-xl bg-slate-100 p-1">
              {TOP_K_OPTIONS.map((k) => {
                const isActive = topK === k
                return (
                  <button
                    key={k}
                    onClick={() => onTopKChange(k)}
                    className={cn(
                      'relative w-12 rounded-lg py-1.5 text-sm font-semibold transition-colors',
                      isActive ? 'text-white' : 'text-slate-500 hover:text-slate-800',
                    )}
                  >
                    {isActive && (
                      <motion.span
                        layoutId="active-topk"
                        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                        className="absolute inset-0 rounded-lg bg-gradient-to-r from-indigo-500 to-blue-600 shadow"
                      />
                    )}
                    <span className="relative z-10">{k}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Run button */}
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={onRun}
            disabled={loading || !activeDisease}
            className={cn(
              'flex h-11 items-center justify-center gap-2 rounded-xl px-6 text-sm font-semibold text-white shadow-lg transition-all',
              loading || !activeDisease
                ? 'cursor-not-allowed bg-slate-300 shadow-none'
                : 'bg-gradient-to-r from-indigo-500 to-blue-600 shadow-indigo-500/30 hover:shadow-xl hover:shadow-indigo-500/40',
            )}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Run AI Repurposing
              </>
            )}
          </motion.button>
        </div>
      </div>
    </div>
  )
}
