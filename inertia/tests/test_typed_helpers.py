from importlib.resources import files
from unittest import TestCase

from inertia.prop_classes import (
    DeferredProp,
    IgnoreOnFirstLoadProp,
    MergeableProp,
    MergeProp,
    OptionalProp,
)
from inertia.utils import defer, lazy, merge, optional


class PyTypedMarkerTestCase(TestCase):
    def test_marker_ships_with_installed_package(self):
        marker = files("inertia").joinpath("py.typed")
        self.assertTrue(
            marker.is_file(),
            "py.typed marker is not part of the installed `inertia` package",
        )


class OptionalHelperTestCase(TestCase):
    def test_returns_optional_prop(self):
        self.assertIsInstance(optional(lambda: "value"), OptionalProp)

    def test_is_ignored_on_first_load(self):
        self.assertIsInstance(optional(lambda: "value"), IgnoreOnFirstLoadProp)

    def test_resolves_callable_value(self):
        prop = optional(lambda: "Basketball")
        self.assertEqual(prop(), "Basketball")

    def test_resolves_static_value(self):
        prop = optional("Basketball")
        self.assertEqual(prop(), "Basketball")


class LazyHelperTestCase(TestCase):
    def test_emits_deprecation_warning(self):
        with self.assertWarns(DeprecationWarning):
            lazy(lambda: "Basketball")

    def test_returns_optional_prop(self):
        with self.assertWarns(DeprecationWarning):
            prop = lazy(lambda: "Basketball")
        self.assertIsInstance(prop, OptionalProp)
        self.assertEqual(prop(), "Basketball")


class DeferHelperTestCase(TestCase):
    def test_returns_deferred_prop(self):
        prop = defer(lambda: "Basketball")
        self.assertIsInstance(prop, DeferredProp)
        self.assertIsInstance(prop, MergeableProp)
        self.assertIsInstance(prop, IgnoreOnFirstLoadProp)

    def test_default_group(self):
        self.assertEqual(defer(lambda: "x").group, "default")

    def test_custom_group(self):
        self.assertEqual(defer(lambda: "x", "stats").group, "stats")

    def test_does_not_merge_by_default(self):
        self.assertFalse(defer(lambda: "x").should_merge())

    def test_merges_when_flag_is_set(self):
        self.assertTrue(defer(lambda: "x", merge=True).should_merge())

    def test_resolves_callable_value(self):
        self.assertEqual(defer(lambda: "Basketball")(), "Basketball")


class MergeHelperTestCase(TestCase):
    def test_returns_merge_prop(self):
        prop = merge(lambda: "Basketball")
        self.assertIsInstance(prop, MergeProp)
        self.assertIsInstance(prop, MergeableProp)

    def test_always_merges(self):
        self.assertTrue(merge(lambda: "x").should_merge())

    def test_resolves_callable_value(self):
        self.assertEqual(merge(lambda: "Basketball")(), "Basketball")
