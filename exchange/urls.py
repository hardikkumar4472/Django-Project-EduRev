from django.urls import path
from . import views

urlpatterns = [
    # Phase 20: Landing & Student Views
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.student_dashboard, name='dashboard'),
    path('exchange-requests/new/', views.create_request_view, name='create_request'),
    path('exchange-requests/<int:pk>/withdraw/', views.withdraw_request_view, name='withdraw_request'),
    path('matches/', views.cycle_explorer_view, name='matches'),
    path('initiate-proposal/', views.initiate_proposal_view, name='initiate_proposal'),
    path('proposals/<int:pk>/', views.proposal_detail_view, name='proposal_detail'),
    path('proposals/<int:pk>/respond/', views.respond_proposal_view, name='respond_proposal'),
    
    # Phase 13 & 15: Warden & Transfers
    path('warden/approvals/', views.warden_dashboard_view, name='warden_approvals'),
    path('warden/approvals/<int:pk>/', views.warden_review_view, name='warden_review'),
    path('transfers/', views.transfers_list_view, name='transfers_list'),
    path('transfers/<int:pk>/', views.transfer_letter_view, name='transfer_letter'),

    # Phase 17 & 18: Admin & Dean & Concurrency
    path('admin/policies/', views.admin_policies_view, name='admin_policies'),
    path('dean/analytics/', views.analytics_dashboard_view, name='dean_analytics'),
    path('admin/analytics/', views.analytics_dashboard_view, name='admin_analytics'),
    path('admin/audit/', views.analytics_dashboard_view, name='admin_audit'),
    path('admin/concurrency/', views.concurrency_demo_view, name='concurrency_demo'),
    path('rooms/<int:pk>/', views.room_detail_view, name='room_detail'),
    path('rooms/', views.room_detail_view, name='room_detail_default'),
]
