"use client"

import { useMemo, useState, Suspense } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import {
  validateSignupPassword,
  getSignupPasswordRules,
  PASSWORD_MAX,
  PASSWORD_MIN_SIGNUP,
} from "@/lib/auth-validation"
import { backendFetch } from "@/lib/api-client"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  FileText,
  Eye,
  EyeOff,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Circle,
  Info,
} from "lucide-react"

function RuleRow({ met, label }: { met: boolean; label: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 text-sm transition-colors duration-200",
        met ? "text-emerald-700 dark:text-emerald-400" : "text-muted-foreground",
      )}
    >
      {met ? (
        <CheckCircle2
          className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400"
          aria-hidden
        />
      ) : (
        <Circle className="h-4 w-4 shrink-0 opacity-35" strokeWidth={1.5} aria-hidden />
      )}
      <span>{label}</span>
    </div>
  )
}

function parseDetail(data: unknown): string | undefined {
  const d = data as { detail?: string | { msg?: string }[] }
  if (typeof d.detail === "string") return d.detail
  if (Array.isArray(d.detail) && d.detail[0]?.msg) return String(d.detail[0].msg)
  return undefined
}

function ResetPasswordFormInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get("token")?.trim() ?? ""

  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [submitAttempted, setSubmitAttempted] = useState(false)
  const [passwordBlurred, setPasswordBlurred] = useState(false)
  const [confirmBlurred, setConfirmBlurred] = useState(false)
  const [passwordRulesOpen, setPasswordRulesOpen] = useState(false)

  const passwordError = useMemo(() => validateSignupPassword(password), [password])
  const confirmMismatch =
    confirm.length > 0 && confirm !== password ? "Passwords do not match." : null
  const showPasswordError = passwordBlurred || submitAttempted
  const showConfirmError = confirmBlurred || submitAttempted
  const passwordInvalid = showPasswordError && passwordError !== null
  const confirmInvalid = showConfirmError && (confirmMismatch !== null || !confirm)

  const signupRules = useMemo(() => getSignupPasswordRules(password), [password])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitAttempted(true)
    setError(null)

    const pErr = validateSignupPassword(password)
    if (!token) {
      setError("This reset link is missing or invalid.")
      return
    }
    if (pErr || !confirm) {
      return
    }
    if (confirm !== password) {
      return
    }

    setPending(true)
    const res = await backendFetch<{ message?: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    })
    setPending(false)

    if (res.ok) {
      router.push("/login?reset=1")
    } else {
      setError(parseDetail(res.data) ?? "Could not reset password. Please request a new link.")
    }
  }

  const missingToken = !token

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
              Choose a new password
            </CardTitle>
            <CardDescription className="text-balance text-muted-foreground/90">
              Enter a new password for your account.
            </CardDescription>
          </CardHeader>

          <CardContent>
            {missingToken ? (
              <div className="flex flex-col gap-4 py-2">
                <div className="flex items-start gap-2.5 rounded-none border border-destructive/30 bg-destructive/5 px-4 py-3.5 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>
                    This reset link is missing or invalid. Request a new link from the sign-in page.
                  </span>
                </div>
                <Button asChild className="rounded-none">
                  <Link href="/forgot-password">Request reset link</Link>
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
                  <div className="flex items-center justify-between gap-2">
                    <Label
                      htmlFor="new-password"
                      className="font-label text-sm font-medium text-foreground/90"
                    >
                      New password
                    </Label>
                    <Popover
                      open={passwordRulesOpen}
                      onOpenChange={setPasswordRulesOpen}
                      modal={false}
                    >
                      <PopoverTrigger asChild>
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/10 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          aria-label="View password requirements"
                        >
                          <Info className="h-3.5 w-3.5" aria-hidden />
                          Requirements
                        </button>
                      </PopoverTrigger>
                      <PopoverContent
                        side="right"
                        align="start"
                        sideOffset={8}
                        className="w-72 border-border/60 bg-popover/95 p-4 shadow-lg backdrop-blur-sm"
                      >
                        <p className="mb-3 font-label text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          Password rules
                        </p>
                        <div className="space-y-2.5">
                          <RuleRow
                            met={signupRules.minLen}
                            label={`At least ${PASSWORD_MIN_SIGNUP} characters`}
                          />
                          <RuleRow met={signupRules.hasUpper} label="One uppercase letter" />
                          <RuleRow met={signupRules.hasLower} label="One lowercase letter" />
                          <RuleRow met={signupRules.hasDigit} label="One number" />
                        </div>
                      </PopoverContent>
                    </Popover>
                  </div>
                  <div className="relative">
                    <Input
                      id="new-password"
                      type={showPassword ? "text" : "password"}
                      placeholder="Create a password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onFocus={() => setPasswordRulesOpen(true)}
                      onBlur={() => setPasswordBlurred(true)}
                      autoComplete="new-password"
                      maxLength={PASSWORD_MAX}
                      aria-invalid={passwordInvalid}
                      aria-describedby={passwordInvalid ? "new-password-error" : undefined}
                      className={cn(
                        "h-11 rounded-lg border-border/80 bg-background/50 pr-11 transition-colors focus-visible:bg-background",
                        passwordInvalid &&
                          "border-destructive/50 focus-visible:border-destructive focus-visible:ring-destructive/20",
                      )}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-none p-1.5 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? (
                        <Eye className="h-4 w-4" />
                      ) : (
                        <EyeOff className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  {passwordInvalid && (
                    <p id="new-password-error" className="text-sm text-destructive animate-fade-in">
                      {passwordError}
                    </p>
                  )}
                </div>

                <div className="flex flex-col gap-2">
                  <Label
                    htmlFor="confirm-password"
                    className="font-label text-sm font-medium text-foreground/90"
                  >
                    Confirm password
                  </Label>
                  <div className="relative">
                    <Input
                      id="confirm-password"
                      type={showConfirm ? "text" : "password"}
                      placeholder="Confirm your password"
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      onBlur={() => setConfirmBlurred(true)}
                      autoComplete="new-password"
                      maxLength={PASSWORD_MAX}
                      aria-invalid={Boolean(confirmInvalid)}
                      aria-describedby={confirmInvalid ? "confirm-password-error" : undefined}
                      className={cn(
                        "h-11 rounded-lg border-border/80 bg-background/50 pr-11 transition-colors focus-visible:bg-background",
                        confirmInvalid &&
                          "border-destructive/50 focus-visible:border-destructive focus-visible:ring-destructive/20",
                      )}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(!showConfirm)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 rounded-none p-1.5 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                      aria-label={showConfirm ? "Hide password" : "Show password"}
                    >
                      {showConfirm ? (
                        <Eye className="h-4 w-4" />
                      ) : (
                        <EyeOff className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  {showConfirmError && confirmMismatch && (
                    <p id="confirm-password-error" className="text-sm text-destructive animate-fade-in">
                      {confirmMismatch}
                    </p>
                  )}
                  {showConfirmError && !confirm && !confirmMismatch && (
                    <p className="text-sm text-destructive animate-fade-in">Confirm your password.</p>
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
                      <span>Updating…</span>
                    </>
                  ) : (
                    "Update password"
                  )}
                </Button>
              </form>
            )}
          </CardContent>

          <CardFooter className="flex justify-center border-t border-border/50 pt-6">
            <p className="text-sm text-muted-foreground">
              <Link
                href="/login"
                className="font-medium text-primary underline-offset-4 transition-colors hover:text-primary/90 hover:underline"
              >
                Back to sign in
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

export function ResetPasswordForm() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-label="Loading" />
        </div>
      }
    >
      <ResetPasswordFormInner />
    </Suspense>
  )
}
