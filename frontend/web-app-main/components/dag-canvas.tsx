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
  type Node,
  type NodeTypes,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { toast } from "sonner"
import { Trail, DAGNode, type ExpansionState } from "@/lib/types"
import { getLayoutedElements } from "@/lib/layout"
import { PaperNode } from "./paper-node"
import { PaperDetailPanel } from "./paper-detail-panel"
import { ThemeToggle } from "./theme-toggle"
import { ExpansionAcceptBar } from "./expansion-accept-bar"
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
  expansionState?: ExpansionState | null
  onRequestExpandFromNode?: (nodeId: string) => void
  onConfirmExpansion?: () => void
  onDismissExpansion?: () => void
  onToggleSelectedInExpansion?: (nodeId: string) => void
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
  const depths = new Map<string, number>()
  const children = new Map<string, string[]>()
  const maxDepth = dagNodes.length

  for (const node of dagNodes) {
    for (const dep of node.dependencies) {
      const list = children.get(dep) ?? []
      list.push(node.id)
      children.set(dep, list)
    }
  }

  const roots = dagNodes.filter((n) => n.dependencies.length === 0)
  const queue: { id: string; depth: number }[] = roots.map((r) => ({
    id: r.id,
    depth: 1,
  }))

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!
    if (depth > maxDepth) continue
    if (depths.has(id) && depths.get(id)! >= depth) continue
    depths.set(id, depth)
    for (const childId of children.get(id) ?? []) {
      queue.push({ id: childId, depth: depth + 1 })
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
  expansionState,
  onRequestExpandFromNode,
  onConfirmExpansion,
  onDismissExpansion,
  onToggleSelectedInExpansion,
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
  const entryCount = trail.nodes.filter((n) => n.dependencies.length === 0).length
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
  const dagNodeMap = useMemo(
    () => new Map(trail.nodes.map((node) => [node.id, node])),
    [trail.nodes],
  )
  const layoutKey = useMemo(
    () =>
      trail.nodes
        .map((node) => `${node.id}:${[...node.dependencies].sort().join(",")}`)
        .sort()
        .join("|"),
    [trail.nodes],
  )
  const fitViewPadding = totalCount > 10 || entryCount > 2 ? 0.36 : 0.26

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

  const allDagNodes: DAGNode[] = useMemo(() => {
    if (!expansionState || expansionState.proposedNodes.length === 0) {
      return trail.nodes
    }
    return [...trail.nodes, ...expansionState.proposedNodes]
  }, [trail.nodes, expansionState])

  const expansionProposedIds = useMemo(
    () =>
      new Set(
        expansionState?.proposedNodes.map((n) => n.id) ?? [],
      ),
    [expansionState],
  )

  const expansionSelectedIds = useMemo(
    () => expansionState?.selectedNodeIds ?? new Set<string>(),
    [expansionState],
  )

  const expansionSourceId = expansionState?.sourceNodeId ?? null

  const { nodes: baseLayoutNodes, edges: baseLayoutEdges } = useMemo(
    () => getLayoutedElements(allDagNodes),
    [allDagNodes, layoutKey],
  )
  const [nodes, setNodes, onNodesChange] = useNodesState(baseLayoutNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(baseLayoutEdges)

  const hydrateNode = useCallback(
    (node: Node) => {
      const dagNode = dagNodeMap.get(node.id)
      const isProposed = expansionProposedIds.has(node.id)
      const isExpansionSource = expansionSourceId === node.id
      const isSelectableInExpansion = !!expansionState && isProposed
      const isSelectedInExpansion = isProposed
        ? expansionSelectedIds.has(node.id)
        : false
      return {
        ...node,
        data: {
          ...node.data,
          paper: dagNode?.paper ?? node.data.paper,
          nodeId: node.id,
          onToggleRead,
          onSelectNode: handleSelectNode,
          isSelected: node.id === selectedNodeId,
          isFrontier: frontier.has(node.id),
          focusMode,
          depth: depthMap.get(node.id) ?? 1,
          isProposed,
          isExpansionSource,
          isSelectableInExpansion,
          isSelectedInExpansion,
          onToggleSelectedInExpansion:
            isSelectableInExpansion && onToggleSelectedInExpansion
              ? onToggleSelectedInExpansion
              : undefined,
          onRequestExpand: onRequestExpandFromNode,
        },
      }
    },
    [
      dagNodeMap,
      onToggleRead,
      handleSelectNode,
      selectedNodeId,
      frontier,
      focusMode,
      depthMap,
      expansionProposedIds,
      expansionState,
      expansionSelectedIds,
      expansionSourceId,
      onToggleSelectedInExpansion,
      onRequestExpandFromNode,
    ],
  )

  useEffect(() => {
    setNodes(baseLayoutNodes)
    setEdges(baseLayoutEdges)
  }, [baseLayoutNodes, baseLayoutEdges, setNodes, setEdges])

  useEffect(() => {
    setNodes((currentNodes) => currentNodes.map(hydrateNode))
  }, [hydrateNode, setNodes])

  // Auto-center on selected node when navigating with keyboard
  useEffect(() => {
    if (!selectedNodeId) return
    const node = nodes.find((n) => n.id === selectedNodeId)
    if (node?.position) {
      setCenter(node.position.x + 140, node.position.y + 50, {
        zoom: 1,
        duration: 300,
      })
    }
  }, [selectedNodeId, nodes, setCenter])

  useEffect(() => {
    const t = setTimeout(
      () => fitView({ padding: fitViewPadding, duration: 400 }),
      80
    )
    return () => clearTimeout(t)
  }, [layoutKey, fitView, fitViewPadding])

  // Edge styling with focus-mode dimming and special style for proposed edges.
  const styledEdges = useMemo(() => {
    return edges.map((edge) => {
      const sourceRead = readNodeIds.has(edge.source)
      const targetRead = readNodeIds.has(edge.target)
      const bothRead = sourceRead && targetRead
      const edgeConnectsProposed =
        expansionProposedIds.has(edge.source) || expansionProposedIds.has(edge.target)
      if (edgeConnectsProposed && expansionSourceId && edge.source === expansionSourceId) {
        const stroke = "var(--amber-edge, rgba(245, 158, 11, 0.85))"
        return {
          ...edge,
          type: "default",
          markerEnd: { type: "arrowclosed" as const, color: stroke },
          style: {
            stroke,
            strokeWidth: 2,
            strokeDasharray: "4 4",
            opacity: 1,
            transition: "opacity 0.3s, stroke-width 0.3s",
          },
          animated: false,
        }
      }
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
  }, [edges, readNodeIds, focusMode, expansionProposedIds, expansionSourceId])

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
              {entryCount > 1 && (
                <>
                  <span>{entryCount} entry points</span>
                  <span className="text-border">|</span>
                </>
              )}
              {frontier.size > 0 && (
                <>
                  <span>{frontier.size} ready next</span>
                  <span className="text-border">|</span>
                </>
              )}
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
          fitViewOptions={{ padding: fitViewPadding }}
          minZoom={0.15}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
          className="bg-background"
          onlyRenderVisibleElements
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
            onExpandFromHere={onRequestExpandFromNode}
            isExpansionDisabled={!!expansionState && expansionState.status !== "idle"}
          />
        )}

        {/* Expansion accept bar */}
        {expansionState && expansionState.proposedNodes.length > 0 && (
          <ExpansionAcceptBar
            expansion={expansionState}
            onConfirm={onConfirmExpansion ?? (() => {})}
            onDismiss={onDismissExpansion ?? (() => {})}
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
