"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { validateAuthEmail } from "@/lib/auth-validation"
import { backendFetch } from "@/lib/api-client"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { FileText, Mail, Loader2, AlertCircle, CheckCircle2 } from "lucide-react"

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [submitAttempted, setSubmitAttempted] = useState(false)
  const [emailBlurred, setEmailBlurred] = useState(false)

  const emailError = useMemo(() => validateAuthEmail(email), [email])
  const showEmailError = emailBlurred || submitAttempted
  const emailInvalid = showEmailError && emailError !== null

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitAttempted(true)
    setError(null)
    if (validateAuthEmail(email)) return

    setPending(true)
    const res = await backendFetch<{ message?: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email: email.trim() }),
    })
    setPending(false)

    if (res.ok && typeof (res.data as { message?: string })?.message === "string") {
      setSubmitted(true)
    } else {
      setError("Something went wrong. Please try again.")
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-4">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,var(--primary)_0%,transparent_50%)] opacity-[0.08]" />
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_100%,var(--primary)_0%,transparent_45%)] opacity-[0.05]" />

      <div className="relative z-10 flex w-full max-w-md flex-col items-center gap-10">
        <Link
          href="/"
          className="group flex items-center gap-3 transition-all duration-200 hover:scale-[1.02]"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-none bg-primary shadow-lg shadow-primary/20 transition-shadow group-hover:shadow-xl group-hover:shadow-primary/25">
            <FileText className="h-6 w-6 text-primary-foreground" />
          </div>
          <span className="font-heading text-2xl font-bold tracking-tight text-foreground">
            Papertrail
          </span>
        </Link>

        <Card className="w-full animate-fade-up border-border/50 bg-card/95 shadow-xl shadow-black/5 backdrop-blur-sm dark:shadow-black/20">
          <CardHeader className="items-center space-y-2 pb-2 text-center">
            <CardTitle className="font-heading text-2xl font-bold tracking-tight text-balance">
              Reset your password
            </CardTitle>
            <CardDescription className="text-balance text-muted-foreground/90">
              Enter your email and we will send you a link to choose a new password.
            </CardDescription>
          </CardHeader>

          <CardContent>
            {submitted ? (
              <div className="flex flex-col items-center gap-4 py-2 text-center">
                <CheckCircle2
                  className="h-12 w-12 text-emerald-600 dark:text-emerald-400"
                  aria-hidden
                />
                <p className="text-sm leading-relaxed text-foreground/90">
                  {successMessage ??
                    "If an account exists for this email, you will receive password reset instructions shortly."}
                </p>
                <Button asChild variant="outline" className="mt-2 rounded-none">
                  <Link href="/login">Back to sign in</Link>
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
                {error && (
                  <div className="flex items-start gap-2.5 rounded-none border border-destructive/30 bg-destructive/5 px-4 py-3.5 text-sm text-destructive animate-fade-in">
                    <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="flex flex-col gap-2">
                  <Label
                    htmlFor="forgot-email"
                    className="font-label text-sm font-medium text-foreground/90"
                  >
                    Email
                  </Label>
                  <div className="relative">
                    <Mail
                      className={cn(
                        "pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transition-colors",
                        showEmailError && emailInvalid
                          ? "text-destructive/80"
                          : "text-muted-foreground/60",
                      )}
                      aria-hidden
                    />
                    <Input
                      id="forgot-email"
                      type="email"
                      inputMode="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onBlur={() => setEmailBlurred(true)}
                      autoFocus
                      aria-invalid={emailInvalid}
                      aria-describedby={emailInvalid ? "forgot-email-error" : undefined}
                      className={cn(
                        "h-11 rounded-lg border-border/80 bg-background/50 pl-10 pr-3 transition-colors focus-visible:bg-background",
                        emailInvalid &&
                          "border-destructive/50 focus-visible:border-destructive focus-visible:ring-destructive/20",
                      )}
                    />
                  </div>
                  {emailInvalid && (
                    <p id="forgot-email-error" className="text-sm text-destructive animate-fade-in">
                      {emailError}
                    </p>
                  )}
                </div>

                <Button
                  type="submit"
                  size="lg"
                  disabled={pending}
                  className="mt-1 h-12 w-full rounded-none font-heading font-medium shadow-sm transition-all hover:shadow-md"
                >
                  {pending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Sending…</span>
                    </>
                  ) : (
                    "Send reset link"
                  )}
                </Button>
              </form>
            )}
          </CardContent>

          <CardFooter className="flex justify-center border-t border-border/50 pt-6">
            <p className="text-sm text-muted-foreground">
              Remember your password?{" "}
              <Link
                href="/login"
                className="font-medium text-primary underline-offset-4 transition-colors hover:text-primary/90 hover:underline"
              >
                Sign in
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
