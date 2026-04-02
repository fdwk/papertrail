"use client"

import { useSearchParams } from "next/navigation"
import { AuthForm } from "@/components/auth-form"

export function LoginAuth() {
  const sp = useSearchParams()
  const passwordResetSuccess = sp.get("reset") === "1"
  const oauthErrorFromUrl = sp.get("oauth_error")
  return (
    <AuthForm
      mode="login"
      passwordResetSuccess={passwordResetSuccess}
      oauthErrorFromUrl={oauthErrorFromUrl}
    />
  )
}
