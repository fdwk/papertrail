import jwt from "jsonwebtoken"

export interface MockUser {
  email: string
  password: string
}

const JWT_SECRET = process.env.AUTH_SECRET || "dev-secret-change-me"
const JWT_TTL_SECONDS = 60 * 60 * 24 * 7 // 7 days

export const mockUsers: MockUser[] = [
  {
    email: "demo@papertrail.dev",
    password: "password123",
  },
]

export function findUser(email: string, password: string): MockUser | undefined {
  return mockUsers.find((u) => u.email === email && u.password === password)
}

export function createUser(email: string, password: string): MockUser {
  const existing = mockUsers.find((u) => u.email === email)
  if (existing) {
    throw new Error("User already exists")
  }

  const user: MockUser = { email, password }
  mockUsers.push(user)
  return user
}

export function createToken(email: string): string {
  const payload = {
    email,
    exp: Math.floor(Date.now() / 1000) + JWT_TTL_SECONDS,
  }

  return jwt.sign(payload, JWT_SECRET)
}

