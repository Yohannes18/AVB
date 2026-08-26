# Humanized SecureBank templates

These templates were restyled to feel more intentionally designed and less like a default AI-generated dashboard. The existing route names, form actions, Jinja variables, and page structure are preserved.

## Design direction

The visual language is a restrained dark banking console: a soot-toned background, raised charcoal surfaces, thin muted dividers, one lime accent, and warm editorial headings. Decorative emoji, excessive gradients, glassmorphism, neon glows, and over-rounded controls were removed or neutralized. The typography pairs DM Sans for interface copy with Newsreader for page headings and IBM Plex Mono for technical values.

## Required file

Keep `templates/human_ui.html` alongside the other templates. Every full page template includes it after its page-specific styles, so it must remain available to the Jinja template loader.

## QA

All 24 page templates passed Jinja syntax validation. A local Chromium smoke-test confirmed the computed palette, typography, cards, navigation, and representative dashboard layout.
