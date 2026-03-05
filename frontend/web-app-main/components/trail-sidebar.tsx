"use client"

import { Trail } from "@/lib/types"
import { useAuth } from "@/lib/auth-context"
import { cn } from "@/lib/utils"
import {
  FileText,
  Plus,
  Menu,
  X,
  ChevronRight,
  LogIn,
  UserPlus,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Map,
} from "lucide-react"
import { useState, useMemo } from "react"
import Link from "next/link"
import { UserMenu } from "@/components/user-menu"

interface TrailSidebarProps {
  trails: Trail[]
  activeTrailId: string | null
  onSelectTrail: (id: string) => void
  onNewTrail: () => void
  trailsLoading?: boolean
}

function getTrailProgress(trail: Trail): number {
  const total = trail.nodes.length
  if (total > 0) {
    const readCount = trail.nodes.filter((n) => n.paper.isRead).length
    return Math.round((readCount / total) * 100)
  }
  const summary = trail as Trail & { readCount?: number; totalCount?: number }
  const r = summary.readCount ?? 0
  const t = summary.totalCount ?? 0
  if (t === 0) return 0
  return Math.round((r / t) * 100)
}

function ProgressRing({ progress, size = 18 }: { progress: number; size?: number }) {
  const strokeWidth = 2
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (progress / 100) * circumference

  return (
    <svg width={size} height={size} className="flex-shrink-0 -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-muted-foreground/15"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        className={cn(
          "transition-all duration-500",
          progress === 100 ? "text-primary" : "text-primary/70"
        )}
      />
    </svg>
  )
}

function SkeletonTrailItems() {
  return (
    <div className="flex flex-col gap-1 px-1">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-2 rounded-xl px-3 py-2.5">
          <div className="h-3.5 w-3.5 flex-shrink-0 animate-shimmer rounded-full" />
          <div className="h-3.5 flex-1 animate-shimmer rounded-md" style={{ animationDelay: `${i * 80}ms` }} />
          <div className="h-4 w-4 flex-shrink-0 animate-shimmer rounded-full" style={{ animationDelay: `${i * 80 + 40}ms` }} />
        </div>
      ))}
    </div>
  )
}

