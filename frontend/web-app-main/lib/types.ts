export interface Paper {
  id: string
  title: string
  authors: string[]
  year: number
  abstract: string
  url: string
  isRead: boolean
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
