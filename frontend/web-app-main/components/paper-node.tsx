"use client"

import { memo, useCallback } from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import type { Paper } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Check, Circle, Plus, Star, X } from "lucide-react"

interface PaperNodeData {
  paper: Paper
  nodeId: string
  isSelected?: boolean
  isFrontier?: boolean
  focusMode?: boolean
  depth?: number
  onToggleRead?: (nodeId: string) => void
  onSelectNode?: (nodeId: string) => void
  isProposed?: boolean
  isExpansionSource?: boolean
  isSelectableInExpansion?: boolean
  isSelectedInExpansion?: boolean
  onToggleSelectedInExpansion?: (nodeId: string) => void
  onRequestExpand?: (nodeId: string) => void
  [key: string]: unknown
}

function truncateAbstract(text: string, max = 80): string {
  if (!text || text.length <= max) return text
  return text.slice(0, max).trimEnd() + "..."
}

function PaperNodeComponent({ data }: NodeProps) {
  const {
    paper,
    nodeId,
    isSelected,
    isFrontier,
    focusMode,
    depth,
    onToggleRead,
    onSelectNode,
    isProposed,
    isExpansionSource,
    isSelectableInExpansion,
    isSelectedInExpansion,
    onToggleSelectedInExpansion,
    onRequestExpand,
  } = data as PaperNodeData

  const handleToggleRead = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onToggleRead?.(nodeId)
    },
    [onToggleRead, nodeId]
  )

  const handleClick = useCallback(() => {
    onSelectNode?.(nodeId)
  }, [onSelectNode, nodeId])

  const handleToggleSelectedInExpansion = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onToggleSelectedInExpansion?.(nodeId)
    },
    [onToggleSelectedInExpansion, nodeId],
  )

  const handleRequestExpand = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      if (!isSelectableInExpansion) return
      onRequestExpand?.(nodeId)
    },
    [isSelectableInExpansion, onRequestExpand, nodeId],
  )

  const dimmed = false

  return (
    <div
      onClick={handleClick}
      className={cn(
        "group relative h-[172px] w-[280px] cursor-pointer rounded-none border-2 transition-all duration-200",
        "hover:shadow-xl",
        isProposed
          ? cn(
              "border-dashed border-ochre/50 bg-ochre/5 dark:bg-ochre/10",
              !isSelectedInExpansion && "opacity-40",
            )
          : [
              isSelected && !paper.isRead &&
                "border-foreground/30 bg-card shadow-lg shadow-foreground/5",
              isSelected && paper.isRead &&
                "border-primary bg-[var(--node-read-bg)] shadow-lg shadow-primary/10",
              !isSelected && paper.isRead &&
                "border-primary/40 bg-[var(--node-read-bg)] shadow-md",
              !isSelected && !paper.isRead &&
                "border-border bg-card shadow-md hover:border-foreground/20",
            ],
        dimmed && "focus-mode-dimmed",
        focusMode && isFrontier && !paper.isRead && !isProposed && "animate-pulse-ring",
        isExpansionSource && "ring-2 ring-ochre/60 ring-offset-2 ring-offset-background",
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2.5 !w-2.5 !rounded-full !border-2 !border-background !bg-primary/50"
      />

      {/* Depth badge or NEW pill for proposed nodes */}
      {isProposed ? (
        <span className="absolute -right-1.5 -top-1.5 z-10 rounded-none bg-ochre px-1.5 py-0.5 font-label text-[10px] font-semibold leading-none text-ochre-foreground shadow-sm ring-1 ring-ochre/80">
          NEW
        </span>
      ) : (
        depth != null && (
          <span className="absolute -right-1.5 -top-1.5 z-10 rounded-none bg-muted px-1.5 py-0.5 font-label font-mono text-[10px] font-semibold leading-none text-muted-foreground shadow-sm ring-1 ring-border">
            L{depth}
          </span>
        )
      )}

      <div className="flex h-full items-start gap-3 p-4">
        {/* Read/unread indicator (disabled for proposed nodes) */}
        <button
          onClick={isProposed ? (e) => e.stopPropagation() : handleToggleRead}
          className={cn(
            "mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full transition-all duration-200",
            isProposed
              ? "border border-amber-400/70 bg-amber-500/10 text-amber-500"
              : paper.isRead
                ? "bg-primary text-primary-foreground shadow-sm shadow-primary/30"
                : "border-2 border-muted-foreground/25 hover:border-primary/50 hover:bg-primary/10",
          )}
          aria-label={
            isProposed
              ? "Proposed paper"
              : paper.isRead
                ? "Mark as unread"
                : "Mark as read"
          }
        >
          {isProposed ? (
            <Circle className="h-2 w-2" />
          ) : paper.isRead ? (
            <Check className="h-3 w-3" strokeWidth={3} />
          ) : (
            <Circle className="h-2 w-2 text-muted-foreground/30" />
          )}
        </button>

        {/* Paper info */}
        <div className="flex min-w-0 flex-1 flex-col">
          <h3
            className={cn(
              "line-clamp-2 text-sm font-semibold leading-snug",
              isProposed
                ? "text-ochre"
                : paper.isRead
                  ? "text-primary"
                  : "text-card-foreground",
            )}
          >
            {paper.title}
          </h3>
          <p className="mt-1 flex items-center gap-1.5 font-label text-xs text-muted-foreground">
            <span className="truncate">
              {paper.authors[0]}
              {paper.authors.length > 1 ? " et al." : ""}
            </span>
            <span className="text-border">|</span>
            <span className="font-mono text-[11px]">{paper.year}</span>
            {(paper.isStarred ?? false) && (
              <Star className="ml-auto h-3.5 w-3.5 shrink-0 fill-ochre text-ochre" />
            )}
          </p>
          {paper.abstract ? (
            <p className="mt-1.5 line-clamp-3 text-[11px] leading-snug text-muted-foreground/70">
              {truncateAbstract(paper.abstract)}
            </p>
          ) : isProposed ? (
            <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground/60">
              No abstract available for this proposed paper.
            </p>
          ) : null}
        </div>
      </div>

      {/* Expansion controls */}
      {isProposed && isSelectableInExpansion && (
        <button
          onClick={handleToggleSelectedInExpansion}
          className={cn(
            "absolute bottom-2 right-2 flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors",
            isSelectedInExpansion
              ? "border-primary/80 bg-primary/10 text-primary"
              : "border-border bg-background/80 text-muted-foreground hover:bg-muted/80",
          )}
        >
          {isSelectedInExpansion ? (
            <>
              <Check className="h-3 w-3" />
              Keep
            </>
          ) : (
            <>
              <X className="h-3 w-3" />
              Skip
            </>
          )}
        </button>
      )}

      {!isProposed && onRequestExpand && (
        <button
          onClick={handleRequestExpand}
          className={cn(
            "absolute bottom-2 right-2 hidden items-center gap-1 rounded-full border border-border bg-background/80 px-2 py-0.5 text-[10px] font-medium text-muted-foreground shadow-sm transition-all group-hover:flex",
            !isSelectableInExpansion && "opacity-40 cursor-not-allowed",
          )}
          title={
            isSelectableInExpansion ? "Expand from here" : "Finish current expansion first"
          }
        >
          <Plus className="h-3 w-3" />
          Expand
        </button>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2.5 !w-2.5 !rounded-full !border-2 !border-background !bg-primary/50"
      />
    </div>
  )
}

export const PaperNode = memo(PaperNodeComponent)
