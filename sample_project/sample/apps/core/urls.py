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
]
