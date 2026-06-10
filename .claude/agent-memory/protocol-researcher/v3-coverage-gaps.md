---
name: v3-coverage-gaps
description: Audit findings — which v3 protocol surfaces the Django adapter's test suite leaves untested or unimplemented (as of 2026-05-30)
metadata:
  type: project
---

# v3 protocol test-coverage gaps (audit 2026-05-30)

Audit of `inertia/tests/` + `playwright_e2e/` against [[v3-protocol-surface]].

**Why:** asked to find what is MISSING from the test suite, not a general overview.
**How to apply:** these are protocol surfaces with no test or no implementation; revisit before claiming 100% v3 coverage.

**UPDATE 2026-06-10:** branch `feat/v3-protocol-completion` (35cbfa1 + 7475a91) implements the entire "Unimplemented" list below (rescuedProps, sharedProps, X-Inertia-Error-Bag, Precognition) with unit + E2E specs; wire conformance re-verified against laravel-precognition@2.0.0 and inertia client v3.3.1. The list is historical once that branch merges.

## Unimplemented in the library (spec features absent from source)
- `rescuedProps[]` page-object field + `defer(rescue=True)` deferred-prop rescue — no source, no test. Client defaults to [] so omission is benign, but the rescue feature is absent.
- `sharedProps[]` page-object field — `share()` exists but the key is never emitted; client uses it for instant-visit carry-over.
- `X-Inertia-Error-Bag` request header — never read; `errors_response`/`share(errors=)` do not namespace under a bag.
- Precognition (`Precognition`, `Precognition-Validate-Only` req; `Precognition`, `Precognition-Success` resp; 204/422) — fully absent.
- `Purpose: prefetch` request header — never read (likely fine; prefetch is client-driven and just re-runs the view).

## Implemented but UNTESTED protocol behavior
- 409 stale-version is NOT GET-gated: middleware `is_stale` fires for any method; spec says 409 only for GET (except a GET redirect after a mutation). No test pins method behavior. `is_stale_inertia_get` helper exists but is unused/untested.
- `X-Inertia-Version` numeric vs string equality, and the request-with-no-version-header path (defaults to server version → not stale). Partially covered (string match only).
- 302→303 conversion is only tested through the decorator/middleware happy path; a plain 301 redirect after PUT is not tested (middleware only converts 301/302 via is_redirect_request, and is_non_post_redirect requires the verb).
- `flash` reflash on 409 — middleware calls `messages.get_messages` to keep flash; the spec's "reflash on 409" behavior is only smoke-tested via force_refresh, not asserted.

## Divergences (lib vs spec) — intentional, documented in source
- scrollProps entries include a `reset` boolean; spec example shows only the 4 pagination keys. Lib comment cites Laravel PropsResolver. Verify against laravel-comparator before treating as a gap.
