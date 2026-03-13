export type TrailSize = "small" | "medium" | "large"

export interface Paper {
  id: string
  title: string
  authors: string[]
  year: number
  abstract: string
  url: string
  isRead: boolean
  isStarred?: boolean
  note?: string
}

export interface DAGNode {
  id: string
  paper: Paper
  dependencies: string[] // IDs of nodes this depends on
}

export interface Trail {
  id: string
  topic: string
  createdAt: string
  nodes: DAGNode[]
}

/** Lightweight trail for list (no nodes). From GET /trails. */
export interface TrailSummary {
  id: string
  topic: string
  createdAt: string
  readCount?: number
  totalCount?: number
}
