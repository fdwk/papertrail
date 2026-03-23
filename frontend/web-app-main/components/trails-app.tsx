"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Trail, TrailSize, TrailSummary, type ExpansionState } from "@/lib/types"
import { TrailSidebar } from "@/components/trail-sidebar"
import { DAGCanvas } from "@/components/dag-canvas"
import { WelcomeScreen } from "@/components/welcome-screen"
import { TrailGenerating, type CandidatePaper } from "@/components/trail-generating"
import { useAuth } from "@/lib/auth-context"
import { backendFetch } from "@/lib/api-client"
import { toast } from "sonner"

const BACKEND_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000"

type TrailStreamEvent =
  | { type: "status"; stage?: string; message?: string }
  | { type: "candidate"; paper?: Partial<CandidatePaper> }
  | { type: "verified"; paper?: Partial<CandidatePaper> }
  | { type: "complete"; trail_id?: string }
  | { type: "error"; message?: string }

interface TrailGeneratingState {
  topic: string
  size: TrailSize
  stage: string
  stageMessage: string
  papers: CandidatePaper[]
}

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
  const [createTrailLoading, setCreateTrailLoading] = useState(false)
  const [generatingState, setGeneratingState] = useState<TrailGeneratingState | null>(null)
  const [expansionState, setExpansionState] = useState<ExpansionState | null>(null)

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
      setExpansionState(null)
      return
    }
    setTrailDetailLoading(true)
    setTrailDetailError(null)
    setActiveTrail(null)
    setExpansionState(null)
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
    setExpansionState(null)
    router.push("/trails")
  }, [router])

  const handleCreateTrail = useCallback(
    async (topic: string, size: TrailSize) => {
      if (createTrailLoading) return
      const token =
        typeof window !== "undefined" ? localStorage.getItem("jwt_token") : null
      const initialStageMessage = `Finding high-signal papers for a ${size} trail...`
      const minimumStageMs: Partial<Record<TrailGeneratingState["stage"], number>> = {
        selecting: 900,
        saving: 700,
      }

      const upsertPaper = (
        previous: CandidatePaper[],
        incoming: CandidatePaper,
      ) => {
        const normalizedTitle = incoming.title.trim().toLowerCase()
        const index = previous.findIndex((paper) => {
          if (paper.title.trim().toLowerCase() !== normalizedTitle) return false
          if (!incoming.year || !paper.year) return true
          return paper.year === incoming.year
        })
        if (index === -1) {
          return [...previous, incoming]
        }
        const next = [...previous]
        next[index] = {
          ...next[index],
          ...incoming,
          verified: next[index].verified || incoming.verified,
        }
        return next
      }

      let displayedStage: TrailGeneratingState["stage"] = "suggesting"
      let lastStageChangeAt = Date.now()

      const maybeAdvanceStage = async (
        nextStage: TrailGeneratingState["stage"],
        nextMessage: string,
      ) => {
        if (displayedStage !== nextStage) {
          const minTime = minimumStageMs[displayedStage] ?? 0
          const elapsed = Date.now() - lastStageChangeAt
          if (elapsed < minTime) {
            await new Promise((resolve) => window.setTimeout(resolve, minTime - elapsed))
          }
          displayedStage = nextStage
          lastStageChangeAt = Date.now()
        }
        setGeneratingState((prev) =>
          prev
            ? {
                ...prev,
                stage: nextStage,
                stageMessage: nextMessage,
              }
            : prev,
        )
      }

      setCreateTrailLoading(true)
      setExpansionState(null)
      setGeneratingState({
        topic,
        size,
        stage: "suggesting",
        stageMessage: initialStageMessage,
        papers: [],
      })
      router.push("/trails")

      try {
        const res = await fetch(`${BACKEND_API_BASE}/trails/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ topic, size }),
        })

        if (!res.ok || !res.body) {
          let detail = ""
          try {
            const err = (await res.json()) as { detail?: string }
            detail = err.detail ?? ""
          } catch {
            detail = ""
          }
          if (res.status === 403 && detail) {
            throw new Error(detail)
          }
          throw new Error(detail || "Unable to start trail generation stream.")
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""
        let createdTrailId: string | null = null

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const chunks = buffer.split("\n\n")
          buffer = chunks.pop() ?? ""

          for (const chunk of chunks) {
            if (!chunk.trim()) continue
            const data = chunk
              .split("\n")
              .filter((line) => line.startsWith("data:"))
              .map((line) => line.replace(/^data:\s?/, ""))
              .join("")
            if (!data) continue

            let event: TrailStreamEvent
            try {
              event = JSON.parse(data) as TrailStreamEvent
            } catch {
              continue
            }

            if (event.type === "status") {
              await maybeAdvanceStage(
                event.stage ?? displayedStage,
                event.message ?? initialStageMessage,
              )
            } else if (event.type === "candidate" || event.type === "verified") {
              const incomingTitle = event.paper?.title?.trim()
              if (!incomingTitle) continue
              const incomingPaper: CandidatePaper = {
                title: incomingTitle,
                authors: Array.isArray(event.paper?.authors)
                  ? event.paper.authors.filter((author): author is string => !!author)
                  : [],
                year: typeof event.paper?.year === "number" ? event.paper.year : undefined,
                verified: event.type === "verified",
                source: event.type === "verified" ? "openalex" : "ai",
              }
              setGeneratingState((prev) =>
                prev
                  ? {
                      ...prev,
                      papers: upsertPaper(prev.papers, incomingPaper),
                    }
                  : prev,
              )
            } else if (event.type === "error") {
              throw new Error(event.message || "Trail generation failed.")
            } else if (event.type === "complete") {
              createdTrailId = event.trail_id ?? null
            }
          }
        }

        if (!createdTrailId) {
          throw new Error("Trail generation ended without creating a trail.")
        }

        const finalStageMin = minimumStageMs[displayedStage] ?? 0
        const finalStageElapsed = Date.now() - lastStageChangeAt
        if (finalStageElapsed < finalStageMin) {
          await new Promise((resolve) => window.setTimeout(resolve, finalStageMin - finalStageElapsed))
        }

        const [trailRes, trailsRes] = await Promise.all([
          backendFetch<Trail>(`/trails/${createdTrailId}`),
          backendFetch<TrailSummary[]>("/trails/"),
        ])

        if (trailsRes.ok && Array.isArray(trailsRes.data)) {
          setTrails(trailsRes.data)
        }
        if (trailRes.ok && trailRes.data) {
          setActiveTrail(trailRes.data)
          setActiveTrailId(createdTrailId)
          router.push(`/trails?trail=${createdTrailId}`)
        } else {
          router.push("/trails")
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to generate trail."
        toast.error(message)
        setTrailDetailError(null)
        router.push("/trails")
      } finally {
        setGeneratingState(null)
        setCreateTrailLoading(false)
      }
    },
    [createTrailLoading, router]
  )

  const handleSelectTrail = useCallback(
    (id: string) => {
      setActiveTrailId(id)
      setExpansionState(null)
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

  const handleRequestExpandFromNode = useCallback(
    async (nodeId: string) => {
      if (!activeTrail || !routeTrailId) return
      if (expansionState && expansionState.status !== "idle") return
      setExpansionState({
        status: "loading",
        sourceNodeId: nodeId,
        proposedNodes: [],
        proposedEdges: [],
        selectedNodeIds: new Set<string>(),
      })
      const res = await backendFetch<{
        nodes: Trail["nodes"]
        edges: { source: string; target: string }[]
      }>(`/trails/${routeTrailId}/expand`, {
        method: "POST",
        body: JSON.stringify({ sourceNodeId: nodeId }),
      })
      if (!res.ok || !res.data) {
        setExpansionState(null)
        const msg =
          (res.data as { detail?: string })?.detail ?? "Failed to propose expansion."
        toast.error(msg)
        return
      }
      const proposedNodes = res.data.nodes
      const proposedEdges = res.data.edges
      if (!Array.isArray(proposedNodes) || proposedNodes.length === 0) {
        setExpansionState(null)
        toast.message("No new papers to add here", {
          description: "Try expanding from a different paper in this trail.",
        })
        return
      }
      setExpansionState({
        status: "staged",
        sourceNodeId: nodeId,
        proposedNodes,
        proposedEdges,
        selectedNodeIds: new Set(proposedNodes.map((n) => n.id)),
      })
    },
    [activeTrail, routeTrailId, expansionState],
  )

  const handleToggleSelectedInExpansion = useCallback((nodeId: string) => {
    setExpansionState((prev) => {
      if (!prev) return prev
      const nextSelected = new Set(prev.selectedNodeIds)
      if (nextSelected.has(nodeId)) {
        nextSelected.delete(nodeId)
      } else {
        nextSelected.add(nodeId)
      }
      return { ...prev, selectedNodeIds: nextSelected }
    })
  }, [])

  const handleDismissExpansion = useCallback(() => {
    setExpansionState(null)
  }, [])

  const handleConfirmExpansion = useCallback(async () => {
    if (!expansionState || !routeTrailId) return
    const accepted = [...expansionState.selectedNodeIds]
    if (accepted.length === 0) return
    setExpansionState((prev) => (prev ? { ...prev, status: "confirming" } : prev))
    const res = await backendFetch<Trail>(`/trails/${routeTrailId}/expand/confirm`, {
      method: "POST",
      body: JSON.stringify({
        sourceNodeId: expansionState.sourceNodeId,
        acceptedNodeIds: accepted,
      }),
    })
    if (res.ok && res.data) {
      setActiveTrail(res.data)
      setExpansionState(null)
      toast.success(
        accepted.length === 1
          ? "Added 1 paper to this trail."
          : `Added ${accepted.length} papers to this trail.`,
      )
      // Refresh sidebar counts
      backendFetch<TrailSummary[]>("/trails/").then((listRes) => {
        if (listRes.ok && Array.isArray(listRes.data)) setTrails(listRes.data)
      })
    } else {
      const msg =
        (res.data as { detail?: string })?.detail ??
        "Failed to apply expansion. Your trail is unchanged."
      toast.error(msg)
      setExpansionState((prev) =>
        prev ? { ...prev, status: "staged" } : prev,
      )
    }
  }, [expansionState, routeTrailId])

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
        {generatingState ? (
          <TrailGenerating
            topic={generatingState.topic}
            stage={generatingState.stage}
            stageMessage={generatingState.stageMessage}
            papers={generatingState.papers}
          />
        ) : trailDetailLoading && routeTrailId ? (
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
            expansionState={expansionState}
            onRequestExpandFromNode={handleRequestExpandFromNode}
            onConfirmExpansion={handleConfirmExpansion}
            onDismissExpansion={handleDismissExpansion}
            onToggleSelectedInExpansion={handleToggleSelectedInExpansion}
          />
        ) : (
          <WelcomeScreen
            onCreateTrail={handleCreateTrail}
            onSelectTrail={handleSelectTrail}
            recentTrails={trails}
            isCreating={createTrailLoading}
          />
        )}
      </main>
    </div>
  )
}

