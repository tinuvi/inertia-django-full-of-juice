import time
from datetime import datetime, timezone

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from inertia import once
from inertia.test import InertiaTestCase, inertia_div, inertia_page


class FirstLoadTestCase(InertiaTestCase):
    def test_with_props(self):
        self.assertContains(
            self.client.get("/props/"),
            inertia_div(
                "props",
                props={
                    "name": "Brandon",
                    "sport": "Hockey",
                },
            ),
        )

    def test_with_template_data(self):
        response = self.client.get("/template_data/")

        self.assertContains(
            response,
            inertia_div(
                "template_data",
                template_data={
                    "name": "Brian",
                    "sport": "Basketball",
                },
            ),
        )

        self.assertContains(response, "template data:Brian, Basketball")

    def test_with_no_data(self):
        self.assertContains(self.client.get("/empty/"), inertia_div("empty"))

    def test_proper_status_code(self):
        self.assertEqual(self.client.get("/empty/").status_code, 200)

    def test_template_rendered(self):
        self.assertTemplateUsed(self.client.get("/empty/"), "inertia.html")


class SubsequentLoadTestCase(InertiaTestCase):
    def test_with_props(self):
        self.assertJSONResponse(
            self.inertia.get("/props/"),
            inertia_page(
                "props",
                props={
                    "name": "Brandon",
                    "sport": "Hockey",
                },
            ),
        )

    def test_with_template_data(self):
        self.assertJSONResponse(
            self.inertia.get("/template_data/"),
            inertia_page(
                "template_data",
                template_data={
                    "name": "Brian",
                    "sport": "Basketball",
                },
            ),
        )

    def test_with_no_data(self):
        self.assertJSONResponse(self.inertia.get("/empty/"), inertia_page("empty"))

    def test_proper_status_code(self):
        self.assertEqual(self.inertia.get("/empty/").status_code, 200)

    def test_redirects_from_inertia_views(self):
        self.assertEqual(self.inertia.get("/inertia-redirect/").status_code, 302)


class LazyPropsTestCase(InertiaTestCase):
    def test_lazy_props_are_not_included(self):
        with self.assertWarns(DeprecationWarning):
            self.assertJSONResponse(
                self.inertia.get("/lazy/"),
                inertia_page("lazy", props={"name": "Brian"}),
            )

    def test_lazy_props_are_included_when_requested(self):
        with self.assertWarns(DeprecationWarning):
            self.assertJSONResponse(
                self.inertia.get(
                    "/lazy/",
                    HTTP_X_INERTIA_PARTIAL_DATA="sport,grit",
                    HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
                ),
                inertia_page("lazy", props={"sport": "Basketball", "grit": "intense"}),
            )


class OptionalPropsTestCase(InertiaTestCase):
    def test_optional_props_are_not_included(self):
        self.assertJSONResponse(
            self.inertia.get("/optional/"),
            inertia_page("optional", props={"name": "Brian"}),
        )

    def test_optional_props_are_included_when_requested(self):
        self.assertJSONResponse(
            self.inertia.get(
                "/optional/",
                HTTP_X_INERTIA_PARTIAL_DATA="sport,grit",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            ),
            inertia_page("optional", props={"sport": "Basketball", "grit": "intense"}),
        )


class ComplexPropsTestCase(InertiaTestCase):
    def test_nested_callable_props_work(self):
        self.assertJSONResponse(
            self.inertia.get("/complex-props/"),
            inertia_page("complex-props", props={"person": {"name": "Brandon"}}),
        )


class ShareTestCase(InertiaTestCase):
    def test_that_shared_props_are_merged(self):
        self.assertJSONResponse(
            self.inertia.get("/share/"),
            inertia_page(
                "share", props={"name": "Brandon", "position": "goalie", "number": 29}
            ),
        )

        self.assertHasExactProps(
            {"name": "Brandon", "position": "goalie", "number": 29, "errors": {}}
        )


class CSRFTestCase(InertiaTestCase):
    def test_that_csrf_inclusion_is_automatic(self):
        response = self.inertia.get("/props/")

        self.assertIsNotNone(response.cookies.get("csrftoken"))

    def test_that_csrf_is_included_even_on_initial_page_load(self):
        response = self.client.get("/props/")

        self.assertIsNotNone(response.cookies.get("csrftoken"))


