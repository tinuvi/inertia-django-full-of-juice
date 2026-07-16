---
name: house-style-test-client-kwargs
description: This repo's test suite is 100% legacy HTTP_* test-client kwargs; Django 5.2 docs prefer headers= — arbitration pending (issue #5 review, 2026-07-16)
metadata:
  type: project
---

The library's test suite uses legacy CGI-style test-client kwargs everywhere (`HTTP_X_INERTIA_VERSION="stale"`, fixture `Client(HTTP_X_INERTIA=True)` in `inertia/test.py:26`); zero `headers=` usage against the Django test client (the only `headers=` hit is an SSR requests call).

**Why:** predates Django 4.2's `headers=` kwarg; both forms hit the identical code path (`django/test/client.py:L662-L663` converts `headers=` into the same WSGI extras), and the legacy form is not deprecated (5.2 docs call `headers=` "preferred for readability" — preference only).

**How to apply:** In the issue #5 review (2026-07-16) I recommended: keep new tests consistent with the legacy house style for now, and if modernizing, convert the whole suite in one dedicated commit rather than mixing voices. Caller arbitrates; record the ruling here once made. Migration landmine: `Client(HTTP_X_INERTIA=True)` passes bool `True`, so a `headers=` conversion must decide the string form (`"true"`) explicitly.

See [[django-52-header-conventions]].
