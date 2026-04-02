"use client"

import { useSearchParams } from "next/navigation"
import { AuthForm } from "@/components/auth-form"

export function LoginAuth() {
  const sp = useSearchParams()
  const passwordResetSuccess = sp.get("reset") === "1"
  return <AuthForm mode="login" passwordResetSuccess={passwordResetSuccess} />
}