class DeferredPropsTestCase(InertiaTestCase):
    def test_deferred_props_are_set(self):
        self.assertJSONResponse(
            self.inertia.get("/defer/"),
            inertia_page(
                "defer", props={"name": "Brian"}, deferred_props={"default": ["sport"]}
            ),
        )

    def test_deferred_props_are_grouped(self):
        self.assertJSONResponse(
            self.inertia.get("/defer-group/"),
            inertia_page(
                "defer-group",
                props={"name": "Brian"},
                deferred_props={"group": ["sport", "team"], "default": ["grit"]},
            ),
        )

    def test_deferred_props_are_included_when_requested(self):
        self.assertJSONResponse(
            self.inertia.get(
                "/defer/",
                HTTP_X_INERTIA_PARTIAL_DATA="sport",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            ),
            inertia_page("defer", props={"sport": "Basketball"}),
        )

    def test_only_deferred_props_in_group_are_included_when_requested(self):
        self.assertJSONResponse(
            self.inertia.get(
                "/defer-group/",
                HTTP_X_INERTIA_PARTIAL_DATA="sport,team",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            ),
            inertia_page("defer-group", props={"sport": "Basketball", "team": "Bulls"}),
        )

        self.assertJSONResponse(
            self.inertia.get(
                "/defer-group/",
                HTTP_X_INERTIA_PARTIAL_DATA="grit",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            ),
            inertia_page("defer-group", props={"grit": "intense"}),
        )


class MergePropsTestCase(InertiaTestCase):
    def test_merge_props_are_included_on_initial_load(self):
        self.assertJSONResponse(
            self.inertia.get("/merge/"),
            inertia_page(
                "merge",
                props={
                    "name": "Brandon",
                    "sport": "Hockey",
                },
                merge_props=["sport", "team"],
                deferred_props={"default": ["team"]},
            ),
        )

    def test_deferred_merge_props_are_included_on_subsequent_load(self):
        # Mirrors Laravel's ``PropsResolver::collectMergeableMetadata``:
        # on a partial render, ``mergeProps`` only includes the keys the
        # client asked for. ``sport`` is not in
        # ``X-Inertia-Partial-Data`` here, so it is stripped from the
        # registry as well as from the resolved props.
        self.assertJSONResponse(
            self.inertia.get(
                "/merge/",
                HTTP_X_INERTIA_PARTIAL_DATA="team",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            ),
            inertia_page(
                "merge",
                props={
                    "team": "Penguins",
                },
                merge_props=["team"],
            ),
        )

    def test_merge_props_are_not_included_when_reset(self):
        self.assertJSONResponse(
            self.inertia.get(
                "/merge/",
                HTTP_X_INERTIA_PARTIAL_DATA="sport,team",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
                HTTP_X_INERTIA_RESET="sport,team",
            ),
            inertia_page(
                "merge",
                props={
                    "sport": "Hockey",
                    "team": "Penguins",
                },
            ),
        )


class PrependPropsTestCase(InertiaTestCase):
    def test_prepend_prop_appears_in_prepend_props(self):
        page = self.inertia.get("/prepend/").json()
        self.assertEqual(page.get("prependProps"), ["notifications"])
        self.assertNotIn("mergeProps", page)
        self.assertNotIn("matchPropsOn", page)

    def test_prepend_prop_with_match_on(self):
        page = self.inertia.get("/prepend-match-on/").json()
        self.assertEqual(page.get("prependProps"), ["notifications"])
        self.assertEqual(page.get("matchPropsOn"), ["notifications.id"])

    def test_reset_excludes_from_prepend_and_match_on(self):
        page = self.inertia.get(
            "/prepend-match-on/",
            HTTP_X_INERTIA_RESET="notifications",
        ).json()
        self.assertNotIn("prependProps", page)
        self.assertNotIn("matchPropsOn", page)


class DeepMergePropsTestCase(InertiaTestCase):
    def test_deep_merge_prop_appears_in_deep_merge_props(self):
        page = self.inertia.get("/deep-merge/").json()
        self.assertEqual(page.get("deepMergeProps"), ["filters"])
        self.assertNotIn("mergeProps", page)
        self.assertNotIn("prependProps", page)
        self.assertNotIn("matchPropsOn", page)

    def test_deep_merge_with_match_on_paths(self):
        page = self.inertia.get("/deep-merge-match-on/").json()
        self.assertEqual(page.get("deepMergeProps"), ["filters"])
        self.assertEqual(
            page.get("matchPropsOn"),
            ["filters.nested.id", "filters.id"],
        )

    def test_reset_excludes_from_deep_merge_and_match_on(self):
        page = self.inertia.get(
            "/deep-merge-match-on/",
            HTTP_X_INERTIA_RESET="filters",
        ).json()
        self.assertNotIn("deepMergeProps", page)
        self.assertNotIn("matchPropsOn", page)


