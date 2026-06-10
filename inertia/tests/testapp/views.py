from datetime import date, datetime, timedelta, timezone

from django import forms
from django.contrib import messages as django_messages
from django.http.response import HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import decorator_from_middleware

from inertia import (
    back,
    clear_history,
    deep_merge,
    defer,
    encrypt_history,
    errors_response,
    flash,
    flash_errors,
    inertia,
    inertia_redirect,
    infinite_scroll,
    lazy,
    location,
    merge,
    once,
    optional,
    precognition,
    prepend,
    preserve_fragment,
    render,
    share,
)
from inertia.http import (
    INERTIA_SESSION_CLEAR_HISTORY,
    INERTIA_SESSION_FLASH,
    INERTIA_SESSION_PRESERVE_FRAGMENT,
)


class ShareMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(
            request,
            position=lambda: "goalie",
            number=29,
        )


def test(request):
    return HttpResponse("Hey good stuff")


@inertia("TestComponent")
def empty_test(request):
    return {}


def redirect_test(request):
    return redirect(empty_test)


@inertia("TestComponent")
def inertia_redirect_test(request):
    return redirect(empty_test)


def external_redirect_test(request):
    return location("http://foobar.com/")


@inertia("TestComponent")
def props_test(request):
    return {
        "name": "Brandon",
        "sport": "Hockey",
    }


def template_data_test(request):
    return render(
        request,
        "TestComponent",
        template_data={
            "name": "Brian",
            "sport": "Basketball",
        },
    )


@inertia("TestComponent")
def lazy_test(request):
    return {
        "name": "Brian",
        "sport": lazy(lambda: "Basketball"),
        "grit": lazy(lambda: "intense"),
    }


@inertia("TestComponent")
def optional_test(request):
    return {
        "name": "Brian",
        "sport": optional(lambda: "Basketball"),
        "grit": optional(lambda: "intense"),
    }


@inertia("TestComponent")
def defer_test(request):
    return {"name": "Brian", "sport": defer(lambda: "Basketball")}


@inertia("TestComponent")
def defer_group_test(request):
    return {
        "name": "Brian",
        "sport": defer(lambda: "Basketball", "group"),
        "team": defer(lambda: "Bulls", "group"),
        "grit": defer(lambda: "intense"),
    }


@inertia("TestComponent")
def merge_test(request):
    return {
        "name": "Brandon",
        "sport": merge(lambda: "Hockey"),
        "team": defer(lambda: "Penguins", merge=True),
    }


@inertia("TestComponent")
def complex_props_test(request):
    return {
        "person": {
            "name": lambda: "Brandon",
        }
    }


@decorator_from_middleware(ShareMiddleware)
@inertia("TestComponent")
def share_test(request):
    return {
        "name": "Brandon",
    }


@inertia("TestComponent")
def encrypt_history_test(request):
    encrypt_history(request)
    return {}


@inertia("TestComponent")
def encrypt_history_false_test(request):
    encrypt_history(request, False)
    return {}


@inertia("TestComponent")
def encrypt_history_type_error_test(request):
    encrypt_history(request, "foo")
    return {}


@inertia("TestComponent")
def clear_history_test(request):
    clear_history(request)
    return {}


@inertia("TestComponent")
def clear_history_redirect_test(request):
    clear_history(request)
    return redirect(empty_test)


@inertia("TestComponent")
def clear_history_type_error_test(request):
    request.session[INERTIA_SESSION_CLEAR_HISTORY] = "foo"
    return {}


@inertia("TestComponent")
def errors_share_test(request):
    share(request, errors={"name": "Required"})
    return {}


@inertia("TestComponent")
def errors_per_render_test(request):
    return {"errors": {"sport": "Invalid"}}


@inertia("TestComponent")
def partial_except_test(request):
    return {
        "name": "Brian",
        "sport": "Hockey",
        "team": "Penguins",
        "grit": "intense",
    }


@inertia("TestComponent")
def partial_except_with_deferred_test(request):
    return {
        "name": "Brian",
        "sport": defer(lambda: "Basketball"),
        "team": defer(lambda: "Bulls"),
    }


