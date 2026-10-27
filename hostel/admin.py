from django.contrib import admin
from .models import Hostel, Block, Room, Bed

@admin.register(Hostel)
class HostelAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'gender_type', 'warden', 'is_active', 'total_capacity', 'occupied_beds_count', 'vacant_beds_count')
    list_filter = ('gender_type', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('gender_type', 'code')

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'hostel')
    list_filter = ('hostel__gender_type', 'hostel')
    search_fields = ('code', 'name', 'hostel__code', 'hostel__name')
    ordering = ('hostel', 'code')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'block', 'room_type', 'floor', 'capacity', 'has_attached_bath', 'has_ac', 'is_active')
    list_filter = ('room_type', 'has_ac', 'has_attached_bath', 'is_active', 'block__hostel')
    search_fields = ('room_number', 'block__code', 'block__hostel__code', 'block__hostel__name')
    ordering = ('block__hostel', 'block', 'room_number')

@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('bed_number', 'room', 'current_occupant', 'occupancy_status')
    list_filter = ('occupancy_status', 'room__block__hostel')
    search_fields = ('bed_number', 'room__room_number', 'room__block__hostel__code', 'current_occupant__username', 'current_occupant__first_name', 'current_occupant__last_name')
    ordering = ('room__block__hostel', 'room', 'bed_number')
