from django.urls import path
from . import views
from .views import UpdateNotes
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = [
    path("", views.notes),
    path("api/update_notes", UpdateNotes.as_view()),
]



urlpatterns += staticfiles_urlpatterns()