"use client"

import { useMemo, useCallback, useEffect, useState, useRef } from "react"
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type NodeTypes,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { toast } from "sonner"
import { Trail, DAGNode } from "@/lib/types"
import { getLayoutedElements } from "@/lib/layout"
import { PaperNode } from "./paper-node"
import { PaperDetailPanel } from "./paper-detail-panel"
import { ThemeToggle } from "./theme-toggle"
import {
  BookOpen,
  Clock,
  Star,
  Share2,
  Eye,
  Keyboard,
  X,
  Check,
  PartyPopper,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface DAGCanvasProps {
  trail: Trail
  onToggleRead: (nodeId: string) => void
  onToggleStar: (nodeId: string) => void
  onSaveNote: (nodeId: string, note: string) => void
  onBack?: () => void
}

const nodeTypes: NodeTypes = {
  paperNode: PaperNode,
}

const AVG_MINUTES_PER_PAPER = 15

function topologicalSort(dagNodes: DAGNode[]): string[] {
  const nodeMap = new Map(dagNodes.map((n) => [n.id, n]))
  const visited = new Set<string>()
  const order: string[] = []

  function visit(id: string) {
    if (visited.has(id)) return
    visited.add(id)
    const node = nodeMap.get(id)
    if (node) {
      for (const dep of node.dependencies) visit(dep)
    }
    order.push(id)
  }

  for (const n of dagNodes) visit(n.id)
  return order
}

function computeFrontier(dagNodes: DAGNode[]): Set<string> {
  const readSet = new Set(
    dagNodes.filter((n) => n.paper.isRead).map((n) => n.id)
  )
  const frontier = new Set<string>()
  for (const node of dagNodes) {
    if (node.paper.isRead) continue
    if (node.dependencies.every((d) => readSet.has(d))) frontier.add(node.id)
  }
  return frontier
}

function computeDepths(dagNodes: DAGNode[]): Map<string, number> {
  const nodeMap = new Map(dagNodes.map((n) => [n.id, n]))
  const depths = new Map<string, number>()
  const roots = dagNodes.filter((n) => n.dependencies.length === 0)
  const queue: { id: string; depth: number }[] = roots.map((r) => ({
    id: r.id,
    depth: 1,
  }))

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!
    if (depths.has(id) && depths.get(id)! >= depth) continue
    depths.set(id, depth)
    for (const node of dagNodes) {
      if (node.dependencies.includes(id)) {
        queue.push({ id: node.id, depth: depth + 1 })
      }
    }
  }

  for (const n of dagNodes) {
    if (!depths.has(n.id)) depths.set(n.id, 1)
  }
  return depths
}

function ShortcutsPopover({ onClose }: { onClose: () => void }) {
  const shortcuts = [
    { key: "J", desc: "Next paper" },
    { key: "K", desc: "Previous paper" },
    { key: "Enter", desc: "Open detail panel" },
    { key: "Esc", desc: "Close panel" },
    { key: "F", desc: "Toggle focus mode" },
    { key: "?", desc: "Toggle shortcuts" },
  ]

  return (
    <div className="animate-fade-in absolute right-0 top-10 z-50 w-56 rounded-xl border border-border bg-card p-3 shadow-xl">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground">
          Keyboard Shortcuts
        </span>
        <button
          onClick={onClose}
          className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:text-foreground"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
      <div className="flex flex-col gap-1.5">
        {shortcuts.map(({ key, desc }) => (
          <div key={key} className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{desc}</span>
            <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              {key}
            </kbd>
          </div>
        ))}
      </div>
    </div>
  )
}

