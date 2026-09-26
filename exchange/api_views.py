from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.utils import timezone
from hostel.models import Hostel, Room, Bed
from exchange.models import ExchangeRequest, ExchangeProposal, TransferRecord
from .serializers import (
    RoomSerializer,
    BedSerializer,
    ExchangeRequestSerializer,
    ExchangeProposalSerializer,
    TransferRecordSerializer
)
from .services.eligibility_service import EligibilityService
from .services.matching_service import MatchingService
from .services.proposal_service import ProposalService
from .services.occupancy_service import AtomicOccupancyEngine, OccupancyTransferError

class HealthCheckAPI(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'platform': 'EduRev P04 Hostel Exchange',
            'database': 'Operational',
            'matching_engine': 'Operational',
            'atomic_occupancy': 'Verified'
        })

class HostelListAPI(APIView):
    def get(self, request):
        hostels = Hostel.objects.filter(is_active=True).values('id', 'name', 'code', 'gender_type')
        return Response(list(hostels))

class RoomListAPI(APIView):
    def get(self, request):
        rooms = Room.objects.filter(is_active=True).select_related('block__hostel').prefetch_related('beds')[:100]
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data)

class ExchangeRequestListCreateAPI(APIView):
    def get(self, request):
        if request.user.is_warden or request.user.is_admin_role:
            requests_qs = ExchangeRequest.objects.all().select_related('requester', 'current_bed__room')[:100]
        else:
            requests_qs = ExchangeRequest.objects.filter(requester=request.user).select_related('requester', 'current_bed__room')
        serializer = ExchangeRequestSerializer(requests_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Validate eligibility first
        validation = EligibilityService.validate_student_eligibility(request.user)
        if not validation['eligible']:
            return Response({'success': False, 'eligibility': validation}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExchangeRequestSerializer(data=request.data)
        if serializer.is_valid():
            current_bed = getattr(request.user, 'allocated_bed', None)
            save_kwargs = {
                'requester': request.user,
                'current_bed': current_bed,
                'status': ExchangeRequest.RequestStatus.ACTIVE,
            }
            if current_bed and current_bed.room:
                save_kwargs['preferred_room_type'] = current_bed.room.room_type

            req_obj = serializer.save(**save_kwargs)
            return Response(ExchangeRequestSerializer(req_obj).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MatchingEngineAPI(APIView):
    def get(self, request):
        target_id = request.user.id if request.user.is_student else None
        matches = MatchingService.find_cycles(target_student_id=target_id)
        return Response({'count': len(matches), 'matches': matches})

class ProposalListAPI(APIView):
    def get(self, request):
        if request.user.is_warden or request.user.is_admin_role or request.user.is_dsw:
            proposals = ExchangeProposal.objects.all().prefetch_related('participants__student')[:50]
        else:
            proposals = ExchangeProposal.objects.filter(participants__student=request.user).prefetch_related('participants__student')
        serializer = ExchangeProposalSerializer(proposals, many=True)
        return Response(serializer.data)

class ProposalRespondAPI(APIView):
    def post(self, request, pk):
        proposal = get_object_or_404(ExchangeProposal, id=pk)
        decision = request.data.get('decision', '').upper()
        if decision not in ['ACCEPT', 'DECLINE']:
            return Response({'error': "Decision must be either 'ACCEPT' or 'DECLINE'"}, status=status.HTTP_400_BAD_REQUEST)

        result = ProposalService.respond_to_proposal(proposal, request.user, decision)
        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

class ProposalApproveAPI(APIView):
    def post(self, request, pk):
        if not (request.user.is_warden or request.user.is_admin_role):
            return Response({'error': 'Unauthorized: Only Wardens can approve room exchanges'}, status=status.HTTP_403_FORBIDDEN)

        proposal = get_object_or_404(ExchangeProposal, id=pk)
        remarks = request.data.get('remarks', 'Approved via DRF API')
        try:
            res = AtomicOccupancyEngine.execute_proposal_atomic(proposal.id, request.user, remarks=remarks)
            return Response(res, status=status.HTTP_200_OK)
        except OccupancyTransferError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

class TransferListAPI(APIView):
    def get(self, request):
        if request.user.is_warden or request.user.is_admin_role or request.user.is_dsw:
            transfers = TransferRecord.objects.all().select_related('student', 'previous_bed__room', 'new_bed__room', 'approved_by')[:100]
        else:
            transfers = TransferRecord.objects.filter(student=request.user).select_related('student', 'previous_bed__room', 'new_bed__room', 'approved_by')
        serializer = TransferRecordSerializer(transfers, many=True)
        return Response(serializer.data)
