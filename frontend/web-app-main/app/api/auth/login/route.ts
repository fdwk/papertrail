import { NextRequest, NextResponse } from "next/server"
import { findUser, createToken } from "@/lib/mock-auth"

export async function POST(req: NextRequest) {
  const { email, password } = await req.json()

  if (!email || !password) {
    return NextResponse.json({ message: "Email and password are required." }, { status: 400 })
  }

  const user = findUser(email, password)

  if (!user) {
    return NextResponse.json({ message: "Invalid email or password." }, { status: 401 })
  }

  const token = createToken(user.email)
  return NextResponse.json({ token })
}

