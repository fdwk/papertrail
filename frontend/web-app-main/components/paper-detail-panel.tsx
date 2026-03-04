"use client"

import type { DAGNode } from "@/lib/types"
import { cn } from "@/lib/utils"
import {
  X,
  ExternalLink,
  Check,
  BookOpen,
  Calendar,
  Users,
} from "lucide-react"

interface PaperDetailPanelProps {
  node: DAGNode
  onClose: () => void
  onToggleRead: (nodeId: string) => void
}

export function PaperDetailPanel({
  node,
  onClose,
  onToggleRead,
}: PaperDetailPanelProps) {
  const { paper } = node

  return (
    <div className="animate-slide-in-right absolute right-4 top-4 bottom-4 z-20 flex w-[380px] flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 border-b border-border p-5">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                paper.isRead
                  ? "bg-primary/15 text-primary"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {paper.isRead ? (
                <>
                  <Check className="h-3 w-3" /> Read
                </>
              ) : (
                <>
                  <BookOpen className="h-3 w-3" /> Unread
                </>
              )}
            </span>
          </div>
          <h3 className="text-lg font-semibold leading-snug text-card-foreground">
            {paper.title}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Close panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Metadata */}
      <div className="flex gap-4 border-b border-border px-5 py-3">
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Users className="h-3.5 w-3.5" />
          <span className="truncate">
            {paper.authors.length <= 2
              ? paper.authors.join(", ")
              : `${paper.authors[0]} et al.`}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Calendar className="h-3.5 w-3.5" />
          <span className="font-mono text-xs">{paper.year}</span>
        </div>
      </div>

      {/* Abstract */}
      <div className="flex-1 overflow-y-auto p-5">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Abstract
        </h4>
        <p className="text-sm leading-relaxed text-card-foreground/85">
          {paper.abstract}
        </p>

        {node.dependencies.length > 0 && (
          <div className="mt-5">
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Prerequisites
            </h4>
            <p className="text-sm text-muted-foreground">
              Depends on {node.dependencies.length} other paper
              {node.dependencies.length > 1 ? "s" : ""} in this trail.
            </p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 border-t border-border p-4">
        <button
          onClick={() => onToggleRead(node.id)}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all",
            paper.isRead
              ? "bg-muted text-muted-foreground hover:bg-muted/80"
              : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
          )}
        >
          {paper.isRead ? (
            <>
              <BookOpen className="h-4 w-4" />
              Mark Unread
            </>
          ) : (
            <>
              <Check className="h-4 w-4" />
              Mark as Read
            </>
          )}
        </button>
        <a
          href={paper.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-card-foreground transition-colors hover:bg-muted"
        >
          <ExternalLink className="h-4 w-4" />
          View
        </a>
      </div>
    </div>
  )
}
