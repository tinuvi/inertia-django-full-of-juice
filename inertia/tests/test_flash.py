"""Tests for the v3 ``flash`` page field (`flash()` + the messages bridge).

Covers the pull-at-render lifecycle (Laravel's ``Response::resolveFlashData``),
redirect survival, partial-reload emission, the 409 stale-version reflash,
and the opt-in ``INERTIA_FLASH_FROM_MESSAGES`` contrib.messages bridge.
"""

from __future__ import annotations

from django.test import override_settings

from inertia.http import INERTIA_SESSION_FLASH
from inertia.test import InertiaTestCase, inertia_page


class FlashLifecycleTestCase(InertiaTestCase):
    def test_flash_set_during_the_request_is_emitted_on_that_render(self) -> None:
        response = self.inertia.get("/flash-set/")

        self.assertJSONResponse(
            response, inertia_page("flash-set", flash={"toast": "Saved!"})
        )

    def test_flash_is_one_shot_and_cleared_after_render(self) -> None:
        self.inertia.get("/flash-set/")

        response = self.inertia.get("/empty/")

        self.assertJSONResponse(response, inertia_page("empty"))
        self.assertNotIn(INERTIA_SESSION_FLASH, self.inertia.session)

    def test_flash_calls_accumulate_and_later_values_win(self) -> None:
        response = self.inertia.get("/flash-accumulate/")

        self.assertJSONResponse(
            response,
            inertia_page(
                "flash-accumulate",
                flash={"toast": "Replaced!", "banner": "Welcome"},
            ),
        )

    def test_flash_survives_a_redirect_and_renders_on_the_follow_up(self) -> None:
        redirect_response = self.inertia.get("/flash-redirect/")
        self.assertEqual(redirect_response.status_code, 302)

        response = self.inertia.get("/empty/")

        self.assertJSONResponse(
            response, inertia_page("empty", flash={"toast": "Saved!"})
        )

    def test_page_without_flash_omits_the_field(self) -> None:
        response = self.inertia.get("/empty/")

        self.assertNotIn("flash", response.json())

    def test_flash_is_emitted_on_partial_reloads(self) -> None:
        session = self.inertia.session
        session[INERTIA_SESSION_FLASH] = {"toast": "Pending"}
        session.save()

        response = self.inertia.get(
            "/props/",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            HTTP_X_INERTIA_PARTIAL_DATA="sport",
        )

        page = response.json()
        self.assertEqual(page["flash"], {"toast": "Pending"})

    def test_non_dict_session_flash_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            self.inertia.get("/flash-type-error/")

    def test_flash_helper_rejects_non_dict_session_state(self) -> None:
        session = self.inertia.session
        session[INERTIA_SESSION_FLASH] = "corrupted"
        session.save()

        with self.assertRaises(TypeError):
            self.inertia.get("/flash-set/")

    def test_flash_accepts_a_request_named_flash_key(self) -> None:
        # ``request`` is positional-only, so a flash key literally named
        # "request" must land in the session instead of clashing.
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory

        from inertia import flash

        request = RequestFactory().get("/empty/")
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)

        flash(request, request="off-limits-name")

        self.assertEqual(
            request.session[INERTIA_SESSION_FLASH], {"request": "off-limits-name"}
        )


class FlashForceRefreshReflashTestCase(InertiaTestCase):
    def test_pending_flash_survives_the_409_stale_version_refresh(self) -> None:
        session = self.inertia.session
        session[INERTIA_SESSION_FLASH] = {"toast": "Pending"}
        session.save()

        stale = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="stale")

        self.assertEqual(stale.status_code, 409)
        self.assertEqual(
            self.inertia.session[INERTIA_SESSION_FLASH], {"toast": "Pending"}
        )

        fresh = self.inertia.get("/empty/")

        self.assertJSONResponse(
            fresh, inertia_page("empty", flash={"toast": "Pending"})
        )


class FlashMessagesBridgeTestCase(InertiaTestCase):
    @override_settings(INERTIA_FLASH_FROM_MESSAGES=True)
    def test_bridge_drains_contrib_messages_into_the_flash_field(self) -> None:
        response = self.inertia.get("/flash-messages-bridge/")

        page = response.json()
        self.assertEqual(
            page["flash"],
            {
                "messages": [
                    {
                        "message": "It worked!",
                        "level": 25,
                        "tags": "billing success",
                        "extra_tags": "billing",
                        "level_tag": "success",
                    }
                ]
            },
        )

    @override_settings(INERTIA_FLASH_FROM_MESSAGES=True)
    def test_bridged_messages_are_cleared_by_the_message_middleware(self) -> None:
        self.inertia.get("/flash-messages-bridge/")

        response = self.inertia.get("/empty/")

        self.assertNotIn("flash", response.json())

    def test_bridge_is_off_by_default(self) -> None:
        response = self.inertia.get("/flash-messages-bridge/")

        self.assertNotIn("flash", response.json())

    @override_settings(INERTIA_FLASH_FROM_MESSAGES=True)
    def test_bridge_overrides_the_reserved_messages_flash_key(self) -> None:
        session = self.inertia.session
        session[INERTIA_SESSION_FLASH] = {"messages": "custom"}
        session.save()

        response = self.inertia.get("/flash-messages-bridge/")

        page = response.json()
        self.assertEqual(len(page["flash"]["messages"]), 1)
        self.assertEqual(page["flash"]["messages"][0]["message"], "It worked!")

    @override_settings(INERTIA_FLASH_FROM_MESSAGES=True)
    def test_bridge_coerces_lazy_translations_to_plain_strings(self) -> None:
        # gettext_lazy message/extra_tags stay lazy when added and drained in
        # one request; the bridge must coerce them itself — reading
        # ``message.tags`` raw would feed the proxy into str.join → TypeError.
        response = self.inertia.get("/flash-messages-lazy-bridge/")

        page = response.json()
        self.assertEqual(
            page["flash"],
            {
                "messages": [
                    {
                        "message": "Saved",
                        "level": 25,
                        "tags": "billing success",
                        "extra_tags": "billing",
                        "level_tag": "success",
                    }
                ]
            },
        )
