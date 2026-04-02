"use client"

import { Suspense, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Loader2 } from "lucide-react"

function OAuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { loginWithToken } = useAuth()

  useEffect(() => {
    const token = searchParams.get("token")
    const err = searchParams.get("error")
    if (err) {
      router.replace(`/login?oauth_error=${encodeURIComponent(err)}`)
      return
    }
    if (token) {
      loginWithToken(token)
      router.replace("/")
      return
    }
    router.replace(
      `/login?oauth_error=${encodeURIComponent("Missing sign-in token.")}`,
    )
  }, [searchParams, router, loginWithToken])

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-4">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,var(--primary)_0%,transparent_50%)] opacity-[0.08]" />
      <Loader2
        className="relative z-10 h-8 w-8 animate-spin text-muted-foreground"
        aria-label="Completing sign-in"
      />
    </div>
  )
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  )
}
