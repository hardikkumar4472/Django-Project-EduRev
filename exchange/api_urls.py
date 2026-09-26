from django.urls import path
from . import api_views

urlpatterns = [
    path('health/', api_views.HealthCheckAPI.as_view(), name='api_health'),
    path('hostels/', api_views.HostelListAPI.as_view(), name='api_hostels'),
    path('rooms/', api_views.RoomListAPI.as_view(), name='api_rooms'),
    path('exchange-requests/', api_views.ExchangeRequestListCreateAPI.as_view(), name='api_exchange_requests'),
    path('matches/', api_views.MatchingEngineAPI.as_view(), name='api_matches'),
    path('proposals/', api_views.ProposalListAPI.as_view(), name='api_proposals'),
    path('proposals/<int:pk>/respond/', api_views.ProposalRespondAPI.as_view(), name='api_proposal_respond'),
    path('proposals/<int:pk>/approve/', api_views.ProposalApproveAPI.as_view(), name='api_proposal_approve'),
    path('transfers/', api_views.TransferListAPI.as_view(), name='api_transfers'),
]
