import { TrailsApp } from "@/components/trails-app"

const MOCK_TRAIL_IDS = ["trail-1", "trail-2", "trail-3"]

export function generateStaticParams() {
  return MOCK_TRAIL_IDS.map((trailId) => ({ trailId }))
}

export default function TrailPage() {
  return <TrailsApp />
}

