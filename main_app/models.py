# Django imports
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Avg, Sum
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = [
        ('teacher', "O'qituvchi"),
        ('manager', "Menejer"),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='teacher')
    first_name = models.CharField(max_length=100, verbose_name="Ism")
    last_name = models.CharField(max_length=100, verbose_name="Familiya")
    
    class Meta:
        verbose_name = "Xodim"
        verbose_name_plural = "Xodimlar"

class Class(models.Model):
    name = models.CharField(max_length=10, unique=True, verbose_name="Sinf nomi")
    grade_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(11)],
        verbose_name="Sinf darajasi"
    )
    section = models.CharField(max_length=5, verbose_name="Bo'lim")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def student_count(self):
        return self.students.count()

    @property
    def average_score(self):
        evaluations = Evaluation.objects.filter(student__class_assigned=self)
        if evaluations.exists():
            return evaluations.aggregate(avg=Avg('scores__value'))['avg'] or 0
        return 0

    class Meta:
        verbose_name = "Sinf"
        verbose_name_plural = "Sinflar"
        ordering = ['grade_level', 'section']

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, verbose_name="Tayinlangan sinf")
    phone_number = models.CharField(max_length=17, blank=True, verbose_name="Telefon raqami")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    image = models.ImageField(upload_to="teachers_photo/", null=True, blank=True)
    hire_date = models.DateField(default=timezone.now, verbose_name="Ishga qabul qilingan sana")

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.class_assigned.name}"

    @property
    def total_evaluations(self):
        return self.evaluations.count()

    @property
    def weekly_evaluation_percentage(self):
        total_students = self.class_assigned.student_count
        if total_students == 0:
            return 0

        week_start = timezone.now().date() - timezone.timedelta(days=timezone.now().weekday())
        week_end = week_start + timezone.timedelta(days=6)

        weekly_evaluations = self.evaluations.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=week_end
        ).values('student').distinct().count()

        return round((weekly_evaluations / total_students) * 100, 1)
    @property
    def average_score_given(self):
        evaluations = self.evaluations.all()
        if evaluations.exists():
            return evaluations.aggregate(avg=Avg('scores__value'))['avg'] or 0
        return 0

    class Meta:
        verbose_name = "O'qituvchi"
        verbose_name_plural = "O'qituvchilar"


class Criterion(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kriteriya nomi")
    max_score = models.PositiveIntegerField(verbose_name="Maksimal ball")
    is_active = models.BooleanField(default=True, verbose_name="Faol kriteriya")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    def __str__(self):
        return f"{self.name} ({self.max_score})"

    class Meta:
        verbose_name = "Kriteriya"
        verbose_name_plural = "Kriteriyalar"


class Student(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Ism")
    last_name = models.CharField(max_length=100, verbose_name="Familiya")
    class_assigned = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='students',
        verbose_name="Sinf"
    )
    student_id = models.CharField(max_length=20, unique=True, verbose_name="O'quvchi ID")
    date_of_birth = models.DateField(verbose_name="Tug'ilgan sana")
    parent_phone = models.CharField(max_length=15, blank=True, verbose_name="Ota-ona telefoni")
    image = models.ImageField(upload_to='students_photo/', null=True, blank=True)
    enrollment_date = models.DateField(default=timezone.now, verbose_name="Ro'yxatga olingan sana")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def total_evaluations(self):
        return self.evaluations.count()

    @property
    def average_score(self):
        evaluations = self.evaluations.all()
        if evaluations.exists():
            return evaluations.aggregate(avg=Avg('scores__value'))['avg'] or 0
        return 0

    @property
    def latest_evaluation(self):
        return self.evaluations.order_by('-created_at').first()

    @property
    def performance_status(self):
        avg = self.average_score
        if avg >= 85:
            return "A'lo"
        elif avg >= 70:
            return "Yaxshi"
        elif avg >= 55:
            return "Qoniqarli"
        else:
            return "Qoniqarsiz"
    class Meta:
        verbose_name = "O'quvchi"
        verbose_name_plural = "O'quvchilar"
        ordering = ['first_name', 'last_name']


class Evaluation(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name="O'quvchi"
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name="O'qituvchi"
    )
    comment = models.TextField(blank=True, verbose_name="Izoh")
    week_number = models.IntegerField(verbose_name="Hafta raqami")
    month = models.IntegerField(default=timezone.now().month, verbose_name="Oy")
    year = models.IntegerField(default=timezone.now().year, verbose_name="Yil")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan vaqt")

    @property
    def total_score(self):
        return self.scores.aggregate(total=Sum('value'))['total'] or 0

    @property
    def max_possible_score(self):
        """Aktiv kriteriyalar bo'yicha maksimal ball"""
        return Criterion.objects.filter(is_active=True).aggregate(total=Sum('max_score'))['total'] or 100

    @property
    def percentage_score(self):
        """Foiz ko'rinishida ball"""
        max_score = self.max_possible_score
        if max_score == 0:
            return 0
        return round((self.total_score / max_score) * 100, 1)

    @property
    def grade_status(self):
        percentage = self.percentage_score
        if percentage >= 85:
            return "A'lo"
        elif percentage >= 70:
            return "Yaxshi"
        elif percentage >= 55:
            return "Qoniqarli"
        else:
            return "Qoniqarsiz"

    def __str__(self):
        max_score = self.max_possible_score
        return f"{self.student.full_name} - {self.total_score}/{max_score} - {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Baholash"
        verbose_name_plural = "Baholashlar"
        ordering = ['-created_at']
        unique_together = ['student', 'teacher', 'week_number', 'year']


class EvaluationScore(models.Model):
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="scores",
        verbose_name="Baholash"
    )
    criterion = models.ForeignKey(
        Criterion,
        on_delete=models.PROTECT,
        verbose_name="Kriteriya"
    )
    value = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Ball")

    def __str__(self):
        return f"{self.criterion.name} : {self.value} / {self.criterion.max_score}"

    class Meta:
        verbose_name = "Baholash natijasi"
        verbose_name_plural = "Baholash natijalari"


