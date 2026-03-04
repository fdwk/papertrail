"use client"

import React, { createContext, useContext, useState, useEffect, useCallback } from "react"
import { backendFetch } from "@/lib/api-client"

export interface AuthUser {
  email: string
}

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>
  signup: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function decodePayload(token: string): { email?: string; exp?: number } | null {
  try {
    const base64 = token.split(".")[1]
    return JSON.parse(atob(base64))
  } catch {
    return null
  }
}

function isTokenExpired(token: string): boolean {
  const payload = decodePayload(token)
  if (!payload?.exp) return false
  return Date.now() >= payload.exp * 1000
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Hydrate from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem("jwt_token")
    if (token && !isTokenExpired(token)) {
      const payload = decodePayload(token)
      if (payload?.email) {
        setUser({ email: payload.email })
      }
    } else if (token) {
      // Expired token -- clean up
      localStorage.removeItem("jwt_token")
    }
    setIsLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await backendFetch<{ token?: string; detail?: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })

    if (res.ok && res.data.token) {
      localStorage.setItem("jwt_token", res.data.token)
      const payload = decodePayload(res.data.token)
      setUser({ email: payload?.email ?? email })
      return { ok: true }
    }

    const msg = (res.data as { detail?: string }).detail
    return { ok: false, error: msg ?? "Login failed. Please try again." }
  }, [])

  const signup = useCallback(async (email: string, password: string) => {
    const res = await backendFetch<{ token?: string; detail?: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })

    if (res.ok && res.data.token) {
      localStorage.setItem("jwt_token", res.data.token)
      const payload = decodePayload(res.data.token)
      setUser({ email: payload?.email ?? email })
      return { ok: true }
    }

    const msg = (res.data as { detail?: string }).detail
    return { ok: false, error: msg ?? "Signup failed. Please try again." }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("jwt_token")
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider")
  return ctx
}
