from django.urls import path
from . import views

urlpatterns = [
    path('', views.rms_dashboard_view, name='rms_dashboard'),
    path('log/', views.create_rms_request_view, name='rms_create'),
    path('tickets/<int:pk>/', views.rms_ticket_detail_view, name='rms_ticket_detail'),
    path('tickets/<int:pk>/escalate/', views.escalate_rms_request_view, name='rms_escalate'),
    path('tickets/<int:pk>/resolve/', views.resolve_rms_request_view, name='rms_resolve'),
    path('tickets/<int:pk>/comment/', views.add_rms_comment_view, name='rms_comment'),
    path('tickets/<int:pk>/rate/', views.rate_rms_request_view, name='rms_rate'),
]

