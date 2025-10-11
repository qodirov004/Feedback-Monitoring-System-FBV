# Django imports
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

# Local imports
from . import views

# App URLs
app_name = 'feedback'

urlpatterns = [
    # Authentication URLs
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Manager URLs
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    
    # Manager - Teachers
    path('manager/teachers/', views.manager_teachers, name='manager_teachers'),
    path('manager/teachers/create/', views.manager_teachers_create, name='manager_teachers_create'),
    path('manager/teachers/<int:teacher_id>/detail/', views.manager_teachers_detail, name='manager_teachers_detail'),
    path('manager/teachers/<int:teacher_id>/edit/', views.manager_teachers_edit, name='manager_teachers_edit'),
    path('manager/teachers/<int:teacher_id>/delete/', views.manager_teachers_delete, name='manager_teachers_delete'),
    path("download-template-teacher/", views.download_teacher_template, name="download_teacher_template"),
    path("upload-teachers", views.upload_teachers_excel, name="upload_teachers_excel"),
    
    # Manager - Students
    path('manager/students/', views.manager_students, name='manager_students'),
    path('manager/students/create/', views.manager_students_create, name='manager_students_create'),
    path('manager/students/<int:student_id>/edit/', views.manager_students_edit, name='manager_students_edit'),
    path('manager/students/<int:student_id>/detail/', views.manager_students_detail, name='manager_students_detail'),
    path('manager/students/<int:student_id>/delete/', views.manager_students_delete, name='manager_students_delete'),
    path('upload-students/', views.upload_students_excel, name='upload_students_excel'),
    path('download-template/', views.download_student_template, name='download_student_template'),
    
    # Manager - Classes
    path('manager/classes/', views.manager_classes, name='manager_classes'),
    path('manager/classes/create/', views.manager_classes_create, name='manager_classes_create'),
    path('manager/class/delete/<int:id>/', views.manager_class_delete, name='manager_class_delete'),
    
    # Manager - Statistics
    path('manager/statistics/', views.manager_statistics, name='manager_statistics'),
    path('manager/teacher/statistics', views.manager_teachers_statistics, name='manager_teachers_statistics'),
    path("manager/students/statistics", views.manager_students_statistics, name = 'manager_students_statistics'),
    
    # Manager - Criteria Management
    path('manager/criteria/', views.manager_criteria, name='manager_criteria'),
    path('manager/criteria/create/', views.manager_criteria_create, name='manager_criteria_create'),
    path('manager/criteria/<int:criterion_id>/edit/', views.manager_criteria_edit, name='manager_criteria_edit'),
    path('manager/criteria/<int:criterion_id>/delete/', views.manager_criteria_delete, name='manager_criteria_delete'),
    path('api/criterion/<int:criterion_id>/toggle-status/', views.manager_criteria_toggle_status, name='manager_criteria_toggle_status'),
    
    # Teacher URLs
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    path('teacher/evaluate/', views.teacher_evaluate, name='teacher_evaluate'),
    path('teacher/statistics/', views.teacher_statistics, name='teacher_statistics'),
    
    # API URLs
    path('api/generate-student-id/', views.generate_student_id, name='generate_student_id'),
    path('api/teacher/<int:teacher_id>/toggle-status/', views.toggle_teacher_status, name='toggle_teacher_status'),
    path('api/student/<int:student_id>/toggle-status/', views.toggle_student_status, name='toggle_student_status'),
    path('api/student/<int:student_id>/evaluations/', views.get_student_evaluations, name='get_student_evaluations'),
    path('api/bulk-actions/', views.bulk_actions, name='bulk_actions'),
    
    # Export URLs
    path('export/excel/', views.export_excel, name='export_excel'),
    path('manager/export/teachers/', views.export_teachers_excel, name='export_teachers_excel'),
    path('reports/school/', views.export_school_report, name='export_school_report'),
    path("reports/class-list/", views.class_report_list, name="class_report_list"),
    path('reports/class/<int:class_id>/', views.export_class_report, name='export_class_report'),
    path('reports/student/<int:student_id>/', views.export_student_report, name='export_student_report'),
    path('reports/students-statistics-pdf/', views.export_students_statistics_pdf, name='export_students_statistics_pdf'),
    
    # Enhanced PDF Reports
    path('reports/student/<int:student_id>/comprehensive/', views.export_comprehensive_student_report, name='export_comprehensive_student_report'),
    path('reports/weekly/', views.export_weekly_report, name='export_weekly_report'),
    path('reports/monthly/', views.export_monthly_report, name='export_monthly_report'),
    path('reports/yearly/', views.export_yearly_report, name='export_yearly_report'),

    #Baholarni Ota-onalarga yuborish
    path('manager/send-grades/', views.send_grades_to_parents, name='send_grades_to_parents'),
]