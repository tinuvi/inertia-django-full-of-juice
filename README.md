# Inertia.js Django Adapter

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=tinuvi_inertia-django-full-of-juice&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=tinuvi_inertia-django-full-of-juice)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=tinuvi_inertia-django-full-of-juice&metric=coverage)](https://sonarcloud.io/summary/new_code?id=tinuvi_inertia-django-full-of-juice)

This adapter supports the Inertia.js v3 protocol, including once props, prepend / deep-merge variants, `matchPropsOn`, infinite scroll, fragment preservation across redirects, and the `useHttp` validation-response shape.

## Installation

### Backend

Install the following python package via pip

```bash
pip install inertia-django
```

Add the Inertia app to your `INSTALLED_APPS` in `settings.py`

```python
INSTALLED_APPS = [
  # django apps,
  'inertia',
  # your project's apps,
]
```

Add the Inertia middleware to your `MIDDLEWARE` in `settings.py`

```python
MIDDLEWARE = [
  # django middleware,
  'inertia.middleware.InertiaMiddleware',
  # your project's middleware,
]
```

Finally, create a layout which exposes `{% block inertia %}{% endblock %}` in the body and set the path to this layout as `INERTIA_LAYOUT` in your `settings.py` file.

Now you're all set!

### Frontend

Django specific frontend docs coming soon. For now, we recommend installing [django_vite](https://github.com/MrBin99/django-vite)
and following the commits on the Django Vite [example repo](https://github.com/MrBin99/django-vite-example). Once Vite is setup with
your frontend of choice, just replace the contents of `entry.js` with [this file (example in react)](https://github.com/BrandonShar/inertia-rails-template/blob/main/app/frontend/entrypoints/application.jsx)

You can also check out the official Inertia docs at https://inertiajs.com/.

### CSRF

Django's CSRF tokens are tightly coupled with rendering templates, so Inertia Django automatically handles adding the CSRF cookie to each Inertia response. The Inertia.js v3 client ships with its own XHR layer (Axios is no longer required) and reads the CSRF cookie / writes the CSRF header using its own default names, which don't match Django's. You'll need to either configure the v3 client OR rename the Django settings so they line up.

By default:

- v3 client: `XSRF-TOKEN` cookie, `X-XSRF-TOKEN` header.
- Django: `csrftoken` cookie, `X-CSRFToken` header.

**You only need to choose one of the following options, just pick whichever makes the most sense to you!**

Option 1: configure the Inertia v3 HTTP client at boot (in your `entry.js`):

```javascript
import { http } from '@inertiajs/core'

http.setClient({
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})
```

Option 2: rename Django settings to match the v3 defaults (in your `settings.py`):

```python
CSRF_HEADER_NAME = 'HTTP_X_XSRF_TOKEN'
CSRF_COOKIE_NAME = 'XSRF-TOKEN'
```

## Usage

### Responses

Render Inertia responses is simple, you can either use the provided inertia render function or, for the most common use case, the inertia decorator. The render function accepts four arguments, the first is your request object. The second is the name of the component you want to render from within your pages directory (without extension). The third argument is a dict of `props` that should be provided to your components. The final argument is `template_data`, for any variables you want to provide to your template, but this is much less common.

```python
from inertia import render
from .models import Event

def index(request):
  return render(request, 'Event/Index', props={
    'events': Event.objects.all()
  })
```

Or use the simpler decorator for the most common use cases

```python
from inertia import inertia
from .models import Event

@inertia('Event/Index')
def index(request):
  return {
    'events': Event.objects.all(),
  }
```

If you need more control, you can also directly return the InertiaResponse class. It has the same arguments as the render method and subclasses HttpResponse to accept of all its arguments as well.

```python
from inertia import InertiaResponse
from .models import Event

def index(request):
  return InertiaResponse(
    request,
    'Event/Index',
    props={
      'events': Event.objects.all()
    }
  )
```

### Shared Data

If you have data that you want to be provided as a prop to every component (a common use-case is information about the authenticated user) you can use the `share` method. A common place to put this would be in some custom middleware.

```python
from inertia import share
from django.conf import settings
from .models import User

def inertia_share(get_response):
  def middleware(request):
    share(request,
      app_name=settings.APP_NAME,
      user_count=lambda: User.objects.count(), # evaluated lazily at render time
      user=lambda: request.user, # evaluated lazily at render time
    )

    return get_response(request)
  return middleware
```
### Prop Serialization

Unlike Rails and Laravel, Django does not handle converting objects to JSON by default so Inertia Django offers two different ways to handle prop serialization.

#### InertiaJsonEncoder

The default behavior is via the InertiaJsonEncoder. The InertiaJsonEncoder is a barebones implementation
that extends the DjangoJSONEncoder with the ability to handle QuerySets and models. Models are JSON encoded
via Django's `model_to_dict` method excluding the field `password`. This method has limitations though, as
`model_to_dict` does not include fields where editable=False (such as automatic timestamps).

#### InertiaMeta

Starting in Inertia Django v1.2, Inertia Django supports an InertiaMeta nested class. Similar to Django Rest Framework's serializers, any class (not just models) can contain an InertiaMeta class which can specify how that class should be serialized to JSON. At this time, in only supports `fields`, but this may be extended in future versions.

```python
class User(models.Model):
  name = models.CharField(max_length=255)
  password = models.CharField(max_length=255)
  created_at = models.DateField(auto_now_add=True)

  class InertiaMeta:
    fields = ('name', 'created_at')
```

### External Redirects

It is possible to redirect to an external website, or even another non-Inertia endpoint in your app while handling an Inertia request.
This can be accomplished using a server-side initiated `window.location` visit via the `location` method:

```python
from inertia import location

def external():
    return location("http://foobar.com/")
```

It will generate a `409 Conflict` response and include the destination URL in the `X-Inertia-Location` header.
When this response is received client-side, Inertia will automatically perform a `window.location = url` visit.

### Optional Props

On the front end, Inertia supports the concept of "partial reloads" where only the props requested
are returned by the server. Sometimes, you may want to use this flow to avoid processing a particularly slow prop on the intial load. In this case, you can use `Optional props`. Optional props aren't evaluated unless they're specifically requested by name in a partial reload.

```python
from inertia import optional, inertia

@inertia('ExampleComponent')
def example(request):
  return {
    'name': lambda: 'Brandon', # this will be rendered on the first load as usual
    'data': optional(lambda: some_long_calculation()), # this will only be run when specifically requested by partial props and WILL NOT be included on the initial load
  }
```

### Deferred Props

As of version 2.0, Inertia supports the ability to defer the fetching of props until after the page has been initially rendered. Essentially this is similar to the concept of `Optional props` however Inertia provides convenient frontend components to automatically fetch the deferred props after the page has initially loaded, instead of requiring the user to initiate a reload. For more info, see [Deferred props](https://inertiajs.com/deferred-props) in the Inertia documentation.

To mark props as deferred on the server side use the `defer` function.

```python
from inertia import defer, inertia

@inertia('ExampleComponent')
def example(request):
  return {
    'name': lambda: 'Brandon', # this will be rendered on the first load as usual
    'data': defer(lambda: some_long_calculation()), # this will only be run after the frontend has initially loaded and inertia requests this prop
  }
```

#### Grouping requests

By default, all deferred props get fetched in one request after the initial page is rendered, but you can choose to fetch data in parallel by grouping props together.

```python
from inertia import defer, inertia

@inertia('ExampleComponent')
def example(request):
  return {
    'name': lambda: 'Brandon', # this will be rendered on the first load as usual
    'data': defer(lambda: some_long_calculation()),
    'data1': defer(lambda: some_long_calculation1(), group='group'),
    'data2': defer(lambda: some_long_calculation1(), 'group'),
  }
```

In the example above, the `data1`, and `data2` props will be fetched in one request, while the `data` prop will be fetched in a separate request in parallel. Group names are arbitrary strings and can be anything you choose.

### Merge Props

By default, Inertia overwrites props with the same name when reloading a page. However, there are instances, such as pagination or infinite scrolling, where that is not the desired behavior. In these cases, you can merge props instead of overwriting them.

```python
from inertia import merge, inertia

@inertia('ExampleComponent')
def example(request):
  return {
    'name': lambda: 'Brandon',
    'data': merge(Paginator(objects, 3)),
  }
```

You can also combine deferred props with mergeable props to defer the loading of the prop and ultimately mark it as mergeable once it's loaded.

```python
from inertia import defer, inertia

@inertia('ExampleComponent')
def example(request):
  return {
    'name': lambda: 'Brandon',
    'data': defer(lambda: Paginator(objects, 3), merge=True),
  }
```

### Prepend Props

`prepend` is the mirror of `merge`. Instead of appending newly loaded values to the existing client-side prop, the v3 client prepends them. Useful for chat logs, activity feeds, and any list where new items belong at the top.

```python
from inertia import inertia, prepend

@inertia('ExampleComponent')
def example(request):
  return {
    'messages': prepend(lambda: latest_messages()),
  }
```

### Deep Merge Props

`deep_merge` recursively merges objects rather than overwriting them. Use it when a prop is a nested dictionary and partial reloads should layer new keys onto the existing client-side state.

```python
from inertia import deep_merge, inertia

@inertia('ExampleComponent')
def example(request):
  return {
    'filters': deep_merge(lambda: build_filters()),
  }
```

### Match props on

When a list is being merged (`merge`, `prepend`, `deep_merge`) or deferred-and-merged (`defer(..., merge=True)`), pass `match_on=[...]` to tell the v3 client which field(s) on each item identify it. The client uses those paths to dedup matching items instead of blindly concatenating, which is what you want for paginated lists, infinite scroll, and any merge that may overlap with already-loaded items.

```python
from inertia import inertia, merge

@inertia('Users/Index')
def index(request):
    return {
        'users': merge(lambda: list_users(), match_on=['id']),
    }
```

`match_on=` is supported on `merge`, `prepend`, `deep_merge`, and `defer`. Each entry is a dot-path resolved against an item in the prop's list.

### Once Props

`once` props are computed on the server, sent to the client, and then cached there. On the next visit, the client signals that it already has them (via `X-Inertia-Except-Once-Props`) and the server skips resolving the callable entirely. This is ideal for data that is expensive to compute but rarely changes per-user — pricing plans, feature flags, static config, etc.

```python
from datetime import timedelta
from inertia import inertia, once

@inertia('Billing/Upgrade')
def upgrade(request):
    return {
        'plans': once(lambda: load_plans()),
        'plans_with_ttl': once(lambda: load_plans(), expires_in=timedelta(hours=1)),
        'plans_custom_key': once(lambda: load_plans(), key='plans-v2'),
    }
```

Supported keyword arguments:

- `key`: override the cache key (defaults to the prop name). Bump it when the underlying shape changes to invalidate stale client caches.
- `fresh`: force the server to re-resolve on this response even if the client claims to have cached it.
- `expires_in`: a `timedelta` or integer seconds. Computed into a unix-ms expiry sent to the client.
- `expires_at`: a `datetime` (timezone-aware preferred) or a unix-ms integer.

`expires_in` and `expires_at` are mutually exclusive.

### Infinite Scroll

`infinite_scroll` wraps a paginated prop so the v3 client can drive append / prepend behavior from the `X-Inertia-Infinite-Scroll-Merge-Intent` header. The helper takes the `request` as an explicit second positional argument because Django doesn't expose an implicit "current request" — pass the same `HttpRequest` your view received. The caller is responsible for computing pagination metadata; the helper itself doesn't know about `Paginator` or any other paging abstraction.

```python
from inertia import inertia, infinite_scroll
from .models import User

@inertia('Users/Index')
def index(request):
    page = int(request.GET.get('page', 1))
    page_size = 20
    qs = User.objects.all().order_by('id')
    users = list(qs[(page - 1) * page_size : page * page_size])
    total = qs.count()
    has_next = page * page_size < total
    return {
        'users': infinite_scroll(
            users,
            request,
            page_name='page',
            current_page=page,
            previous_page=page - 1 if page > 1 else None,
            next_page=page + 1 if has_next else None,
            match_on=['id'],
        ),
    }
```

The prop emits a `scrollProps` entry on the page object with `pageName`, `previousPage`, `nextPage`, `currentPage`, and a `reset` boolean derived from `X-Inertia-Reset`. Combined with `match_on=['id']`, the v3 client will dedup overlapping pages by item id.

### Preserving fragments across redirects

Browsers don't send the URL fragment (the `#section` part) to the server, but the v3 client tracks it locally. When a view redirects after handling a request, you can flag the response so the client carries the fragment over to the redirect target.

```python
from inertia import preserve_fragment
from django.shortcuts import redirect

def update(request):
    # ... handle update ...
    preserve_fragment(request)
    return redirect('/settings')
```

Additionally, `InertiaMiddleware` automatically converts any redirect response whose `Location` contains a `#fragment` (e.g. `redirect('/foo#section')`) on an Inertia request into a `409 + X-Inertia-Redirect`, so the v3 client honors the fragment without any extra work on your part.

### Validation responses for `useHttp`

The v3 frontend ships a `useHttp` hook for non-Inertia XHR calls (think: small async actions that don't navigate). Unlike the Inertia visit flow, `useHttp` expects a `422` JSON response with the shape `{"message": "...", "errors": {field: msg}}` on validation failure. `errors_response()` builds exactly that.

```python
from inertia import errors_response

def submit(request):
    form = MyForm(request.POST)
    if not form.is_valid():
        errors = {field: errs[0] for field, errs in form.errors.items()}
        return errors_response(errors, message="Please fix the highlighted fields.")
    # ... handle valid form ...
```

For regular Inertia visits (form submissions through `useForm` / `router.post`), the convention is still the redirect-back-with-flashed-errors pattern — projects flash validation errors to the session and re-share them on the next GET via `share(request, errors=...)`. `errors_response()` is specifically for the `useHttp` hook.

### Json Encoding

Inertia Django ships with a custom JsonEncoder at `inertia.utils.InertiaJsonEncoder` that extends Django's
`DjangoJSONEncoder` with additional logic to handle encoding models and Querysets. If you have other json
encoding logic you'd prefer, you can set a new JsonEncoder via the settings.

### History Encryption

Inertia.js supports [history encryption](https://inertiajs.com/history-encryption) to protect sensitive data in the browser's history state. This is useful when your pages contain sensitive information that shouldn't be stored in plain text in the browser's history. This feature requires HTTPS since it relies on `window.crypto.subtle` which is only available in secure contexts.

You can enable history encryption globally via the `INERTIA_ENCRYPT_HISTORY` setting in your `settings.py`:

```python
INERTIA_ENCRYPT_HISTORY = True
```

For more granular control, you can enable encryption on specific views:

```python
from inertia import encrypt_history, inertia

@inertia('TestComponent')
def encrypt_history_test(request):
    encrypt_history(request)
    return {}

# If you have INERTIA_ENCRYPT_HISTORY = True but want to disable encryption for specific views:
@inertia('PublicComponent')
def public_view(request):
    encrypt_history(request, False)  # Explicitly disable encryption for this view
    return {}
```

When users log out, you might want to clear the history to ensure no sensitive data can be accessed. You can do this by extending the logout view:

```python
from inertia import clear_history
from django.contrib.auth import views as auth_views

class LogoutView(auth_views.LogoutView):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        clear_history(request)
        return response
```

### SSR

#### Backend

* Ensure `requests` is installed, so inertia-django can do SSR requests.
  * `requests` is configured as a dependency if you install the `[ssr]` extra,
    e.g. `inertia-django[ssr]` in your requirements.
* Enable SSR via the `INERTIA_SSR_URL` and `INERTIA_SSR_ENABLED` settings.

#### Frontend

Coming Soon!

## Settings

Inertia Django has a few different settings options that can be set from within your project's `settings.py` file. Some of them have defaults.

The default config is shown below

```python
INERTIA_VERSION = '1.0' # defaults to '1.0'; bump this when shipping v3 to force a hard reload
INERTIA_LAYOUT = 'layout.html' # required and has no default
INERTIA_JSON_ENCODER = CustomJsonEncoder # defaults to inertia.utils.InertiaJsonEncoder
INERTIA_SSR_URL = 'http://localhost:13714' # defaults to http://localhost:13714
INERTIA_SSR_ENABLED = False # defaults to False
INERTIA_ENCRYPT_HISTORY = False # defaults to False
```

## Testing

Inertia Django ships with a custom TestCase to give you some nice helper methods and assertions.
To use it, just make sure your TestCase inherits from `InertiaTestCase`. `InertiaTestCase` inherits from Django's `django.test.TestCase` so it includes transaction support and a client.

```python
from inertia.test import InertiaTestCase

class ExampleTestCase(InertiaTestCase):
  def test_show_assertions(self):
    self.client.get('/events/')

    # check the component
    self.assertComponentUsed('Event/Index')

    # access the component name
    self.assertEqual(self.component(), 'Event/Index')

    # props (including shared props)
    self.assertHasExactProps({name: 'Brandon', sport: 'hockey'})
    self.assertIncludesProps({sport: 'hockey'})

    # access props
    self.assertEquals(self.props()['name'], 'Brandon')

    # template data
    self.assertHasExactTemplateData({name: 'Brian', sport: 'basketball'})
    self.assertIncludesTemplateData({sport: 'basketball'})

    # access template data
    self.assertEquals(self.template_data()['name'], 'Brian')
```

The inertia test helper also includes a special `inertia` client that pre-sets the inertia headers
for you to simulate an inertia response. You can access and use it just like the normal client with commands like `self.inertia.get('/events/')`. When using the inertia client, inertia custom assertions **are not** enabled though, so only use it if you want to directly assert against the json response.

Because v3 emits `encryptHistory`, `clearHistory`, and `preserveFragment` only when `True`, prefer asserting their effective value via `.get(..., False)` rather than direct key lookups in your tests:

```python
self.assertEqual(self.page().get("encryptHistory", False), True)
```

## Examples

- [Django Svelte Template](https://github.com/pmdevita/Django-Svelte-Template) - A Django template and example project demonstrating Inertia with Svelte and SSR.
- [Django React](https://github.com/willianantunes/inertia-django-playground): A Django + React project including CRUD operations, form handling, authentication, deployment using Docker, and more.

## Thank you

A huge thank you to the community members who have worked on InertiaJS for Django before us. Parts of this repo were particularly inspired by [Andres Vargas](https://github.com/zodman) and [Samuel Girardin](https://github.com/girardinsamuel). Additional thanks to Andres for the Pypi project.
