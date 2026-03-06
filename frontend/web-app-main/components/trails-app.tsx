"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Trail, TrailSummary } from "@/lib/types"
import { TrailSidebar } from "@/components/trail-sidebar"
import { DAGCanvas } from "@/components/dag-canvas"
import { WelcomeScreen } from "@/components/welcome-screen"
import { useAuth } from "@/lib/auth-context"
import { backendFetch } from "@/lib/api-client"

export function TrailsApp() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const routeTrailId = searchParams.get("trail")
  const { isAuthenticated } = useAuth()

  const [trails, setTrails] = useState<TrailSummary[]>([])
  const [activeTrailId, setActiveTrailId] = useState<string | null>(routeTrailId)
  const [activeTrail, setActiveTrail] = useState<Trail | null>(null)
  const [trailsLoading, setTrailsLoading] = useState(false)
  const [trailDetailLoading, setTrailDetailLoading] = useState(false)
  const [trailDetailError, setTrailDetailError] = useState<string | null>(null)

  useEffect(() => {
    setActiveTrailId(routeTrailId)
  }, [routeTrailId])

  // When user is logged in, fetch their trail list (no nodes/edges).
  useEffect(() => {
    if (!isAuthenticated) {
      setTrails([])
      setTrailsLoading(false)
      return
    }
    setTrailsLoading(true)
    let cancelled = false
    const timeoutId = window.setTimeout(() => {
      if (cancelled) return
      setTrailsLoading(false)
    }, 15000)
    backendFetch<TrailSummary[]>("/trails/")
      .then((res) => {
        if (cancelled) return
        if (res.ok && Array.isArray(res.data)) setTrails(res.data)
      })
      .catch(() => { /* ensure finally runs if something throws */ })
      .finally(() => {
        cancelled = true
        window.clearTimeout(timeoutId)
        setTrailsLoading(false)
      })
    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [isAuthenticated])

  // When a trail is selected, fetch full trail with graph.
  useEffect(() => {
    if (!routeTrailId || !isAuthenticated) {
      setActiveTrail(null)
      setTrailDetailError(null)
      return
    }
    setTrailDetailLoading(true)
    setTrailDetailError(null)
    setActiveTrail(null)
    backendFetch<Trail>(`/trails/${routeTrailId}`)
      .then((res) => {
        if (res.ok && res.data) {
          setActiveTrail(res.data)
          setTrailDetailError(null)
        } else {
          const msg =
            res.status === 0
              ? "Network error. Is the backend running?"
              : (res.data as { detail?: string })?.detail ?? "Failed to load trail"
          setTrailDetailError(msg)
        }
      })
      .finally(() => setTrailDetailLoading(false))
  }, [routeTrailId, isAuthenticated])

  const handleNewTrail = useCallback(() => {
    setActiveTrailId(null)
    setActiveTrail(null)
    router.push("/trails")
  }, [router])

  const handleCreateTrail = useCallback(
    async (topic: string) => {
      const existing = trails.find(
        (t) => t.topic.toLowerCase() === topic.toLowerCase()
      )
      if (existing) {
        router.push(`/trails?trail=${existing.id}`)
        return
      }
      const res = await backendFetch<TrailSummary>("/trails/", {
        method: "POST",
        body: JSON.stringify({ topic }),
      })
      if (res.ok && res.data) {
        setTrails((prev) => [...prev, res.data as TrailSummary])
        router.push(`/trails?trail=${(res.data as TrailSummary).id}`)
      } else {
        router.push("/trails")
      }
    },
    [trails, router]
  )

  const handleSelectTrail = useCallback(
    (id: string) => {
      setActiveTrailId(id)
      router.push(`/trails?trail=${id}`)
    },
    [router]
  )

  const handleDeleteTrail = useCallback(
    async (trailId: string) => {
      const res = await backendFetch(`/trails/${trailId}`, { method: "DELETE" })
      if (res.ok) {
        setTrails((prev) => prev.filter((t) => t.id !== trailId))
        if (trailId === activeTrailId) {
          setActiveTrailId(null)
          setActiveTrail(null)
          router.push("/trails")
        }
      }
    },
    [activeTrailId, router]
  )

  const handleToggleRead = useCallback(
    (nodeId: string) => {
      if (!activeTrail) return
      const node = activeTrail.nodes.find((n) => n.id === nodeId)
      const nextRead = !(node?.paper.isRead ?? false)
      backendFetch(`/papers/${nodeId}/user-state`, {
        method: "PATCH",
        body: JSON.stringify({ isRead: nextRead }),
      }).then((res) => {
        if (res.ok) {
          setActiveTrail((prev) =>
            prev
              ? {
                  ...prev,
                  nodes: prev.nodes.map((n) =>
                    n.id === nodeId
                      ? { ...n, paper: { ...n.paper, isRead: nextRead } }
                      : n
                  ),
                }
              : null
          )
          // Refetch trail list so every trail's progress (including those sharing this paper) is correct
          backendFetch<TrailSummary[]>("/trails/").then((listRes) => {
            if (listRes.ok && Array.isArray(listRes.data)) setTrails(listRes.data)
          })
        }
      })
    },
    [activeTrail, activeTrailId]
  )

  const sidebarTrails: Trail[] = trails.map((t) => ({
    ...t,
    nodes: [],
    readCount: t.readCount,
    totalCount: t.totalCount,
  }))

  const handleToggleStar = useCallback((nodeId: string) => {
    if (!activeTrail) return
    const node = activeTrail.nodes.find((n) => n.id === nodeId)
    const nextStarred = !(node?.paper.isStarred ?? false)
    backendFetch(`/papers/${nodeId}/user-state`, {
      method: "PATCH",
      body: JSON.stringify({ isStarred: nextStarred }),
    }).then((res) => {
      if (res.ok) {
        setActiveTrail((prev) =>
          prev
            ? {
                ...prev,
                nodes: prev.nodes.map((n) =>
                  n.id === nodeId
                    ? {
                        ...n,
                        paper: {
                          ...n.paper,
                          isStarred: nextStarred,
                        },
                      }
                    : n
                ),
              }
            : null
        )
      }
    })
  }, [activeTrail])

  const handleSaveNote = useCallback((nodeId: string, note: string) => {
    backendFetch(`/papers/${nodeId}/user-state`, {
      method: "PATCH",
      body: JSON.stringify({ note }),
    }).then((res) => {
      if (res.ok) {
        setActiveTrail((prev) =>
          prev
            ? {
                ...prev,
                nodes: prev.nodes.map((n) =>
                  n.id === nodeId
                    ? { ...n, paper: { ...n.paper, note } }
                    : n
                ),
              }
            : null
        )
      }
    })
  }, [])

  return (
    <div className="flex h-dvh bg-background">
      <TrailSidebar
        trails={sidebarTrails}
        activeTrailId={activeTrailId}
        onSelectTrail={handleSelectTrail}
        onNewTrail={handleNewTrail}
        onDeleteTrail={handleDeleteTrail}
        trailsLoading={trailsLoading}
      />
      <main className="flex flex-1 flex-col overflow-hidden">
        {trailDetailLoading && routeTrailId ? (
          <div className="flex flex-1 items-center justify-center text-muted-foreground">
            Loading trail…
          </div>
        ) : trailDetailError && routeTrailId ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 text-muted-foreground">
            <p>{trailDetailError}</p>
            <button
              type="button"
              onClick={() => {
                setTrailDetailError(null)
                setTrailDetailLoading(true)
                backendFetch<Trail>(`/trails/${routeTrailId}`).then((res) => {
                  if (res.ok && res.data) {
                    setActiveTrail(res.data)
                    setTrailDetailError(null)
                  } else {
                    setTrailDetailError(
                      (res.data as { detail?: string })?.detail ?? "Failed to load trail"
                    )
                  }
                }).finally(() => setTrailDetailLoading(false))
              }}
              className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:opacity-90"
            >
              Retry
            </button>
          </div>
        ) : activeTrail ? (
          <DAGCanvas
            trail={activeTrail}
            onToggleRead={handleToggleRead}
            onToggleStar={handleToggleStar}
            onSaveNote={handleSaveNote}
            onBack={handleNewTrail}
          />
        ) : (
          <WelcomeScreen
            onCreateTrail={handleCreateTrail}
            onSelectTrail={handleSelectTrail}
            recentTrails={trails}
          />
        )}
      </main>
    </div>
  )
}

