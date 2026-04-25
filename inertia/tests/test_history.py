from django.test import override_settings

from inertia.test import InertiaTestCase


class HistoryTestCase(InertiaTestCase):
    def test_encrypt_history_setting(self):
        self.client.get("/empty/")
        assert self.page().get("encryptHistory", False) is False
        assert "encryptHistory" not in self.page()

        with override_settings(INERTIA_ENCRYPT_HISTORY=True):
            self.client.get("/empty/")
            assert self.page()["encryptHistory"] is True

    def test_encrypt_history(self):
        self.client.get("/encrypt-history/")
        assert self.page()["encryptHistory"] is True

        with override_settings(INERTIA_ENCRYPT_HISTORY=True):
            self.client.get("/no-encrypt-history/")
            assert self.page().get("encryptHistory", False) is False
            assert "encryptHistory" not in self.page()

    def test_clear_history(self):
        self.client.get("/clear-history/")
        assert self.page()["clearHistory"] is True

    def test_clear_history_redirect(self):
        response = self.client.get("/clear-history-redirect/", follow=True)
        self.assertRedirects(response, "/empty/")
        assert self.page()["clearHistory"] is True

    def test_clear_history_not_emitted_when_false(self):
        self.client.get("/empty/")
        assert "clearHistory" not in self.page()

    def test_raises_type_error(self):
        with self.assertRaisesMessage(
            TypeError, "Expected bool for encrypt_history, got str"
        ):
            self.client.get("/encrypt-history-type-error/")

        with self.assertRaisesMessage(
            TypeError, "Expected bool for clear_history, got str"
        ):
            self.client.get("/clear-history-type-error/")


class PreserveFragmentTestCase(InertiaTestCase):
    def test_preserve_fragment_emitted_when_set(self):
        self.client.get("/preserve-fragment/")
        assert self.page().get("preserveFragment") is True

    def test_preserve_fragment_is_session_pop(self):
        self.client.get("/preserve-fragment/")
        assert self.page().get("preserveFragment") is True

        self.client.get("/empty/")
        assert "preserveFragment" not in self.page()

    def test_preserve_fragment_not_emitted_when_unset(self):
        self.client.get("/empty/")
        assert "preserveFragment" not in self.page()

    def test_preserve_fragment_raises_type_error_when_non_bool(self):
        with self.assertRaisesMessage(
            TypeError, "Expected bool for preserve_fragment, got str"
        ):
            self.client.get("/preserve-fragment-type-error/")