class MergeMatchOnTestCase(InertiaTestCase):
    def test_merge_with_match_on_emits_match_props_on(self):
        page = self.inertia.get("/merge-match-on/").json()
        self.assertEqual(page.get("mergeProps"), ["users"])
        self.assertEqual(page.get("matchPropsOn"), ["users.id"])

    def test_merge_with_multiple_match_on_paths_in_order(self):
        page = self.inertia.get("/merge-match-on-multiple/").json()
        self.assertEqual(page.get("mergeProps"), ["posts"])
        self.assertEqual(
            page.get("matchPropsOn"),
            ["posts.data.id", "posts.id"],
        )

    def test_merge_without_match_on_emits_only_merge_props(self):
        page = self.inertia.get("/merge/").json()
        self.assertIn("mergeProps", page)
        self.assertNotIn("matchPropsOn", page)


class DeferMatchOnTestCase(InertiaTestCase):
    def test_defer_merge_with_match_on(self):
        page = self.inertia.get("/defer-match-on/").json()
        self.assertEqual(page.get("mergeProps"), ["users"])
        self.assertEqual(page.get("matchPropsOn"), ["users.id"])
        self.assertEqual(page.get("deferredProps"), {"default": ["users"]})


class MisconfiguredLayoutTestCase(InertiaTestCase):
    def test_with_props(self):
        with (
            override_settings(INERTIA_LAYOUT=None),
            self.assertRaisesMessage(
                ImproperlyConfigured,
                "INERTIA_LAYOUT must be set",
            ),
        ):
            self.client.get("/props/")


