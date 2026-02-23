from django.urls import path
from .views import upload_and_optimize, add_entity_and_reoptimize

urlpatterns = [
    path("upload/", upload_and_optimize),
    path("add-entity/", add_entity_and_reoptimize),
]