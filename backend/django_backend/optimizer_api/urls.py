from django.urls import path
from .views import upload_excel, add_entity

urlpatterns = [
    path("upload-excel/", upload_excel),
    path("add-entity/", add_entity),
]