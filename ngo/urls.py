from django.urls import path

from . import views

app_name = "ngo"

urlpatterns = [
    path("activities/", views.activity_list, name="activity_list"),
    path("admin/ngos/api/", views.admin_ngo_api, name="admin_ngo_api"),
    path("admin/ngos/", views.admin_ngo_manage, name="admin_ngo_manage"),
    path("admin/ngos/create/", views.admin_ngo_create, name="admin_ngo_create"),
    path("admin/ngos/<int:ngo_id>/update/", views.admin_ngo_update, name="admin_ngo_update"),
    path("admin/ngos/<int:ngo_id>/delete/", views.admin_ngo_delete, name="admin_ngo_delete"),
    path("admin/activities/", views.admin_activity_manage, name="admin_activity_manage"),
    path("admin/activities/create/", views.admin_activity_create, name="admin_activity_create"),
    path(
        "admin/activities/<int:activity_id>/update/",
        views.admin_activity_update,
        name="admin_activity_update",
    ),
    path(
        "admin/activities/<int:activity_id>/delete/",
        views.admin_activity_delete,
        name="admin_activity_delete",
    ),
]

