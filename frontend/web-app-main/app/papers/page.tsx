import { Suspense } from "react"
import { PapersPage } from "@/components/papers-page"

export default function PapersRoutePage() {
  return (
    <Suspense fallback={<div className="flex h-dvh items-center justify-center bg-background" />}>
      <PapersPage />
    </Suspense>
  )
}

