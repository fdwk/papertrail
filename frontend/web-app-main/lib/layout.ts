import dagre from "@dagrejs/dagre"
import type { Node, Edge } from "@xyflow/react"
import type { DAGNode } from "./types"

const NODE_WIDTH = 280
const NODE_HEIGHT = 172

function getGraphConfig(dagNodes: DAGNode[]) {
  const rootCount = dagNodes.filter((n) => n.dependencies.length === 0).length
  const wide = dagNodes.length >= 10 || rootCount >= 3

  return {
    rankdir: "TB" as const,
    ranker: dagNodes.length >= 12 ? "tight-tree" : "network-simplex",
    align: "UL" as const,
    nodesep: wide ? 120 : 88,
    ranksep: dagNodes.length >= 8 ? 196 : 168,
    edgesep: wide ? 72 : 56,
    marginx: 48,
    marginy: 48,
  }
}

export function getLayoutedElements(dagNodes: DAGNode[]) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph(getGraphConfig(dagNodes))

  for (const dagNode of dagNodes) {
    g.setNode(dagNode.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }

  const edges: Edge[] = []

  for (const dagNode of dagNodes) {
    for (const depId of dagNode.dependencies) {
      g.setEdge(depId, dagNode.id, { weight: 2, minlen: 1 })
      edges.push({
        id: `e-${depId}-${dagNode.id}`,
        source: depId,
        target: dagNode.id,
        type: "default",
        animated: false,
        markerEnd: { type: "arrowclosed" },
      })
    }
  }

  dagre.layout(g)

  const nodes: Node[] = dagNodes.map((dagNode) => {
    const pos = g.node(dagNode.id)
    return {
      id: dagNode.id,
      type: "paperNode",
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
      data: {
        paper: dagNode.paper,
        nodeId: dagNode.id,
      },
    }
  })

  return { nodes, edges }
}
