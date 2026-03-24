# Oxford Monograph Design System

### 1. Overview & Creative North Star
**Creative North Star: The Digital Archivist**
Oxford Monograph is a design system built for the intersection of classical scholarship and modern data science. It rejects the "app-like" fluidity of modern SaaS in favor of the structured, intentional gravity of an academic journal. The system prioritizes high-contrast serif typography and a rigorous "No-Line" architectural philosophy.

Through intentional asymmetry—such as offset grid layouts and varied column widths—the system mimics the feel of a meticulously typeset book. It is designed to feel authoritative, archival, and enduring.

### 2. Colors
The palette is rooted in "Ink on Vellum"—deep Navies (#002147) and Ochre (#745a2b) set against a warmth-calibrated neutral base (#fafaf5).

*   **The "No-Line" Rule:** Structural separation must be achieved through background shifts (e.g., transitioning from `surface` to `surface_container_low`) rather than 1px borders. If a boundary is strictly required for accessibility, use `outline_variant` at 10% opacity.
*   **Surface Hierarchy:**
    *   **Lowest (#ffffff):** Used for elevated cards and primary input fields.
    *   **Low (#f4f4ef):** The standard background for secondary content sections.
    *   **High/Highest (#e8e8e3):** Used for interactive wells and toggle backgrounds.
*   **Signature Textures:** A subtle "DAG-Grid" (radial dot pattern) should be applied to hero backgrounds at 3% opacity to suggest a mathematical foundation.

### 3. Typography
Oxford Monograph uses a tri-font system to establish a scholarly rhythm:
*   **Headlines (Manrope):** A modern sans-serif used sparingly for navigation and section headers to provide a contemporary edge.
*   **Body & Display (Newsreader):** The heart of the system. Large display sizes (up to 8xl / 6rem) should always use the Italic variant to convey a "written" feel.
*   **Labels (Inter):** High-legibility sans-serif for technical data, metadata, and microscopic UI elements.

**Measured Scale:**
*   **Display:** 3rem to 6rem (Newsreader Italic).
*   **Section Headers:** 1.5rem (Manrope Extrabold, All Caps).
*   **Body Large:** 1.25rem / 1.125rem (Newsreader).
*   **Micro-Labels:** 9px - 11px (Inter Bold, Tracking 0.1em).

### 4. Elevation & Depth
Depth is created through "Tonal Layering" rather than traditional drop shadows. 

*   **The Layering Principle:** Elements gain prominence by moving to lighter surfaces. A card on a `surface_container_low` background should be `surface_container_lowest`.
*   **Ambient Shadows:** Use the `shadow-sm` profile exclusively. This is an ultra-diffused, low-opacity shadow that suggests the element is barely hovering above the page.
*   **Glassmorphism:** Navigation bars use a 95% opacity blur to maintain a sense of content continuity as the user scrolls through long-form research.

### 5. Components
*   **Buttons:** Rectangular (0px radius). Primary buttons use `primary` fill with `on_primary` text. Secondary buttons are text-only with a 2px bottom border in `secondary`.
*   **Inputs:** Underlined style only. No full enclosures. Uses a 2px `outline` that intensifies on focus.
*   **Cards:** Rigid 90-degree corners. Content should be padded deeply (32px+) to maintain an editorial feel.
*   **Trail Depth Toggles:** Use `surface_container` wells where the active state is marked by a `surface_container_lowest` "raised" tile.

### 6. Do's and Don'ts
*   **Do:** Use Newsreader Italic for any text meant to feel "exploratory" or "academic."
*   **Do:** Embrace whitespace. Layouts should feel like they have room to breathe, resembling a well-margined manuscript.
*   **Don't:** Use rounded corners. Every element must be sharp and architectural.
*   **Don't:** Use vibrant primary colors. Stick to the muted, archival tones of the defined palette to maintain the "Archivist" persona.
*   **Do:** Use `secondary` (Ochre) as a "highlighter" color for active states and critical academic calls-to-action.