export function TrailSidebar({
  trails,
  activeTrailId,
  onSelectTrail,
  onNewTrail,
  trailsLoading = false,
}: TrailSidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const { isAuthenticated } = useAuth()

  const filteredTrails = useMemo(() => {
    if (!searchQuery.trim()) return trails
    const q = searchQuery.toLowerCase()
    return trails.filter((t) => t.topic.toLowerCase().includes(q))
  }, [trails, searchQuery])

  const showSearch = trails.length >= 4

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
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-sidebar-border bg-sidebar transition-all duration-200 md:static md:translate-x-0",
          collapsed ? "w-[56px]" : "w-72",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        {/* Brand */}
        <div className={cn(
          "flex items-center gap-2.5 py-4 transition-all",
          collapsed ? "justify-center px-2" : "px-5"
        )}>
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary shadow-sm">
            <FileText className="h-4 w-4 text-primary-foreground" />
          </div>
          {!collapsed && (
            <h1 className="text-base font-bold tracking-tight text-sidebar-foreground">
              Papertrail
            </h1>
          )}
        </div>

        {/* New Trail Button */}
        <div className={cn("pb-2", collapsed ? "px-1.5" : "px-3")}>
          <button
            onClick={() => {
              onNewTrail()
              setMobileOpen(false)
            }}
            title={collapsed ? "New Trail" : undefined}
            className={cn(
              "flex w-full items-center rounded-xl border border-dashed border-sidebar-border text-sm text-sidebar-foreground/70 transition-all hover:border-primary/40 hover:bg-sidebar-accent hover:text-sidebar-foreground",
              collapsed ? "justify-center px-0 py-2.5" : "gap-2 px-3 py-2.5"
            )}
          >
            <Plus className="h-4 w-4 flex-shrink-0" />
            {!collapsed && <span>New Trail</span>}
          </button>
        </div>

        {/* Search (when expanded and 4+ trails) */}
        {!collapsed && showSearch && (
          <div className="px-3 pb-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Escape") setSearchQuery("") }}
                placeholder="Search trails..."
                className="w-full rounded-lg border border-sidebar-border bg-sidebar-accent/50 py-1.5 pl-8 pr-3 text-xs text-sidebar-foreground placeholder:text-muted-foreground/50 focus:border-primary/40 focus:outline-none focus:ring-1 focus:ring-primary/20 transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-muted-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Trail List */}
        <nav
          className={cn("flex-1 overflow-y-auto pb-4 pt-1", collapsed ? "px-1.5" : "px-3")}
          aria-label="Trails"
        >
          {!collapsed && (
            <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
              Your Trails
            </p>
          )}

          {trailsLoading ? (
            collapsed ? (
              <div className="flex flex-col items-center gap-2 pt-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-8 w-8 animate-shimmer rounded-lg" />
                ))}
              </div>
            ) : (
              <SkeletonTrailItems />
            )
          ) : isAuthenticated && trails.length === 0 ? (
            /* Empty state */
            !collapsed ? (
              <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted">
                  <Map className="h-5 w-5 text-muted-foreground/50" />
                </div>
                <p className="text-sm font-medium text-sidebar-foreground/70">No trails yet</p>
                <p className="text-xs text-muted-foreground/60">
                  Create your first trail to start exploring research papers.
                </p>
                <button
                  onClick={() => { onNewTrail(); setMobileOpen(false) }}
                  className="mt-1 flex items-center gap-1.5 rounded-lg bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
                >
                  <Plus className="h-3 w-3" />
                  Create a trail
                </button>
              </div>
            ) : null
          ) : (
            <ul className="flex flex-col gap-0.5">
              {filteredTrails.map((trail) => {
                const progress = getTrailProgress(trail)
                const isActive = trail.id === activeTrailId
                return (
                  <li key={trail.id}>
                    <button
                      onClick={() => {
                        onSelectTrail(trail.id)
                        setMobileOpen(false)
                      }}
                      title={collapsed ? trail.topic : undefined}
                      className={cn(
                        "group relative flex w-full items-center text-left text-sm transition-all",
                        collapsed
                          ? "justify-center rounded-lg px-0 py-2"
                          : "gap-2 rounded-xl px-3 py-2.5",
                        isActive
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                      )}
                    >
                      {/* Left accent bar */}
                      <span
                        className={cn(
                          "absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary transition-all duration-200",
                          isActive ? "opacity-100" : "opacity-0 group-hover:opacity-50"
                        )}
                      />

                      {collapsed ? (
                        <ProgressRing progress={progress} size={24} />
                      ) : (
                        <>
                          <ChevronRight
                            className={cn(
                              "h-3.5 w-3.5 flex-shrink-0 transition-transform duration-200",
                              isActive
                                ? "text-primary rotate-90"
                                : "text-muted-foreground/40 group-hover:rotate-45 group-hover:text-muted-foreground/60"
                            )}
                          />
                          <span className="flex-1 truncate font-medium">
                            {trail.topic}
                          </span>
                          <ProgressRing progress={progress} />
                        </>
                      )}
                    </button>
                  </li>
                )
              })}
              {!collapsed && searchQuery && filteredTrails.length === 0 && (
                <p className="px-3 py-4 text-center text-xs text-muted-foreground/60">
                  No trails match "{searchQuery}"
                </p>
              )}
            </ul>
          )}
        </nav>

        {/* Collapse toggle (desktop only) */}
        <div className={cn(
          "hidden border-t border-sidebar-border md:flex",
          collapsed ? "justify-center px-1.5 py-2" : "px-3 py-2"
        )}>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground/60 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Footer */}
        <SidebarFooter trails={trails} collapsed={collapsed} />
      </aside>
    </>
  )
}

function SidebarFooter({ trails, collapsed }: { trails: Trail[]; collapsed: boolean }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className={cn("border-t border-sidebar-border py-3", collapsed ? "px-1.5" : "px-5")}>
        <div className={cn("animate-pulse rounded-lg bg-sidebar-accent", collapsed ? "mx-auto h-8 w-8" : "h-8 w-full")} />
      </div>
    )
  }

  if (isAuthenticated) {
    return (
      <div className={cn("border-t border-sidebar-border py-3", collapsed ? "px-1.5" : "px-3")}>
        {collapsed ? (
          <div className="flex justify-center">
            <UserMenu collapsed />
          </div>
        ) : (
          <>
            <UserMenu />
            <p className="mt-2 px-3 text-[11px] text-muted-foreground/60">
              {trails.length} trail{trails.length !== 1 ? "s" : ""} created
            </p>
          </>
        )}
      </div>
    )
  }

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2 border-t border-sidebar-border py-3 px-1.5">
        <Link
          href="/login"
          title="Sign in"
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <LogIn className="h-4 w-4" />
        </Link>
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