def fragment_redirect_test(request):
    return redirect("/empty/#section")


def preserve_fragment_view(request):
    preserve_fragment(request)
    return render(request, "TestComponent", props={})


@inertia("TestComponent")
def preserve_fragment_type_error_test(request):
    request.session[INERTIA_SESSION_PRESERVE_FRAGMENT] = "foo"
    return {}


def errors_response_view(request):
    return errors_response({"email": "Required", "password": ["Too short", "Too weak"]})


def errors_response_custom_view(request):
    return errors_response(
        {"name": "Required"},
        message="Custom message",
        status=400,
    )


def inertia_redirect_helper_test(request):
    return inertia_redirect("/foo#bar")


@inertia("TestComponent")
def once_test(request):
    return {
        "name": "Brian",
        "plans": once(lambda: ["A", "B"]),
    }


@inertia("TestComponent")
def once_custom_key_test(request):
    return {
        "plans": once(lambda: ["A", "B"], key="custom-key"),
    }


@inertia("TestComponent")
def once_fresh_test(request):
    return {
        "plans": once(lambda: ["A", "B"], fresh=True),
    }


@inertia("TestComponent")
def once_multiple_test(request):
    return {
        "plans": once(lambda: ["A", "B"]),
        "config": once(lambda: {"x": 1}),
    }


@inertia("TestComponent")
def once_expires_in_timedelta_test(request):
    return {
        "plans": once(lambda: ["A"], expires_in=timedelta(seconds=60)),
    }


@inertia("TestComponent")
def once_expires_in_int_test(request):
    return {
        "plans": once(lambda: ["A"], expires_in=30),
    }


ONCE_FIXED_DATETIME = datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@inertia("TestComponent")
def once_expires_at_datetime_test(request):
    return {
        "plans": once(lambda: ["A"], expires_at=ONCE_FIXED_DATETIME),
    }


@inertia("TestComponent")
def prepend_test(request):
    return {
        "name": "Brandon",
        "notifications": prepend(lambda: ["a", "b"]),
    }


@inertia("TestComponent")
def prepend_match_on_test(request):
    return {
        "notifications": prepend(lambda: ["a", "b"], match_on=["id"]),
    }


@inertia("TestComponent")
def deep_merge_test(request):
    return {
        "filters": deep_merge(lambda: {"a": 1}),
    }


@inertia("TestComponent")
def deep_merge_match_on_test(request):
    return {
        "filters": deep_merge(lambda: {"a": 1}, match_on=["nested.id", "id"]),
    }


@inertia("TestComponent")
def merge_match_on_test(request):
    return {
        "users": merge(lambda: [{"id": 1}], match_on=["id"]),
    }


@inertia("TestComponent")
def merge_match_on_multiple_test(request):
    return {
        "posts": merge(lambda: [{"id": 1}], match_on=["data.id", "id"]),
    }


@inertia("TestComponent")
def defer_match_on_test(request):
    return {
        "users": defer(lambda: [{"id": 1}], merge=True, match_on=["id"]),
    }


@inertia("TestComponent")
def infinite_scroll_test(request):
    return {
        "items": infinite_scroll(
            lambda: [{"id": 1}, {"id": 2}],
            request,
        ),
    }


@inertia("TestComponent")
def infinite_scroll_match_on_test(request):
    return {
        "items": infinite_scroll(
            lambda: [{"id": 1}, {"id": 2}],
            request,
            match_on=["id"],
        ),
    }


@inertia("TestComponent")
def infinite_scroll_pagination_test(request):
    return {
        "items": infinite_scroll(
            lambda: [{"id": 1}, {"id": 2}],
            request,
            page_name="cursor",
            previous_page=2,
            next_page=4,
            current_page=3,
        ),
    }


@inertia("TestComponent")
def infinite_scroll_two_props_test(request):
    return {
        "items": infinite_scroll(
            lambda: [{"id": 1}, {"id": 2}],
            request,
            current_page=1,
        ),
        "feed": infinite_scroll(
            lambda: [{"id": 10}],
            request,
            current_page=5,
        ),
    }


