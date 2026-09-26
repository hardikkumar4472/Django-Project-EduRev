"""
Occupancy Service & P03 Integration Boundary Interface.
Encapsulates room queries, bed occupancy validation, and integration with
the master University Housing system (P03 adapter).
"""
from typing import Dict, Any, List, Optional
from .models import Bed, Room, Hostel

class OccupancyProviderInterface:
    """Interface contract for University Master Occupancy Management (P03)."""
    def get_student_bed(self, student_id: int) -> Optional[Bed]:
        raise NotImplementedError

    def verify_bed_available(self, bed_id: int) -> bool:
        raise NotImplementedError

    def sync_occupancy_snapshot(self) -> Dict[str, Any]:
        raise NotImplementedError


class LocalOccupancyService(OccupancyProviderInterface):
    """
    Standard native ORM implementation of the occupancy provider.
    Fulfills Phase 05 adapter requirements.
    """
    def get_student_bed(self, student_id: int) -> Optional[Bed]:
        try:
            return Bed.objects.select_related('room__block__hostel', 'current_occupant').get(current_occupant_id=student_id)
        except Bed.DoesNotExist:
            return None

    def verify_bed_available(self, bed_id: int) -> bool:
        return Bed.objects.filter(id=bed_id, occupancy_status=Bed.OccupancyStatus.VACANT).exists()

    def get_room_visual_matrix(self, room_id: int) -> Dict[str, Any]:
        room = Room.objects.select_related('block__hostel').prefetch_related('beds__current_occupant').get(id=room_id)
        beds_data = []
        for bed in room.beds.all():
            beds_data.append({
                'id': bed.id,
                'bed_number': bed.bed_number,
                'status': bed.occupancy_status,
                'occupant_name': bed.current_occupant.get_full_name() if bed.current_occupant else None,
                'occupant_uid': bed.current_occupant.university_id if bed.current_occupant else None,
                'occupant_id': bed.current_occupant.id if bed.current_occupant else None,
            })
        return {
            'room_id': room.id,
            'room_number': room.room_number,
            'block': room.block.name,
            'hostel': room.block.hostel.name,
            'capacity': room.capacity,
            'room_type': room.get_room_type_display(),
            'beds': beds_data,
        }

    def sync_occupancy_snapshot(self) -> Dict[str, Any]:
        total_beds = Bed.objects.count()
        occupied = Bed.objects.filter(occupancy_status=Bed.OccupancyStatus.OCCUPIED).count()
        vacant = Bed.objects.filter(occupancy_status=Bed.OccupancyStatus.VACANT).count()
        locked = Bed.objects.filter(occupancy_status=Bed.OccupancyStatus.LOCKED_FOR_TRANSFER).count()
        return {
            'total_beds': total_beds,
            'occupied': occupied,
            'vacant': vacant,
            'locked_for_transfer': locked,
            'occupancy_rate_pct': round((occupied / total_beds * 100), 1) if total_beds > 0 else 0
        }

# Global singleton provider instance
occupancy_service = LocalOccupancyService()
