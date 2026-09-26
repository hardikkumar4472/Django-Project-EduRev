from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('claim-bed/', views.claim_bed_view, name='claim_bed'),
    path('admin/users/', views.admin_users_list_view, name='admin_users_list'),
    path('admin/users/create/', views.admin_user_create_view, name='admin_user_create'),
    path('admin/users/<int:pk>/modify/', views.admin_user_modify_view, name='admin_user_modify'),
    path('admin/users/<int:pk>/delete/', views.admin_user_delete_view, name='admin_user_delete'),
]

