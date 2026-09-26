from django.urls import path
from . import views

urlpatterns = [
    path('', views.hostels_list_view, name='hostels_list'),
    path('create/', views.hostel_create_view, name='hostel_create'),
    path('<int:pk>/delete/', views.hostel_delete_view, name='hostel_delete'),
    path('<int:pk>/toggle/', views.hostel_toggle_status_view, name='hostel_toggle_status'),
]
