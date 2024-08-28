from django.contrib import admin
from django.urls import path, include
from home import views  # Adicione esta linha

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.transcription_view, name='index'),
]