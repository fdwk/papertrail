"use client"

import { useState, type FormEvent } from "react"
import { ArrowRight, Sparkles, BookOpen, GitBranch, Search } from "lucide-react"
import { ThemeToggle } from "./theme-toggle"

interface WelcomeScreenProps {
  onCreateTrail: (topic: string) => void
}

export function WelcomeScreen({ onCreateTrail }: WelcomeScreenProps) {
  const [topic, setTopic] = useState("")

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (topic.trim()) {
      onCreateTrail(topic.trim())
      setTopic("")
    }
  }

  const suggestions = [
    "Transformer Architecture",
    "Graph Neural Networks",
    "Federated Learning",
    "Quantum Computing",
  ]

  return (
    <div className="relative flex h-full flex-col items-center justify-center px-6">
      {/* Theme toggle in top-right */}
      <div className="absolute right-5 top-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-xl">
        {/* Icon + heading */}
        <div className="mb-10 flex flex-col items-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
            <Search className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-6 text-balance text-center text-3xl font-bold tracking-tight text-foreground">
            What do you want to learn?
          </h2>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            Enter a research topic to generate a structured reading trail.
          </p>
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., Transformer Architecture, Reinforcement Learning..."
            className="w-full rounded-2xl border border-border bg-card px-5 py-4 pr-14 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/15 transition-all"
          />
          <button
            type="submit"
            disabled={!topic.trim()}
            className="absolute right-2.5 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm transition-all disabled:opacity-25 hover:bg-primary/90"
            aria-label="Create trail"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        {/* Suggestion chips */}
        <div className="mt-3 flex flex-wrap items-center justify-center gap-1.5">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onCreateTrail(s)}
              className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-all hover:border-primary/30 hover:text-foreground hover:bg-primary/5"
            >
              {s}
            </button>
          ))}
        </div>

        {/* Features */}
        <div className="mt-14 grid grid-cols-3 gap-3">
          {[
            {
              icon: GitBranch,
              title: "DAG Structure",
              desc: "Papers connected by dependencies",
            },
            {
              icon: BookOpen,
              title: "Track Progress",
              desc: "Mark papers read, track completion",
            },
            {
              icon: Sparkles,
              title: "Learning Paths",
              desc: "Curated trails for any topic",
            },
          ].map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="flex flex-col items-center rounded-xl border border-border/60 bg-card/40 px-3 py-4 text-center"
            >
              <Icon className="mb-1.5 h-4 w-4 text-primary/70" />
              <p className="text-xs font-semibold text-foreground">{title}</p>
              <p className="mt-0.5 text-[11px] leading-tight text-muted-foreground">
                {desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
