from inertia.test import InertiaTestCase


class InfiniteScrollTestCase(InertiaTestCase):
    def test_default_intent_is_append(self):
        page = self.inertia.get("/infinite-scroll/").json()
        self.assertEqual(page.get("mergeProps"), ["items"])
        self.assertNotIn("prependProps", page)
        self.assertEqual(
            page.get("scrollProps"),
            {
                "items": {
                    "pageName": "page",
                    "previousPage": None,
                    "nextPage": None,
                    "currentPage": None,
                    "reset": False,
                },
            },
        )

    def test_prepend_intent_routes_to_prepend_props(self):
        page = self.inertia.get(
            "/infinite-scroll/",
            HTTP_X_INERTIA_INFINITE_SCROLL_MERGE_INTENT="prepend",
        ).json()
        self.assertEqual(page.get("prependProps"), ["items"])
        self.assertNotIn("mergeProps", page)
        self.assertEqual(
            page.get("scrollProps"),
            {
                "items": {
                    "pageName": "page",
                    "previousPage": None,
                    "nextPage": None,
                    "currentPage": None,
                    "reset": False,
                },
            },
        )

    def test_append_intent_matches_default(self):
        page = self.inertia.get(
            "/infinite-scroll/",
            HTTP_X_INERTIA_INFINITE_SCROLL_MERGE_INTENT="append",
        ).json()
        self.assertEqual(page.get("mergeProps"), ["items"])
        self.assertNotIn("prependProps", page)
        self.assertIn("scrollProps", page)

    def test_unknown_intent_falls_back_to_append(self):
        page = self.inertia.get(
            "/infinite-scroll/",
            HTTP_X_INERTIA_INFINITE_SCROLL_MERGE_INTENT="foo",
        ).json()
        self.assertEqual(page.get("mergeProps"), ["items"])
        self.assertNotIn("prependProps", page)
        self.assertIn("scrollProps", page)

    def test_reset_drops_from_merge_buckets_but_emits_scroll_with_reset_true(self):
        page = self.inertia.get(
            "/infinite-scroll-match-on/",
            HTTP_X_INERTIA_RESET="items",
        ).json()
        self.assertNotIn("mergeProps", page)
        self.assertNotIn("prependProps", page)
        self.assertNotIn("matchPropsOn", page)
        self.assertEqual(
            page.get("scrollProps"),
            {
                "items": {
                    "pageName": "page",
                    "previousPage": None,
                    "nextPage": None,
                    "currentPage": None,
                    "reset": True,
                },
            },
        )

    def test_match_on_emits_dot_prefixed_paths(self):
        page = self.inertia.get("/infinite-scroll-match-on/").json()
        self.assertEqual(page.get("mergeProps"), ["items"])
        self.assertEqual(page.get("matchPropsOn"), ["items.id"])
        self.assertIn("scrollProps", page)
        self.assertEqual(page["scrollProps"]["items"]["reset"], False)

    def test_pagination_metadata_round_trips(self):
        page = self.inertia.get("/infinite-scroll-pagination/").json()
        self.assertEqual(
            page.get("scrollProps"),
            {
                "items": {
                    "pageName": "cursor",
                    "previousPage": 2,
                    "nextPage": 4,
                    "currentPage": 3,
                    "reset": False,
                },
            },
        )

    def test_two_scroll_props_route_correctly(self):
        page = self.inertia.get(
            "/infinite-scroll-two/",
            HTTP_X_INERTIA_INFINITE_SCROLL_MERGE_INTENT="prepend",
        ).json()
        self.assertEqual(set(page.get("prependProps", [])), {"items", "feed"})
        self.assertNotIn("mergeProps", page)
        scroll = page.get("scrollProps", {})
        self.assertEqual(set(scroll.keys()), {"items", "feed"})
        self.assertEqual(scroll["items"]["currentPage"], 1)
        self.assertEqual(scroll["feed"]["currentPage"], 5)
        self.assertFalse(scroll["items"]["reset"])
        self.assertFalse(scroll["feed"]["reset"])

    def test_partial_data_includes_scroll_prop_value_and_metadata(self):
        page = self.inertia.get(
            "/infinite-scroll-partial/",
            HTTP_X_INERTIA_PARTIAL_DATA="items",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertIn("items", page["props"])
        self.assertEqual(page["props"]["items"], [{"id": 1}, {"id": 2}])
        self.assertNotIn("name", page["props"])
        self.assertEqual(page.get("mergeProps"), ["items"])
        self.assertEqual(
            page.get("scrollProps"),
            {
                "items": {
                    "pageName": "page",
                    "previousPage": None,
                    "nextPage": None,
                    "currentPage": 2,
                    "reset": False,
                },
            },
        )

    def test_partial_except_omits_value_but_still_emits_scroll_metadata(self):
        # Decision: we walk ``self.props`` for scrollProps, mirroring
        # ``build_merge_kinds`` and ``build_once_props``. So the
        # registry entry survives even when partial-except removes the
        # value from ``props``. Document this behavior in the test.
        page = self.inertia.get(
            "/infinite-scroll-partial/",
            HTTP_X_INERTIA_PARTIAL_DATA="name,items",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="items",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertNotIn("items", page["props"])
        self.assertIn("name", page["props"])
        self.assertEqual(page.get("mergeProps"), ["items"])
        self.assertIn("scrollProps", page)
        self.assertEqual(page["scrollProps"]["items"]["reset"], False)
