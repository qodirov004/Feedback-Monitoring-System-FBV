from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Avg, Count
from .models import (
    User, Teacher, Student, Class, 
    Evaluation, Parents
)
from django.utils.safestring import mark_safe


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Qo\'shimcha ma\'lumotlar', {'fields': ('role',)}),
    )

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_level', 'section', 'student_count', 'average_score_display')
    list_filter = ('grade_level',)
    search_fields = ('name',)
    readonly_fields = ('created_at',)
    
    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = 'O\'quvchilar soni'
    
    @admin.display(description="O'rtacha ball")
    def average_score_display(self, obj):
        avg = obj.average_score or 0
        color = 'green' if avg >= 85 else 'orange' if avg >= 70 else 'red'
        avg_formatted = f"{float(avg):.2f}"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, avg_formatted
        )
    average_score_display.short_description = 'O\'rtacha ball'

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'class_assigned', 'is_active', 'evaluation_count', 'average_score_display', "image")
    list_filter = ('is_active', 'class_assigned__grade_level')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    readonly_fields = ('hire_date',)
    
    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'To\'liq ism'
    
    def evaluation_count(self, obj):
        return obj.evaluations.count()
    evaluation_count.short_description = 'Baholashlar soni'
    
    def average_score_display(self, obj):
        avg = obj.average_score_given or 0
        if avg > 0:
            color = 'green' if avg >= 85 else 'orange' if avg >= 70 else 'red'
            avg_formatted = f"{avg:.1f}"
            return format_html(
                '<span style="color: {};">{}</span>',
                color, avg_formatted
            )
        return '-'
    average_score_display.short_description = 'O\'rtacha ball'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'class_assigned', 'student_id', 'evaluation_count', 'average_score_display', 'performance_status', "image")
    list_filter = ('class_assigned', 'enrollment_date')
    search_fields = ('first_name', 'last_name', 'student_id')
    readonly_fields = ('enrollment_date',)
    
    def evaluation_count(self, obj):
        return obj.evaluations.count()
    evaluation_count.short_description = 'Baholashlar soni'
    
    def average_score_display(self, obj):
        avg = obj.average_score or 0  # None bo'lsa 0
        if avg > 0:
            color = 'green' if avg >= 85 else 'orange' if avg >= 70 else 'red'
            avg_formatted = f"{avg:.1f}"
            return format_html(
                '<span style="color: {};">{}</span>',
                color, avg_formatted
            )
        return '-'
    average_score_display.short_description = 'O\'rtacha ball'

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'colored_total_score', 'grade_status', 'week_number', 'year', 'created_at')
    list_filter = ('year', 'week_number', 'student__class_assigned', 'created_at')
    search_fields = (
        'student__first_name',
        'student__last_name',
        'teacher__user__first_name',
        'teacher__user__last_name'
    )
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('student', 'teacher', 'week_number', 'year')
        }),
        ('Baholash', {
            'fields': ('homework_score', 'discipline_score', 'uniform_score')
        }),
        ("Qo'shimcha", {
            'fields': ('comment', 'created_at', 'updated_at')
        }),
    )

    def colored_total_score(self, obj):
        try:
            total = float(obj.total_score)  # SafeString bo'lsa, float() bilan aniq floatga o‘tkazamiz
        except (TypeError, ValueError):
            return "-"
        color = 'green' if total >= 85 else 'orange' if total >= 70 else 'red'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{total:.1f}/100</span>')

    colored_total_score.short_description = "Jami ball"

    def grade_status(self, obj):
        return obj.grade_status
    grade_status.short_description = "Bahosi"

# @admin.register(SystemSettings)
# class SystemSettingsAdmin(admin.ModelAdmin):
#     list_display = ('key', 'value', 'description', 'updated_at')
#     search_fields = ('key', 'description')
#     readonly_fields = ('created_at', 'updated_at')

@admin.register(Parents)
class ParentsAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'student_name', 'student_code')
    list_display_links = ('student_name', 'telegram_id')

    @admin.display(description="Ism-Familiyasi")
    def student_name(self, obj):
        if obj.student_id:
            return f'{obj.student_id.first_name} {obj.student_id.last_name}'
        return "-"

    @admin.display(description="Student ID")
    def student_code(self, obj):
        return obj.student_id.student_id if obj.student_id else "-"

# Admin site sozlamalari
admin.site.site_header = 'Feedback Monitoring System'
admin.site.site_title = 'FMS Admin'
admin.site.index_title = 'Boshqaruv paneli'