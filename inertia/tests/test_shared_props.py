"""Tests for the v3 ``sharedProps`` page field.

Mirrors Laravel's ``PropsResolver::resolveSharedProps`` (3.x): deduped
top-level key names (first dot segment) of props registered via ``share()``,
emitted on every response — partial reloads included — and gated by
``INERTIA_EXPOSE_SHARED_PROP_KEYS`` (default ``True``, like Laravel's
``inertia.expose_shared_prop_keys``).
"""

from __future__ import annotations

from django.test import override_settings

from inertia.test import InertiaTestCase


class SharedPropsFieldTestCase(InertiaTestCase):
    def test_shared_keys_are_listed_in_registration_order(self) -> None:
        response = self.inertia.get("/share/")

        page = response.json()
        self.assertEqual(page["sharedProps"], ["position", "number"])
        self.assertEqual(page["props"]["position"], "goalie")
        self.assertEqual(page["props"]["number"], 29)

    def test_pages_without_shared_props_omit_the_field(self) -> None:
        response = self.inertia.get("/empty/")

        self.assertNotIn("sharedProps", response.json())

    @override_settings(INERTIA_EXPOSE_SHARED_PROP_KEYS=False)
    def test_setting_disables_the_field(self) -> None:
        response = self.inertia.get("/share/")

        self.assertNotIn("sharedProps", response.json())

    def test_shared_props_survive_partial_reload_filtering(self) -> None:
        response = self.inertia.get(
            "/share/",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            HTTP_X_INERTIA_PARTIAL_DATA="name",
        )

        page = response.json()
        self.assertEqual(page["sharedProps"], ["position", "number"])
        self.assertNotIn("position", page["props"])

    def test_dotted_keys_reduce_to_first_segment_deduped(self) -> None:
        # "auth.user", "auth.flags" AND the two-dot "auth.profile.name" all
        # collapse to the single first segment "auth".
        response = self.inertia.get("/share-dotted/")

        page = response.json()
        self.assertEqual(page["sharedProps"], ["position", "number", "auth"])
