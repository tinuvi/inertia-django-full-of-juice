import json
from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from inertia import (
    deep_merge,
    defer,
    inertia,
    infinite_scroll,
    merge,
    once,
    optional,
    prepend,
    preserve_fragment,
    share,
)


@inertia("Home")
def home(request: HttpRequest) -> dict:
    return {
        "version": "0.3.0",
    }


@inertia("Lazy")
def lazy_page(request: HttpRequest) -> dict:
    return {
        "name": "Brian",
        "sport": optional(lambda: "Basketball"),
        "team": defer(lambda: "Bulls"),
        "grit": defer(lambda: "intense", "extras"),
        "plans": once(lambda: ["A", "B"], expires_in=timedelta(minutes=5)),
    }


@inertia("Lists")
def lists_page(request: HttpRequest) -> dict:
    return {
        "users": merge(
            lambda: [
                {"id": 1, "name": "Brandon"},
                {"id": 2, "name": "Brian"},
            ],
            match_on=["id"],
        ),
        "notifications": prepend(lambda: ["welcome back"]),
        "filters": deep_merge(lambda: {"status": "active", "page": 1}),
    }


@inertia("Feed")
def feed_page(request: HttpRequest) -> dict:
    page = int(request.GET.get("page", "1"))
    items = [{"id": page * 10 + i, "title": f"Item {page * 10 + i}"} for i in range(5)]
    return {
        "items": infinite_scroll(
            lambda: items,
            request,
            current_page=page,
            previous_page=page - 1 if page > 1 else None,
            next_page=page + 1,
        ),
    }


@inertia("Form")
def form_page(request: HttpRequest) -> dict:
    return {}


@require_http_methods(["POST"])
@inertia("Form")
def form_submit(request: HttpRequest) -> HttpResponse | dict:
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = {}
    name = str(payload.get("name") or "").strip()
    email = str(payload.get("email") or "").strip()
    errors: dict[str, str] = {}
    if not name:
        errors["name"] = "Name is required"
    if "@" not in email:
        errors["email"] = "Email is invalid"
    if errors:
        share(request, errors=errors)
        return {}
    return redirect("/?submitted=1")


def redirect_fragment(request: HttpRequest) -> HttpResponse:
    preserve_fragment(request)
    return redirect("/lists/#users")
