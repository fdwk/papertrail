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

  useEffect(() => {
    setActiveTrailId(routeTrailId)
  }, [routeTrailId])

  // When user is logged in, fetch their trail list (no nodes/edges).
  useEffect(() => {
    if (!isAuthenticated) {
      setTrails([])
      return
    }
    setTrailsLoading(true)
    backendFetch<TrailSummary[]>("/trails/")
      .then((res) => {
        if (res.ok && Array.isArray(res.data)) setTrails(res.data)
      })
      .finally(() => setTrailsLoading(false))
  }, [isAuthenticated])

  // When a trail is selected, fetch full trail with graph.
  useEffect(() => {
    if (!routeTrailId || !isAuthenticated) {
      setActiveTrail(null)
      return
    }
    setTrailDetailLoading(true)
    setActiveTrail(null)
    backendFetch<Trail>(`/trails/${routeTrailId}`)
      .then((res) => {
        if (res.ok && res.data) setActiveTrail(res.data)
      })
      .finally(() => setTrailDetailLoading(false))
  }, [routeTrailId, isAuthenticated])

  const handleNewTrail = useCallback(() => {
    setActiveTrailId(null)
    setActiveTrail(null)
    router.push("/trails")
  }, [router])

  const handleCreateTrail = useCallback(
    (topic: string) => {
      const existing = trails.find(
        (t) => t.topic.toLowerCase() === topic.toLowerCase()
      )
      if (existing) {
        router.push(`/trails?trail=${existing.id}`)
        return
      }
      // TODO: POST /trails when backend supports create
      router.push("/trails")
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
          setTrails((prev) =>
            prev.map((t) =>
              t.id === activeTrailId
                ? {
                    ...t,
                    readCount: (t.readCount ?? 0) + (nextRead ? 1 : -1),
                  }
                : t
            )
          )
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
        trailsLoading={trailsLoading}
      />
      <main className="flex flex-1 flex-col overflow-hidden">
        {trailDetailLoading && routeTrailId ? (
          <div className="flex flex-1 items-center justify-center text-muted-foreground">
            Loading trail…
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

