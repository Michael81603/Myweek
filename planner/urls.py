from django.urls import path

from . import views

urlpatterns = [
    path("connexion/", views.login_view, name="login"),
    path("inscription/", views.signup_view, name="signup"),
    path("deconnexion/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("taches/", views.task_list, name="tasks"),
    path("taches/ajouter/", views.task_form, name="task_add"),
    path("taches/<int:pk>/modifier/", views.task_form, name="task_edit"),
    path("taches/<int:pk>/terminer/", views.task_done, name="task_done"),
    path("taches/<int:pk>/supprimer/", views.task_delete, name="task_delete"),
    path("habitudes/", views.habit_list, name="habits"),
    path("habitudes/ajouter/", views.habit_form, name="habit_add"),
    path("habitudes/<int:pk>/modifier/", views.habit_form, name="habit_edit"),
    path("habitudes/<int:pk>/cocher/", views.habit_toggle, name="habit_toggle"),
    path("habitudes/<int:pk>/supprimer/", views.habit_delete, name="habit_delete"),
    path("emploi-du-temps/", views.schedule, name="schedule"),
    path("emploi-du-temps/export-pdf/", views.schedule_pdf, name="schedule_pdf"),
    path("emploi-du-temps/ajouter/", views.schedule_form, name="schedule_add"),
    path("emploi-du-temps/<int:pk>/modifier/", views.schedule_form, name="schedule_edit"),
    path("emploi-du-temps/<int:pk>/supprimer/", views.schedule_delete, name="schedule_delete"),
    path("statistiques/", views.statistics, name="statistics"),
    path("parametres/", views.settings_view, name="settings"),
]
