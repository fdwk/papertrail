"use client"

import Link from "next/link"
import { Check, ArrowLeft, Sparkles, BookOpen, Users, Zap, Shield, BarChart3, Brain, Infinity, HeadphonesIcon } from "lucide-react"
import { ThemeToggle } from "@/components/theme-toggle"
import { cn } from "@/lib/utils"

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
  return (
    <div className="min-h-dvh bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Papertrail
        </Link>
        <ThemeToggle />
      </header>

      {/* Hero */}
      <div className="mx-auto max-w-4xl px-6 pb-6 pt-8 text-center">
        <div className="mx-auto mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
          <Zap className="h-6 w-6 text-primary" />
        </div>
        <h1 className="text-balance text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Choose your plan
        </h1>
        <p className="mx-auto mt-4 max-w-lg text-balance text-base text-muted-foreground">
          Unlock deeper research capabilities. From solo exploration to full team collaboration.
        </p>
      </div>

      {/* Pricing Cards */}
      <div className="mx-auto grid max-w-5xl gap-5 px-6 pb-20 pt-6 md:grid-cols-3">
        {tiers.map((tier) => {
          const isScholar = tier.accent === "scholar"
          const isLab = tier.accent === "lab"

          return (
            <div
              key={tier.name}
              className={cn(
                "relative flex flex-col rounded-2xl border p-6 transition-all",
                isScholar
                  ? "border-primary/40 bg-primary/[0.03] shadow-lg shadow-primary/5 ring-1 ring-primary/10"
                  : "border-border bg-card"
              )}
            >
              {/* Badge */}
              {tier.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground shadow-sm">
                    {tier.badge}
                  </span>
                </div>
              )}

              {/* Icon + Name */}
              <div className="mb-4 flex items-center gap-3">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-xl",
                    isScholar
                      ? "bg-primary/15 text-primary"
                      : isLab
                        ? "bg-violet-500/15 text-violet-500 dark:text-violet-400"
                        : "bg-muted text-muted-foreground"
                  )}
                >
                  <tier.icon className="h-5 w-5" />
                </div>
                <h2 className="text-lg font-bold text-foreground">{tier.name}</h2>
              </div>

              {/* Price */}
              <div className="mb-1 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold tracking-tight text-foreground">
                  {tier.price}
                </span>
                {tier.period && (
                  <span className="text-sm text-muted-foreground">{tier.period}</span>
                )}
              </div>
              <p className="mb-6 text-sm text-muted-foreground">{tier.description}</p>

              {/* Features */}
              <ul className="mb-8 flex flex-1 flex-col gap-2.5">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm">
                    <Check
                      className={cn(
                        "mt-0.5 h-4 w-4 shrink-0",
                        isScholar
                          ? "text-primary"
                          : isLab
                            ? "text-violet-500 dark:text-violet-400"
                            : "text-muted-foreground/60"
                      )}
                    />
                    <span className="text-foreground/90">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <button
                disabled={tier.disabled}
                className={cn(
                  "w-full rounded-xl py-3 text-sm font-semibold transition-all",
                  tier.ctaStyle === "solid"
                    ? "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 active:scale-[0.98]"
                    : "border border-border text-foreground hover:bg-accent active:scale-[0.98]",
                  tier.disabled && "cursor-default opacity-60 hover:bg-transparent active:scale-100"
                )}
              >
                {tier.cta}
              </button>
            </div>
          )
        })}
      </div>

      {/* Bottom feature highlights */}
      <div className="border-t border-border bg-card/40">
        <div className="mx-auto grid max-w-4xl gap-6 px-6 py-14 sm:grid-cols-3">
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
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">{title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ-style section */}
      <div className="mx-auto max-w-2xl px-6 py-14 text-center">
        <p className="text-sm text-muted-foreground">
          Questions?{" "}
          <a
            href="mailto:support@papertrail.app"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            Reach out to our team
          </a>
          . We&apos;re happy to help you find the right plan.
        </p>
      </div>
    </div>
  )
}
