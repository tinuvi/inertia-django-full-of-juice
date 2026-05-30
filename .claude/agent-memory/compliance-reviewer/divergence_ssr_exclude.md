---
name: divergence-ssr-exclude-regex-vs-glob
description: Accepted divergence — INERTIA_SSR_EXCLUDE uses re.search on request.path vs Laravel's anchored glob on full URL + slash-trimmed path
metadata:
  type: project
---

`INERTIA_SSR_EXCLUDE` (Django adapter, added in `[0.4.0]`, 2026-05-30) intentionally diverges from Laravel's SSR path exclusion. Do not re-flag the surface choice on future reviews; do still review correctness of individual patterns/edge cases.

Accepted divergences:
1. **regex vs glob.** Django: `re.search(pattern, request.path)` (unanchored). Laravel: `Str::is` glob, whole-string anchored, against full URL AND slash-trimmed path. Justification: mirrors Django's own `SECURE_REDIRECT_EXEMPT` idiom in `SecurityMiddleware` (compile-once + `.search()`). Native-to-Django choice — accepted.
2. **settings vs code.** Django: `INERTIA_SSR_EXCLUDE` Django setting. Laravel: `Inertia::withoutSsr()` helper + middleware `$except`, kept out of `config/inertia.php`. Accepted.

**Why:** v3 spec does not define SSR exclusion at the wire level (it is an adapter/SSR-doc feature, not in the protocol .md). So any matching strategy is spec-compliant as long as the observable wire result of an excluded route == client-side-only inline-JSON shell with no POST to the SSR server. Confirmed that is what the Django port produces.

**How to apply:** Treat both divergences as settled. The remaining review surface is correctness of the matching itself: anchoring (`re.search` is unanchored, so a bare `props` pattern matches any path containing it — documented + tested), leading-slash semantics (Django keeps the leading slash on `request.path`; Laravel strips it — so patterns are NOT portable between the two adapters; users porting Laravel `withoutSsr('admin/*')` must rewrite as `r'^/admin/'`), and invalid-regex handling (an invalid pattern raises `re.error` at request time inside `_compiled_ssr_exclude`, surfacing as a 500 — no graceful handling, matching the team's other settings which also trust developer input).

See [[reference-sha]].
