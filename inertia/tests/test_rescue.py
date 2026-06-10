"""Tests for ``defer(..., rescue=True)`` and the ``rescuedProps`` page field.

Mirrors Laravel's PropsResolver rescue semantics (3.x): when a rescuable
deferred prop's resolver raises during resolution, the exception is logged,
the prop is dropped from ``props``, and its key is emitted via the
``rescuedProps`` page field (only when at least one rescue happened).
"""

from __future__ import annotations

from inertia.test import InertiaTestCase, inertia_page


class RescuedDeferredPropsTestCase(InertiaTestCase):
    def partial(self, url: str, only: str):
        return self.inertia.get(
            url,
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            HTTP_X_INERTIA_PARTIAL_DATA=only,
        )

    def test_throwing_rescuable_prop_is_dropped_and_reported_in_rescued_props(
        self,
    ) -> None:
        with self.assertLogs("inertia_django_full_of_juice", level="ERROR") as logs:
            response = self.partial("/defer-rescue/", "stats")

        self.assertEqual(response.status_code, 200)
        self.assertJSONResponse(
            response, inertia_page("defer-rescue", rescued_props=["stats"])
        )
        self.assertTrue(
            any("rescuing prop 'stats'" in record for record in logs.output)
        )

    def test_successful_sibling_props_resolve_alongside_a_rescue(self) -> None:
        response = self.partial("/defer-rescue/", "stats,teams")

        page = response.json()
        self.assertEqual(page["props"]["teams"], ["Bulls"])
        self.assertNotIn("stats", page["props"])
        self.assertEqual(page["rescuedProps"], ["stats"])

    def test_rescued_props_is_omitted_when_nothing_was_rescued(self) -> None:
        response = self.partial("/defer-rescue/", "teams")

        page = response.json()
        self.assertEqual(page["props"]["teams"], ["Bulls"])
        self.assertNotIn("rescuedProps", page)

    def test_first_load_skips_deferred_resolution_and_emits_no_rescues(self) -> None:
        response = self.inertia.get("/defer-rescue/")

        page = response.json()
        self.assertNotIn("rescuedProps", page)
        self.assertEqual(page["deferredProps"], {"default": ["stats", "teams"]})
        self.assertNotIn("stats", page["props"])

    def test_non_rescuable_deferred_prop_still_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            self.partial("/defer-no-rescue/", "stats")

    def test_rescue_scan_continues_past_non_rescuable_props(self) -> None:
        # The rescuable prop is declared AFTER a healthy one: the scan must
        # keep walking (continue, not break) or the resolver explodes later
        # during the generic callable resolution.
        response = self.partial("/defer-rescue-after-ok/", "teams,stats")

        page = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(page["props"]["teams"], ["Bulls"])
        self.assertEqual(page["rescuedProps"], ["stats"])


class DeferRescueSignatureTestCase(InertiaTestCase):
    def test_defer_defaults_to_no_rescue(self) -> None:
        from inertia import defer

        prop = defer(lambda: 1)

        self.assertFalse(prop.should_rescue())
        self.assertFalse(prop.rescue)

    def test_defer_public_defaults(self) -> None:
        from inertia import defer

        prop = defer(lambda: 1)

        self.assertEqual(prop.group, "default")
        self.assertFalse(prop.should_merge())
        self.assertEqual(prop.match_on(), [])

    def test_prop_class_constructor_defaults(self) -> None:
        from inertia.prop_classes import DeferredProp, OnceProp

        deferred = DeferredProp(lambda: 1, group="g")
        self.assertFalse(deferred.should_merge())
        self.assertFalse(deferred.should_rescue())

        once_prop = OnceProp(lambda: 1)
        self.assertFalse(once_prop.fresh)
        self.assertIsNone(once_prop.key)
        self.assertIsNone(once_prop.expires_at)

    def test_defer_rescue_flag_is_carried(self) -> None:
        from inertia import defer

        prop = defer(lambda: 1, group="stats", rescue=True)

        self.assertTrue(prop.should_rescue())
        self.assertEqual(prop.group, "stats")