function DAGCanvasInner({
  trail,
  onToggleRead,
  onToggleStar,
  onSaveNote,
  onBack,
}: DAGCanvasProps) {
  const { fitView, setCenter } = useReactFlow()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [focusMode, setFocusMode] = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)
  const prevProgressRef = useRef<number | null>(null)

  const topoOrder = useMemo(() => topologicalSort(trail.nodes), [trail.nodes])
  const frontier = useMemo(() => computeFrontier(trail.nodes), [trail.nodes])
  const depthMap = useMemo(() => computeDepths(trail.nodes), [trail.nodes])

  const readCount = trail.nodes.filter((n) => n.paper.isRead).length
  const totalCount = trail.nodes.length
  const starCount = trail.nodes.filter((n) => n.paper.isStarred).length
  const progress = totalCount > 0 ? Math.round((readCount / totalCount) * 100) : 0
  const remainingPapers = totalCount - readCount
  const estimatedMinutes = remainingPapers * AVG_MINUTES_PER_PAPER
  const readingTime =
    estimatedMinutes >= 60
      ? `~${(estimatedMinutes / 60).toFixed(1)} hrs`
      : estimatedMinutes === 0
        ? "Done"
        : `~${estimatedMinutes} min`

  const readNodeIds = useMemo(
    () => new Set(trail.nodes.filter((n) => n.paper.isRead).map((n) => n.id)),
    [trail.nodes]
  )

  // Trail completion celebration
  useEffect(() => {
    if (prevProgressRef.current !== null && prevProgressRef.current < 100 && progress === 100) {
      toast.success("Trail complete! You've read every paper 🎉", {
        duration: 5000,
        icon: <PartyPopper className="h-5 w-5 text-primary" />,
      })
    }
    prevProgressRef.current = progress
  }, [progress])

  const selectedDAGNode = useMemo(
    () => trail.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [trail.nodes, selectedNodeId]
  )

  const handleSelectNode = useCallback((nodeId: string) => {
    setSelectedNodeId((prev) => (prev === nodeId ? null : nodeId))
  }, [])

  const handleClosePanel = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  useEffect(() => {
    setSelectedNodeId(null)
    setFocusMode(false)
    prevProgressRef.current = null
  }, [trail.id])

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return
      if ((e.target as HTMLElement)?.isContentEditable) return

      if (e.key === "Escape") {
        e.preventDefault()
        setSelectedNodeId(null)
        setShowShortcuts(false)
        return
      }

      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        setShowShortcuts((v) => !v)
        return
      }

      if (e.key === "f" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        setFocusMode((v) => !v)
        return
      }

      if (e.key === "j" || e.key === "k") {
        e.preventDefault()
        setSelectedNodeId((prev) => {
          const currentIdx = prev ? topoOrder.indexOf(prev) : -1
          let nextIdx: number
          if (e.key === "j") {
            nextIdx = currentIdx < topoOrder.length - 1 ? currentIdx + 1 : 0
          } else {
            nextIdx = currentIdx > 0 ? currentIdx - 1 : topoOrder.length - 1
          }
          return topoOrder[nextIdx] ?? null
        })
        return
      }

      if (e.key === "Enter") {
        e.preventDefault()
        setSelectedNodeId((prev) => prev ?? topoOrder[0] ?? null)
        return
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [topoOrder])

  const { layoutedNodes, layoutedEdges } = useMemo(() => {
    const { nodes: rawNodes, edges: rawEdges } = getLayoutedElements(trail.nodes)
    const enrichedNodes = rawNodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        onToggleRead,
        onSelectNode: handleSelectNode,
        isSelected: node.id === selectedNodeId,
        isFrontier: frontier.has(node.id),
        focusMode,
        depth: depthMap.get(node.id) ?? 1,
      },
    }))
    return { layoutedNodes: enrichedNodes, layoutedEdges: rawEdges }
  }, [trail.nodes, onToggleRead, handleSelectNode, selectedNodeId, frontier, focusMode, depthMap])

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges)

  useEffect(() => {
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges])

  // Auto-center on selected node when navigating with keyboard
  useEffect(() => {
    if (!selectedNodeId) return
    const node = layoutedNodes.find((n) => n.id === selectedNodeId)
    if (node?.position) {
      setCenter(node.position.x + 140, node.position.y + 50, {
        zoom: 1,
        duration: 300,
      })
    }
  }, [selectedNodeId, layoutedNodes, setCenter])

  useEffect(() => {
    const t = setTimeout(() => fitView({ padding: 0.25, duration: 400 }), 80)
    return () => clearTimeout(t)
  }, [trail.id, fitView])

  // Edge styling with focus-mode dimming
  const styledEdges = useMemo(() => {
    return edges.map((edge) => {
      const bothRead = readNodeIds.has(edge.source) && readNodeIds.has(edge.target)
      const stroke = bothRead ? `var(--edge-active)` : `var(--edge-default)`
      return {
        ...edge,
        type: "default",
        markerEnd: { type: "arrowclosed" as const, color: stroke },
        style: {
          stroke,
          strokeWidth: bothRead ? 2.5 : 1.5,
          opacity: focusMode && !bothRead ? 0.3 : 1,
          transition: "opacity 0.3s, stroke-width 0.3s",
        },
        animated: bothRead,
      }
    })
  }, [edges, readNodeIds, focusMode])

  // Color-coded minimap
  const minimapNodeColor = useCallback(
    (node: { id?: string }) => {
      if (node.id && readNodeIds.has(node.id)) return `var(--primary)`
      return `var(--minimap-node)`
    },
    [readNodeIds]
  )

  const handleShare = useCallback(() => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      toast.success("Trail link copied to clipboard")
    })
  }, [])

  return (
    <div className="flex h-full flex-col">
      {/* Trail Header */}
      <header className="relative z-10 flex flex-shrink-0 items-center justify-between border-b border-border bg-card/80 px-6 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              {onBack && (
                <button
                  onClick={onBack}
                  className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  Trails
                  <span className="mx-1.5 text-border">/</span>
                </button>
              )}
              <h2 className="text-lg font-semibold text-foreground">
                {trail.topic}
              </h2>
              {progress === 100 && (
                <span className="flex items-center gap-1 rounded-full bg-primary/15 px-2 py-0.5 text-[11px] font-semibold text-primary">
                  <Check className="h-3 w-3" />
                  Completed
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span>{totalCount} papers</span>
              <span className="text-border">|</span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {readingTime}{progress < 100 ? " left" : ""}
              </span>
              {starCount > 0 && (
                <>
                  <span className="text-border">|</span>
                  <span className="flex items-center gap-1">
                    <Star className="h-3 w-3 fill-amber-500 text-amber-500 dark:fill-amber-400 dark:text-amber-400" />
                    {starCount}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Progress */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <BookOpen className="h-3.5 w-3.5" />
              <span className="text-xs">
                {readCount}/{totalCount}
              </span>
            </div>
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="font-mono text-xs font-semibold text-primary">
              {progress}%
            </span>
          </div>

          <div className="h-5 w-px bg-border" />

          {/* Grouped action buttons */}
          <div className="flex items-center gap-0.5 rounded-xl bg-muted/40 p-0.5">
            <button
              onClick={() => setFocusMode((v) => !v)}
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-lg transition-all",
                focusMode
                  ? "bg-primary/15 text-primary shadow-sm"
                  : "text-muted-foreground hover:bg-background/80 hover:text-foreground"
              )}
              aria-label="Toggle focus mode"
              title="Focus mode (F)"
            >
              <Eye className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleShare}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition-all hover:bg-background/80 hover:text-foreground"
              aria-label="Share trail"
              title="Share trail"
            >
              <Share2 className="h-3.5 w-3.5" />
            </button>
            <div className="relative">
              <button
                onClick={() => setShowShortcuts((v) => !v)}
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-lg transition-all",
                  showShortcuts
                    ? "bg-background/80 text-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-background/80 hover:text-foreground"
                )}
                aria-label="Keyboard shortcuts"
                title="Shortcuts (?)"
              >
                <Keyboard className="h-3.5 w-3.5" />
              </button>
              {showShortcuts && (
                <ShortcutsPopover onClose={() => setShowShortcuts(false)} />
              )}
            </div>
          </div>

          <div className="h-5 w-px bg-border" />
          <ThemeToggle />
        </div>
      </header>

      {/* React Flow Canvas */}
      <div className="relative flex-1">
        <ReactFlow
          nodes={nodes}
          edges={styledEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          minZoom={0.15}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
          className="bg-background"
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable
          panOnScroll
          zoomOnScroll
          zoomOnPinch
          onPaneClick={handleClosePanel}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={24}
            size={1}
            color={`var(--canvas-dot)`}
          />
          <Controls
            showInteractive={false}
            className="!rounded-xl !border !border-border !bg-card !shadow-lg [&>button]:!border-t [&>button]:!border-border [&>button]:!bg-card [&>button]:!text-muted-foreground [&>button]:hover:!bg-accent [&>button]:hover:!text-foreground [&>button]:!w-8 [&>button]:!h-8 [&>button:first-child]:!rounded-t-xl [&>button:first-child]:!border-t-0 [&>button:last-child]:!rounded-b-xl"
          />
          <MiniMap
            nodeColor={minimapNodeColor}
            maskColor={`var(--minimap-mask)`}
            className="!rounded-xl !border !border-border !bg-card/90 !shadow-lg"
            pannable
            zoomable
          />
        </ReactFlow>

        {/* Detail Panel Overlay */}
        {selectedDAGNode && (
          <PaperDetailPanel
            node={selectedDAGNode}
            onClose={handleClosePanel}
            onToggleRead={onToggleRead}
            onToggleStar={onToggleStar}
            onSaveNote={onSaveNote}
          />
        )}
      </div>
    </div>
  )
}

export function DAGCanvas(props: DAGCanvasProps) {
  return (
    <ReactFlowProvider>
      <DAGCanvasInner {...props} />
    </ReactFlowProvider>
  )
}
