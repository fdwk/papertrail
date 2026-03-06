/**
 * Auth: Next.js routes at /api/auth. Backend (FastAPI): use backendFetch with NEXT_PUBLIC_API_BASE.
 */

const AUTH_API_BASE = "/api/auth"
const BACKEND_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000"

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

  const res = await fetch(`${AUTH_API_BASE}${path}`, {
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

/** Calls FastAPI backend. Attaches JWT if present. Never throws; returns ok: false on network error. */
export async function backendFetch<T = unknown>(
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

  let res: Response
  try {
    res = await fetch(`${BACKEND_API_BASE}${path}`, {
      ...options,
      headers,
    })
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: { message: "Failed to fetch" } as T,
    }
  }

  let data: T
  try {
    data = await res.json()
  } catch {
    data = {} as T
  }

  return { ok: res.ok, status: res.status, data }
}
