from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'university_id', 'role', 'gender', 'first_name', 'last_name', 'email', 'is_staff', 'is_active')
    list_filter = ('role', 'gender', 'is_staff', 'is_active', 'has_fee_clearance', 'has_disciplinary_hold')
    search_fields = ('username', 'university_id', 'first_name', 'last_name', 'email')
    ordering = ('role', 'username')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Campus & Residence Info', {
            'fields': ('university_id', 'role', 'gender', 'phone', 'has_fee_clearance', 'has_disciplinary_hold', 'last_transferred_at')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Campus & Residence Info', {
            'fields': ('university_id', 'role', 'gender', 'phone')
        }),
    )
