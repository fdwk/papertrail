/**
 * Client-side auth validation.
 * Login: allow any stored password length (legacy-friendly); max length only.
 * Signup: matches backend SignupBody — 8+ chars, lowercase, uppercase, and a number.
 */

export const PASSWORD_MIN_SIGNUP = 8
export const PASSWORD_MAX = 256

// Practical RFC 5322–inspired pattern without being overly strict
const EMAIL_RE =
  /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/

export function validateAuthEmail(email: string): string | null {
  const t = email.trim()
  if (!t) return "Enter your email address."
  if (!EMAIL_RE.test(t)) return "Enter a valid email address."
  return null
}

/** Login / existing accounts: do not enforce complexity */
export function validateLoginPassword(password: string): string | null {
  if (!password) return "Enter your password."
  if (password.length > PASSWORD_MAX) {
    return `Use at most ${PASSWORD_MAX} characters.`
  }
  return null
}

/** New signups — keep in sync with backend SignupBody */
export function validateSignupPassword(password: string): string | null {
  if (password.length < PASSWORD_MIN_SIGNUP) {
    return `Use at least ${PASSWORD_MIN_SIGNUP} characters.`
  }
  if (password.length > PASSWORD_MAX) {
    return `Use at most ${PASSWORD_MAX} characters.`
  }
  if (!/[a-z]/.test(password)) {
    return "Include a lowercase letter."
  }
  if (!/[A-Z]/.test(password)) {
    return "Include an uppercase letter."
  }
  if (!/\d/.test(password)) {
    return "Include a number."
  }
  return null
}

/** Live rule state for signup password UI (popover checklist) */
export function getSignupPasswordRules(password: string) {
  return {
    minLen: password.length >= PASSWORD_MIN_SIGNUP,
    hasLower: /[a-z]/.test(password),
    hasUpper: /[A-Z]/.test(password),
    hasDigit: /\d/.test(password),
  }
}
