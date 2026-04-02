import { Suspense } from "react"
import { AuthForm } from "@/components/auth-form"

export const metadata = {
  title: "Sign up - Papertrail",
  description: "Create a Papertrail account",
}

export default function SignupPage() {
  return (
    <Suspense fallback={<AuthForm mode="signup" />}>
      <AuthForm mode="signup" />
    </Suspense>
  )
}
