from django.urls import path
from . import views as v

urlpatterns = [
    path("", v.index, name="index"),
    path("api/dashboard", v.dashboard),
    path("api/library", v.library),
    path("api/upload", v.upload),
    path("api/ask", v.ask),
    path("api/quiz/next", v.quiz_next),
    path("api/quiz/answer", v.quiz_answer),
    path("api/topics/<int:tid>/ppt", v.topic_ppt),
    path("api/topics/<int:tid>/notes", v.topic_notes),
    path("login", v.login_page, name="login"),
    path("api/auth/register", v.auth_register),
    path("api/auth/login", v.auth_login),
    path("api/auth/demo", v.auth_demo),
    path("api/auth/logout", v.auth_logout),
    path("api/courses", v.courses),
    path("api/courses/create", v.course_create),
    path("api/courses/select", v.course_select),
    path("api/courses/delete", v.course_delete),
    path("api/paste", v.paste),
    path("api/reset", v.reset_progress),
]
