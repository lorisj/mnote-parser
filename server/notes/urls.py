from django.urls import path
from . import views
from .views import UpdateNotes, RemoveNotes
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = [
    path("", views.notes),
    path("api/update_notes", UpdateNotes.as_view()),
    path("api/remove_notes", RemoveNotes.as_view()),
]



urlpatterns += staticfiles_urlpatterns()