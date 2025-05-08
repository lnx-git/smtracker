from django.urls import path

from . import views

app_name = 'smtracker'
urlpatterns = [
    path('', views.default_page, name='default_page'),
    path('robots/', views.robot_list, name='robot_list'),
    path('robots/edit/', views.robot_registration_edit, name='robot_registration_edit'),
    path('rounds/', views.round_list, name='round_list'),
    path('rounds/<int:round_id>/results/', views.match_results, name='match_results'),
    path('rounds/<int:round_id>/scheduled/', views.scheduled_matches, name='scheduled_matches'),
    path('rounds/<int:round_id>/round_results/', views.round_results, name='round_results'),
]