@inertia("TestComponent")
def infinite_scroll_partial_test(request):
    return {
        "name": "Brian",
        "items": infinite_scroll(
            lambda: [{"id": 1}, {"id": 2}],
            request,
            current_page=2,
        ),
    }


# --- Shared-prop registry views (Fix #1) ---


class ShareOnceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(
            request,
            shared_plans=once(lambda: ["A", "B"]),
        )


@decorator_from_middleware(ShareOnceMiddleware)
@inertia("TestComponent")
def share_once_test(request):
    return {"name": "Brian"}


class ShareDeferMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(
            request,
            shared_sport=defer(lambda: "Basketball"),
        )


@decorator_from_middleware(ShareDeferMiddleware)
@inertia("TestComponent")
def share_defer_test(request):
    return {"name": "Brian"}


class ShareMergeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(
            request,
            shared_users=merge(lambda: [{"id": 1}], match_on=["id"]),
        )


@decorator_from_middleware(ShareMergeMiddleware)
@inertia("TestComponent")
def share_merge_test(request):
    return {"name": "Brian"}


class SharePrependMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(
            request,
            shared_notifications=prepend(lambda: ["a"]),
        )


@decorator_from_middleware(SharePrependMiddleware)
@inertia("TestComponent")
def share_prepend_test(request):
    return {"name": "Brian"}


class ShareDeepMergeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(
            request,
            shared_filters=deep_merge(lambda: {"a": 1}),
        )


@decorator_from_middleware(ShareDeepMergeMiddleware)
@inertia("TestComponent")
def share_deep_merge_test(request):
    return {"name": "Brian"}


class ShareScrollMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(
            request,
            shared_items=infinite_scroll(
                lambda: [{"id": 1}],
                request,
                current_page=2,
            ),
        )


@decorator_from_middleware(ShareScrollMiddleware)
@inertia("TestComponent")
def share_scroll_test(request):
    return {"name": "Brian"}


# Per-request prop overrides a shared prop with the same key
class ShareCollisionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(request, name="from-shared")


@decorator_from_middleware(ShareCollisionMiddleware)
@inertia("TestComponent")
def share_collision_test(request):
    return {"name": "from-per-request"}


# --- Registry filtering on partial reloads (Fix #2) ---


@inertia("TestComponent")
def filter_merge_props_test(request):
    return {
        "foo": merge(lambda: [1]),
        "bar": merge(lambda: [2]),
    }


@inertia("TestComponent")
def filter_prepend_props_test(request):
    return {
        "foo": prepend(lambda: [1]),
        "bar": prepend(lambda: [2]),
    }


@inertia("TestComponent")
def filter_deep_merge_props_test(request):
    return {
        "foo": deep_merge(lambda: {"a": 1}),
        "bar": deep_merge(lambda: {"b": 2}),
    }


@inertia("TestComponent")
def filter_match_on_props_test(request):
    return {
        "foo": merge(lambda: [{"id": 1}], match_on=["id"]),
        "bar": merge(lambda: [{"id": 2}], match_on=["id"]),
    }


@inertia("TestComponent")
def filter_once_props_test(request):
    return {
        "foo": once(lambda: ["A"]),
        "bar": once(lambda: ["B"]),
    }


@inertia("TestComponent")
def filter_scroll_props_test(request):
    return {
        "foo": infinite_scroll(lambda: [{"id": 1}], request, current_page=1),
        "bar": infinite_scroll(lambda: [{"id": 2}], request, current_page=2),
    }


# --- Mutmut kill targets for inertia/http.py ---


@inertia("EscapeChars")
def escape_chars_in_props_test(request):
    return {"value": "<script>alert(1)</script>&y"}


class ShareErrorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_request(self, request):
        share(request, errors={"shared": "value"})


@decorator_from_middleware(ShareErrorsMiddleware)
@inertia("TestComponent")
def share_errors_then_optional_test(request):
    return {"sport": optional(lambda: "Basketball")}


