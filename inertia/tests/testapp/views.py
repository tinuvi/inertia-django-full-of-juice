from datetime import datetime, timedelta, timezone

from django.http.response import HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import decorator_from_middleware

from inertia import (
    deep_merge,
    defer,
    errors_response,
    inertia,
    inertia_redirect,
    infinite_scroll,
    lazy,
    location,
    merge,
    once,
    optional,
    prepend,
    preserve_fragment,
    render,
    share,
)
from inertia.http import (
    INERTIA_SESSION_CLEAR_HISTORY,
    INERTIA_SESSION_PRESERVE_FRAGMENT,
    clear_history,
    encrypt_history,
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
