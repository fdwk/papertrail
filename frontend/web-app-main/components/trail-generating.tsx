"use client"

import { Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

export interface CandidatePaper {
  title: string
  authors: string[]
  year?: number
  verified: boolean
  source?: "openalex" | "ai"
}

interface TrailGeneratingProps {
  topic: string
  stage: string
  stageMessage: string
  papers: CandidatePaper[]
}

const STAGES = ["suggesting", "searching", "selecting", "saving"] as const

function stageLabel(stage: string) {
  switch (stage) {
    case "suggesting":
      return "Suggesting"
    case "searching":
      return "Confirming"
    case "selecting":
      return "Curating"
    case "saving":
      return "Building"
    default:
      return "Generating"
  }
}

function stageAccentCopy(stage: string) {
  switch (stage) {
    case "selecting":
      return "Ranking the strongest papers and shaping the learning arc."
    case "saving":
      return "Finalizing the graph structure and preparing your trail."
    case "searching":
      return "Cross-checking papers against the literature graph."
    default:
      return "Exploring the literature and gathering strong candidates."
  }
}

export function TrailGenerating({ topic, stage, stageMessage, papers }: TrailGeneratingProps) {
  const currentStageIndex = Math.max(0, STAGES.indexOf(stage as (typeof STAGES)[number]))
  const verifiedCount = papers.filter((paper) => paper.verified).length
  const verifiedPapers = papers.filter((paper) => paper.verified)
  const candidatePapers = papers.filter((paper) => !paper.verified)
  const isFinalizing = stage === "selecting" || stage === "saving"

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-background">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.22]"
        aria-hidden
        style={{
          backgroundImage:
            "radial-gradient(circle, var(--border) 1px, transparent 1px)",
          backgroundSize: "26px 26px",
        }}
      />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-primary/[0.04] to-transparent" />

      <div className="relative z-10 px-6 pb-3 pt-6">
        <div className="mx-auto flex w-full max-w-4xl flex-col items-center gap-2.5 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/80 px-3 py-1 backdrop-blur-sm">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
            <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Generating Trail
            </span>
          </div>
          <div className="space-y-0.5">
            <h2 className="text-balance text-[22px] font-semibold tracking-tight text-foreground">
              {topic}
            </h2>
            <p className="text-[13px] text-muted-foreground">{stageMessage}</p>
          </div>
          <div className="flex w-full max-w-2xl items-center gap-2 pt-0.5">
            {STAGES.map((key, index) => {
              const active = index <= currentStageIndex
              return (
                <div key={key} className="flex min-w-0 flex-1 flex-col gap-1">
                  <div className="h-1 rounded-full bg-muted/70">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-300",
                        active ? "w-full bg-primary" : "w-0 bg-primary/30",
                      )}
                    />
                  </div>
                  <p
                    className={cn(
                      "text-[9px] uppercase tracking-[0.16em]",
                      active ? "text-foreground" : "text-muted-foreground/50",
                    )}
                  >
                    {stageLabel(key)}
                  </p>
                </div>
              )
            })}
          </div>
          <div className="flex w-full max-w-2xl flex-wrap items-center justify-center gap-2 pt-0.5">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-card/75 px-3 py-1.5 text-xs backdrop-blur-sm">
              <span className="text-muted-foreground/65">Confirmed</span>
              <span className="font-semibold text-foreground">{verifiedCount}</span>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/75 px-3 py-1.5 text-xs backdrop-blur-sm">
              <span className="text-muted-foreground/65">Candidates</span>
              <span className="font-semibold text-foreground">{candidatePapers.length}</span>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/75 px-3 py-1.5 text-xs backdrop-blur-sm">
              <Sparkles className="h-3.5 w-3.5 text-primary/80" />
              <span className="font-medium text-foreground">{stageLabel(stage)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 flex-1 overflow-y-auto px-6 pb-8 pt-2">
        <div className="mx-auto w-full max-w-5xl">
          {papers.length === 0 ? (
            <div className="flex h-[42vh] items-center justify-center rounded-3xl border border-border/60 bg-card/50 px-8 text-center backdrop-blur-sm">
              <div className="flex max-w-sm flex-col items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary/90" />
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary/60 [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary/35 [animation-delay:300ms]" />
                </div>
                <p className="text-sm text-muted-foreground">
                  Looking across the literature and assembling a clean reading path.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <section
                className={cn(
                  "overflow-hidden rounded-3xl border bg-card/55 backdrop-blur-sm transition-all duration-500",
                  isFinalizing
                    ? "border-primary/20 shadow-sm shadow-primary/10"
                    : "border-border/60",
                )}
              >
                <div className="relative px-5 py-4">
                  {isFinalizing ? (
                    <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-primary/[0.03] via-primary/[0.08] to-transparent" />
                  ) : null}
                  <div className="relative flex items-center justify-between gap-4">
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground/60">
                        Current Phase
                      </p>
                      <p className="mt-1 text-sm font-medium text-foreground">
                        {stageLabel(stage)}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {stageAccentCopy(stage)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-primary/90" />
                      <span className="h-2 w-2 animate-pulse rounded-full bg-primary/65 [animation-delay:180ms]" />
                      <span className="h-2 w-2 animate-pulse rounded-full bg-primary/40 [animation-delay:360ms]" />
                    </div>
                  </div>
                </div>
              </section>

              <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.9fr)]">
              <section className="rounded-3xl border border-primary/15 bg-card/55 p-4 backdrop-blur-sm">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.18em] text-primary/70">
                      OpenAlex Confirmed
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Papers already matched in the literature graph.
                    </p>
                  </div>
                  <div className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
                    {verifiedPapers.length}
                  </div>
                </div>
                <div className="grid auto-rows-fr gap-2.5 sm:grid-cols-2">
                  {verifiedPapers.map((paper, index) => (
                    <article
                      key={`${paper.title}-${index}`}
                      className="animate-in fade-in-0 slide-in-from-bottom-4 rounded-2xl border border-primary/20 bg-background/90 px-4 py-3 duration-300"
                      style={{ animationDelay: `${index * 70}ms` }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 items-start gap-3">
                          <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary shadow-[0_0_14px_rgba(99,102,241,0.45)]" />
                          <div className="min-w-0">
                            <h3 className="line-clamp-2 text-[13px] font-medium leading-5 text-foreground">
                              {paper.title}
                            </h3>
                            <p className="mt-1 text-[11px] text-muted-foreground/75">
                              Mapped into OpenAlex
                            </p>
                          </div>
                        </div>
                        {paper.year ? (
                          <span className="shrink-0 text-[11px] text-muted-foreground/70">
                            {paper.year}
                          </span>
                        ) : null}
                      </div>
                    </article>
                  ))}
                  {verifiedPapers.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-primary/15 bg-background/60 px-4 py-6 text-sm text-muted-foreground">
                      Waiting for the first confirmed literature matches...
                    </div>
                  ) : null}
                </div>
              </section>

              <section className="rounded-3xl border border-border/60 bg-card/45 p-4 backdrop-blur-sm">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
                      Secondary Candidates
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Suggestions being validated against the literature graph.
                    </p>
                  </div>
                  <div className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                    {candidatePapers.length}
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  {candidatePapers.slice(0, 8).map((paper, index) => (
                    <article
                      key={`${paper.title}-${index}`}
                      className="animate-in fade-in-0 slide-in-from-bottom-4 rounded-2xl border border-border/70 bg-background/75 px-3.5 py-3 duration-300"
                      style={{ animationDelay: `${index * 70}ms` }}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-muted-foreground/35" />
                        <div className="min-w-0">
                          <h3 className="line-clamp-2 text-[13px] font-medium leading-5 text-foreground">
                            {paper.title}
                          </h3>
                          <p className="mt-1 text-[11px] text-muted-foreground/75">
                            Evaluating relevance
                          </p>
                        </div>
                      </div>
                    </article>
                  ))}
                  {candidatePapers.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-border/70 bg-background/60 px-4 py-6 text-sm text-muted-foreground">
                      Secondary candidates will appear here while the trail is being shaped.
                    </div>
                  ) : null}
                </div>
              </section>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
