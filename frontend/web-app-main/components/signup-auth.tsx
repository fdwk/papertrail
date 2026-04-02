"use client"

import { useSearchParams } from "next/navigation"
import { AuthForm } from "@/components/auth-form"

export function SignupAuth() {
  const sp = useSearchParams()
  const oauthErrorFromUrl = sp.get("oauth_error")
  return <AuthForm mode="signup" oauthErrorFromUrl={oauthErrorFromUrl} />
}
