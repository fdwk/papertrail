"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { backendFetch } from "@/lib/api-client"
import type { Paper } from "@/lib/types"
import { cn } from "@/lib/utils"
import { BookOpen, ChevronLeft, Loader2, PencilLine, Search, Star, X } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"

interface UserPaper extends Paper {
  trailTopics?: string[]
  lastRead?: string | null
}

type FilterMode = "all" | "read" | "unread"
type SortMode = "newest" | "oldest"

export function PapersPage() {
  const [papers, setPapers] = useState<UserPaper[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [filter, setFilter] = useState<FilterMode>("all")
  const [sort, setSort] = useState<SortMode>("newest")
  const [starredOnly, setStarredOnly] = useState(false)
  const [noteDraftId, setNoteDraftId] = useState<string | null>(null)
  const [noteDraft, setNoteDraft] = useState<string>("")

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    backendFetch<UserPaper[]>("/papers/user")
      .then((res) => {
        if (!cancelled) {
          if (res.ok && Array.isArray(res.data)) {
            setPapers(res.data)
          } else {
            setError("Unable to load your papers right now.")
          }
        }
      })
      .catch(() => {
        if (!cancelled) setError("Unable to load your papers right now.")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const filtered = useMemo(() => {
    let list = [...papers]

    if (query.trim()) {
      const q = query.toLowerCase()
      list = list.filter((p) => {
        const inTitle = p.title.toLowerCase().includes(q)
        const inAuthors = p.authors.some((a) => a.toLowerCase().includes(q))
        return inTitle || inAuthors
      })
    }

    if (filter === "read") {
      list = list.filter((p) => p.isRead)
    } else if (filter === "unread") {
      list = list.filter((p) => !p.isRead)
    }

    if (starredOnly) {
      list = list.filter((p) => p.isStarred)
    }

    list.sort((a, b) => {
      if (sort === "newest") return b.year - a.year
      return a.year - b.year
    })

    return list
  }, [papers, query, filter, sort, starredOnly])

  function handleToggleStar(paperId: string) {
    const target = papers.find((p) => p.id === paperId)
    if (!target) return
    const next = !(target.isStarred ?? false)
    setPapers((prev) =>
      prev.map((p) =>
        p.id === paperId ? { ...p, isStarred: next } : p,
      ),
    )
    backendFetch(`/papers/${paperId}/user-state`, {
      method: "PATCH",
      body: JSON.stringify({ isStarred: next }),
    }).then((res) => {
      if (!res.ok) {
        // revert
        setPapers((prev) =>
          prev.map((p) =>
            p.id === paperId ? { ...p, isStarred: target.isStarred } : p,
          ),
        )
      }
    })
  }

  function handleToggleRead(paperId: string) {
    const target = papers.find((p) => p.id === paperId)
    if (!target) return
    const next = !target.isRead
    setPapers((prev) =>
      prev.map((p) =>
        p.id === paperId ? { ...p, isRead: next } : p,
      ),
    )
    backendFetch(`/papers/${paperId}/user-state`, {
      method: "PATCH",
      body: JSON.stringify({ isRead: next }),
    }).then((res) => {
      if (!res.ok) {
        setPapers((prev) =>
          prev.map((p) =>
            p.id === paperId ? { ...p, isRead: target.isRead } : p,
          ),
        )
      }
    })
  }

  function openNoteEditor(paper: UserPaper) {
    setNoteDraftId(paper.id)
    setNoteDraft(paper.note ?? "")
  }

  function closeNoteEditor() {
    setNoteDraftId(null)
    setNoteDraft("")
  }

  function saveNote(paperId: string) {
    const note = noteDraft.trim()
    const prev = papers.find((p) => p.id === paperId)
    setPapers((p) =>
      p.map((paper) =>
        paper.id === paperId ? { ...paper, note } : paper,
      ),
    )
    backendFetch(`/papers/${paperId}/user-state`, {
      method: "PATCH",
      body: JSON.stringify({ note }),
    }).then((res) => {
      if (!res.ok && prev) {
        setPapers((p) =>
          p.map((paper) =>
            paper.id === paperId ? { ...paper, note: prev.note } : paper,
          ),
        )
      }
    })
    closeNoteEditor()
  }

  return (
    <div className="flex h-dvh flex-col bg-background">
      <header className="relative border-b border-border/50 bg-card/90 shadow-sm shadow-black/[0.02] backdrop-blur-md dark:shadow-none">
        {/* Subtle gradient overlay */}
        <div
          className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/[0.06] via-transparent to-muted/30 opacity-90 dark:from-primary/[0.08] dark:to-muted/20"
          aria-hidden
        />
        <div className="relative mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <Link
              href="/"
              className="flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
              aria-label="Back to home"
            >
              <ChevronLeft className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">Home</span>
            </Link>
            <span className="h-5 w-px shrink-0 bg-border/60" aria-hidden />
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/20 dark:ring-primary/15">
                <BookOpen className="h-5 w-5 text-primary" />
              </div>
              <div className="min-w-0">
                <h1 className="truncate text-base font-semibold tracking-tight text-foreground">
                  Your Papers
                </h1>
                <p className="truncate text-xs text-muted-foreground">
                  All papers from your trails in one place
                </p>
              </div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground md:flex">
              <span className="font-mono font-medium tabular-nums text-foreground/80">
                {papers.length}
              </span>
              <span>papers</span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="text-emerald-600 dark:text-emerald-400">
                {papers.filter((p) => p.isRead).length} read
              </span>
              <span className="text-muted-foreground/70">
                {papers.filter((p) => !p.isRead).length} unread
              </span>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 px-4 py-4">
        <section className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card/60 p-3 backdrop-blur-sm md:flex-row md:items-center md:justify-between">
          <div className="relative w-full md:max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/60" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by title or author..."
              className="w-full rounded-xl border border-border/60 bg-background/60 py-2 pl-9 pr-8 text-xs text-foreground placeholder:text-muted-foreground/60 focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted-foreground/60 hover:bg-muted hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="inline-flex items-center gap-1 rounded-full bg-background/60 p-1">
              {(["all", "unread", "read"] as FilterMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setFilter(mode)}
                  className={cn(
                    "rounded-full px-2.5 py-1 capitalize transition-colors",
                    filter === mode
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted/70",
                  )}
                >
                  {mode}
                </button>
              ))}
            </div>
            <button
              onClick={() => setStarredOnly((v) => !v)}
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2.5 py-1",
                starredOnly
                  ? "border-amber-400/70 bg-amber-500/10 text-amber-400"
                  : "border-border/60 text-muted-foreground hover:bg-muted/60",
              )}
            >
              <Star className={cn("h-3.5 w-3.5", starredOnly && "fill-current")} />
              <span>Starred only</span>
            </button>
            <div className="ml-auto inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-1">
              <span className="text-muted-foreground/70">Sort</span>
              <button
                onClick={() => setSort("newest")}
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[11px]",
                  sort === "newest"
                    ? "bg-primary/80 text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted/70",
                )}
              >
                Newest
              </button>
              <button
                onClick={() => setSort("oldest")}
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[11px]",
                  sort === "oldest"
                    ? "bg-primary/80 text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted/70",
                )}
              >
                Oldest
              </button>
            </div>
          </div>
        </section>

        {loading ? (
          <div className="flex flex-1 items-center justify-center text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading papers…
          </div>
        ) : error ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
            <p className="text-sm">{error}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center text-center text-muted-foreground">
            <p className="text-sm font-medium">No papers found</p>
            <p className="mt-1 text-xs">
              Try adjusting your filters or search query.
            </p>
          </div>
        ) : (
          <section className="grid flex-1 grid-cols-1 gap-3 pb-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((paper) => {
              const isEditing = noteDraftId === paper.id
              return (
                <article
                  key={paper.id}
                  className={cn(
                    "group flex h-[240px] flex-col overflow-hidden rounded-2xl border border-border/70 bg-card/90 p-3 text-sm shadow-sm transition-all hover:border-primary/40 hover:shadow-md",
                    paper.isRead ? "ring-1 ring-primary/10" : "",
                  )}
                >
                  <div className="mb-2 flex shrink-0 items-start gap-2">
                    <button
                      onClick={() => handleToggleRead(paper.id)}
                      className={cn(
                        "mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 text-[11px] transition-all",
                        paper.isRead
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-muted-foreground/30 text-muted-foreground hover:border-primary/60 hover:bg-primary/5",
                      )}
                      aria-label={paper.isRead ? "Mark unread" : "Mark read"}
                    >
                      <BookOpen className="h-3 w-3" />
                    </button>
                    <div className="min-w-0 flex-1">
                      <h2
                        className={cn(
                          "line-clamp-2 text-[13px] font-semibold leading-snug",
                          paper.isRead ? "text-primary" : "text-foreground",
                        )}
                      >
                        {paper.title}
                      </h2>
                      <p className="mt-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                        <span className="truncate">
                          {paper.authors[0]}
                          {paper.authors.length > 1 ? " et al." : ""}
                        </span>
                        <span className="text-border">|</span>
                        <span className="font-mono text-[10px]">{paper.year}</span>
                        <button
                          onClick={() => handleToggleStar(paper.id)}
                          className="ml-auto inline-flex items-center justify-center rounded-full p-0.5 text-amber-400 hover:bg-amber-500/10"
                          aria-label={paper.isStarred ? "Unstar paper" : "Star paper"}
                        >
                          <Star
                            className={cn(
                              "h-3 w-3",
                              paper.isStarred && "fill-current",
                            )}
                          />
                        </button>
                      </p>
                    </div>
                  </div>
                  <div className="min-h-0 flex-1 overflow-y-auto">
                    {paper.abstract && (
                      <p className="mt-1 line-clamp-3 text-[11px] leading-snug text-muted-foreground/80">
                        {paper.abstract}
                      </p>
                    )}
                    {paper.trailTopics && paper.trailTopics.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {paper.trailTopics.slice(0, 3).map((topic) => (
                          <span
                            key={topic}
                            className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                          >
                            {topic}
                          </span>
                        ))}
                        {paper.trailTopics.length > 3 && (
                          <span className="text-[10px] text-muted-foreground/70">
                            +{paper.trailTopics.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                    <div className="mt-2 flex flex-col gap-2 text-[11px]">
                    {paper.note && !isEditing && (
                      <p className="line-clamp-2 rounded-lg bg-muted/40 px-2 py-1 text-muted-foreground">
                        {paper.note}
                      </p>
                    )}
                    {isEditing && (
                      <div className="flex flex-col gap-1">
                        <textarea
                          value={noteDraft}
                          onChange={(e) => setNoteDraft(e.target.value)}
                          rows={3}
                          className="w-full rounded-lg border border-border bg-background/60 px-2 py-1 text-[11px] text-foreground placeholder:text-muted-foreground focus:border-primary/40 focus:outline-none focus:ring-1 focus:ring-primary/30"
                          placeholder="Add a quick note..."
                        />
                        <div className="flex justify-end gap-1">
                          <button
                            type="button"
                            onClick={closeNoteEditor}
                            className="rounded-full px-2 py-0.5 text-[10px] text-muted-foreground hover:bg-muted/50"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => saveNote(paper.id)}
                            className="rounded-full bg-primary px-2.5 py-0.5 text-[10px] font-medium text-primary-foreground hover:bg-primary/90"
                          >
                            Save
                          </button>
                        </div>
                      </div>
                    )}
                    </div>
                  </div>
                  <div className="mt-3 flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openNoteEditor(paper)}
                      className="inline-flex items-center gap-1 rounded-xl border border-border/70 bg-background/60 px-2.5 py-1.5 text-[11px] text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
                    >
                      <PencilLine className="h-3 w-3" />
                      <span>{paper.note ? "Edit note" : "Add note"}</span>
                    </button>
                    {paper.url && (
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-auto inline-flex items-center justify-between rounded-xl border border-border/70 bg-background/60 px-2.5 py-1.5 text-[11px] font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-primary/5"
                      >
                        <span className="truncate">Open paper</span>
                        <span className="ml-2 text-[10px] text-muted-foreground">
                          ↗
                        </span>
                      </a>
                    )}
                  </div>
                </article>
              )
            })}
          </section>
        )}
      </main>
    </div>
  )
}

