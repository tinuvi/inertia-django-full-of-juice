from inertia.test import InertiaTestCase, inertia_page


class TestTestCase(InertiaTestCase):
    def test_include_props(self):
        self.client.get("/props/")

        self.assertIncludesProps({"name": "Brandon"})

    def test_has_exact_props(self):
        self.client.get("/props/")

        self.assertHasExactProps({"name": "Brandon", "sport": "Hockey", "errors": {}})

    def test_has_template_data(self):
        self.client.get("/template_data/")

        self.assertIncludesTemplateData({"name": "Brian"})

    def test_has_exact_template_data(self):
        self.client.get("/template_data/")

        self.assertHasExactTemplateData({"name": "Brian", "sport": "Basketball"})

    def test_component_name(self):
        self.client.get("/props/")

        self.assertComponentUsed("TestComponent")

    def test_merge_props_helper_returns_merge_props(self):
        self.inertia.get("/merge/")

        self.assertEqual(self.merge_props(), ["sport", "team"])

    def test_deferred_props_helper_returns_deferred_props(self):
        self.inertia.get("/defer/")

        self.assertEqual(self.deferred_props(), {"default": ["sport"]})


class InertiaPageHelperTestCase(InertiaTestCase):
    """Exercises the optional ``inertia_page`` keyword arguments so the
    test helper itself is fully covered."""

    def test_inertia_page_supports_history_and_fragment_flags(self):
        page = inertia_page(
            "x",
            encrypt_history=True,
            clear_history=True,
            preserve_fragment=True,
        )
        self.assertTrue(page["encryptHistory"])
        self.assertTrue(page["clearHistory"])
        self.assertTrue(page["preserveFragment"])

    def test_inertia_page_supports_all_registry_kwargs(self):
        page = inertia_page(
            "x",
            prepend_props=["foo"],
            deep_merge_props=["bar"],
            match_props_on=["foo.id"],
            once_props={"foo": {"prop": "foo", "expiresAt": None}},
            scroll_props={"foo": {"pageName": "page"}},
        )
        self.assertEqual(page["prependProps"], ["foo"])
        self.assertEqual(page["deepMergeProps"], ["bar"])
        self.assertEqual(page["matchPropsOn"], ["foo.id"])
        self.assertEqual(page["onceProps"], {"foo": {"prop": "foo", "expiresAt": None}})
        self.assertEqual(page["scrollProps"], {"foo": {"pageName": "page"}})
