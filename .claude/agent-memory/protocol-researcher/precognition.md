---
name: precognition
description: Full v3 Precognition wire contract — headers, transport, 204/422 handling, absence behavior; spec + inertia 3.x + laravel-precognition 2.x citations
metadata:
  type: reference
---

# Precognition (v3) wire contract

Spec: https://inertiajs.com/docs/v3/core-concepts/the-protocol (Request Headers L147-155, Response Headers L177-191, Status Codes L530 of the-protocol.mdx).

## Transport — NOT an Inertia request
- Validate requests are built by the `laravel-precognition` npm package (v2), NOT inertia's request.ts. inertia core pins `"laravel-precognition": "^2.0.0"` (packages/core/package.json L64, 3.x).
- Default transport = laravel-precognition's own `fetchHttpClient` (laravel/precognition 2.x packages/core/src/client.ts L11). inertia never calls `client.useHttpClient()`; it only forwards xsrf cookie/header names (inertia packages/core/src/http.ts L31-37).
- NO `X-Inertia`, NO `X-Inertia-Version` on validate requests. Custom headers only via Form `headers` prop → `UseFormUtils.mergeHeadersForValidation` (core/useFormUtils.ts L131-157; react/Form.ts slot `validate`).

## Request
- Headers (laravel/precognition client.ts resolveConfig L188-199): `Accept: application/json`, `Content-Type` = application/json | multipart/form-data when files (L276-281), `Precognition: true` (L193), `Precognition-Validate-Only: f1,f2` comma-joined (L196) from `config.only ?? config.validate ?? touched` (validator.ts L295).
- Method = form's method; GET/DELETE put data in query params, others in body (client.ts mergeConfig L98-108).
- Files stripped by default: `parseData = validateFiles===false ? forgetFiles(data) : data` (validator.ts L408-410); warning if validating a file field w/o validateFiles (~L390). Opt-in via `form.validateFiles()` / `<Form validateFiles>`.
- Debounce 1500 ms default (validator.ts L215), per-request timeout 5000 ms (L298). validate(field) skips send when value unchanged vs last validated data (~L396-402). Aborts in-flight matching fingerprint `${method}:${baseURL}${url}` (client.ts L31, abortMatchingRequests).

## Response contract
- MUST carry `Precognition: true` response header on every precognitive response (success AND error): `validatePrecognitionResponse` throws `Error('Did not receive a Precognition response. Ensure you have the Precognition middleware in place for the route.')` when `response.headers?.precognition !== 'true'` (client.ts L245-249; called ~L135 success path, ~L165 error path).
- Success = `status === 204 && headers['precognition-success'] === 'true'` (successResolver, client.ts L36) → validator marks `only` fields validated + clears their errors (validator.ts onPrecognitionSuccess ~L317-326). 204 without Precognition-Success ⇒ fields marked validated via onSuccess but errors NOT cleared.
- Failure = 422 with JSON body; client reads `response.data.errors` (Laravel `{message, errors: {field: [msgs]}}`) and merges over existing errors after clearing errors matching the `only` patterns (validator.ts onValidationError ~L299-309). Server filters validation to Validate-Only fields (server obligation; spec wording only). inertia simplifies arrays→first string via `toSimpleValidationErrors` unless `withAllErrors` (react/useFormState.ts ~L404-411; config `form.withAllErrors`).
- Status handlers map 401/403/404/409(onConflict)/422/423 (client.ts L263-271). NO 419 handler. fetchClient has no redirect option ⇒ fetch default follows 3xx; followed response w/o Precognition header ⇒ throws. Client never reads `Vary` or any echoed Validate-Only response header.
- 422 + cancelled errors are swallowed by the debounced runner; everything else (incl. the missing-header Error) rejects (validator.ts L247-275).

## Client triggers (react, 3.x)
- `useForm(method, url, data)` / `useForm(wayfinder, data)` (core/useFormUtils.ts parseUseFormArguments L48-96) or `.withPrecognition(...)`; `<Form>` ALWAYS calls `useForm({}).withPrecognition(() => resolvedMethod, () => url).setValidationTimeout(validationTimeout)` (react/Form.ts L93-99; validationTimeout default 1500, validateFiles default false); `useHttp` exposes the same `withPrecognition`/`validate` (react/useHttp.ts L71, L155-160). All funnel into `createValidator((client)=>client[method](url, transformedData))` (react/useFormState.ts L384-392). No request until `validate()`/`touch()+validate()` is called — a non-precognition server is safe if validate() is never invoked.
