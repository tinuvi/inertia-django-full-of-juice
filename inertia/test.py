from json import dumps, loads
from typing import Any
from unittest.mock import patch

from django.template.loader import render_to_string as base_render_to_string
from django.test import Client, TestCase

from inertia.settings import resolve_inertia_version


class ClientWithLastResponse:
    def __init__(self, client):
        self.client = client
        self.last_response = None

    def get(self, *args, **kwargs):
        self.last_response = self.client.get(*args, **kwargs)
        return self.last_response

    def __getattr__(self, name):
        return getattr(self.client, name)


class BaseInertiaTestCase:
    def setUp(self):
        self.inertia = ClientWithLastResponse(Client(HTTP_X_INERTIA=True))
        self.client = ClientWithLastResponse(Client())

    def last_response(self):
        return self.inertia.last_response or self.client.last_response

    def assertJSONResponse(self, response, json_obj):
        self.assertEqual(response.headers["Content-Type"], "application/json")
        self.assertEqual(response.json(), json_obj)


class InertiaTestCase(BaseInertiaTestCase, TestCase):
    def setUp(self):
        super().setUp()

        self.mock_inertia = patch(
            "inertia.http.render_to_string", wraps=base_render_to_string
        )
        self.mock_render = self.mock_inertia.start()

    def tearDown(self):
        self.mock_inertia.stop()

    def page(self):
        page_data = (
            self.mock_render.call_args[0][1]["page"]
            if self.mock_render.call_args
            else self.last_response().content
        )

        return loads(page_data)

    def props(self):
        return self.page()["props"]

    def merge_props(self):
        return self.page()["mergeProps"]

    def deferred_props(self):
        return self.page()["deferredProps"]

    def template_data(self):
        context = self.mock_render.call_args[0][1]
        return {
            key: context[key]
            for key in context
            if key not in ["page", "inertia_layout"]
        }

    def component(self):
        return self.page()["component"]

    def assertIncludesProps(self, props):
        self.assertDictEqual(self.props(), {**self.props(), **props})

    def assertHasExactProps(self, props):
        self.assertDictEqual(self.props(), props)

    def assertIncludesTemplateData(self, template_data):
        self.assertDictEqual(
            self.template_data(), {**self.template_data(), **template_data}
        )

    def assertHasExactTemplateData(self, template_data):
        self.assertDictEqual(self.template_data(), template_data)

    def assertComponentUsed(self, component_name):
        self.assertEqual(component_name, self.component())


def inertia_page(
    url,
    component="TestComponent",
    props=None,
    template_data=None,
    deferred_props=None,
    merge_props=None,
    prepend_props=None,
    deep_merge_props=None,
    match_props_on=None,
    once_props=None,
    scroll_props=None,
    encrypt_history: bool = False,
    clear_history: bool = False,
    preserve_fragment: bool = False,
    flash: dict[str, Any] | None = None,
    shared_props: list[str] | None = None,
    rescued_props: list[str] | None = None,
):
    props = props or {}
    template_data = template_data or {}
    if "errors" not in props:
        props = {**props, "errors": {}}
    _page: dict[str, Any] = {
        "component": component,
        "props": props,
        "url": f"/{url}/",
        "version": resolve_inertia_version(),
    }

    conditional_fields: dict[str, Any] = {
        # Truthiness-gated, like the library's own emission: the three
        # one-shot flags emit a literal True, deferredProps only when
        # non-empty.
        "encryptHistory": True if encrypt_history else None,
        "clearHistory": True if clear_history else None,
        "preserveFragment": True if preserve_fragment else None,
        "deferredProps": deferred_props or None,
        # Presence-gated: any non-None value is emitted verbatim, empty
        # containers included.
        "mergeProps": merge_props,
        "prependProps": prepend_props,
        "deepMergeProps": deep_merge_props,
        "matchPropsOn": match_props_on,
        "onceProps": once_props,
        "scrollProps": scroll_props,
        "flash": flash,
        "sharedProps": shared_props,
        "rescuedProps": rescued_props,
    }
    for key, value in conditional_fields.items():
        if value is not None:
            _page[key] = value

    return _page


def inertia_div(*args, **kwargs):
    page = inertia_page(*args, **kwargs)
    safe_data = (
        dumps(page)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("/", "\\u002f")
    )
    return f'<script data-page="app" type="application/json">{safe_data}</script>'
