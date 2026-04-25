from django.urls import path

from . import views

urlpatterns = [
    path("test/", views.test),
    path("empty/", views.empty_test),
    path("redirect/", views.redirect_test),
    path("props/", views.props_test),
    path("template_data/", views.template_data_test),
    path("lazy/", views.lazy_test),
    path("optional/", views.optional_test),
    path("defer/", views.defer_test),
    path("defer-group/", views.defer_group_test),
    path("merge/", views.merge_test),
    path("complex-props/", views.complex_props_test),
    path("share/", views.share_test),  # type: ignore[arg-type]
    path("inertia-redirect/", views.inertia_redirect_test),
    path("external-redirect/", views.external_redirect_test),
    path("encrypt-history/", views.encrypt_history_test),
    path("no-encrypt-history/", views.encrypt_history_false_test),
    path("encrypt-history-type-error/", views.encrypt_history_type_error_test),
    path("clear-history/", views.clear_history_test),
    path("clear-history-redirect/", views.clear_history_redirect_test),
    path("clear-history-type-error/", views.clear_history_type_error_test),
    path("errors-share/", views.errors_share_test),  # type: ignore[arg-type]
    path("errors-per-render/", views.errors_per_render_test),
    path("partial-except/", views.partial_except_test),
    path("partial-except-deferred/", views.partial_except_with_deferred_test),
    path("fragment-redirect/", views.fragment_redirect_test),
    path("preserve-fragment/", views.preserve_fragment_view),
    path("preserve-fragment-type-error/", views.preserve_fragment_type_error_test),
    path("errors-response/", views.errors_response_view),
    path("errors-response-custom/", views.errors_response_custom_view),
    path("inertia-redirect-helper/", views.inertia_redirect_helper_test),
]