class ErrorsAutoInjectTestCase(InertiaTestCase):
    def test_errors_present_on_every_response(self):
        self.inertia.get("/empty/")
        self.assertEqual(self.props().get("errors"), {})

    def test_errors_present_with_props(self):
        self.inertia.get("/props/")
        self.assertEqual(self.props().get("errors"), {})

    def test_user_provided_errors_via_share_are_preserved(self):
        self.inertia.get("/errors-share/")
        self.assertEqual(self.props().get("errors"), {"name": "Required"})

    def test_user_provided_errors_via_per_render_props_are_preserved(self):
        self.inertia.get("/errors-per-render/")
        self.assertEqual(self.props().get("errors"), {"sport": "Invalid"})

    def test_errors_survives_partial_reload(self):
        self.inertia.get(
            "/props/",
            HTTP_X_INERTIA_PARTIAL_DATA="name",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        page_props = self.props()
        self.assertIn("errors", page_props)
        self.assertEqual(page_props["errors"], {})
        self.assertIn("name", page_props)
        self.assertNotIn("sport", page_props)


class PartialExceptTestCase(InertiaTestCase):
    def test_only_with_except(self):
        self.inertia.get(
            "/partial-except/",
            HTTP_X_INERTIA_PARTIAL_DATA="name,sport,team",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="team",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        page_props = self.props()
        self.assertIn("name", page_props)
        self.assertIn("sport", page_props)
        self.assertNotIn("team", page_props)
        self.assertNotIn("grit", page_props)

    def test_except_overrides_only(self):
        self.inertia.get(
            "/partial-except/",
            HTTP_X_INERTIA_PARTIAL_DATA="name,sport",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="sport",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        page_props = self.props()
        self.assertIn("name", page_props)
        self.assertNotIn("sport", page_props)

    def test_except_with_deferred(self):
        self.inertia.get(
            "/partial-except-deferred/",
            HTTP_X_INERTIA_PARTIAL_DATA="sport,team",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="team",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        page_props = self.props()
        self.assertIn("sport", page_props)
        self.assertEqual(page_props["sport"], "Basketball")
        self.assertNotIn("team", page_props)

    def test_except_alone_without_partial_data(self):
        # The v3 client emits ``router.reload({ except: [...] })`` with only
        # ``X-Inertia-Partial-Except`` and ``X-Inertia-Partial-Component`` —
        # no ``X-Inertia-Partial-Data``. The protocol expects this to be
        # honored as a partial render. Mirrors Laravel's
        # ``PropsResolver`` predicate, which keys off the component header
        # alone (see ``inertiajs/inertia-laravel`` 3.x
        # ``src/PropsResolver.php``).
        self.inertia.get(
            "/partial-except/",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="name",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        page_props = self.props()
        self.assertNotIn("name", page_props)
        self.assertIn("sport", page_props)
        self.assertIn("team", page_props)
        self.assertIn("grit", page_props)

    def test_except_alone_suppresses_deferred_props(self):
        # ``deferredProps`` must be suppressed on a partial render — otherwise
        # the v3 client would refetch every deferred group on every
        # ``router.reload({ except: [...] })`` call.
        self.inertia.get(
            "/partial-except-deferred/",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="team",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        self.assertNotIn("deferredProps", self.page())


class ErrorsResponseTestCase(InertiaTestCase):
    def test_default_status_and_shape(self):
        response = self.client.get("/errors-response/")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(
            response.json(),
            {
                "message": "The given data was invalid.",
                "errors": {
                    "email": "Required",
                    "password": ["Too short", "Too weak"],
                },
            },
        )

    def test_custom_message_and_status(self):
        response = self.client.get("/errors-response-custom/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "message": "Custom message",
                "errors": {"name": "Required"},
            },
        )


class OncePropsTestCase(InertiaTestCase):
    def test_initial_load_resolves_and_emits_registry(self):
        self.assertJSONResponse(
            self.inertia.get("/once/"),
            inertia_page(
                "once",
                props={"name": "Brian", "plans": ["A", "B"]},
                once_props={"plans": {"prop": "plans", "expiresAt": None}},
            ),
        )

    def test_subsequent_request_with_except_omits_value_keeps_registry(self):
        self.inertia.get("/once/", HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="plans")
        page_props = self.props()
        self.assertNotIn("plans", page_props)
        self.assertIn("name", page_props)
        self.assertEqual(
            self.page()["onceProps"],
            {"plans": {"prop": "plans", "expiresAt": None}},
        )

    def test_custom_key_in_registry(self):
        self.inertia.get("/once-custom-key/")
        page = self.page()
        self.assertEqual(page["props"].get("plans"), ["A", "B"])
        self.assertEqual(
            page["onceProps"],
            {"custom-key": {"prop": "plans", "expiresAt": None}},
        )

    def test_custom_key_in_except_header_omits_value(self):
        self.inertia.get(
            "/once-custom-key/",
            HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="custom-key",
        )
        page = self.page()
        self.assertNotIn("plans", page["props"])
        self.assertEqual(
            page["onceProps"],
            {"custom-key": {"prop": "plans", "expiresAt": None}},
        )

    def test_fresh_overrides_except_header(self):
        self.inertia.get("/once-fresh/", HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="plans")
        page = self.page()
        self.assertEqual(page["props"].get("plans"), ["A", "B"])
        self.assertEqual(
            page["onceProps"],
            {"plans": {"prop": "plans", "expiresAt": None}},
        )

    def test_partial_reload_with_key_in_partial_data_always_resolves(self):
        self.inertia.get(
            "/once/",
            HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="plans",
            HTTP_X_INERTIA_PARTIAL_DATA="plans",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        page = self.page()
        self.assertEqual(page["props"].get("plans"), ["A", "B"])
        self.assertEqual(
            page["onceProps"],
            {"plans": {"prop": "plans", "expiresAt": None}},
        )

    def test_multiple_once_props_in_one_response(self):
        self.inertia.get("/once-multiple/")
        page = self.page()
        self.assertEqual(page["props"].get("plans"), ["A", "B"])
        self.assertEqual(page["props"].get("config"), {"x": 1})
        self.assertEqual(
            page["onceProps"],
            {
                "plans": {"prop": "plans", "expiresAt": None},
                "config": {"prop": "config", "expiresAt": None},
            },
        )

    def test_expires_in_timedelta_emits_numeric_expires_at(self):
        before_ms = int(time.time() * 1000) + 60_000
        self.inertia.get("/once-expires-in-td/")
        after_ms = int(time.time() * 1000) + 60_000
        page = self.page()
        expires_at = page["onceProps"]["plans"]["expiresAt"]
        self.assertIsInstance(expires_at, int)
        self.assertGreaterEqual(expires_at, before_ms - 2_000)
        self.assertLessEqual(expires_at, after_ms + 2_000)

    def test_expires_in_int_seconds_emits_numeric_expires_at(self):
        before_ms = int(time.time() * 1000) + 30_000
        self.inertia.get("/once-expires-in-int/")
        after_ms = int(time.time() * 1000) + 30_000
        page = self.page()
        expires_at = page["onceProps"]["plans"]["expiresAt"]
        self.assertIsInstance(expires_at, int)
        self.assertGreaterEqual(expires_at, before_ms - 2_000)
        self.assertLessEqual(expires_at, after_ms + 2_000)

    def test_expires_at_datetime_emits_correct_ms(self):
        target = datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        expected_ms = int(target.timestamp() * 1000)
        self.inertia.get("/once-expires-at-dt/")
        page = self.page()
        self.assertEqual(page["onceProps"]["plans"]["expiresAt"], expected_ms)

    def test_dual_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            once(lambda: ["A"], expires_in=60, expires_at=1234567890123)
