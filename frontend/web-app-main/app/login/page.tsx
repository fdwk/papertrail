import { Suspense } from "react"
import { AuthForm } from "@/components/auth-form"
import { LoginAuth } from "@/components/login-auth"

export const metadata = {
  title: "Sign in - Papertrail",
  description: "Sign in to your Papertrail account",
}

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthForm mode="login" />}>
      <LoginAuth />
    </Suspense>
  )
}
