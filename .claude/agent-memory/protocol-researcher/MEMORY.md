# Protocol Researcher Memory

Index of settled v3-protocol research for the inertia-django-full-of-juice adapter. Read this first.

## References
- [v3 protocol surface](v3-protocol-surface.md) — full header/page-object/status-code enumeration with spec + 3.x client citations.
- [validation errors](validation-errors.md) — errors prop (specified-but-optional), error bags, form.errors consumption, redirect/error-flash coupling; spec + 3.x client.
- [once props](once-props.md) — except-once header on EVERY request; reset rides Partial-Data; expiresAt = epoch ms; fresh is server-only; cached-value merge mechanics.

## Project findings
- [v3 coverage gaps](v3-coverage-gaps.md) — what the test suite leaves untested or the library leaves unimplemented (audit 2026-05-30).