@inertia("TestComponent")
def merge_after_non_merging_defer_test(request):
    return {
        "name": "Brandon",
        "sport": defer(lambda: "Basketball"),
        "team": merge(lambda: "Bulls"),
    }


@inertia("TestComponent")
def date_prop_test(request):
    return {"when": date(2030, 1, 1)}


def render_helper_with_props_test(request):
    return render(request, "TestComponent", props={"hello": "world"})


@inertia("TestComponent")
def string_callable_props_test(request):
    # Plain strings that share a name with a builtin callable must be sent
    # verbatim, never invoked (a str is not callable in Python).
    return {"first": "date", "second": "trim"}


# --- v3 flash page field ---------------------------------------------------


@inertia("TestComponent")
def flash_set_and_render_test(request):
    flash(request, toast="Saved!")
    return {}


@inertia("TestComponent")
def flash_accumulate_test(request):
    flash(request, toast="Saved!")
    flash(request, banner="Welcome", toast="Replaced!")
    return {}


@inertia("TestComponent")
def flash_redirect_test(request):
    flash(request, toast="Saved!")
    return redirect(empty_test)


@inertia("TestComponent")
def flash_type_error_test(request):
    request.session[INERTIA_SESSION_FLASH] = "foo"
    return {}


@inertia("TestComponent")
def flash_messages_bridge_test(request):
    django_messages.success(request, "It worked!", extra_tags="billing")
    return {}


# --- built-in validation-errors flow ----------------------------------------


class GuestForm(forms.Form):
    name = forms.CharField(max_length=10)
    email = forms.EmailField()


def back_with_dict_errors_test(request):
    return back(request, errors={"name": ["Required", "Too short"], "email": "Invalid"})


def back_with_form_errors_test(request):
    form = GuestForm(data={"name": "x" * 20, "email": "nope"})
    form.is_valid()
    return back(request, errors=form)


def back_plain_test(request):
    return back(request, fallback="/empty/")


def flash_errors_only_test(request):
    flash_errors(request, {"name": "Required"})
    return redirect(empty_test)


# --- precognition -------------------------------------------------------------


class PrecogForm(forms.Form):
    name = forms.CharField(max_length=5)
    email = forms.EmailField()
    age = forms.IntegerField(min_value=18)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("name") == "admin":
            self.add_error(None, "Reserved name")
        return cleaned


@precognition(PrecogForm)
@inertia("TestComponent")
def precog_test(request):
    return {"submitted": True}


@precognition(PrecogForm)
async def precog_async_test(request):
    return HttpResponse("async ok")


class PrecogUploadForm(forms.Form):
    avatar = forms.FileField()


@precognition(PrecogUploadForm)
def precog_upload_test(request):
    return HttpResponse("upload ok")


@decorator_from_middleware(ShareMiddleware)
@inertia("TestComponent")
def share_dotted_key_test(request):
    # share() takes kwargs, so dotted keys can only arrive via direct registry
    # writes — pin that sharedProps reduces them to their FIRST dot segment
    # (multi-dot keys included), deduped, mirroring Laravel's
    # resolveSharedProps.
    request.inertia.props["auth.user"] = "Brandon"
    request.inertia.props["auth.flags"] = []
    request.inertia.props["auth.profile.name"] = "B"
    return {}


# --- rescuable deferred props ---------------------------------------------


def _explode():
    raise RuntimeError("boom")


@inertia("TestComponent")
def defer_rescue_test(request):
    return {
        "name": "Brandon",
        "stats": defer(_explode, rescue=True),
        "teams": defer(lambda: ["Bulls"]),
    }


@inertia("TestComponent")
def defer_no_rescue_test(request):
    return {
        "name": "Brandon",
        "stats": defer(_explode),
    }


@inertia("TestComponent")
def defer_rescue_after_ok_test(request):
    # A healthy deferred prop declared BEFORE the rescuable one — pins that
    # the rescue scan keeps walking past non-rescuable props.
    return {
        "teams": defer(lambda: ["Bulls"]),
        "stats": defer(_explode, rescue=True),
    }
