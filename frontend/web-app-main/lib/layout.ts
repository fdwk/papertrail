import dagre from "@dagrejs/dagre"
import type { Node, Edge } from "@xyflow/react"
import type { DAGNode } from "./types"

const NODE_WIDTH = 280
const NODE_HEIGHT = 80

export function getLayoutedElements(dagNodes: DAGNode[]) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({
    rankdir: "TB",
    nodesep: 60,
    ranksep: 100,
    marginx: 40,
    marginy: 40,
  })

  // Add nodes
  for (const dagNode of dagNodes) {
    g.setNode(dagNode.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }

  // Add edges
  const edges: Edge[] = []
  for (const dagNode of dagNodes) {
    for (const depId of dagNode.dependencies) {
      edges.push({
        id: `e-${depId}-${dagNode.id}`,
        source: depId,
        target: dagNode.id,
        type: "smoothstep",
        animated: false,
      })
    }
  }

  for (const edge of edges) {
    g.setEdge(edge.source, edge.target)
  }

  dagre.layout(g)

  const nodes: Node[] = dagNodes.map((dagNode) => {
    const nodeWithPosition = g.node(dagNode.id)
    return {
      id: dagNode.id,
      type: "paperNode",
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
      data: {
        paper: dagNode.paper,
        nodeId: dagNode.id,
      },
    }
  })

  return { nodes, edges }
}
