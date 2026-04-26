import json
from datetime import timedelta

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from inertia import (
    deep_merge,
    defer,
    errors_response,
    inertia,
    inertia_redirect,
    infinite_scroll,
    location,
    merge,
    once,
    optional,
    prepend,
    preserve_fragment,
    share,
)
from inertia.http import clear_history, encrypt_history


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
        "topic": once(lambda: "Hockey", key="lazy-topic-v1", fresh=True),
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
        "notifications": prepend(
            lambda: [{"id": 1, "text": "welcome back"}],
            match_on=["id"],
        ),
        "filters": deep_merge(
            lambda: {
                "buckets": [
                    {"id": "active", "label": "Active", "count": 2},
                    {"id": "archived", "label": "Archived", "count": 0},
                ],
            },
            match_on=["buckets.id"],
        ),
        "recent_orders": defer(
            lambda: [
                {"id": 101, "total": "$10.00"},
                {"id": 102, "total": "$24.50"},
            ],
            merge=True,
            match_on=["id"],
        ),
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
            match_on=["id"],
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
    return redirect("/lists/#users")


def preserve_fragment_view(request: HttpRequest) -> HttpResponse:
    preserve_fragment(request)
    return redirect("/lists/")


def inertia_redirect_view(request: HttpRequest) -> HttpResponse:
    return inertia_redirect("/lists/")


def external_location_view(request: HttpRequest) -> HttpResponse:
    return location("https://example.com/")


@inertia("History")
def history_page(request: HttpRequest) -> dict:
    encrypt_history(request)
    return {"note": "encryptHistory should be true on this response"}


def clear_history_view(request: HttpRequest) -> HttpResponse:
    clear_history(request)
    return redirect("/history-after-clear/")


@inertia("History")
def history_after_clear(request: HttpRequest) -> dict:
    return {"note": "clearHistory should be true on this response (one-shot)"}


@inertia("Method")
def method_page(request: HttpRequest) -> dict:
    return {}


@require_http_methods(["PUT", "PATCH", "DELETE"])
def method_handler(request: HttpRequest) -> HttpResponse:
    return redirect(f"/?method={request.method.lower()}")


@inertia("Validate")
def validate_page(request: HttpRequest) -> dict:
    return {}


@require_http_methods(["POST"])
def validate_api(request: HttpRequest) -> HttpResponse:
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = {}
    name = str(payload.get("name") or "").strip()
    errors: dict[str, str] = {}
    if not name:
        errors["name"] = "Name is required"
    if errors:
        return errors_response(errors)
    return JsonResponse({"ok": True})
