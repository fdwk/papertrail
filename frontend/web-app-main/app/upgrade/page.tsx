"use client"

import { useState } from "react"
import Link from "next/link"
import { Check, ArrowLeft, Sparkles, BookOpen, Users, Shield, BarChart3, Brain } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import { backendFetch } from "@/lib/api-client"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

const tiers = [
  {
    name: "Reader",
    price: "Free",
    period: "",
    description: "For curious minds getting started with research exploration.",
    accent: "primary",
    badge: null,
    features: [
      "Up to 3 active trails",
      "DAG-based paper navigation",
      "Track reading progress",
      "Paper notes & highlights",
      "Community-curated trails",
    ],
    cta: "Current Plan",
    ctaStyle: "outline" as const,
    disabled: true,
    icon: BookOpen,
  },
  {
    name: "Scholar",
    price: "$15",
    period: "/mo",
    description: "For researchers who need deeper insights and unlimited access.",
    accent: "scholar",
    badge: "Most Popular",
    features: [
      "Unlimited active trails",
      "AI-powered paper summaries",
      "Smart recommendations",
      "Export trails & notes",
      "Priority paper indexing",
      "Advanced search filters",
      "Reading analytics",
    ],
    cta: "Upgrade to Scholar",
    ctaStyle: "solid" as const,
    disabled: false,
    icon: Sparkles,
  },
  {
    name: "Lab",
    price: "Custom",
    period: "",
    description: "For research teams & institutions that collaborate at scale.",
    accent: "lab",
    badge: null,
    features: [
      "Everything in Scholar",
      "Shared team trails",
      "Collaborative annotations",
      "Admin dashboard",
      "SSO & SAML auth",
      "Dedicated support",
      "Custom integrations",
      "SLA guarantee",
    ],
    cta: "Contact Sales",
    ctaStyle: "outline" as const,
    disabled: false,
    icon: Users,
  },
]

