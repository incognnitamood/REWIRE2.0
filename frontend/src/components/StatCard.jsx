import { motion } from 'framer-motion'
import { cn } from '../lib/utils'

const TONES = {
  indigo: 'from-indigo-500 to-blue-600 shadow-indigo-500/30',
  emerald: 'from-emerald-500 to-teal-600 shadow-emerald-500/30',
  violet: 'from-violet-500 to-purple-600 shadow-violet-500/30',
}

export default function StatCard({ icon: Icon, label, value, tone = 'indigo', index = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: 'easeOut' }}
      className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
    >
      <div
        className={cn(
          'flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg',
          TONES[tone],
        )}
      >
        <Icon className="h-6 w-6" strokeWidth={2.2} />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {label}
        </p>
        <p className="font-mono text-2xl font-bold tabular-nums tracking-tight text-slate-900">
          {value}
        </p>
      </div>
    </motion.div>
  )
}
