from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from main_app.models import Subject, Class, Teacher, Student, Evaluation
from django.utils import timezone
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup initial data for Feedback Monitoring System'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data...')
        
        # Create superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                password='admin123',
                first_name='Admin',
                last_name='User',
                role='manager'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created: admin/admin123'))
        
        # Create subjects
        subjects_data = [
            'Matematika', 'Fizika', 'Kimyo', 'Biologiya', 
            'Ingliz tili', 'Rus tili', 'O\'zbek tili', 
            'Tarix', 'Geografiya', 'Informatika'
        ]
        
        for subject_name in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=subject_name,
                defaults={'description': f'{subject_name} fani'}
            )
            if created:
                self.stdout.write(f'Subject created: {subject_name}')
        
        # Create classes
        classes_data = [
            ('7-A', 7, 'A'), ('7-B', 7, 'B'),
            ('8-A', 8, 'A'), ('8-B', 8, 'B'),
            ('9-A', 9, 'A'), ('9-B', 9, 'B'),
        ]
        
        for name, grade, section in classes_data:
            cls, created = Class.objects.get_or_create(
                name=name,
                defaults={'grade_level': grade, 'section': section}
            )
            if created:
                self.stdout.write(f'Class created: {name}')
        
        # Create teachers
        teachers_data = [
            ('aziza', 'Aziza', 'Karimova', 'Matematika', '7-A'),
            ('bobur', 'Bobur', 'Rahimov', 'Fizika', '8-B'),
            ('malika', 'Malika', 'Tosheva', 'Kimyo', '9-A'),
            ('jasur', 'Jasur', 'Aliev', 'Biologiya', '7-B'),
            ('dilnoza', 'Dilnoza', 'Karimova', 'Ingliz tili', '8-A'),
        ]
        
        for username, first_name, last_name, subject_name, class_name in teachers_data:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    password='teacher123',
                    first_name=first_name,
                    last_name=last_name,
                    role='teacher'
                )
                
                subject = Subject.objects.get(name=subject_name)
                class_obj = Class.objects.get(name=class_name)
                
                Teacher.objects.create(
                    user=user,
                    subject=subject,
                    class_assigned=class_obj
                )
                self.stdout.write(f'Teacher created: {username}/teacher123')
        
        # Create students
        students_data = [
            # 7-A sinfi
            ('Akmal', 'Toshev', '7-A', '7A001'),
            ('Malika', 'Rahimova', '7-A', '7A002'),
            ('Bobur', 'Aliev', '7-A', '7A003'),
            ('Dilnoza', 'Karimova', '7-A', '7A004'),
            ('Jasur', 'Abdullayev', '7-A', '7A005'),
            # 7-B sinfi
            ('Zarina', 'Usmonova', '7-B', '7B001'),
            ('Aziz', 'Toshev', '7-B', '7B002'),
            ('Nigora', 'Aliyeva', '7-B', '7B003'),
            # 8-A sinfi
            ('Sardor', 'Karimov', '8-A', '8A001'),
            ('Madina', 'Rahimova', '8-A', '8A002'),
            # 8-B sinfi
            ('Otabek', 'Usmonov', '8-B', '8B001'),
            ('Sevara', 'Tosheva', '8-B', '8B002'),
            # 9-A sinfi
            ('Bekzod', 'Aliev', '9-A', '9A001'),
            ('Gulnoza', 'Karimova', '9-A', '9A002'),
        ]
        
        for first_name, last_name, class_name, student_id in students_data:
            if not Student.objects.filter(student_id=student_id).exists():
                class_obj = Class.objects.get(name=class_name)
                Student.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    class_assigned=class_obj,
                    student_id=student_id,
                    date_of_birth=timezone.now().date() - timezone.timedelta(days=random.randint(4000, 5000))
                )
                self.stdout.write(f'Student created: {first_name} {last_name}')
        
        # Create sample evaluations
        teachers = Teacher.objects.all()
        for teacher in teachers:
            students = teacher.class_assigned.students.all()
            for student in students[:5]:  # Faqat birinchi 5 ta o'quvchi uchun
                for week in range(1, 4):  # 3 hafta uchun
                    if not Evaluation.objects.filter(
                        student=student, 
                        teacher=teacher, 
                        week_number=week,
                        year=timezone.now().year
                    ).exists():
                        Evaluation.objects.create(
                            student=student,
                            teacher=teacher,
                            homework_score=random.randint(25, 40),
                            discipline_score=random.randint(25, 40),
                            uniform_score=random.randint(15, 20),
                            week_number=week,
                            year=timezone.now().year,
                            comment=f'Hafta {week} baholash'
                        )
        
        self.stdout.write(self.style.SUCCESS('Initial data setup completed!'))
        self.stdout.write('Login credentials:')
        self.stdout.write('Admin: admin/admin123')
        self.stdout.write('Teachers: aziza/teacher123, bobur/teacher123, etc.')