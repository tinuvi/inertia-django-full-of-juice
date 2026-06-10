# Compliance reviewer memory

## Reference SHA
- [Laravel/client reference points](reference_sha.md) — 3.x sources read for 0.4.0 SSR + 0.5.0 flash/errors/precognition/rescued/shared reviews (last 2026-06-10)

## Recurring accepted divergences
- [INERTIA_SSR_EXCLUDE regex vs glob](divergence_ssr_exclude.md) — Django re.search on request.path vs Laravel anchored glob; both divergences settled, don't re-flag the surface
- [0.5.0 v3-completion accepted set](divergence_v3_completion.md) — single error bag, back() referer guard, sharedProps minus errors, pop-lifetime flash/errors, stronger-than-Laravel 409 restore

## Open gaps
- [0.5.0 open findings](open_gaps_v3_completion.md) — mergeProps leaks for rescued props (untested combo); undocumented 400-vs-422 malformed precognitive body; NIT cluster
