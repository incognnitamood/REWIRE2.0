import { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { Loader2, Network, MousePointerClick } from 'lucide-react'

const TARGET_COLOR = '#ef4444' // red-500
const NEIGHBOR_COLOR = '#3b82f6' // blue-500
const TARGET_RADIUS = 6
const NEIGHBOR_RADIUS = 3

export default function NetworkGraph({ drug, data, loading }) {
  const containerRef = useRef(null)
  const [width, setWidth] = useState(800)
  const height = 540

  // Keep the canvas spanning the full container width responsively.
  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current
    const update = () => setWidth(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // ForceGraph2D mutates node/link objects, so give it a fresh clone per dataset.
  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    return {
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.links.map((l) => ({ ...l })),
    }
  }, [data])

  const counts = useMemo(() => {
    const targets = graphData.nodes.filter((n) => n.group === 'target').length
    return { targets, neighbors: graphData.nodes.length - targets }
  }, [graphData])

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Header / legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100">
            <Network className="h-4 w-4 text-slate-600" />
          </span>
          <div>
            <p className="text-sm font-bold text-slate-900">
              {drug ? `${drug} — PPI Neighborhood` : 'Network Topology'}
            </p>
            <p className="text-xs text-slate-400">
              {drug
                ? `${counts.targets} target · ${counts.neighbors} neighbors · ${graphData.links.length} interactions`
                : 'Select a drug to visualize its target network'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500" /> Target
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-blue-500" /> Neighbor
          </span>
        </div>
      </div>

      {/* Canvas area */}
      <div
        ref={containerRef}
        className="relative w-full overflow-hidden rounded-b-2xl bg-slate-50/50"
        style={{ height }}
      >
        {loading ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-slate-400">
            <Loader2 className="h-7 w-7 animate-spin text-indigo-500" />
            <p className="text-sm font-medium">Loading network…</p>
          </div>
        ) : !drug || graphData.nodes.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-slate-400">
            <MousePointerClick className="h-8 w-8" />
            <p className="max-w-xs text-center text-sm font-medium">
              Click a drug in the Ranked Candidates table to render its protein
              interaction network.
            </p>
          </div>
        ) : (
          <ForceGraph2D
            graphData={graphData}
            width={width}
            height={height}
            backgroundColor="rgba(0,0,0,0)"
            nodeLabel={(node) => node.id}
            nodeRelSize={1}
            linkColor={(link) =>
              `rgba(148, 163, 184, ${Math.max(0.08, Math.min(1, link.weight ?? 0.3))})`
            }
            linkWidth={(link) => 0.5 + (link.weight ?? 0.3)}
            cooldownTicks={120}
            nodeCanvasObjectMode={() => 'replace'}
            nodeCanvasObject={(node, ctx) => {
              const isTarget = node.group === 'target'
              const r = isTarget ? TARGET_RADIUS : NEIGHBOR_RADIUS
              ctx.beginPath()
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false)
              ctx.fillStyle = isTarget ? TARGET_COLOR : NEIGHBOR_COLOR
              ctx.fill()
              if (isTarget) {
                ctx.lineWidth = 1.5
                ctx.strokeStyle = 'rgba(239, 68, 68, 0.35)'
                ctx.stroke()
              }
            }}
            nodePointerAreaPaint={(node, color, ctx) => {
              const r = node.group === 'target' ? TARGET_RADIUS : NEIGHBOR_RADIUS
              ctx.beginPath()
              ctx.arc(node.x, node.y, r + 1, 0, 2 * Math.PI, false)
              ctx.fillStyle = color
              ctx.fill()
            }}
          />
        )}
      </div>
    </div>
  )
}
