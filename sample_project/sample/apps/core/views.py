import json
from datetime import timedelta
from uuid import uuid4

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from inertia import (
    clear_history,
    deep_merge,
    defer,
    encrypt_history,
    errors_response,
    flash,
    inertia,
    inertia_redirect,
    infinite_scroll,
    location,
    merge,
    once,
    optional,
    precognition,
    prepend,
    preserve_fragment,
    redirect_back,
)

from .models import Player


def health(request: HttpRequest) -> HttpResponse:
    # Plain 200, no Inertia/Vite dependency — used by the compose healthcheck.
    return HttpResponse("ok")


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
def form_submit(request: HttpRequest) -> HttpResponse:
    # The built-in redirect-back-with-errors flow: `redirect_back()` flashes
    # errors to the session and the next render pulls them into the
    # `errors` prop (first message per field), Laravel-style.
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
        return redirect_back(request, errors=errors, fallback="/form/")
    return redirect("/?submitted=1")


@inertia("Bags")
def bags_page(request: HttpRequest) -> dict:
    return {}


@require_http_methods(["POST"])
def bags_newsletter(request: HttpRequest) -> HttpResponse:
    # Error-bag scoping is built in: the render nests the flashed errors
    # under the `X-Inertia-Error-Bag` header the client re-sends while
    # following the redirect, so only the opted-in form receives them.
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = {}
    email = str(payload.get("email") or "").strip()
    if "@" not in email:
        return redirect_back(
            request, errors={"email": "Email is invalid"}, fallback="/bags/"
        )
    return redirect("/bags/?subscribed=1")


@require_http_methods(["POST"])
def bags_feedback(request: HttpRequest) -> HttpResponse:
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = {}
    comment = str(payload.get("comment") or "").strip()
    if not comment:
        return redirect_back(
            request, errors={"comment": "Comment is required"}, fallback="/bags/"
        )
    return redirect("/bags/?thanked=1")


@inertia("Flash")
def flash_page(request: HttpRequest) -> dict:
    return {}


@require_http_methods(["POST"])
def flash_notify(request: HttpRequest) -> HttpResponse:
    # Vanilla Django messages + PRG; ShareDemoMiddleware drains them into the
    # `messages` shared prop on the redirected-to response.
    messages.success(request, "Profile saved successfully.")
    messages.warning(request, "Subscription expires soon.")
    return redirect("/flash/")


@inertia("Roster")
def roster_page(request: HttpRequest) -> dict:
    # QuerySet passed straight through — InertiaJsonEncoder serializes each
    # row via the model's InertiaMeta.fields.
    return {"players": Player.objects.order_by("number")}


# --- Consumer recipe chain ---------------------------------------------------
# Mirrors the shapes a production consumer (tinuvi/onsen) runs: Django
# messages drained eagerly into a `messages` shared prop by middleware
# (ShareDemoMiddleware), an account-linking-style redirect that lands on a
# gate which redirects again without rendering, and axios-style JSON
# endpoints that queue state without ever rendering an Inertia page. The
# messages-recipe spec pins where that recipe loses messages and how the v3
# `flash` field survives the identical flows.


def chain_link_messages(request: HttpRequest) -> HttpResponse:
    # onsen's /callback/ shape: queue a Django message, then redirect into
    # a gate. The eager recipe consumes the message at the gate hop.
    messages.success(request, "Contas vinculadas com sucesso!")
    return redirect("/chain/gate/")


def chain_link_flash(request: HttpRequest) -> HttpResponse:
    # The same chain shape with the v3 flash field: pull-at-render means
    # intermediate hops that never render cannot consume it.
    flash(request, toast={"text": "Contas vinculadas com sucesso!", "kind": "success"})
    return redirect("/chain/gate/")


def chain_gate(request: HttpRequest) -> HttpResponse:
    # onsen's @subscription_required shape: an intermediate hop that
    # redirects without rendering a page.
    return redirect("/chain/final/")


@inertia("Chain")
def chain_final(request: HttpRequest) -> dict:
    return {"stamp": str(uuid4())}


@require_http_methods(["POST"])
def chain_plant_message(request: HttpRequest) -> HttpResponse:
    # onsen's latent axios pattern: a JSON endpoint queues a message but
    # never renders — the message sits pending in the messages storage.
    messages.success(request, "Pending toast")
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def chain_plant_flash(request: HttpRequest) -> HttpResponse:
    flash(request, toast={"text": "Pending toast", "kind": "success"})
    return JsonResponse({"ok": True})


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


class SignupForm(forms.Form):
    name = forms.CharField(max_length=12)
    email = forms.EmailField()
    age = forms.IntegerField(min_value=18)


@inertia("Precognition")
def precognition_page(request: HttpRequest) -> dict:
    return {}


@precognition(SignupForm)
@require_http_methods(["POST"])
def precognition_submit(request: HttpRequest) -> HttpResponse:
    # Precognitive requests never reach this body — the decorator answers
    # them (204 / 422). Real submits validate the full form once more.
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = {}
    form = SignupForm(payload)
    if not form.is_valid():
        return redirect_back(request, errors=form, fallback="/precognition/")
    return redirect("/precognition/?signed=1")


@inertia("FlashNative")
def flash_native_page(request: HttpRequest) -> dict:
    return {}


@require_http_methods(["POST"])
def flash_native_save(request: HttpRequest) -> HttpResponse:
    flash(request, toast={"text": "Saved with the v3 flash field!", "kind": "success"})
    return redirect("/flash-native/")


def _broken_stats() -> dict:
    raise RuntimeError("stats backend down")


@inertia("Rescue")
def rescue_page(request: HttpRequest) -> dict:
    return {
        "profile": defer(lambda: {"name": "Brandon"}),
        "stats": defer(_broken_stats, "stats", rescue=True),
    }