export default function UpgradePage() {
  const { user, isLoading } = useAuth()
  const currentTier = (user?.tier ?? "Reader").toLowerCase()
  const router = useRouter()

  const [updatingTier, setUpdatingTier] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [downgradePrompt, setDowngradePrompt] = useState<{
    tier: string
    message: string
  } | null>(null)

  const choosePlan = async (nextTier: string, confirmDowngrade = false) => {
    setUpdatingTier(true)
    setError(null)
    try {
      const res = await backendFetch<{ token?: string; detail?: string }>(
        "/auth/choose-tier",
        {
          method: "POST",
          body: JSON.stringify({ tier: nextTier, confirmDowngrade }),
        },
      )

      if (res.ok && res.data?.token) {
        localStorage.setItem("jwt_token", res.data.token)
        window.location.reload()
        return
      }

      if (res.status === 409 && !confirmDowngrade) {
        const msg =
          res.data?.detail ??
          "Downgrading will remove older trails to fit the free-tier limit. Continue?"
        setDowngradePrompt({ tier: nextTier, message: msg })
        return
      }

      setError(res.data?.detail ?? "Failed to update plan.")
      router.refresh()
    } finally {
      setUpdatingTier(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-dvh bg-background flex items-center justify-center text-muted-foreground">
        Loading your plan…
      </div>
    )
  }

  return (
    <>
      <div className="relative min-h-dvh bg-background">
        {/* DAG-Grid dot pattern */}
        <div
          className="pointer-events-none fixed inset-0 opacity-[0.03]"
          aria-hidden
          style={{
            backgroundImage:
              "radial-gradient(circle, var(--border) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />

        {/* Header */}
        <header className="relative flex items-center justify-between px-8 py-5">
          <Link
            href="/"
            className="flex items-center gap-2 font-label text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Papertrail
          </Link>
          <ThemeToggle />
        </header>

        {/* Hero */}
        <div className="relative mx-auto max-w-4xl px-8 pb-4 pt-12 text-center">
          <p className="font-label text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground/50">
            Plans & Pricing
          </p>
          <h1 className="mt-4 text-balance text-[clamp(2.5rem,5vw,3.75rem)] font-light italic leading-[1.1] tracking-tight text-foreground">
            Invest in your research
          </h1>
          <p className="mx-auto mt-5 max-w-md text-balance text-sm leading-relaxed text-muted-foreground">
            From solo exploration to full team collaboration — unlock deeper capabilities at every stage of your work.
          </p>
          <div className="mx-auto mt-8 w-12 border-t border-border/60" />
        </div>

        {error && (
          <div className="relative mx-auto mb-4 max-w-2xl px-8">
            <div className="border-l-2 border-destructive bg-destructive/5 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          </div>
        )}

        {/* Pricing Cards */}
        <div className="relative mx-auto grid max-w-5xl gap-0 px-8 pb-24 pt-10 md:grid-cols-3">
          {tiers.map((tier, idx) => {
            const isCurrent = tier.name.toLowerCase() === currentTier
            const isScholar = tier.accent === "scholar"
            const isLab = tier.accent === "lab"
            const isChooseable = !isCurrent && !isLab

            return (
              <div
                key={tier.name}
                className={cn(
                  "relative flex flex-col p-8 transition-all",
                  isScholar
                    ? "bg-card shadow-sm ring-1 ring-primary/15 z-10 md:-my-3 md:p-10"
                    : "bg-card/60",
                  idx === 0 && "md:border-r md:border-border/30",
                  idx === 2 && "md:border-l md:border-border/30",
                )}
              >
                {/* Badge */}
                {tier.badge && (
                  <div className="mb-6">
                    <span className="bg-primary px-2.5 py-1 font-label text-[10px] font-bold uppercase tracking-[0.1em] text-primary-foreground">
                      {tier.badge}
                    </span>
                  </div>
                )}

                {isCurrent && (
                  <div className="mb-6">
                    <span className="bg-primary/10 px-2.5 py-1 font-label text-[10px] font-bold uppercase tracking-[0.1em] text-primary">
                      Current Plan
                    </span>
                  </div>
                )}

                {!tier.badge && !isCurrent && <div className="mb-6 h-[22px]" />}

                {/* Name */}
                <div className="mb-5 flex items-center gap-3">
                  <div
                    className={cn(
                      "flex h-9 w-9 items-center justify-center",
                      isScholar
                        ? "bg-primary/10 text-primary"
                        : isLab
                          ? "bg-ochre/10 text-ochre"
                          : "bg-muted text-muted-foreground/60"
                    )}
                  >
                    <tier.icon className="h-4 w-4" />
                  </div>
                  <h2 className="font-label text-xs font-bold uppercase tracking-[0.1em] text-foreground/70">{tier.name}</h2>
                </div>

                {/* Price */}
                <div className="mb-1 flex items-baseline gap-1">
                  <span className="text-4xl font-light italic tracking-tight text-foreground">
                    {tier.price}
                  </span>
                  {tier.period && (
                    <span className="font-label text-xs text-muted-foreground/60">{tier.period}</span>
                  )}
                </div>
                <p className="mb-8 text-sm leading-relaxed text-muted-foreground">{tier.description}</p>

                {/* Features */}
                <ul className="mb-10 flex flex-1 flex-col gap-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5 text-[13px]">
                      <Check
                        className={cn(
                          "mt-0.5 h-3.5 w-3.5 shrink-0",
                          isScholar
                            ? "text-primary"
                            : isLab
                              ? "text-ochre"
                              : "text-muted-foreground/40"
                        )}
                      />
                      <span className="text-foreground/80">{feature}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <button
                  disabled={!isChooseable || updatingTier}
                  className={cn(
                    "w-full py-3 font-label text-xs font-bold uppercase tracking-[0.06em] transition-all",
                    tier.ctaStyle === "solid"
                      ? "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 active:scale-[0.98]"
                      : "border-b-2 border-border text-foreground/70 hover:border-primary/40 hover:text-foreground active:scale-[0.98]",
                    !isChooseable &&
                      "pointer-events-none cursor-default opacity-50 hover:bg-transparent active:scale-100"
                  )}
                  onClick={() => {
                    if (isChooseable) choosePlan(tier.name)
                  }}
                >
                  {isCurrent
                    ? "Current Plan"
                    : isLab
                      ? tier.cta
                      : updatingTier
                        ? "Choosing…"
                        : "Choose"}
                </button>
              </div>
            )
          })}
        </div>

        {/* Bottom feature highlights */}
        <div className="bg-muted/40">
          <div className="mx-auto grid max-w-4xl gap-10 px-8 py-20 sm:grid-cols-3">
            {[
              {
                icon: Brain,
                title: "AI-Powered",
                desc: "Smart paper recommendations and summaries powered by the latest models.",
              },
              {
                icon: Shield,
                title: "Secure & Private",
                desc: "Your reading data stays private. SOC 2 compliant infrastructure.",
              },
              {
                icon: BarChart3,
                title: "Research Analytics",
                desc: "Track your reading habits and discover knowledge gaps.",
              },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex flex-col items-center text-center">
                <div className="mb-4 flex h-10 w-10 items-center justify-center bg-primary/8">
                  <Icon className="h-5 w-5 text-primary/70" />
                </div>
                <h3 className="font-label text-[11px] font-bold uppercase tracking-[0.1em] text-foreground/70">{title}</h3>
                <p className="mt-2 max-w-[220px] text-[13px] leading-relaxed text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer / Contact */}
        <div className="mx-auto max-w-2xl px-8 py-16 text-center">
          <p className="text-sm italic text-muted-foreground">
            Questions?{" "}
            <a
              href="mailto:support@papertrail.app"
              className="not-italic font-medium text-primary underline-offset-4 hover:underline"
            >
              Reach out to our team
            </a>
            . We&apos;re happy to help you find the right plan.
          </p>
        </div>
      </div>
      <AlertDialog
        open={downgradePrompt !== null}
        onOpenChange={(open) => {
          if (!open) setDowngradePrompt(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Downgrade to Reader?</AlertDialogTitle>
            <AlertDialogDescription>
              {downgradePrompt?.message ??
                "Downgrading may remove older trails to meet the free-tier limit."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => {
                setError("Downgrade cancelled. You can delete trails manually and try again.")
                setDowngradePrompt(null)
              }}
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                const tier = downgradePrompt?.tier
                setDowngradePrompt(null)
                if (tier) {
                  void choosePlan(tier, true)
                }
              }}
            >
              Continue and delete oldest
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
