"use client"

const SKELETON_NODES = [
  { x: 300, y: 40, w: 220, h: 56 },
  { x: 140, y: 160, w: 220, h: 56 },
  { x: 460, y: 160, w: 220, h: 56 },
  { x: 60, y: 300, w: 220, h: 56 },
  { x: 340, y: 300, w: 220, h: 56 },
]

const SKELETON_EDGES: [number, number][] = [
  [0, 1],
  [0, 2],
  [1, 3],
  [1, 4],
  [2, 4],
]

export function DAGSkeleton() {
  return (
    <div className="flex h-full flex-col">
      {/* Skeleton header */}
      <div className="flex flex-shrink-0 items-center justify-between border-b border-border bg-card/80 px-6 py-3 backdrop-blur-sm">
        <div className="flex flex-col gap-1.5">
          <div className="h-5 w-48 animate-shimmer rounded-md" />
          <div className="h-3 w-24 animate-shimmer rounded-md" />
        </div>
        <div className="flex items-center gap-3">
          <div className="h-4 w-20 animate-shimmer rounded-md" />
          <div className="h-1.5 w-24 animate-shimmer rounded-full" />
        </div>
      </div>

      {/* Skeleton canvas */}
      <div className="relative flex-1 overflow-hidden bg-background">
        {/* Dot grid background */}
        <svg className="absolute inset-0 h-full w-full opacity-30">
          <pattern id="skeldots" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" fill="var(--canvas-dot)" />
          </pattern>
          <rect width="100%" height="100%" fill="url(#skeldots)" />
        </svg>

        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 620 420" preserveAspectRatio="xMidYMid meet">
          {/* Edges */}
          {SKELETON_EDGES.map(([from, to], i) => {
            const f = SKELETON_NODES[from]
            const t = SKELETON_NODES[to]
            return (
              <line
                key={i}
                x1={f.x + f.w / 2}
                y1={f.y + f.h}
                x2={t.x + t.w / 2}
                y2={t.y}
                stroke="var(--edge-default)"
                strokeWidth="1.5"
                strokeDasharray="6 4"
                opacity="0.4"
              />
            )
          })}

          {/* Nodes */}
          {SKELETON_NODES.map((node, i) => (
            <g key={i}>
              <rect
                x={node.x}
                y={node.y}
                width={node.w}
                height={node.h}
                rx="12"
                fill="var(--card)"
                stroke="var(--border)"
                strokeWidth="1.5"
                className="animate-pulse"
                style={{ animationDelay: `${i * 120}ms` }}
              />
              {/* Title placeholder */}
              <rect
                x={node.x + 16}
                y={node.y + 14}
                width={node.w * 0.65}
                height={10}
                rx="4"
                className="animate-shimmer"
                style={{ animationDelay: `${i * 120}ms` }}
              />
              {/* Subtitle placeholder */}
              <rect
                x={node.x + 16}
                y={node.y + 32}
                width={node.w * 0.4}
                height={8}
                rx="3"
                className="animate-shimmer"
                style={{ animationDelay: `${i * 120 + 60}ms` }}
              />
            </g>
          ))}
        </svg>

        <div className="absolute inset-0 flex items-center justify-center">
          <p className="rounded-full bg-card/80 px-4 py-2 text-sm text-muted-foreground shadow-sm backdrop-blur-sm">
            Loading trail…
          </p>
        </div>
      </div>
    </div>
  )
}
