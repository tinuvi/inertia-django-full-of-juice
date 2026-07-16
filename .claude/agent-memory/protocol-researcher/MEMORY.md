# Protocol Researcher Memory

Index of settled v3-protocol research for the inertia-django-full-of-juice adapter. Read this first.

## References
- [v3 protocol surface](v3-protocol-surface.md) — full header/page-object/status-code enumeration with spec + 3.x client citations.
- [validation errors](validation-errors.md) — errors prop (specified-but-optional), error bags, form.errors consumption, redirect/error-flash coupling; spec + 3.x client.
- [once props](once-props.md) — except-once header on EVERY request; reset rides Partial-Data; expiresAt = epoch ms; fresh is server-only; cached-value merge mechanics.
- [precognition](precognition.md) — full wire contract: laravel-precognition v2 transport (no X-Inertia), Precognition/Validate-Only req headers, mandatory Precognition resp header (throws if absent), 204+Precognition-Success / 422 {message,errors}.
- [flash / sharedProps / rescuedProps](flash-shared-rescued.md) — shape, lifecycle, consumers, absence tolerance (`?? {}` / `?? []`), versions: flash+sharedProps v3.0.0, rescuedProps v3.1.0. Protocol page omits `flash` from its field table (doc gap).
- [location event / versionChange](location-event-version-change.md) — v3.6.0+: server echoes CURRENT `X-Inertia-Version` on the mismatch-409 ONLY (still undocumented 2026-07-16); gates async suppression + event detail truthfulness; prefetch is exempt (fetch-time short-circuit).

## Project findings
- [v3 coverage gaps](v3-coverage-gaps.md) — what the test suite leaves untested or the library leaves unimplemented (audit 2026-05-30).
