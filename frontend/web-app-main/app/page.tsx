"use client"

import { useState, useCallback } from "react"
import { Trail } from "@/lib/types"
import { staticTrails } from "@/lib/static-data"
import { TrailSidebar } from "@/components/trail-sidebar"
import { DAGCanvas } from "@/components/dag-canvas"
import { WelcomeScreen } from "@/components/welcome-screen"

function generateNewTrailData(topic: string): Trail {
  const id = `trail-${Date.now()}`
  return {
    id,
    topic,
    createdAt: new Date().toISOString().split("T")[0],
    nodes: [
      {
        id: `${id}-n1`,
        paper: {
          id: `${id}-p1`,
          title: `A Survey of ${topic}`,
          authors: ["Survey, A.", "Review, B."],
          year: 2023,
          abstract: `This comprehensive survey covers the foundational concepts, recent advancements, and future directions in ${topic}. We review key methodologies and their applications across multiple domains.`,
          url: "https://arxiv.org",
          isRead: false,
        },
        dependencies: [],
      },
      {
        id: `${id}-n2`,
        paper: {
          id: `${id}-p2`,
          title: `Foundations of ${topic}: Core Principles`,
          authors: ["Foundation, C.", "Principles, D."],
          year: 2021,
          abstract: `We establish the theoretical underpinnings that make ${topic} possible. This work provides essential background for understanding more advanced techniques in the field.`,
          url: "https://arxiv.org",
          isRead: false,
        },
        dependencies: [`${id}-n1`],
      },
      {
        id: `${id}-n3`,
        paper: {
          id: `${id}-p3`,
          title: `Advances in ${topic}: Methods and Applications`,
          authors: ["Advances, E.", "Methods, F."],
          year: 2022,
          abstract: `Building on foundational work, this paper introduces novel methods for ${topic} that significantly improve upon existing approaches in terms of both efficiency and accuracy.`,
          url: "https://arxiv.org",
          isRead: false,
        },
        dependencies: [`${id}-n1`],
      },
      {
        id: `${id}-n4`,
        paper: {
          id: `${id}-p4`,
          title: `Scaling ${topic} to Real-World Problems`,
          authors: ["Scale, G.", "Real, H."],
          year: 2024,
          abstract: `We demonstrate how recent advances in ${topic} can be scaled to address real-world challenges. Our approach combines insights from both theoretical foundations and practical innovations.`,
          url: "https://arxiv.org",
          isRead: false,
        },
        dependencies: [`${id}-n2`, `${id}-n3`],
      },
    ],
  }
}

export default function Home() {
  const [trails, setTrails] = useState<Trail[]>(staticTrails)
  const [activeTrailId, setActiveTrailId] = useState<string | null>(null)

  const activeTrail = trails.find((t) => t.id === activeTrailId) ?? null

  const handleNewTrail = useCallback(() => {
    setActiveTrailId(null)
  }, [])

  const handleCreateTrail = useCallback(
    (topic: string) => {
      const existing = trails.find(
        (t) => t.topic.toLowerCase() === topic.toLowerCase()
      )
      if (existing) {
        setActiveTrailId(existing.id)
        return
      }
      const newTrail = generateNewTrailData(topic)
      setTrails((prev) => [newTrail, ...prev])
      setActiveTrailId(newTrail.id)
    },
    [trails]
  )

  const handleToggleRead = useCallback((nodeId: string) => {
    setTrails((prev) =>
      prev.map((trail) => ({
        ...trail,
        nodes: trail.nodes.map((node) =>
          node.id === nodeId
            ? {
                ...node,
                paper: { ...node.paper, isRead: !node.paper.isRead },
              }
            : node
        ),
      }))
    )
  }, [])

  return (
    <div className="flex h-dvh bg-background">
      <TrailSidebar
        trails={trails}
        activeTrailId={activeTrailId}
        onSelectTrail={setActiveTrailId}
        onNewTrail={handleNewTrail}
      />
      <main className="flex flex-1 flex-col overflow-hidden">
        {activeTrail ? (
          <DAGCanvas trail={activeTrail} onToggleRead={handleToggleRead} />
        ) : (
          <WelcomeScreen onCreateTrail={handleCreateTrail} />
        )}
      </main>
    </div>
  )
}
