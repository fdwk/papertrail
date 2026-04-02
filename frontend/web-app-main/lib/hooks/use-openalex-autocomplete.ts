"use client"

import { useEffect, useState } from "react"

const OPENALEX_AUTOCOMPLETE_BASE =
  "https://api.openalex.org/autocomplete/concepts"

const DEBOUNCE_MS = 300
const MIN_QUERY_LENGTH = 2
const MAX_RESULTS = 8

export interface AutocompleteSuggestion {
  id: string
  display_name: string
  hint: string | null
  cited_by_count: number
  entity_type: string
}

interface OpenAlexAutocompleteResponse {
  meta?: { count: number }
  results?: Array<{
    id: string
    display_name: string
    hint?: string | null
    cited_by_count?: number
    entity_type?: string
  }>
}

function getMailto(): string | undefined {
  const email = process.env.NEXT_PUBLIC_OPENALEX_EMAIL?.trim()
  return email && email.length > 0 ? email : undefined
}

export function useOpenAlexAutocomplete(query: string) {
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < MIN_QUERY_LENGTH) {
      setSuggestions([])
      setLoading(false)
      return
    }

    const controller = new AbortController()
    const timeoutId = window.setTimeout(async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams({ q: trimmed })
        const mailto = getMailto()
        if (mailto) {
          params.set("mailto", mailto)
        }
        const url = `${OPENALEX_AUTOCOMPLETE_BASE}?${params.toString()}`
        const res = await fetch(url, { signal: controller.signal })
        if (!res.ok) {
          setSuggestions([])
          return
        }
        const data = (await res.json()) as OpenAlexAutocompleteResponse
        const raw = data.results ?? []
        const mapped: AutocompleteSuggestion[] = raw
          .slice(0, MAX_RESULTS)
          .map((r) => ({
            id: r.id,
            display_name: r.display_name,
            hint: r.hint ?? null,
            cited_by_count: r.cited_by_count ?? 0,
            entity_type: r.entity_type ?? "concept",
          }))
        if (!controller.signal.aborted) {
          setSuggestions(mapped)
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") {
          return
        }
        if (!controller.signal.aborted) {
          setSuggestions([])
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }, DEBOUNCE_MS)

    return () => {
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [query])

  return { suggestions, loading }
}
