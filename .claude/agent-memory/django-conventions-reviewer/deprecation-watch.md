---
name: deprecation-watch
description: Django main-branch deprecations relevant to this repo's header/test-client APIs — none pending as of 2026-07-16
metadata:
  type: reference
---

Checked django/django `main` on 2026-07-16 (response.py last commit 2026-06-10):

- `RemovedInDjango71Warning` in `django/http/response.py` (main L23 import, L760-L774) is ONLY the `JsonResponse(safe=...)` parameter deprecation. Nothing header-related.
- No `RemovedInDjango*` markers in `django/test/client.py` on main — legacy `HTTP_*` extra kwargs on the test client are not deprecated and not heading toward deprecation.
- `response[...]` / `response.headers[...]` write spellings: both alive on main; `HttpResponseBase.__setitem__` delegation unchanged.
- New hardening on main: `_control_chars_re` (main response.py L37) is applied only to the `reason_phrase` setter (L159-L162, `if value and _control_chars_re.search(value)`). Does not affect header values; empty strings unaffected (`if value and ...`).

**How to apply:** re-scan when the repo bumps its Django floor or when main cuts 6.x/7.x branches. See [[django-52-header-conventions]].
