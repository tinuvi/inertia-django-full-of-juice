from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inertia.tests.settings")

import django  # noqa: E402

django.setup()

from django.test.runner import DiscoverRunner  # noqa: E402
from django.test.utils import _TestState, setup_test_environment  # noqa: E402

if not hasattr(_TestState, "saved_data"):
    setup_test_environment()
    _runner = DiscoverRunner(verbosity=0, keepdb=True)
    _runner.setup_databases()
