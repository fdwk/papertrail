import { NextRequest, NextResponse } from "next/server"
import { createUser, createToken } from "@/lib/mock-auth"

export async function POST(req: NextRequest) {
  const { email, password } = await req.json()

  if (!email || !password) {
    return NextResponse.json({ message: "Email and password are required." }, { status: 400 })
  }

  try {
    const user = createUser(email, password)
    const token = createToken(user.email)
    return NextResponse.json({ token })
  } catch (err) {
    return NextResponse.json({ message: "User already exists." }, { status: 400 })
  }
}

