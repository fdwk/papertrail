import { TrailsApp } from "@/components/trails-app"
import { staticTrails } from "@/lib/static-data"

export function generateStaticParams() {
  return staticTrails.map((trail) => ({
    trailId: trail.id,
  }))
}

export default function TrailPage() {
  return <TrailsApp />
}

