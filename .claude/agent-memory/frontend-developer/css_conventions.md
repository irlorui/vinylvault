---
name: CSS conventions and design tokens
description: Color palette, shared utility classes, animation patterns, and accessibility rules in styles.css
type: project
---

## Color palette (hardcoded, no CSS custom properties yet)
- Background: `#0d0d0d` + radial gradient `rgba(80,5,35,0.65)`
- Primary text: `#f0f0f0`
- Accent / lime: `#b4ff00` — used for score pips, REVEAL button, WIN card background, START button, focus rings
- Pink: `#f0187a` — logo accent, hero headline
- Muted text: `#555` (labels), `#999` (subtitle), `#777` (config label)
- Card cream: `#e9e5dc` with `#b0a898` border — staging and pending cards
- 10 placed-card colors: `.placed-card-0` through `.placed-card-9` (neon blue, purple, orange, pink, mint, cyan, yellow, teal, red, coral)

## Shared utility classes
- `.hidden` — `display: none !important`, toggled heavily by JS
- `.score-label` and `.topbar-label` — merged into a single selector block (identical rules: 0.65rem, 700, 0.18em spacing, #555, uppercase)

## Focus styles
- `#device-select:focus` — lime border + rgba(180,255,0,0.3) box-shadow, no default outline
- `#win-score-select:focus` — lime box-shadow, no default outline
- `#player-name-input:focus` — lime `border-bottom-color`, no default outline (compensated by underline pattern)
- All other interactive elements: default browser outline (not overridden)

## Animations
- `shake`, `fade-out`, `pop-in`, `fade-in` — used on wrong-card, win screen, placed cards
- All animations must be wrapped: `@media (prefers-reduced-motion: reduce)` block at end of file sets duration to 0.01ms
- Pending card border is `dashed`, not `solid` — intentional mystery-card aesthetic

## Missing (not yet implemented)
- No CSS custom properties / design tokens — all colors are hardcoded literals
- No mobile breakpoints / responsive layout beyond `clamp()` for hero text
