"use client"

import { Trail } from "@/lib/types"
import { useAuth } from "@/lib/auth-context"
import { cn } from "@/lib/utils"
import { FileText, Plus, Menu, X, ChevronRight, LogIn, UserPlus } from "lucide-react"
import { useState } from "react"
import Link from "next/link"
import { UserMenu } from "@/components/user-menu"

interface TrailSidebarProps {
  trails: Trail[]
  activeTrailId: string | null
  onSelectTrail: (id: string) => void
  onNewTrail: () => void
}

function getTrailProgress(trail: Trail): number {
  if (trail.nodes.length === 0) return 0
  const readCount = trail.nodes.filter((n) => n.paper.isRead).length
  return Math.round((readCount / trail.nodes.length) * 100)
}

export function TrailSidebar({
  trails,
  activeTrailId,
  onSelectTrail,
  onNewTrail,
}: TrailSidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed top-3 left-3 z-50 flex h-9 w-9 items-center justify-center rounded-lg bg-card text-foreground shadow-lg border border-border md:hidden"
        aria-label={mobileOpen ? "Close sidebar" : "Open sidebar"}
      >
        {mobileOpen ? (
          <X className="h-4 w-4" />
        ) : (
          <Menu className="h-4 w-4" />
        )}
      </button>

      {/* Overlay for mobile */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-background/60 backdrop-blur-sm md:hidden animate-fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-200 md:static md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary shadow-sm">
            <FileText className="h-4 w-4 text-primary-foreground" />
          </div>
          <h1 className="text-base font-bold tracking-tight text-sidebar-foreground">
            Papertrail
          </h1>
        </div>

        {/* New Trail Button */}
        <div className="px-3 pb-2">
          <button
            onClick={() => {
              onNewTrail()
              setMobileOpen(false)
            }}
            className="flex w-full items-center gap-2 rounded-xl border border-dashed border-sidebar-border px-3 py-2.5 text-sm text-sidebar-foreground/70 transition-all hover:border-primary/40 hover:bg-sidebar-accent hover:text-sidebar-foreground"
          >
            <Plus className="h-4 w-4" />
            <span>New Trail</span>
          </button>
        </div>

        {/* Trail List */}
        <nav
          className="flex-1 overflow-y-auto px-3 pb-4 pt-1"
          aria-label="Trails"
        >
          <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
            Your Trails
          </p>
          <ul className="flex flex-col gap-0.5">
            {trails.map((trail) => {
              const progress = getTrailProgress(trail)
              const isActive = trail.id === activeTrailId
              return (
                <li key={trail.id}>
                  <button
                    onClick={() => {
                      onSelectTrail(trail.id)
                      setMobileOpen(false)
                    }}
                    className={cn(
                      "group flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm transition-all",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                    )}
                  >
                    <ChevronRight
                      className={cn(
                        "h-3.5 w-3.5 flex-shrink-0 transition-transform",
                        isActive
                          ? "text-primary rotate-90"
                          : "text-muted-foreground/40"
                      )}
                    />
                    <span className="flex-1 truncate font-medium">
                      {trail.topic}
                    </span>
                    <span
                      className={cn(
                        "flex-shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[11px] font-semibold",
                        progress === 100
                          ? "bg-primary/15 text-primary"
                          : "text-muted-foreground/60"
                      )}
                    >
                      {progress}%
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Footer */}
        <SidebarFooter trails={trails} />
      </aside>
    </>
  )
}

function SidebarFooter({ trails }: { trails: Trail[] }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="border-t border-sidebar-border px-5 py-3">
        <div className="h-8 w-full animate-pulse rounded-lg bg-sidebar-accent" />
      </div>
    )
  }

  if (isAuthenticated) {
    return (
      <div className="border-t border-sidebar-border px-3 py-3">
        <UserMenu />
        <p className="mt-2 px-3 text-[11px] text-muted-foreground/60">
          {trails.length} trail{trails.length !== 1 ? "s" : ""} created
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 border-t border-sidebar-border px-3 py-3">
      <Link
        href="/login"
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        <LogIn className="h-4 w-4" />
        <span>Sign in</span>
      </Link>
      <Link
        href="/signup"
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-sidebar-border px-3 py-2 text-sm font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
      >
        <UserPlus className="h-4 w-4" />
        <span>Sign up</span>
      </Link>
    </div>
  )
}
