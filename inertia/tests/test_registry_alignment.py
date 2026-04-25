"""Tests for alignment with Laravel's ``PropsResolver`` registry semantics.

Two divergences are covered here:

* **Fix #1** — registries (once / deferred / merge / prepend / deep-merge /
  match-on / scroll) must include props injected via
  :func:`inertia.share` in addition to the per-request props passed to
  :func:`inertia.render`. Laravel's ``PropsResolver::resolve()`` walks
  the merged set, so we mirror that behaviour.

* **Fix #2** — when the request is a partial render, registry entries
  must be stripped according to ``X-Inertia-Partial-Data``,
  ``X-Inertia-Partial-Except``, and (for the merge family)
  ``X-Inertia-Reset``. This mirrors
  ``PropsResolver::collectMergeableMetadata()`` and
  ``PropsResolver::collectOnceMetadata()``.
"""

from inertia.test import InertiaTestCase


class SharedPropsRegistriesTestCase(InertiaTestCase):
    """Fix #1 — registries pick up props injected via ``share()``."""

    def test_shared_once_prop_appears_in_once_registry(self):
        page = self.inertia.get("/share-once/").json()
        self.assertIn("shared_plans", page["props"])
        self.assertEqual(
            page.get("onceProps"),
            {"shared_plans": {"prop": "shared_plans", "expiresAt": None}},
        )

    def test_shared_defer_prop_appears_in_deferred_registry(self):
        page = self.inertia.get("/share-defer/").json()
        # Deferred props are ignored on first load.
        self.assertNotIn("shared_sport", page["props"])
        self.assertEqual(page.get("deferredProps"), {"default": ["shared_sport"]})

    def test_shared_merge_prop_appears_in_merge_and_match_on_registries(self):
        page = self.inertia.get("/share-merge/").json()
        self.assertEqual(page["props"]["shared_users"], [{"id": 1}])
        self.assertEqual(page.get("mergeProps"), ["shared_users"])
        self.assertEqual(page.get("matchPropsOn"), ["shared_users.id"])

    def test_shared_prepend_prop_appears_in_prepend_registry(self):
        page = self.inertia.get("/share-prepend/").json()
        self.assertEqual(page["props"]["shared_notifications"], ["a"])
        self.assertEqual(page.get("prependProps"), ["shared_notifications"])

    def test_shared_deep_merge_prop_appears_in_deep_merge_registry(self):
        page = self.inertia.get("/share-deep-merge/").json()
        self.assertEqual(page["props"]["shared_filters"], {"a": 1})
        self.assertEqual(page.get("deepMergeProps"), ["shared_filters"])

    def test_shared_scroll_prop_appears_in_scroll_registry(self):
        page = self.inertia.get("/share-scroll/").json()
        self.assertEqual(page["props"]["shared_items"], [{"id": 1}])
        self.assertEqual(page.get("mergeProps"), ["shared_items"])
        self.assertIn("scrollProps", page)
        self.assertEqual(page["scrollProps"]["shared_items"]["currentPage"], 2)
        self.assertFalse(page["scrollProps"]["shared_items"]["reset"])

    def test_per_request_prop_overrides_shared_prop_on_key_collision(self):
        # Mirrors Laravel's ``array_merge($shared, $perRequest)`` ordering.
        page = self.inertia.get("/share-collision/").json()
        self.assertEqual(page["props"]["name"], "from-per-request")


