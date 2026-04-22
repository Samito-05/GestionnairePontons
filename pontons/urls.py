from django.urls import path
from . import views

urlpatterns = [
    # Planning public
    path('planning/', views.planning, name='planning'),

    # Gestionnaire
    path('gestionnaire/', views.gestionnaire, name='gestionnaire'),
    path('gestionnaire/louer/<int:pk>/', views.louer_embarcation, name='louer_embarcation'),
    path('gestionnaire/retour/<int:pk>/', views.retour_embarcation, name='retour_embarcation'),

    # API
    path('api/status/', views.api_status, name='api_status'),

    # Admin custom
    path('gestion/', views.admin_dashboard, name='admin_dashboard'),

    path('gestion/pontons/', views.admin_pontons, name='admin_pontons'),
    path('gestion/pontons/new/', views.admin_ponton_new, name='admin_ponton_new'),
    path('gestion/pontons/<int:pk>/edit/', views.admin_ponton_edit, name='admin_ponton_edit'),
    path('gestion/pontons/<int:pk>/delete/', views.admin_ponton_delete, name='admin_ponton_delete'),

    path('gestion/embarcations/', views.admin_embarcations, name='admin_embarcations'),
    path('gestion/embarcations/new/', views.admin_embarcation_new, name='admin_embarcation_new'),
    path('gestion/embarcations/<int:pk>/edit/', views.admin_embarcation_edit, name='admin_embarcation_edit'),
    path('gestion/embarcations/<int:pk>/delete/', views.admin_embarcation_delete, name='admin_embarcation_delete'),

    path('gestion/locations/', views.admin_locations, name='admin_locations'),
    path('gestion/locations/new/', views.admin_location_new, name='admin_location_new'),
    path('gestion/locations/<int:pk>/edit/', views.admin_location_edit, name='admin_location_edit'),
    path('gestion/locations/<int:pk>/delete/', views.admin_location_delete, name='admin_location_delete'),

    path('gestion/users/', views.admin_users, name='admin_users'),
    path('gestion/users/new/', views.admin_user_new, name='admin_user_new'),
    path('gestion/users/<int:pk>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('gestion/users/<int:pk>/delete/', views.admin_user_delete, name='admin_user_delete'),
]
