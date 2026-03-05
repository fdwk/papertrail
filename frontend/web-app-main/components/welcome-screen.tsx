"use client"

import { useState, useMemo, type FormEvent } from "react"
import {
  ArrowRight,
  Sparkles,
  BookOpen,
  GitBranch,
  Search,
  Zap,
  TrendingUp,
  Clock,
  FileText,
} from "lucide-react"
import { ThemeToggle } from "./theme-toggle"
import Link from "next/link"
import { cn } from "@/lib/utils"
import type { TrailSummary } from "@/lib/types"

interface WelcomeScreenProps {
  onCreateTrail: (topic: string) => void
  onSelectTrail?: (id: string) => void
  recentTrails?: TrailSummary[]
}

const trendingTopics = [
  { label: "Transformer Architecture", papers: 142 },
  { label: "Graph Neural Networks", papers: 98 },
  { label: "Federated Learning", papers: 67 },
  { label: "Quantum Computing", papers: 85 },
  { label: "Diffusion Models", papers: 124 },
  { label: "Reinforcement Learning", papers: 113 },
  { label: "LLM Alignment", papers: 76 },
  { label: "Neural Radiance Fields", papers: 59 },
]

function getGreeting(): string {
  const h = new Date().getHours()
  if (h >= 23 || h < 4) return "It's late at night"
  if (h < 12) return "Good morning"
  if (h < 17) return "Good afternoon"
  return "Good evening"
}

export function WelcomeScreen({
  onCreateTrail,
  onSelectTrail,
  recentTrails = [],
}: WelcomeScreenProps) {
  const [topic, setTopic] = useState("")
  const greeting = useMemo(() => getGreeting(), [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (topic.trim()) {
      onCreateTrail(topic.trim())
      setTopic("")
    }
  }

  const hasRecent = recentTrails.length > 0
  const displayTrails = recentTrails.slice(0, 3)

  return (
    <div className="relative flex h-full flex-col items-center justify-center overflow-y-auto px-6 py-12">
      {/* Subtle dot pattern background */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(circle, var(--border) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      />

      {/* Theme toggle */}
      <div className="absolute right-5 top-4 z-10 animate-fade-up delay-0">
        <ThemeToggle />
      </div>

      <div className="relative w-full max-w-xl">
        {/* Icon + heading */}
        <div className="mb-10 flex flex-col items-center">
          <div className="animate-fade-up delay-0 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/[0.08]">
            <Search className="h-6 w-6 text-primary" />
          </div>
          <h2 className="animate-fade-up delay-1 mt-6 text-balance text-center text-3xl font-bold tracking-tight text-foreground">
            {greeting}. What will you explore?
          </h2>
          <p className="animate-fade-up delay-2 mt-2 text-center text-sm text-muted-foreground">
            Enter a research topic to generate a structured reading trail.
          </p>
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="animate-fade-up delay-3 relative">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., Transformer Architecture, Reinforcement Learning..."
            className="w-full rounded-2xl border border-border bg-card px-5 py-4 pr-14 text-sm text-foreground shadow-sm shadow-black/[0.03] placeholder:text-muted-foreground/50 transition-all focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/15 focus:shadow-md focus:shadow-primary/[0.04]"
          />
          <button
            type="submit"
            disabled={!topic.trim()}
            className="absolute right-2.5 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm transition-all disabled:opacity-25 hover:bg-primary/90 active:scale-95"
            aria-label="Create trail"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        {/* Trending topics */}
        <div className="animate-fade-up delay-4 mt-5">
          <div className="mb-2.5 flex items-center justify-center gap-1.5">
            <TrendingUp className="h-3 w-3 text-muted-foreground/50" />
            <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/50">
              Trending
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-1.5">
            {trendingTopics.map((t) => (
              <button
                key={t.label}
                onClick={() => onCreateTrail(t.label)}
                className="group flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-all hover:border-primary/30 hover:bg-primary/5 hover:text-foreground active:scale-[0.97]"
              >
                <span>{t.label}</span>
                <span className="rounded-md bg-muted px-1 py-px font-mono text-[10px] text-muted-foreground/50 transition-colors group-hover:bg-primary/10 group-hover:text-primary/70">
                  {t.papers}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Continue reading */}
        {hasRecent && (
          <div className="animate-fade-up delay-5 mt-10">
            <div className="mb-3 flex items-center justify-center gap-1.5">
              <Clock className="h-3 w-3 text-muted-foreground/50" />
              <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/50">
                Pick up where you left off
              </span>
            </div>
            <div className={cn(
              "grid gap-2",
              displayTrails.length === 1 ? "grid-cols-1 max-w-[220px] mx-auto" :
              displayTrails.length === 2 ? "grid-cols-2" : "grid-cols-3"
            )}>
              {displayTrails.map((trail) => {
                const total = trail.totalCount ?? 0
                const read = trail.readCount ?? 0
                const pct = total > 0 ? Math.round((read / total) * 100) : 0
                return (
                  <button
                    key={trail.id}
                    onClick={() => onSelectTrail?.(trail.id)}
                    className="group flex flex-col gap-2.5 rounded-xl border border-border/60 bg-card/80 p-3.5 text-left backdrop-blur-sm transition-all hover:border-primary/30 hover:bg-card hover:shadow-sm active:scale-[0.98]"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="h-3.5 w-3.5 shrink-0 text-primary/50 transition-colors group-hover:text-primary" />
                      <span className="truncate text-xs font-semibold text-foreground">
                        {trail.topic}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary/60 transition-all duration-500 group-hover:bg-primary"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="font-mono text-[10px] font-semibold text-muted-foreground/60">
                        {pct}%
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Thin divider */}
        <div className={cn("animate-fade-up mx-auto w-12 border-t border-border/60", hasRecent ? "delay-6 mt-8" : "delay-5 mt-12")} />

        {/* Features */}
        <div className={cn("animate-fade-up grid grid-cols-3 gap-3", hasRecent ? "delay-6 mt-8" : "delay-5 mt-8")}>
          {[
            {
              icon: GitBranch,
              title: "DAG Structure",
              desc: "Papers linked by prerequisite chains",
            },
            {
              icon: BookOpen,
              title: "Track Progress",
              desc: "Mark papers read, see completion",
            },
            {
              icon: Sparkles,
              title: "Learning Paths",
              desc: "AI-curated trails for any topic",
            },
          ].map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="flex flex-col items-center rounded-xl border border-border/50 bg-card/60 px-3 py-4 text-center backdrop-blur-sm transition-colors hover:bg-card/80"
            >
              <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-primary/[0.08]">
                <Icon className="h-4 w-4 text-primary/80" />
              </div>
              <p className="text-xs font-semibold text-foreground">{title}</p>
              <p className="mt-0.5 text-[11px] leading-tight text-muted-foreground">
                {desc}
              </p>
            </div>
          ))}
        </div>

        {/* Upgrade prompt */}
        <div className={cn("animate-fade-up mt-8 flex justify-center", hasRecent ? "delay-7" : "delay-6")}>
          <Link
            href="/upgrade"
            className="group flex items-center gap-2 rounded-full border border-border/60 bg-card/60 px-4 py-2 backdrop-blur-sm transition-all hover:border-primary/30 hover:bg-card/80"
          >
            <span className="text-xs text-muted-foreground">Free plan</span>
            <span className="h-1 w-1 rounded-full bg-border" />
            <span className="flex items-center gap-1 text-xs font-medium text-primary transition-colors group-hover:text-primary/80">
              <Zap className="h-3 w-3" />
              Upgrade
            </span>
          </Link>
        </div>
      </div>
    </div>
  )
}
