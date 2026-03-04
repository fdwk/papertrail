import { AuthForm } from "@/components/auth-form"

export const metadata = {
  title: "Sign in - Papertrail",
  description: "Sign in to your Papertrail account",
}

export default function LoginPage() {
  return <AuthForm mode="login" />
}
