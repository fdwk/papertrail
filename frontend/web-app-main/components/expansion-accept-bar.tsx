import { ExpansionState } from "@/lib/types"
import { cn } from "@/lib/utils"
import { X, Check } from "lucide-react"

interface ExpansionAcceptBarProps {
  expansion: ExpansionState
  onConfirm: () => void
  onDismiss: () => void
}

export function ExpansionAcceptBar({
  expansion,
  onConfirm,
  onDismiss,
}: ExpansionAcceptBarProps) {
  const total = expansion.proposedNodes.length
  const selected = expansion.selectedNodeIds.size
  const disabled = selected === 0

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-4 z-40 flex justify-center">
      <div className="pointer-events-auto flex items-center gap-3 rounded-2xl border border-border bg-card/95 px-4 py-2 shadow-xl backdrop-blur-md">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary">
            {selected}/{total}
          </span>
          <span>
            {selected > 0 ? "papers selected to add" : "choose papers to add"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onDismiss}
            className="inline-flex items-center gap-1 rounded-xl border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/80"
          >
            <X className="h-3 w-3" />
            Dismiss
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={disabled}
            className={cn(
              "inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-xs font-medium transition-colors",
              disabled
                ? "cursor-not-allowed bg-primary/10 text-primary/40"
                : "bg-primary text-primary-foreground hover:bg-primary/90",
            )}
          >
            <Check className="h-3 w-3" />
            Add selected ({selected})
          </button>
        </div>
      </div>
    </div>
  )
}

