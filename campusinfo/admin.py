from django.contrib import admin
from .models import (
    University, Campus, AdministrationRole, RoleStaffMember, Office,
    Faculty, Department, FeeGroup, Program, BusRoute, FAQ, ChatbotChunk,
)


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "website_domain")

    def has_add_permission(self, request):
        # singleton: block adding a second row once one exists
        return not University.objects.exists()


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ("name", "address")
    search_fields = ("name",)


class RoleStaffInline(admin.TabularInline):
    model = RoleStaffMember
    extra = 1


@admin.register(AdministrationRole)
class AdministrationRoleAdmin(admin.ModelAdmin):
    list_display = ("designation", "name", "verified")
    list_filter = ("verified",)
    search_fields = ("name", "designation")
    inlines = [RoleStaffInline]


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ("display_name", "office_type", "email", "phone", "verified")
    list_filter = ("office_type", "verified")
    search_fields = ("display_name", "email", "phone")


class ProgramInline(admin.TabularInline):
    model = Program
    extra = 0
    fields = ("name", "short_name", "program_type", "fee_status", "verified")
    show_change_link = True


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty_id")
    search_fields = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty", "department_id")
    list_filter = ("faculty",)
    search_fields = ("name",)
    inlines = [ProgramInline]


@admin.register(FeeGroup)
class FeeGroupAdmin(admin.ModelAdmin):
    list_display = ("label", "group_id", "morning_total", "afternoon_total", "verified")
    list_filter = ("verified",)
    search_fields = ("label", "group_id")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "program_type", "fee_status", "verified")
    list_filter = ("program_type", "fee_status", "verified", "department__faculty")
    search_fields = ("name", "short_name", "original_name")
    autocomplete_fields = ("department", "fee_group")


@admin.register(BusRoute)
class BusRouteAdmin(admin.ModelAdmin):
    list_display = ("route_id", "starting_point", "destination", "departure_time", "arrival_time", "driver_name", "verified")
    list_filter = ("verified", "shift_label")
    search_fields = ("starting_point", "destination", "driver_name")
    ordering = ("departure_time",)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "verified", "expires_on")
    list_filter = ("category", "verified")
    search_fields = ("question", "answer")


@admin.register(ChatbotChunk)
class ChatbotChunkAdmin(admin.ModelAdmin):
    list_display = ("title", "chunk_type", "category", "verified", "updated_at")
    list_filter = ("chunk_type", "category", "verified")
    search_fields = ("title", "content", "chunk_id")
    readonly_fields = ("updated_at",)
