from django.urls import path
from . import views

urlpatterns = [
    path('', views.transcription_view, name='index'),
]
