"use client"

import { useMemo, useCallback, useEffect, useState } from "react"
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Node,
  type Edge,
  type NodeTypes,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { useTheme } from "next-themes"
import { Trail } from "@/lib/types"
import { getLayoutedElements } from "@/lib/layout"
import { PaperNode } from "./paper-node"
import { PaperDetailPanel } from "./paper-detail-panel"
import { ThemeToggle } from "./theme-toggle"
import { BookOpen } from "lucide-react"

interface DAGCanvasProps {
  trail: Trail
  onToggleRead: (nodeId: string) => void
  onToggleStar: (nodeId: string) => void
  onSaveNote: (nodeId: string, note: string) => void
}

const nodeTypes: NodeTypes = {
  paperNode: PaperNode,
}

function DAGCanvasInner({
  trail,
  onToggleRead,
  onToggleStar,
  onSaveNote,
}: DAGCanvasProps) {
  const { fitView } = useReactFlow()
  const { resolvedTheme } = useTheme()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const isDark = resolvedTheme === "dark"

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

  // Clear selection when trail changes
  useEffect(() => {
    setSelectedNodeId(null)
  }, [trail.id])

  const { layoutedNodes, layoutedEdges } = useMemo(() => {
    const { nodes, edges } = getLayoutedElements(trail.nodes)
    const enrichedNodes = nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        onToggleRead,
        onSelectNode: handleSelectNode,
        isSelected: node.id === selectedNodeId,
      },
    }))
    return { layoutedNodes: enrichedNodes, layoutedEdges: edges }
  }, [trail.nodes, onToggleRead, handleSelectNode, selectedNodeId])

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges)

  useEffect(() => {
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges])

  useEffect(() => {
    const t = setTimeout(() => fitView({ padding: 0.25, duration: 400 }), 80)
    return () => clearTimeout(t)
  }, [trail.id, fitView])

  // Theme-aware edge styling (curved edges with directed arrows)
  const styledEdges = useMemo(() => {
    const readNodes = new Set(
      trail.nodes.filter((n) => n.paper.isRead).map((n) => n.id)
    )
    return edges.map((edge) => {
      const bothRead = readNodes.has(edge.source) && readNodes.has(edge.target)
      const stroke = bothRead
        ? `var(--edge-active)`
        : `var(--edge-default)`
      return {
        ...edge,
        type: "default",
        markerEnd: { type: "arrowclosed" as const, color: stroke },
        style: {
          stroke,
          strokeWidth: bothRead ? 2.5 : 1.5,
        },
        animated: bothRead,
      }
    })
  }, [edges, trail.nodes])

  const readCount = trail.nodes.filter((n) => n.paper.isRead).length
  const totalCount = trail.nodes.length
  const progress =
    totalCount > 0 ? Math.round((readCount / totalCount) * 100) : 0

  return (
    <div className="flex h-full flex-col">
      {/* Trail Header */}
      <header className="relative z-10 flex flex-shrink-0 items-center justify-between border-b border-border bg-card/80 px-6 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {trail.topic}
            </h2>
            <p className="text-xs text-muted-foreground">
              {totalCount} papers
            </p>
          </div>
        </div>
        <div className="flex items-center gap-5">
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
            nodeColor={() => `var(--minimap-node)`}
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
