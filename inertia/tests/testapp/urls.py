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
    path("once/", views.once_test),
    path("once-custom-key/", views.once_custom_key_test),
    path("once-fresh/", views.once_fresh_test),
    path("once-multiple/", views.once_multiple_test),
    path("once-expires-in-td/", views.once_expires_in_timedelta_test),
    path("once-expires-in-int/", views.once_expires_in_int_test),
    path("once-expires-at-dt/", views.once_expires_at_datetime_test),
    path("prepend/", views.prepend_test),
    path("prepend-match-on/", views.prepend_match_on_test),
    path("deep-merge/", views.deep_merge_test),
    path("deep-merge-match-on/", views.deep_merge_match_on_test),
    path("merge-match-on/", views.merge_match_on_test),
    path("merge-match-on-multiple/", views.merge_match_on_multiple_test),
    path("defer-match-on/", views.defer_match_on_test),
    path("infinite-scroll/", views.infinite_scroll_test),
    path("infinite-scroll-match-on/", views.infinite_scroll_match_on_test),
    path("infinite-scroll-pagination/", views.infinite_scroll_pagination_test),
    path("infinite-scroll-two/", views.infinite_scroll_two_props_test),
    path("infinite-scroll-partial/", views.infinite_scroll_partial_test),
    path("share-once/", views.share_once_test),  # type: ignore[arg-type]
    path("share-defer/", views.share_defer_test),  # type: ignore[arg-type]
    path("share-merge/", views.share_merge_test),  # type: ignore[arg-type]
    path("share-prepend/", views.share_prepend_test),  # type: ignore[arg-type]
    path("share-deep-merge/", views.share_deep_merge_test),  # type: ignore[arg-type]
    path("share-scroll/", views.share_scroll_test),  # type: ignore[arg-type]
    path("share-collision/", views.share_collision_test),  # type: ignore[arg-type]
    path("filter-merge/", views.filter_merge_props_test),
    path("filter-prepend/", views.filter_prepend_props_test),
    path("filter-deep-merge/", views.filter_deep_merge_props_test),
    path("filter-match-on/", views.filter_match_on_props_test),
    path("filter-once/", views.filter_once_props_test),
    path("filter-scroll/", views.filter_scroll_props_test),
]
