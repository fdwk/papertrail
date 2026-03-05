import { Suspense } from "react"
import { TrailsApp } from "@/components/trails-app"

export default function HomePage() {
  return (
    <Suspense fallback={<div className="flex h-dvh items-center justify-center bg-background" />}>
      <TrailsApp />
    </Suspense>
  )
}
