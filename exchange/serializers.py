from rest_framework import serializers
from accounts.models import User
from hostel.models import Hostel, Block, Room, Bed
from exchange.models import (
    PolicyRule,
    ExchangeRequest,
    ExchangeProposal,
    ProposalParticipant,
    TransferRecord,
    AuditEntry
)

class BedSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    hostel_name = serializers.CharField(source='room.block.hostel.name', read_only=True)
    occupant_name = serializers.CharField(source='current_occupant.get_full_name', read_only=True)

    class Meta:
        model = Bed
        fields = ['id', 'bed_number', 'room_number', 'hostel_name', 'occupancy_status', 'occupant_name']


class RoomSerializer(serializers.ModelSerializer):
    beds = BedSerializer(many=True, read_only=True)
    hostel_name = serializers.CharField(source='block.hostel.name', read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'room_number', 'floor', 'room_type', 'capacity', 'hostel_name', 'beds']


class ExchangeRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requester.get_full_name', read_only=True)
    current_room = serializers.CharField(source='current_bed.room.room_number', read_only=True)

    class Meta:
        model = ExchangeRequest
        fields = [
            'id', 'requester', 'requester_name', 'current_bed', 'current_room',
            'preferred_hostel', 'preferred_room_type', 'preferred_floor',
            'status', 'reason', 'created_at'
        ]
        read_only_fields = ['requester', 'current_bed', 'status', 'created_at']


class ProposalParticipantSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    university_id = serializers.CharField(source='student.university_id', read_only=True)
    current_room = serializers.CharField(source='current_bed.room.room_number', read_only=True)
    target_room = serializers.CharField(source='target_bed.room.room_number', read_only=True)

    class Meta:
        model = ProposalParticipant
        fields = ['id', 'student', 'student_name', 'university_id', 'current_room', 'target_room', 'response', 'responded_at', 'order_index']


class ExchangeProposalSerializer(serializers.ModelSerializer):
    participants = ProposalParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = ExchangeProposal
        fields = [
            'id', 'proposal_code', 'proposal_type', 'status',
            'compatibility_score', 'expires_at', 'created_at', 'participants'
        ]


class TransferRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    university_id = serializers.CharField(source='student.university_id', read_only=True)
    previous_room = serializers.CharField(source='previous_bed.room.room_number', read_only=True)
    new_room = serializers.CharField(source='new_bed.room.room_number', read_only=True)
    approver_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = TransferRecord
        fields = [
            'id', 'transfer_code', 'student_name', 'university_id',
            'previous_room', 'new_room', 'approver_name', 'completed_at', 'verification_token'
        ]
