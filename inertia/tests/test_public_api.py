"""Tests pinning the package's public import surface.

The README documents ``from inertia import encrypt_history`` /
``clear_history`` (and now the v3 additions) — these imports are a
documented contract, so their presence in ``inertia.__all__`` is pinned
here to prevent regressions like the pre-0.5.0 missing exports.
"""

from __future__ import annotations

from django.test import RequestFactory, SimpleTestCase

import inertia
from inertia import is_inertia

DOCUMENTED_EXPORTS = [
    "InertiaResponse",
    "back",
    "clear_history",
    "deep_merge",
    "defer",
    "encrypt_history",
    "errors_response",
    "flash",
    "flash_errors",
    "inertia",
    "inertia_redirect",
    "infinite_scroll",
    "is_inertia",
    "is_precognitive",
    "lazy",
    "location",
    "merge",
    "once",
    "optional",
    "precognition",
    "prepend",
    "preserve_fragment",
    "render",
    "share",
]


class PublicApiTestCase(SimpleTestCase):
    def test_every_documented_name_is_importable_and_exported(self) -> None:
        for name in DOCUMENTED_EXPORTS:
            with self.subTest(name=name):
                self.assertTrue(hasattr(inertia, name))
                self.assertIn(name, inertia.__all__)

    def test_all_only_lists_real_attributes(self) -> None:
        for name in inertia.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(inertia, name))


class IsInertiaHelperTestCase(SimpleTestCase):
    def test_detects_the_x_inertia_header(self) -> None:
        factory = RequestFactory()

        self.assertTrue(is_inertia(factory.get("/", HTTP_X_INERTIA="true")))
        self.assertFalse(is_inertia(factory.get("/")))
