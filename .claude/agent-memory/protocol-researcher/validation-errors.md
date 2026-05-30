---
name: validation-errors
description: How Inertia v3 specifies the errors prop, error bags (X-Inertia-Error-Bag), form.errors consumption, and redirect/error coupling — spec + 3.x client citations
metadata:
  type: reference
---

# Validation-error handling in Inertia v3 (spec + 3.x client)

## errors prop — formally specified, optional, defaults to {}
- Spec (the-protocol.md, Page Object table): `props` "Contains all of the page data along with an errors object (defaults to {} if there are no errors)." So `errors` IS a named part of the page object, not a loose convention. Both protocol examples show `"props":{"errors":{}, ...}`.
- Spec (validation.md): "Inertia checks the page.props.errors object for the existence of any errors. In the event that errors are present, the request's onError() callback will be called instead of the onSuccess() callback." And: "your server-side framework must share them via the errors prop... For other frameworks, you may need to do this manually."
- Server is NOT required to inject errors. Spec says first-party (Laravel) adapters do it automatically; others "may need to do this manually." An adapter that omits automatic error injection is still protocol-compliant — the client reads page.props.errors and treats empty/absent as "no errors."

## errors shape: {field: "string"} by default; arrays only opt-in
- Spec (validation.md "Multiple Errors Per Field"): "By default, Inertia's Laravel adapter returns only the first validation error for each field. You may opt-in to receiving all errors by setting `$withAllErrors`... When enabled, each field will contain an array of error strings instead of a single string."
- Client type (packages/core/src/types.ts): `export type Errors = Record<string, ErrorValue>` and `export type ErrorBag = Record<string, Errors>`. `ErrorValue = InertiaConfigFor<'errorValueType'>` (default string; user-configurable). Client does not enforce string-vs-array — it stores whatever the server sends per field. The first-vs-array choice is a server-adapter decision (Laravel default = first string).

## Error bags (X-Inertia-Error-Bag)
- Spec (the-protocol.md request headers): "X-Inertia-Error-Bag — Specifies which error bag to use for validation errors." Request header, sent by client only when an errorBag is set.
- Client sets header only when set: requestParams.ts — `if (this.params.errorBag && this.params.errorBag.length > 0) { headers['X-Inertia-Error-Bag'] = this.params.errorBag }`.
- Client reads namespaced errors (response.ts getScopedErrors): `if (!this.requestParams.all().errorBag) return errors; return errors[errorBag || ''] || {}`. So with errorBag='createUser', client pulls `page.props.errors.createUser` and passes THAT to onError/fireErrorEvent.
- Instant-visit path (router.ts): `const scopedErrors = params.errorBag ? errors[params.errorBag || ''] || {} : errors; onError?.(scopedErrors)`.
- useForm({errorBag}) threads the option into the visit params → header + scoping. errorBag defaults to null (vue3/src/form.ts). "Make errorBag parameter optional" — CHANGELOG PR #2445.

## Client error flow (packages/core/src/response.ts process())
- After setPage: `const errors = currentPage.get().props.errors || {}`. If `Object.keys(errors).length > 0`: `getScopedErrors` → `fireErrorEvent(scopedErrors)` → `onError(scopedErrors)` and RETURNS (onSuccess/fireSuccessEvent NOT called). Else → fireSuccessEvent + onSuccess.
- So presence of any key in page.props.errors is the sole client-side switch between success and error callbacks. Empty {} or absent ⇒ success path. Matches validation.md wording.

## form.errors / setError / clearErrors (framework useForm, e.g. vue3 useFormState.ts)
- form.errors is a reactive copy maintained by the form helper, populated from the onError(scopedErrors) callback. setError merges (`Object.assign(this.errors, errors)`, sets hasErrors). clearErrors filters keys out. markAsSuccessful clearErrors() on success.
- usePage().props.errors is the raw page-object errors object (un-scoped, includes bag namespacing if the server nested it); form.errors is the scoped/merged helper copy.
- Net: the client just reflects whatever the server put in errors. No client-side validation, no synthesis of error messages.

## Redirects — NOT in the protocol page; only 409 is
- the-protocol.md says NOTHING about 302/303 or post-non-GET redirects. Its only status-code/redirect content is 409 (X-Inertia-Location external redirect, X-Inertia-Redirect fragment redirect). 303/302 guidance lives in the-basics/redirects.md (a guide), not the protocol spec.
- redirects.md: "When redirecting after a PUT, PATCH, or DELETE request, you must use a 303 response code, otherwise the subsequent request will not be treated as a GET... If you're using one of our official server-side adapters, all redirects will automatically be converted to 303 redirects." (302 vs 303: 303 forces follow-up GET.)
- Client follows ordinary 30x via the browser/XHR (axios maxRedirects default); the client only specially handles 409 (isLocationVisit / isInertiaRedirect). No protocol-level coupling between redirects and error display.
- Error FLASHING across a redirect (PRG pattern) is explicitly a server/framework concern: validation.md — "you redirect (server-side) the user back to the form page... flashing the validation errors in the session... Some frameworks, such as Laravel, do this automatically." The wire protocol does not mandate flashing; it only defines that the next page response carries errors in page.props.errors.

## Bottom line
- errors is a specified-but-optional page-object field. Client reads whatever is (or isn't) there; empty/absent = success path. An adapter that does NOT auto-inject errors is protocol-compliant (spec explicitly contemplates manual sharing for non-first-party frameworks). The PRG-redirect + session-flash mechanism that makes errors survive a redirect is a server-adapter responsibility, not a wire-protocol requirement.
