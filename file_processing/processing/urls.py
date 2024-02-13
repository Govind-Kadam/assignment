from django.urls import path
from .views import *

urlpatterns = [
    path("process/", ProcessingAPI.as_view()),
]