class RegistryFilteringOnPartialReloadsTestCase(InertiaTestCase):
    """Fix #2 — partial-data / partial-except / reset filter registry entries."""

    # --- mergeProps ---

    def test_partial_except_strips_merge_props_entry(self):
        page = self.inertia.get(
            "/filter-merge/",
            HTTP_X_INERTIA_PARTIAL_DATA="foo,bar",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="foo",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(page.get("mergeProps"), ["bar"])
        self.assertNotIn("foo", page["props"])

    def test_partial_data_only_keeps_listed_merge_props_entry(self):
        page = self.inertia.get(
            "/filter-merge/",
            HTTP_X_INERTIA_PARTIAL_DATA="bar",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(page.get("mergeProps"), ["bar"])
        self.assertNotIn("foo", page["props"])

    def test_reset_strips_merge_props_entry(self):
        page = self.inertia.get(
            "/filter-merge/",
            HTTP_X_INERTIA_RESET="foo",
        ).json()
        self.assertEqual(page.get("mergeProps"), ["bar"])

    # --- prependProps ---

    def test_partial_except_strips_prepend_props_entry(self):
        page = self.inertia.get(
            "/filter-prepend/",
            HTTP_X_INERTIA_PARTIAL_DATA="foo,bar",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="foo",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(page.get("prependProps"), ["bar"])

    def test_partial_data_only_keeps_listed_prepend_props_entry(self):
        page = self.inertia.get(
            "/filter-prepend/",
            HTTP_X_INERTIA_PARTIAL_DATA="bar",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(page.get("prependProps"), ["bar"])

    def test_reset_strips_prepend_props_entry(self):
        page = self.inertia.get(
            "/filter-prepend/",
            HTTP_X_INERTIA_RESET="bar",
        ).json()
        self.assertEqual(page.get("prependProps"), ["foo"])

    # --- deepMergeProps ---

    def test_partial_except_strips_deep_merge_props_entry(self):
        page = self.inertia.get(
            "/filter-deep-merge/",
            HTTP_X_INERTIA_PARTIAL_DATA="foo,bar",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="foo",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(page.get("deepMergeProps"), ["bar"])

    def test_partial_data_only_keeps_listed_deep_merge_props_entry(self):
        page = self.inertia.get(
            "/filter-deep-merge/",
            HTTP_X_INERTIA_PARTIAL_DATA="bar",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(page.get("deepMergeProps"), ["bar"])

    def test_reset_strips_deep_merge_props_entry(self):
        page = self.inertia.get(
            "/filter-deep-merge/",
            HTTP_X_INERTIA_RESET="foo",
        ).json()
        self.assertEqual(page.get("deepMergeProps"), ["bar"])

    # --- matchPropsOn ---

    def test_partial_except_strips_match_props_on_entries(self):
        page = self.inertia.get(
            "/filter-match-on/",
            HTTP_X_INERTIA_PARTIAL_DATA="foo,bar",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="foo",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(page.get("matchPropsOn"), ["bar.id"])
        self.assertEqual(page.get("mergeProps"), ["bar"])

    def test_reset_strips_match_props_on_entries(self):
        page = self.inertia.get(
            "/filter-match-on/",
            HTTP_X_INERTIA_RESET="foo",
        ).json()
        self.assertEqual(page.get("matchPropsOn"), ["bar.id"])

    # --- onceProps ---

    def test_partial_except_strips_once_props_entry(self):
        page = self.inertia.get(
            "/filter-once/",
            HTTP_X_INERTIA_PARTIAL_DATA="foo,bar",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="foo",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(
            page.get("onceProps"),
            {"bar": {"prop": "bar", "expiresAt": None}},
        )

    def test_partial_data_only_keeps_listed_once_props_entry(self):
        page = self.inertia.get(
            "/filter-once/",
            HTTP_X_INERTIA_PARTIAL_DATA="bar",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        self.assertEqual(
            page.get("onceProps"),
            {"bar": {"prop": "bar", "expiresAt": None}},
        )

    def test_reset_strips_once_props_entry(self):
        page = self.inertia.get(
            "/filter-once/",
            HTTP_X_INERTIA_RESET="foo",
        ).json()
        # ``X-Inertia-Reset`` without partial-data is not a partial render,
        # but the reset path is honoured for once metadata to mirror
        # Laravel's ``collectOnceMetadata``.
        self.assertEqual(
            page.get("onceProps"),
            {"bar": {"prop": "bar", "expiresAt": None}},
        )

    # --- scrollProps ---

    def test_partial_except_strips_scroll_props_entry(self):
        page = self.inertia.get(
            "/filter-scroll/",
            HTTP_X_INERTIA_PARTIAL_DATA="foo,bar",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="foo",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        scroll = page.get("scrollProps", {})
        self.assertNotIn("foo", scroll)
        self.assertIn("bar", scroll)
        # Merge family also stripped.
        self.assertEqual(page.get("mergeProps"), ["bar"])

    def test_partial_data_only_keeps_listed_scroll_props_entry(self):
        page = self.inertia.get(
            "/filter-scroll/",
            HTTP_X_INERTIA_PARTIAL_DATA="bar",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        ).json()
        scroll = page.get("scrollProps", {})
        self.assertEqual(set(scroll.keys()), {"bar"})
