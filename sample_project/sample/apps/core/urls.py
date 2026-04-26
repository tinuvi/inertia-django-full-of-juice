from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("lazy/", views.lazy_page, name="lazy"),
    path("lists/", views.lists_page, name="lists"),
    path("feed/", views.feed_page, name="feed"),
    path("form/", views.form_page, name="form"),
    path("form/submit/", views.form_submit, name="form-submit"),
    path("redirect-fragment/", views.redirect_fragment, name="redirect-fragment"),
    path("preserve-fragment/", views.preserve_fragment_view, name="preserve-fragment"),
    path("inertia-redirect/", views.inertia_redirect_view, name="inertia-redirect"),
    path("location/", views.external_location_view, name="location"),
    path("history/", views.history_page, name="history"),
    path("clear-history/", views.clear_history_view, name="clear-history"),
    path(
        "history-after-clear/",
        views.history_after_clear,
        name="history-after-clear",
    ),
    path("method/", views.method_page, name="method"),
    path("method/submit/", views.method_handler, name="method-submit"),
    path("validate/", views.validate_page, name="validate"),
    path("api/validate/", views.validate_api, name="validate-api"),
]
