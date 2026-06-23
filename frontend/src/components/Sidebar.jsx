import { motion } from 'framer-motion'
import { Activity, Brain, Microscope, Shield, Dna, ChevronRight } from 'lucide-react'
import { cn, DISEASE_GROUPS } from '../lib/utils'

const ICONS = { Brain, Microscope, Activity, Shield }

const ACCENTS = {
  violet: 'text-violet-600 bg-violet-50',
  rose: 'text-rose-600 bg-rose-50',
  emerald: 'text-emerald-600 bg-emerald-50',
  amber: 'text-amber-600 bg-amber-50',
}

export default function Sidebar({ activeDisease, onSelect }) {
  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-r border-slate-200 bg-white">
      {/* Brand */}
      <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-lg shadow-indigo-500/30">
          <Dna className="h-5 w-5 text-white" strokeWidth={2.5} />
        </div>
        <div className="leading-tight">
          <h1 className="bg-gradient-to-r from-indigo-600 to-blue-600 bg-clip-text text-xl font-extrabold tracking-tight text-transparent">
            REWIRE
          </h1>
          <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Repurposing Engine
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-6 overflow-y-auto px-4 py-6">
        {DISEASE_GROUPS.map((group) => {
          const Icon = ICONS[group.icon] || Activity
          return (
            <div key={group.category}>
              <div className="mb-2 flex items-center gap-2 px-2">
                <span
                  className={cn(
                    'flex h-6 w-6 items-center justify-center rounded-md',
                    ACCENTS[group.accent],
                  )}
                >
                  <Icon className="h-3.5 w-3.5" strokeWidth={2.5} />
                </span>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  {group.category}
                </span>
              </div>

              <div className="space-y-1">
                {group.diseases.map((d) => {
                  const isActive = activeDisease === d.key
                  return (
                    <button
                      key={d.key}
                      onClick={() => onSelect(d.key)}
                      className={cn(
                        'group relative flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors',
                        isActive
                          ? 'text-white'
                          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
                      )}
                    >
                      {isActive && (
                        <motion.span
                          layoutId="active-disease"
                          transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                          className="absolute inset-0 rounded-lg bg-gradient-to-r from-indigo-500 to-blue-600 shadow-md shadow-indigo-500/30"
                        />
                      )}
                      <span className="relative z-10">{d.label}</span>
                      <ChevronRight
                        className={cn(
                          'relative z-10 h-4 w-4 transition-transform',
                          isActive
                            ? 'translate-x-0 opacity-90'
                            : '-translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-60',
                        )}
                      />
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </nav>

      <div className="border-t border-slate-100 px-6 py-4">
        <p className="text-[11px] leading-relaxed text-slate-400">
          GAT-powered network medicine.{' '}
          <span className="font-semibold text-slate-500">8 disease clusters</span>
        </p>
      </div>
    </aside>
  )
}
