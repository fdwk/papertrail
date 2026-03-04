/**
 * Lightweight fetch wrapper that auto-attaches the JWT Bearer token.
 *
 * Change API_BASE to point at your real backend when ready.
 */

const API_BASE = "/api/auth"

export interface ApiResponse<T = unknown> {
  ok: boolean
  status: number
  data: T
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("jwt_token") : null

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  let data: T
  try {
    data = await res.json()
  } catch {
    data = {} as T
  }

  return { ok: res.ok, status: res.status, data }
}
