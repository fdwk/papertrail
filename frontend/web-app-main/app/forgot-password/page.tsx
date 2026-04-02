import { ForgotPasswordForm } from "@/components/forgot-password-form"

export const metadata = {
  title: "Reset password - Papertrail",
  description: "Request a link to reset your Papertrail password",
}

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />
}
