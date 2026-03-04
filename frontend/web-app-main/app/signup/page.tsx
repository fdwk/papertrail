import { AuthForm } from "@/components/auth-form"

export const metadata = {
  title: "Sign up - Papertrail",
  description: "Create a Papertrail account",
}

export default function SignupPage() {
  return <AuthForm mode="signup" />
}
