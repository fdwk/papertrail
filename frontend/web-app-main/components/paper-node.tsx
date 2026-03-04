"use client"

import { memo, useCallback } from "react"
import { Handle, Position, type NodeProps } from "@xyflow/react"
import type { Paper } from "@/lib/types"
import { cn } from "@/lib/utils"
import { Check, Circle, Star } from "lucide-react"

interface PaperNodeData {
  paper: Paper
  nodeId: string
  isSelected?: boolean
  onToggleRead?: (nodeId: string) => void
  onSelectNode?: (nodeId: string) => void
  [key: string]: unknown
}

function PaperNodeComponent({ data }: NodeProps) {
  const { paper, nodeId, isSelected, onToggleRead, onSelectNode } =
    data as PaperNodeData

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

  // Determine the "step" label based on read status
  const stepNumber = paper.isRead ? null : null

  return (
    <div
      onClick={handleClick}
      className={cn(
        "group w-[280px] cursor-pointer rounded-xl border-2 transition-all duration-200",
        "hover:shadow-xl",
        isSelected && !paper.isRead &&
          "border-foreground/30 bg-card shadow-lg shadow-foreground/5",
        isSelected && paper.isRead &&
          "border-primary/60 bg-primary/5 shadow-lg shadow-primary/10",
        !isSelected && paper.isRead &&
          "border-primary/30 bg-primary/5 shadow-md shadow-primary/5",
        !isSelected && !paper.isRead &&
          "border-border bg-card shadow-md hover:border-foreground/20"
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2.5 !w-2.5 !rounded-full !border-2 !border-background !bg-primary/50"
      />

      <div className="flex items-start gap-3 p-4">
        {/* Read/unread indicator */}
        <button
          onClick={handleToggleRead}
          className={cn(
            "mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full transition-all duration-200",
            paper.isRead
              ? "bg-primary text-primary-foreground shadow-sm shadow-primary/30"
              : "border-2 border-muted-foreground/25 hover:border-primary/50 hover:bg-primary/10"
          )}
          aria-label={paper.isRead ? "Mark as unread" : "Mark as read"}
        >
          {paper.isRead ? (
            <Check className="h-3 w-3" strokeWidth={3} />
          ) : (
            <Circle className="h-2 w-2 text-muted-foreground/30" />
          )}
        </button>

        {/* Paper info */}
        <div className="min-w-0 flex-1">
          <h3
            className={cn(
              "text-sm font-semibold leading-snug",
              paper.isRead
                ? "text-primary"
                : "text-card-foreground"
            )}
          >
            {paper.title}
          </h3>
          <p className="mt-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="truncate">
              {paper.authors[0]}
              {paper.authors.length > 1 ? " et al." : ""}
            </span>
            <span className="text-border">|</span>
            <span className="font-mono text-[11px]">{paper.year}</span>
            {(paper.isStarred ?? false) && (
              <Star className="ml-auto h-3.5 w-3.5 shrink-0 fill-amber-500 text-amber-500 dark:fill-amber-400 dark:text-amber-400" />
            )}
          </p>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2.5 !w-2.5 !rounded-full !border-2 !border-background !bg-primary/50"
      />
    </div>
  )
}

export const PaperNode = memo(PaperNodeComponent)
