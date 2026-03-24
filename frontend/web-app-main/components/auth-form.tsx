"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
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
import { FileText, Eye, EyeOff, AlertCircle, Loader2 } from "lucide-react"

interface AuthFormProps {
  mode: "login" | "signup"
}

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter()
  const { login, signup } = useAuth()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const isLogin = mode === "login"
  const title = isLogin ? "Welcome back" : "Create your account"
  const description = isLogin
    ? "Sign in to continue your learning trails"
    : "Start building structured learning paths today"
  const submitLabel = isLogin ? "Sign in" : "Create account"
  const altText = isLogin ? "Don't have an account?" : "Already have an account?"
  const altLink = isLogin ? "/signup" : "/login"
  const altLabel = isLogin ? "Sign up" : "Sign in"

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setPending(true)

    const result = isLogin
      ? await login(email, password)
      : await signup(email, password)

    setPending(false)

    if (result.ok) {
      router.push("/")
    } else {
      setError(result.error ?? "Something went wrong.")
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-4">
      {/* Layered gradient background */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,var(--primary)_0%,transparent_50%)] opacity-[0.08]" />
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_100%,var(--primary)_0%,transparent_45%)] opacity-[0.05]" />
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_50%_30%_at_20%_80%,var(--primary)_0%,transparent_50%)] opacity-[0.04]" />
      {/* Subtle grid overlay */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.015]"
        style={{
          backgroundImage: `linear-gradient(var(--border)_1px,transparent_1px),linear-gradient(90deg,var(--border)_1px,transparent_1px)`,
          backgroundSize: "48px 48px",
        }}
      />

      <div className="relative z-10 flex w-full max-w-md flex-col items-center gap-10">
        {/* Logo / brand */}
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

        {/* Auth card */}
        <Card className="w-full animate-fade-up border-border/50 bg-card/95 shadow-xl shadow-black/5 backdrop-blur-sm dark:shadow-black/20">
          <CardHeader className="items-center space-y-2 pb-2 text-center">
            <CardTitle className="font-heading text-2xl font-bold tracking-tight text-balance">
              {title}
            </CardTitle>
            <CardDescription className="text-balance text-muted-foreground/90">
              {description}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              {/* Error banner */}
              {error && (
                <div className="flex items-start gap-2.5 rounded-none border border-destructive/30 bg-destructive/5 px-4 py-3.5 text-sm text-destructive animate-fade-in">
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Email */}
              <div className="flex flex-col gap-2">
                <Label htmlFor="email" className="font-label text-sm font-medium text-foreground/90">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  autoFocus
                  className="h-11 rounded-lg border-border/80 bg-background/50 transition-colors focus-visible:bg-background"
                />
              </div>

              {/* Password */}
              <div className="flex flex-col gap-2">
                <Label htmlFor="password" className="font-label text-sm font-medium text-foreground/90">
                  Password
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder={isLogin ? "Enter your password" : "Create a password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    autoComplete={isLogin ? "current-password" : "new-password"}
                    className="h-11 rounded-lg border-border/80 bg-background/50 pr-11 transition-colors focus-visible:bg-background"
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
              </div>

              {/* Submit */}
              <Button
                type="submit"
                size="lg"
                disabled={pending}
                className="mt-1 h-12 w-full rounded-none font-heading font-medium shadow-sm transition-all hover:shadow-md"
              >
                {pending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>{isLogin ? "Signing in..." : "Creating account..."}</span>
                  </>
                ) : (
                  submitLabel
                )}
              </Button>
            </form>
          </CardContent>

          <CardFooter className="flex justify-center border-t border-border/50 pt-6">
            <p className="text-sm text-muted-foreground">
              {altText}{" "}
              <Link
                href={altLink}
                className="font-medium text-primary underline-offset-4 transition-colors hover:text-primary/90 hover:underline"
              >
                {altLabel}
              </Link>
            </p>
          </CardFooter>
        </Card>

        {/* Footer note */}
        <p className="text-center font-label text-xs text-muted-foreground/70 leading-relaxed max-w-sm">
          By continuing, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  )
}
