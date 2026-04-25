import time
from datetime import datetime, timedelta, timezone
from importlib.resources import files
from unittest import TestCase

from inertia.prop_classes import (
    DeferredProp,
    IgnoreOnFirstLoadProp,
    MergeableProp,
    MergeProp,
    OnceProp,
    OptionalProp,
)
from inertia.utils import defer, lazy, merge, once, optional


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


class OnceHelperTestCase(TestCase):
    def test_returns_once_prop(self):
        prop = once(lambda: "Basketball")
        self.assertIsInstance(prop, OnceProp)

    def test_default_key_is_none(self):
        self.assertIsNone(once(lambda: "x").key)

    def test_custom_key_is_preserved(self):
        self.assertEqual(once(lambda: "x", key="custom").key, "custom")

    def test_default_fresh_flag_is_false(self):
        self.assertFalse(once(lambda: "x").fresh)

    def test_fresh_flag_is_set(self):
        self.assertTrue(once(lambda: "x", fresh=True).fresh)

    def test_default_expires_at_is_none(self):
        self.assertIsNone(once(lambda: "x").expires_at)

    def test_resolves_callable_value(self):
        self.assertEqual(once(lambda: "Basketball")(), "Basketball")

    def test_resolves_static_value(self):
        self.assertEqual(once("Basketball")(), "Basketball")

    def test_expires_in_timedelta_resolves_to_ms(self):
        before_ms = int(time.time() * 1000) + 60_000
        prop = once(lambda: "x", expires_in=timedelta(seconds=60))
        after_ms = int(time.time() * 1000) + 60_000
        self.assertIsNotNone(prop.expires_at)
        assert prop.expires_at is not None
        self.assertGreaterEqual(prop.expires_at, before_ms - 2_000)
        self.assertLessEqual(prop.expires_at, after_ms + 2_000)

    def test_expires_in_int_seconds_resolves_to_ms(self):
        before_ms = int(time.time() * 1000) + 30_000
        prop = once(lambda: "x", expires_in=30)
        after_ms = int(time.time() * 1000) + 30_000
        self.assertIsNotNone(prop.expires_at)
        assert prop.expires_at is not None
        self.assertGreaterEqual(prop.expires_at, before_ms - 2_000)
        self.assertLessEqual(prop.expires_at, after_ms + 2_000)

    def test_expires_at_aware_datetime_resolves_to_ms(self):
        target = datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        expected_ms = int(target.timestamp() * 1000)
        prop = once(lambda: "x", expires_at=target)
        self.assertEqual(prop.expires_at, expected_ms)

    def test_expires_at_naive_datetime_assumed_utc(self):
        naive = datetime(2030, 1, 1, 0, 0, 0)
        expected_ms = int(naive.replace(tzinfo=timezone.utc).timestamp() * 1000)
        prop = once(lambda: "x", expires_at=naive)
        self.assertEqual(prop.expires_at, expected_ms)

    def test_expires_at_int_passes_through_as_ms(self):
        prop = once(lambda: "x", expires_at=1234567890123)
        self.assertEqual(prop.expires_at, 1234567890123)

    def test_dual_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            once(lambda: "x", expires_in=60, expires_at=1234567890123)

    def test_is_not_ignored_on_first_load(self):
        prop = once(lambda: "x")
        self.assertNotIsInstance(prop, IgnoreOnFirstLoadProp)

    def test_is_not_mergeable(self):
        prop = once(lambda: "x")
        self.assertNotIsInstance(prop, MergeableProp)