class WeeklyReport(models.Model):
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, verbose_name="Sinf")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name="O'qituvchi")
    week_number = models.IntegerField(verbose_name="Hafta raqami")
    year = models.IntegerField(default=timezone.now().year, verbose_name="Yil")

    total_students = models.IntegerField(verbose_name="Jami o'quvchilar")
    evaluated_students = models.IntegerField(verbose_name="Baholangan o'quvchilar")
    average_score = models.FloatField(verbose_name="O'rtacha ball")

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def evaluation_percentage(self):
        if self.total_students == 0:
            return 0
        return round((self.evaluated_students / self.total_students) * 100, 1)

    def __str__(self):
        return f"{self.class_assigned.name} - {self.year} yil {self.week_number}-hafta"

    class Meta:
        verbose_name = "Haftalik hisobot"
        verbose_name_plural = "Haftalik hisobotlar"
        unique_together = ['class_assigned', 'teacher', 'week_number', 'year']
        ordering = ['-year', '-week_number']


# 🆕 Oylik sinf/o'qituvchi hisobot
class MonthlyReport(models.Model):
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, verbose_name="Sinf")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name="O'qituvchi")
    month = models.IntegerField(verbose_name="Oy")
    year = models.IntegerField(default=timezone.now().year, verbose_name="Yil")

    total_students = models.IntegerField(verbose_name="Jami o'quvchilar")
    evaluated_students = models.IntegerField(verbose_name="Baholangan o'quvchilar")
    average_score = models.FloatField(verbose_name="O'rtacha ball")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.class_assigned.name} - {self.year} yil {self.month}-oy"

    class Meta:
        verbose_name = "Oylik hisobot"
        verbose_name_plural = "Oylik hisobotlar"
        unique_together = ['class_assigned', 'teacher', 'month', 'year']
        ordering = ['-year', '-month']


# 🆕 Oquvchi uchun oylik hisobot
class StudentMonthlyReport(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="monthly_reports",
        verbose_name="O'quvchi"
    )
    month = models.IntegerField(verbose_name="Oy")
    year = models.IntegerField(default=timezone.now().year, verbose_name="Yil")

    total_evaluations = models.IntegerField(verbose_name="Baholashlar soni")
    average_score = models.FloatField(verbose_name="O'rtacha ball")
    highest_score = models.FloatField(verbose_name="Eng yuqori ball", null=True, blank=True)
    lowest_score = models.FloatField(verbose_name="Eng past ball", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def performance_status(self):
        avg = self.average_score
        if avg >= 85:
            return "A'lo"
        elif avg >= 70:
            return "Yaxshi"
        elif avg >= 55:
            return "Qoniqarli"
        return "Qoniqarsiz"

    def __str__(self):
        return f"{self.student.full_name} - {self.year} yil {self.month}-oy"

    class Meta:
        verbose_name = "O'quvchi oylik hisobot"
        verbose_name_plural = "O'quvchilar oylik hisobotlari"
        unique_together = ['student', 'month', 'year']
        ordering = ['-year', '-month']


class SystemSettings(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name="Kalit")
    value = models.TextField(verbose_name="Qiymat")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.value}"

    class Meta:
        verbose_name = "Tizim sozlamasi"
        verbose_name_plural = "Tizim sozlamalari"


class Parents(models.Model):
    telegram_id = models.BigIntegerField(verbose_name="Ota-onasining telegram ID si")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="O'quvchi")

    def __str__(self):
        return f"{self.student.full_name} ({self.student.student_id})"

    class Meta:
        verbose_name = "Ota-ona"
        verbose_name_plural = "Ota-onalar"
