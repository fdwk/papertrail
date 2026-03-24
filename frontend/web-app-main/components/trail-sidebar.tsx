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
  Trash2,
} from "lucide-react"
import { useState, useMemo } from "react"
import Link from "next/link"
import { UserMenu } from "@/components/user-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface TrailSidebarProps {
  trails: Trail[]
  activeTrailId: string | null
  onSelectTrail: (id: string) => void
  onNewTrail: () => void
  onDeleteTrail?: (id: string) => void
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
    <div className="flex flex-col gap-1 px-2">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-2.5 px-3 py-2.5">
          <div className="h-3.5 w-3.5 flex-shrink-0 animate-shimmer" />
          <div className="h-3.5 flex-1 animate-shimmer" style={{ animationDelay: `${i * 80}ms` }} />
          <div className="h-4 w-4 flex-shrink-0 animate-shimmer" style={{ animationDelay: `${i * 80 + 40}ms` }} />
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
  onDeleteTrail,
  trailsLoading = false,
}: TrailSidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [deleteTrailId, setDeleteTrailId] = useState<string | null>(null)
  const { isAuthenticated, user } = useAuth()

  const filteredTrails = useMemo(() => {
    if (!searchQuery.trim()) return trails
    const q = searchQuery.toLowerCase()
    return trails.filter((t) => t.topic.toLowerCase().includes(q))
  }, [trails, searchQuery])

  const trailToDelete = deleteTrailId ? filteredTrails.find((t) => t.id === deleteTrailId) : null
  const showSearch = trails.length >= 4

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed top-3 left-3 z-50 flex h-9 w-9 items-center justify-center bg-card text-foreground shadow-sm border border-border/40 md:hidden"
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
          "fixed inset-y-0 left-0 z-40 flex flex-col bg-sidebar transition-all duration-200 md:static md:translate-x-0",
          collapsed ? "w-[56px]" : "w-72",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        {/* Brand */}
        <div className={cn(
          "flex items-center gap-3 py-5 transition-all",
          collapsed ? "justify-center px-2" : "px-5"
        )}>
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center bg-primary shadow-sm">
            <FileText className="h-4 w-4 text-primary-foreground" />
          </div>
          {!collapsed && (
            <div className="flex w-full items-center gap-2">
              <h1 className="text-lg font-light italic tracking-tight text-sidebar-foreground">
                Papertrail
              </h1>
              {user?.tier && (
                <Link
                  href="/upgrade"
                  className="ml-auto bg-primary/10 px-2 py-0.5 font-label text-[10px] font-bold uppercase tracking-[0.08em] text-primary/80 hover:bg-primary/15 transition-colors"
                >
                  {user.tier}
                </Link>
              )}
            </div>
          )}
        </div>

        {/* New Trail Button */}
        <div className={cn("pb-3", collapsed ? "px-1.5" : "px-5")}>
          <button
            onClick={() => {
              onNewTrail()
              setMobileOpen(false)
            }}
            title={collapsed ? "New Trail" : undefined}
            className={cn(
              "flex w-full items-center border-b-2 border-dashed border-sidebar-border/60 font-label text-sm text-sidebar-foreground/60 transition-all hover:border-primary/40 hover:text-sidebar-foreground",
              collapsed ? "justify-center px-0 py-2.5" : "gap-2 px-0 py-2.5"
            )}
          >
            <Plus className="h-4 w-4 flex-shrink-0" />
            {!collapsed && <span className="text-xs">New Trail</span>}
          </button>
        </div>

        {/* Search (when expanded and 4+ trails) */}
        {!collapsed && showSearch && (
          <div className="px-5 pb-3">
            <div className="relative">
              <Search className="absolute left-0 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/40" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Escape") setSearchQuery("") }}
                placeholder="Search trails..."
                className="w-full border-b border-sidebar-border bg-transparent py-1.5 pl-5 pr-6 font-label text-xs text-sidebar-foreground placeholder:text-muted-foreground/40 focus:border-primary/60 focus:outline-none transition-colors"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-0 top-1/2 -translate-y-1/2 p-0.5 text-muted-foreground/50 hover:text-muted-foreground"
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
            <p className="mb-2 px-2 font-label text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground/50">
              Your Trails
            </p>
          )}

          {trailsLoading ? (
            collapsed ? (
              <div className="flex flex-col items-center gap-2 pt-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-8 w-8 animate-shimmer" />
                ))}
              </div>
            ) : (
              <SkeletonTrailItems />
            )
          ) : isAuthenticated && trails.length === 0 ? (
            /* Empty state */
            !collapsed ? (
              <div className="flex flex-col items-center gap-3 px-5 py-10 text-center">
                <div className="flex h-10 w-10 items-center justify-center bg-sidebar-accent">
                  <Map className="h-5 w-5 text-muted-foreground/40" />
                </div>
                <p className="text-sm italic text-sidebar-foreground/60">No trails yet</p>
                <p className="font-label text-[11px] leading-relaxed text-muted-foreground/50">
                  Create your first trail to start exploring.
                </p>
                <button
                  onClick={() => { onNewTrail(); setMobileOpen(false) }}
                  className="mt-1 flex items-center gap-1.5 bg-primary/10 px-3 py-1.5 font-label text-[11px] font-medium text-primary transition-colors hover:bg-primary/20"
                >
                  <Plus className="h-3 w-3" />
                  Create a trail
                </button>
              </div>
            ) : null
          ) : (
            <ul className="flex flex-col gap-1">
              {filteredTrails.map((trail) => {
                const progress = getTrailProgress(trail)
                const isActive = trail.id === activeTrailId
                return (
                  <li
                    key={trail.id}
                    className={cn(
                      "group/row flex w-full items-stretch gap-0 rounded-none transition-[background-color,border-color] duration-150",
                      isActive
                        ? "bg-sidebar-accent"
                        : "hover:bg-sidebar-accent/40"
                    )}
                  >
                    <button
                      onClick={() => {
                        onSelectTrail(trail.id)
                        setMobileOpen(false)
                      }}
                      title={collapsed ? trail.topic : undefined}
                      className={cn(
                        "relative flex min-w-0 flex-1 items-center text-left text-sm outline-none transition-colors duration-150",
                        collapsed
                          ? "justify-center rounded-none px-0 py-2.5"
                          : "gap-2.5 rounded-none px-3 py-2.5",
                        isActive
                          ? "text-sidebar-accent-foreground"
                          : "text-sidebar-foreground/85 hover:text-sidebar-foreground"
                      )}
                    >
                      {/* Left accent bar — shows when active or on row hover */}
                      <span
                        className={cn(
                          "absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-none bg-primary transition-opacity duration-150",
                          isActive ? "opacity-100" : "opacity-0 group-hover/row:opacity-60"
                        )}
                      />

                      {collapsed ? (
                        <ProgressRing progress={progress} size={24} />
                      ) : (
                        <>
                          <ChevronRight
                            className={cn(
                              "h-3.5 w-3.5 flex-shrink-0 transition-transform duration-150",
                              isActive
                                ? "text-primary rotate-90"
                                : "text-muted-foreground/50 group-hover/row:rotate-45 group-hover/row:text-muted-foreground/70"
                            )}
                          />
                          <span className="min-w-0 flex-1 truncate">
                            {trail.topic}
                          </span>
                        </>
                      )}
                    </button>
                    {!collapsed && onDeleteTrail && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setDeleteTrailId(trail.id)
                        }}
                        title="Delete trail"
                        className={cn(
                          "flex-shrink-0 px-2 py-1.5 text-muted-foreground/50 transition-opacity duration-150",
                          "hover:bg-destructive/10 hover:text-destructive",
                          "focus:outline-none",
                          "opacity-0 group-hover/row:opacity-100"
                        )}
                        aria-label={`Delete trail ${trail.topic}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                    {!collapsed && (
                      <span className="flex flex-shrink-0 items-center rounded-none pl-2 pr-2.5 py-1">
                        <ProgressRing progress={progress} />
                      </span>
                    )}
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
          "hidden md:flex",
          collapsed ? "justify-center px-1.5 py-2" : "px-3 py-2"
        )}>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="flex h-8 w-8 items-center justify-center text-muted-foreground/50 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
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

      {/* Delete trail confirmation */}
      <AlertDialog
        open={deleteTrailId !== null}
        onOpenChange={(open) => !open && setDeleteTrailId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete trail?</AlertDialogTitle>
            <AlertDialogDescription>
              {trailToDelete ? (
                <>
                  &ldquo;{trailToDelete.topic}&rdquo; and all its papers will be removed. This
                  cannot be undone.
                </>
              ) : (
                "This trail will be permanently removed. This cannot be undone."
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (deleteTrailId && onDeleteTrail) {
                  onDeleteTrail(deleteTrailId)
                  setMobileOpen(false)
                }
                setDeleteTrailId(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

function SidebarFooter({ trails, collapsed }: { trails: Trail[]; collapsed: boolean }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className={cn("bg-sidebar-accent/30 py-3", collapsed ? "px-1.5" : "px-5")}>
        <div className={cn("animate-pulse bg-sidebar-accent", collapsed ? "mx-auto h-8 w-8" : "h-8 w-full")} />
      </div>
    )
  }

  if (isAuthenticated) {
    return (
      <div className={cn("bg-sidebar-accent/30 py-3", collapsed ? "px-1.5" : "px-3")}>
        {collapsed ? (
          <div className="flex justify-center">
            <UserMenu collapsed />
          </div>
        ) : (
          <>
            <UserMenu />
            <p className="mt-2 px-3 font-label text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/50">
              {trails.length} trail{trails.length !== 1 ? "s" : ""} created
            </p>
          </>
        )}
      </div>
    )
  }

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2 bg-sidebar-accent/30 py-3 px-1.5">
        <Link
          href="/login"
          title="Sign in"
          className="flex h-8 w-8 items-center justify-center bg-primary text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <LogIn className="h-4 w-4" />
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 bg-sidebar-accent/30 px-4 py-4">
      <Link
        href="/login"
        className="flex w-full items-center justify-center gap-2 bg-primary px-3 py-2.5 font-label text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        <LogIn className="h-4 w-4" />
        <span>Sign in</span>
      </Link>
      <Link
        href="/signup"
        className="flex w-full items-center justify-center gap-2 border-b-2 border-sidebar-border px-3 py-2 font-label text-sm font-medium text-sidebar-foreground/70 transition-colors hover:border-primary/40 hover:text-sidebar-foreground"
      >
        <UserPlus className="h-4 w-4" />
        <span>Sign up</span>
      </Link>
    </div>
  )
}
