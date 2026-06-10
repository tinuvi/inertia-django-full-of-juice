---
name: divergence-v3-completion-accepted
description: Accepted divergences from the 0.5.0 v3-completion review (flash/errors/precognition/rescued/shared) — don't re-flag these surfaces
metadata:
  type: project
---

Reviewed 2026-06-10 (`feat/v3-protocol-completion`, 5 commits). These divergences are intentional, documented (CHANGELOG 0.5.0 + commit 35cbfa1 body with Laravel citations), and client-safe. Do not re-flag the surface choices; still review edge-case correctness.

1. **Single error bag.** Django stores `_inertia_errors` as one flat dict (no ViewErrorBag); nests under `X-Inertia-Error-Bag` whenever the header is present. Equivalent to Laravel's `resolveValidationErrors` pipe under single-bag storage (Laravel's `has('default') && header` is always true when Django errors exist). Named-bag (`validateWithBag`) emission is unreachable by construction.
2. **`back()` validates the Referer** with `url_has_allowed_host_and_scheme` + `fallback`; Laravel's `Redirector::back` trusts its previous-URL/referrer. Security-positive, adapter API only.
3. **`sharedProps` excludes the auto-injected `errors` prop.** Laravel lists it because its middleware *shares* errors; Django injects at build time. Client filters `k in current.props` and defaults `?? []` — no breakage; only effect is errors not carried to the instant-visit intermediate page (same as pre-0.5.0 reality).
4. **Flash/errors lifetime is pop-on-render**, not Laravel one-request flash aging. One-shot state survives interleaved non-Inertia requests and abandoned redirects until the next Inertia render (possible stale delivery — client tolerates, wholesale replace). README documents the survive-redirects half.
5. **409 stale-refresh restore is STRONGER than Laravel.** Django stashes pulled one-shot state (`_pulled_*` on the response) and `force_refresh` re-flashes it. Laravel's `onVersionChange` only does `$session->reflash()` (key lists) — it cannot restore `inertia.flash_data` already pulled by `resolveFlashData` during the discarded render, so upstream actually LOSES flash there despite the-protocol.mdx L480 promising adapters reflash it. Django honors the spec sentence; also restores errors/clearHistory/preserveFragment.
6. **Session key names** `_inertia_flash`/`_inertia_errors` vs Laravel `inertia.flash_data` (adapter-internal, cited in commit body).

**Why:** all six verified against `inertia-laravel@3.x` source + the 3.x client's tolerance paths during the 0.5.0 review; flagged-and-accepted there.
**How to apply:** treat as settled in future diffs touching these files. Open items from the same review live in [[open-gaps-v3-completion]].
