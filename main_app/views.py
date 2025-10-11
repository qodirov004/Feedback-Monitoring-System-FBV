# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum, FloatField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# Standard library imports
from datetime import datetime, timedelta
import json
import re
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
try:
    from aiogram import Bot
    from set_app.settings import BOT_TOKEN
    from aiogram.client.bot import DefaultBotProperties
    
    if BOT_TOKEN:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
        BOT_AVAILABLE = True
        print("✅ Bot created successfully")
    else:
        print("❌ BOT_TOKEN not found in settings")
        BOT_AVAILABLE = False
        bot = None
except ImportError as e:
    print(f"❌ aiogram import failed: {e}")
    # Fallback: Mock bot yaratish
    class MockBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            print(f"📤 [MOCK] Sending message to {chat_id}:")
            print(f"📝 Message: {text[:200]}...")
            return True
    
    bot = MockBot()
    BOT_AVAILABLE = True
    print("✅ Mock bot created for testing")
except Exception as e:
    print(f"❌ Bot creation failed: {e}")
    BOT_AVAILABLE = False
    bot = None
from asgiref.sync import sync_to_async
from datetime import date
from django.utils.timezone import now
import random
try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
from io import BytesIO
from django.db.models import F, ExpressionWrapper, IntegerField, Avg, Count, FloatField
from django.core.exceptions import ObjectDoesNotExist
if OPENPYXL_AVAILABLE:
    from openpyxl import Workbook, load_workbook
    from openpyxl.utils import get_column_letter
    from django.core.files.base import ContentFile


from .models import User, Teacher, Student, Class, Evaluation, Criterion, EvaluationScore, Parents
from set_app.forms import LoginForm, TeacherCreateForm, StudentCreateForm, ClassCreateForm, EvaluationForm, TeacherEditForm, CriterionForm, DynamicEvaluationForm

# ======================================================================================================================================================================
#                                                             Authentication Views
# ======================================================================================================================================================================

def login_view(request):
    """Login sahifasi"""
    if request.user.is_authenticated:
        if request.user.role == 'manager':
            return redirect('feedback:manager_dashboard')
        elif request.user.role == 'teacher':
            return redirect('feedback:teacher_dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if user.role == 'manager':
                    return redirect('feedback:manager_dashboard')
                elif user.role == 'teacher':
                    return redirect('feedback:teacher_dashboard')
            else:
                messages.error(request, 'Login yoki parol noto\'g\'ri')
    else:
        form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})

@login_required
def logout_view(request):
    """Logout"""
    logout(request)
    return redirect('feedback:login')

# ======================================================================================================================================================================
#                                                                   Manager Views
# ======================================================================================================================================================================

@login_required
def manager_dashboard(request):
    """Manager dashboard"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    # Annotated Evaluation queryset (total_score = barcha criteria summasi)
    evaluations = Evaluation.objects.annotate(
        total_score_annotated=Sum('scores__value')
    )

    # Statistikalar
    total_teachers = Teacher.objects.filter(user__is_active=True).count()
    total_students = Student.objects.all().count()

    # Hafta boshlanish sanasi
    week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())

    # Haftalik baholashlar soni
    weekly_evaluations = evaluations.filter(
        created_at__date__gte=week_start
    ).count()

    # O'rtacha baho
    avg_score = evaluations.aggregate(avg=Avg('total_score_annotated'))['avg'] or 0

    # Eng faol o'qituvchilar
    top_teachers = Teacher.objects.annotate(
        evaluation_count=Count('evaluations')
    ).order_by('-evaluation_count')[:3]

    # Eng yaxshi sinflar (o‘rtacha baho bo‘yicha)
    top_classes = Class.objects.annotate(
        avg_score=Avg('students__evaluations__scores__value'),
        num_students=Count('students')
    ).order_by('-avg_score')[:5]

    context = {
        'total_teachers': total_teachers,
        'weekly_evaluations': weekly_evaluations,
        'avg_score': round(avg_score, 1),
        'top_teachers': top_teachers,
        'top_classes': top_classes,
        'total_students': total_students,
    }

    return render(request, 'manager/dashboard.html', context)

@login_required
def manager_teachers(request):
    """O'qituvchilar ro'yxati"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    search = request.GET.get('search', '')
    teachers = Teacher.objects.select_related('user', 'class_assigned').all()


    if search:
        teachers = teachers.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(class_assigned__name__icontains=search)
        )

    # Add statistics for each teacher
    for teacher in teachers:
        # Get evaluations with total scores from criteria
        evaluations = teacher.evaluations.annotate(
            total_score_annotated=Sum('scores__value')
        )
        teacher.total_evals = evaluations.count()
        teacher.avg_score = evaluations.aggregate(avg=Avg('total_score_annotated'))['avg'] or 0

        # Weekly progress
        week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
        weekly_evals = evaluations.filter(created_at__date__gte=week_start).count()
        total_students = teacher.class_assigned.students.count() if teacher.class_assigned else 0
        teacher.weekly_progress = (weekly_evals / total_students * 100) if total_students > 0 else 0

    # Pagination
    paginator = Paginator(teachers, 10)
    page_number = request.GET.get('page')
    teachers = paginator.get_page(page_number)

    context = {
        'teachers': teachers,
        'search': search,
    }

    return render(request, 'manager/teacher.html', context)

@login_required
def manager_teachers_create(request):
    """Yangi o'qituvchi qo'shish"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    if request.method == 'POST':
        # ENG MUHIM O'ZGARISH:
        form = TeacherCreateForm(request.POST, request.FILES)

        if form.is_valid():
            # Create User
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                role='teacher'
            )

            # Create Teacher
            Teacher.objects.create(
                user=user,
                class_assigned=form.cleaned_data['class_assigned'],
                phone_number=form.cleaned_data.get('phone_number', ''),
                image=form.cleaned_data.get('image')  # <-- image ni ham qo'shdik!
            )

            messages.success(request, f"O'qituvchi {user.get_full_name()} muvaffaqiyatli qo'shildi!")
            return redirect('feedback:manager_teachers')
    else:
        form = TeacherCreateForm()
    return render(request, 'manager/teacher_create.html', {'form': form})

@login_required
def upload_teachers_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        file = request.FILES['excel_file']
        wb = load_workbook(file)
        sheet = wb.active

        # Excel rasmlarini (col, row) bo‘yicha xarita qilish
        image_map = {}
        for img in getattr(sheet, '_images', []):  # _images bo'lmasa xato bermaslik
            try:
                col = img.anchor._from.col + 1  # 1-based index
                row = img.anchor._from.row + 1
                image_map[(col, row)] = img
            except Exception:
                continue

        created = 0
        skipped = []

        for row in sheet.iter_rows(min_row=2):
            try:
                first_name = row[0].value or ''
                last_name = row[1].value or ''
                class_name = row[2].value or ''
                username = row[3].value or ''
                password = row[4].value or ''
                phone_number = row[5].value or ''
                image_col_index = 7  # Excel ustun H (1-based)

                # Ma'lumot to'liqmi tekshir
                if not all([first_name, last_name, class_name, username, password]):
                    messages.warning(request, f"Qator {row[0].row}: Majburiy maydonlar to'liq emas.")
                    continue

                if User.objects.filter(username=username).exists():
                    skipped.append(f"{first_name} {last_name} (Username: {username})")
                    continue

                # Class get_or_create ishlating, yoki xato chiqarish
                try:
                    class_assigned = Class.objects.get(name=class_name)
                except Class.DoesNotExist:
                    messages.error(request, f"{first_name} {last_name} — Sinf '{class_name}' topilmadi.")
                    continue

                # User yaratish
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role='teacher'
                )

                teacher = Teacher(
                    user=user,
                    class_assigned=class_assigned,
                    phone_number=phone_number
                )

                # Rasmni fayl sifatida saqlash
                img_key = (image_col_index, row[0].row)
                if img_key in image_map:
                    excel_img = image_map[img_key]
                    image_data = excel_img._data()
                    image_content = ContentFile(image_data)
                    filename = f"{username}_{first_name}.png"
                    teacher.image.save(filename, image_content, save=False)

                teacher.save()
                created += 1

            except Exception as e:
                messages.error(request, f"Qator {row[0].row} — Xatolik: {str(e)}")
                continue

        if skipped:
            messages.warning(request, f"Takrorlangan loginlar: {', '.join(skipped)}")
        messages.success(request, f"{created} ta o'qituvchi muvaffaqiyatli yuklandi.")
        return redirect('feedback:manager_teachers')

    return redirect('feedback:upload_teachers_excel')

@login_required
def download_teacher_template(request):
    if request.user.role != 'manager':
        return HttpResponse("Ruxsat yo‘q", status=403)

    wb = Workbook()
    ws = wb.active
    ws.title = "O'qituvchilar"

    # Ustun sarlavhalari
    headers = [
        "Ism", "Familiya",
        "Sinf", "Login", "Parol (Belgilar 8 tadan kam bo'lmasligi kerak)", "Telefon raqam",
        "Rasm fayl nomi (students_photo/)"
    ]
    ws.append(headers)

    # Ustun kengliklari
    column_widths = [15, 20, 20, 20, 43, 28, 30]  # har bir ustun uchun o‘lcham

    for i, width in enumerate(column_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # Demo ma'lumot
    ws.append([
        "Ali", "Valiyev", "1-A",
        "ali_valiyev", "alibek123",
        '+998991234567', "Rasmmi joylang"
    ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=teacher_template.xlsx"
    wb.save(response)
    return response

@login_required
def manager_teachers_detail(request, teacher_id):
    """O'qituvchi bo'yicha to'liq statistika sahifasi"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    teacher = get_object_or_404(Teacher, id=teacher_id)

    # ✅ POST so‘rov bo‘lsa: faollikni almashtirish
    if request.method == 'POST':
        teacher.is_active = not teacher.is_active
        teacher.save()
        status = "faollashtirildi" if teacher.is_active else "nofaollashtirildi"
        messages.success(request, f"O'qituvchi {teacher.user.get_full_name()} {status}.")
        return redirect('feedback:manager_teachers_detail', teacher_id=teacher_id)

    # ✅ GET so‘rov: statistikani hisoblash
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    evaluations = teacher.evaluations.select_related('student').annotate(
        total_score_calc=Sum('scores__value')
    ).order_by('-created_at')

    total_evaluations = evaluations.count()
    avg_score = evaluations.aggregate(avg=Avg('total_score_calc'))['avg'] or 0

    # Get criteria averages
    criteria_avgs = {}
    for criterion in Criterion.objects.filter(is_active=True):
        criteria_avgs[criterion.name] = EvaluationScore.objects.filter(
            evaluation__teacher=teacher,
            criterion=criterion
        ).aggregate(avg=Avg('value'))['avg'] or 0

    weekly_evaluations = evaluations.filter(created_at__date__gte=week_start).count()
    monthly_evaluations = evaluations.filter(created_at__date__gte=month_start).count()

    weekly_trends = []
    for i in range(4):
        start = today - timedelta(days=today.weekday() + i * 7)
        end = start + timedelta(days=6)
        week_evals = evaluations.filter(created_at__date__range=(start, end))
        weekly_trends.append({
            'week': f'{4 - i}-hafta',
            'average': round(week_evals.aggregate(avg=Avg('total_score_calc'))['avg'] or 0, 1),
            'count': week_evals.count()
        })

    excellent, good, average, unevaluated = [], [], [], []

    if teacher.class_assigned:
        students = teacher.class_assigned.students.all()
        for student in students:
            student_evals = student.evaluations.filter(teacher=teacher).annotate(
                total_score_calc=Sum('scores__value')
            )
            avg = student_evals.aggregate(avg=Avg('total_score_calc'))['avg']
            if avg is None:
                unevaluated.append(student)
            elif avg >= 85:
                excellent.append({'student': student, 'avg': avg})
            elif avg >= 70:
                good.append({'student': student, 'avg': avg})
            else:
                average.append({'student': student, 'avg': avg})

        excellent.sort(key=lambda x: x['avg'], reverse=True)
        good.sort(key=lambda x: x['avg'], reverse=True)
        average.sort(key=lambda x: x['avg'])

    class_stats = None
    if teacher.class_assigned:
        total_students = teacher.class_assigned.students.count()
        evaluated_this_week = teacher.class_assigned.students.filter(
            evaluations__teacher=teacher,
            evaluations__created_at__date__gte=week_start
        ).distinct().count()

        class_avg = teacher.class_assigned.students.annotate(
            score=Sum('evaluations__scores__value')
        ).aggregate(avg=Avg('score'))['avg'] or 0

        class_stats = {
            'total_students': total_students,
            'evaluated_this_week': evaluated_this_week,
            'weekly_percentage': round((evaluated_this_week / total_students * 100), 1) if total_students else 0,
            'class_average': round(class_avg, 1)
        }

    recent_evaluations = evaluations[:10]

    context = {
        'teacher': teacher,
        'evaluations': recent_evaluations,
        'total_evaluations': total_evaluations,
        'avg_score': round(avg_score, 1),
        'criteria_avgs': criteria_avgs,
        'weekly_evaluations': weekly_evaluations,
        'monthly_evaluations': monthly_evaluations,
        'weekly_trends': weekly_trends,
        'excellent_students': excellent[:5],
        'good_students': good[:5],
        'needs_improvement': average[:5],
        'unevaluated_students': unevaluated[:5],
        'class_stats': class_stats,
        'last_login': teacher.user.last_login or teacher.user.date_joined,
        'days_since_creation': (today - teacher.user.date_joined.date()).days,
    }

    return render(request, 'manager/teacher_detail.html', context)

@login_required
def manager_teachers_edit(request, teacher_id):
    """ O'qituvchi ma'lumotlarini tahrirlash """
    teacher = get_object_or_404(Teacher, id=teacher_id)
    user = teacher.user

    if request.method == 'POST':
        form = TeacherEditForm(request.POST, request.FILES, instance=teacher, user_instance=user)
        if form.is_valid():
            # Teacher modelini saqlash
            teacher = form.save()

            # User modelini yangilash
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.username = form.cleaned_data['username']
            if form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])
            user.save()

            messages.success(request, f"O'qituvchi {user.get_full_name()} ma'lumotlari yangilandi!")
            return redirect('feedback:manager_teachers')
        else:
            messages.error(request, "Formada xatoliklar mavjud. Iltimos tekshirib ko'ring.")
    else:
        form = TeacherEditForm(instance=teacher, user_instance=user)

    return render(request, 'manager/teacher_edit.html', {
        'form': form,
        'teacher': teacher
    })


@login_required
def manager_teachers_delete(request, teacher_id):
    """O'qituvchini o'chirish"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    teacher = get_object_or_404(Teacher, id=teacher_id)

    if request.method == 'POST':
        teacher_name = teacher.user.get_full_name()
        teacher.user.delete()  # This will also delete the teacher due to CASCADE
        messages.success(request, f"O'qituvchi {teacher_name} o'chirildi!")
        return redirect('feedback:manager_teachers')
    return render(request, 'manager/teachers_delete.html', {'teacher': teacher})

@login_required
def manager_teachers_statistics(request):
    teachers = Teacher.objects.select_related('user', 'class_assigned').all()

    stats = []
    labels = []
    percentages = []

    # Haftaning boshlanish va tugash sanasini aniqlash
    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday())  # dushanba
    week_end = week_start + timezone.timedelta(days=6)  # yakshanba

    for teacher in teachers:
        total_students = teacher.class_assigned.students.count()

        weekly_evaluated_students = Evaluation.objects.filter(
            teacher=teacher,
            created_at__date__range=(week_start, week_end)
        ).values('student').distinct().count()

        if total_students > 0:
            percentage = round((weekly_evaluated_students / total_students) * 100, 1)
        else:
            percentage = 0

        avg_score = Evaluation.objects.filter(
            teacher=teacher
        ).aggregate(avg=Avg('scores__value'))['avg'] or 0
        avg_score = round(avg_score, 1)

        stats.append({
            'teacher': teacher,
            'percentage': percentage,
            'average_score': avg_score
        })

        labels.append(teacher.user.get_full_name())
        percentages.append(percentage)

    chart_data = {
        'labels': labels,
        'percentages': percentages
    }

    return render(request, 'manager/teacher_statistics.html', {
        'teachers_data': stats,
        'chart_data': chart_data
    })

@login_required
def manager_class_create(request):
    if request.method == 'POST':
        form = ClassCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Sinf muvaffaqiyatli yaratildi!")
            return redirect('feedback:manager_dashboard')
        else:
            messages.error(request, "Formada xatoliklar mavjud. Iltimos, tekshirib ko'ring.")
    else:
        form = ClassCreateForm()
    return render(request, 'manager/class_create.html', {'form': form})

@login_required
def class_list(request):
    classes = Class.objects.all().order_by('grade_level', 'section')
    return render(request, 'manager/classes.html', {'classes': classes})

@login_required
def manager_students(request):
    """O'quvchilar ro'yxati"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    search = request.GET.get('search', '')
    class_filter = request.GET.get('class', '')

    classes = Class.objects.all()

    students = Student.objects.select_related('class_assigned').all()


    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(student_id__icontains=search)
        )

    if class_filter:
        students = students.filter(class_assigned__name=class_filter)

    for student in students:
        student.total_evals = student.evaluations.count()
        student.avg_score = student.evaluations.annotate(
            total_score_calc=Sum('scores__value')
        ).aggregate(avg=Avg('total_score_calc'))['avg'] or 0

        student.latest_eval = student.evaluations.order_by('-created_at').first()

        if student.avg_score >= 85:
            student.status = "A'lo"
        elif student.avg_score >= 70:
            student.status = "Yaxshi"
        elif student.avg_score >= 55:
            student.status = "Qoniqarli"
        else:
            student.status = "Qoniqarsiz" if student.avg_score > 0 else "Baholanmagan"

    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)

    context = {
        'students': students,
        'classes': classes,
        'search': search,
        'class_filter': class_filter,
    }

    return render(request, 'manager/students.html', context)

@login_required
def manager_students_create(request):
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    if request.method == 'POST':
        form = StudentCreateForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"O'quvchi {student.full_name} muvaffaqiyatli qo'shildi!")
            return redirect('feedback:manager_students')
        else:
            messages.error(request, "Formada xatoliklar mavjud. Iltimos, tekshirib ko'ring.")
    else:
        form = StudentCreateForm()

    return render(request, 'manager/student_create.html', {'form': form})

@login_required
def upload_students_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        file = request.FILES['excel_file']
        wb = load_workbook(file)
        sheet = wb.active

        # Excel rasmlarni hujayra (col, row) bo‘yicha xaritalash
        image_map = {}
        for img in getattr(sheet, '_images', []):
            try:
                col = img.anchor._from.col + 1  # 1-indekslanadi
                row = img.anchor._from.row + 1
                image_map[(col, row)] = img
            except Exception:
                continue

        created = 0
        skipped = []

        for row in sheet.iter_rows(min_row=2):  # Sarlavhadan keyin
            try:
                first_name = row[0].value
                last_name = row[1].value
                dob = row[2].value
                parent_phone = row[3].value
                class_name = row[4].value

                image_col_index = 6  # Excelda rasm ustuni: F (6)

                # Tug‘ilgan sanani parse qilish
                if isinstance(dob, str):
                    try:
                        dob = datetime.strptime(dob, "%d-%m-%Y").date()
                    except ValueError:
                        dob = datetime.strptime(dob, "%d.%m.%Y").date()

                student_class = Class.objects.get(name=class_name)

                # student_id avtomatik yaratish
                class_code = class_name.replace(" ", "").replace("-", "").upper()
                # Sinf nomidan 2 ta belgi olish (masalan: "7A" -> "7A", "10B" -> "10")
                class_code = class_code[:2] if len(class_code) >= 2 else class_code
                while True:
                    rand_num = f"{random.randint(100000, 999999)}"  # 6 xonali random raqam
                    student_id = f"{class_code}{rand_num}"
                    if not Student.objects.filter(student_id=student_id).exists():
                        break

                # O'quvchini yaratish
                student = Student(
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=dob,
                    parent_phone=parent_phone,
                    student_id=student_id,
                    class_assigned=student_class,
                )

                # Rasmni yuklash
                img_key = (image_col_index, row[0].row)
                if img_key in image_map:
                    excel_img = image_map[img_key]
                    image_data = excel_img._data()
                    image_content = ContentFile(image_data)
                    filename = f"{student_id}_{first_name}.png"
                    student.image.save(filename, image_content, save=False)

                student.save()
                created += 1

            except Exception as e:
                messages.error(request, f"Xatolik: {first_name} {last_name} — {str(e)}")
                continue

        if skipped:
            messages.warning(request, f"Takrorlangan IDlar: {', '.join(skipped)}")
        messages.success(request, f"{created} ta o‘quvchi muvaffaqiyatli yuklandi.")
        return redirect('feedback:manager_students')

    messages.error(request, "Fayl topilmadi yoki noto‘g‘ri so‘rov yuborildi.")
    return redirect("feedback:upload_students_excel")

@login_required
def download_student_template(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"

    # Sarlavhalar
    headers = ['Ism', 'Familiya', 'Tug\'ilgan sana', 'Ota-ona tel', 'Sinf', 'Rasm']
    ws.append(headers)

    # Namuna qatori
    ws.append(['Ali', 'Valiyev', '15-09-2010', '+998901112233', '1-A', ''])

    # Ustun kengliklarini belgilash
    ws.column_dimensions['A'].width = 20  # Ism
    ws.column_dimensions['B'].width = 20  # Familiya
    ws.column_dimensions['C'].width = 15  # Tug'ilgan sana
    ws.column_dimensions['D'].width = 18  # Ota-ona tel
    ws.column_dimensions['E'].width = 10  # Sinf
    ws.column_dimensions['F'].width = 25  # Rasm

    # Qator balandligini belgilash (rasmlar uchun yetarlicha bo'lsin)
    for row in range(1, 16):  # 15 qatorga qadar tayyor bo'lib tursin
        ws.row_dimensions[row].height = 40

    # Faylni yuborish
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    response = HttpResponse(stream, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="student_template.xlsx"'
    return response

@login_required
def manager_students_edit(request, student_id):
    """O'quvchi ma'lumotlarini tahrirlash"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        form = StudentCreateForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"O'quvchi {student.full_name} ma'lumotlari yangilandi!")
            return redirect('feedback:manager_students')
        else:
            messages.error(request, "Formada xatoliklar mavjud. Iltimos, tekshirib qaytadan urinib ko'ring.")
    else:
        form = StudentCreateForm(instance=student)
    context = {
        'form': form,
        'student': student,
        'title': 'O\'quvchi ma\'lumotlarini tahrirlash'
    }
    return render(request, 'manager/student_create.html', context)

@login_required
def manager_students_detail(request, student_id):
    """O'quvchi batafsil ma'lumotlari"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    student = get_object_or_404(Student, id=student_id)

    evaluations = student.evaluations.select_related('teacher__user').annotate(
        total_score_calc=Sum('scores__value')
    ).order_by('-created_at')

    total_evaluations = evaluations.count()
    avg_score = evaluations.aggregate(avg=Avg('total_score_calc'))['avg'] or 0

    # Get criteria averages
    criteria_avgs = {}
    for criterion in Criterion.objects.filter(is_active=True):
        criteria_avgs[criterion.name] = EvaluationScore.objects.filter(
            evaluation__student=student,
            criterion=criterion
        ).aggregate(avg=Avg('value'))['avg'] or 0

    week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
    is_evaluated_this_week = evaluations.filter(created_at__date__gte=week_start).exists()

    weekly_trends = []
    for i in range(4):
        week_start = timezone.now().date() - timedelta(days=timezone.now().weekday() + (i * 7))
        week_end = week_start + timedelta(days=6)
        week_evals = evaluations.filter(created_at__date__range=[week_start, week_end])
        week_avg = week_evals.aggregate(avg=Avg('total_score_calc'))['avg'] or 0

        weekly_trends.append({
            'week': f'{4 - i}-hafta',
            'average': round(week_avg, 1),
            'count': week_evals.count()
        })
    context = {
        'student': student,
        'evaluations': evaluations[:10],
        'total_evaluations': total_evaluations,
        'avg_score': round(avg_score, 1),
        'criteria_avgs': criteria_avgs,
        'is_evaluated_this_week': is_evaluated_this_week,
        'weekly_trends': weekly_trends,
    }

    return render(request, 'manager/student_detail.html', context)

@login_required
def manager_students_delete(request, student_id):
    """O'quvchini o'chirish"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        student_name = student.full_name
        student.delete()
        messages.success(request, f"O'quvchi {student_name} o'chirildi!")
        return redirect('feedback:manager_students')
    context = {
        'student': student,
        'title': 'O\'quvchini o\'chirish'
    }
    return render(request, 'manager/students_delete.html', context)

@login_required
def manager_students_statistics(request):
    """O'quvchilar statistikasi"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    classes = Class.objects.all()
    selected_class_id = request.GET.get('class_id')
    period = request.GET.get('period', 'weekly')

    # O'quvchilarni filter qilish
    if selected_class_id:
        students = Student.objects.filter(class_assigned_id=selected_class_id)
    else:
        students = Student.objects.all()

    # Period bo'yicha evaluationlarni filter qilish
    now = timezone.now().date()
    
    if period == 'weekly':
        # Oxirgi hafta
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        evaluations_filter = {'created_at__date__range': [week_start, week_end]}
        
    elif period == 'monthly':
        # Oxirgi oy
        month_start = now.replace(day=1)
        next_month = month_start.replace(month=month_start.month + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
        month_end = next_month - timedelta(days=1)
        evaluations_filter = {'created_at__date__range': [month_start, month_end]}
        
    elif period == 'yearly':
        # Oxirgi yil
        evaluations_filter = {'created_at__year': now.year}
    else:
        # Default: haftalik
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        evaluations_filter = {'created_at__date__range': [week_start, week_end]}

    labels = []
    scores = []

    for student in students:
        # Period bo'yicha filtered evaluations
        student_evaluations = student.evaluations.filter(**evaluations_filter)
        avg_score = student_evaluations.aggregate(avg=Avg('scores__value'))['avg'] or 0
        labels.append(student.full_name)
        scores.append(round(avg_score, 1))

    chart_data = {
        'labels': labels,
        'scores': scores
    }

    return render(request, 'manager/students_statistics.html', {
        'classes': classes,
        'selected_class_id': int(selected_class_id) if selected_class_id else None,
        'chart_data': chart_data,
        'period': period
    })

@login_required
def export_students_statistics_pdf(request):
    """Filtered o'quvchilar statistikasi PDF hisoboti"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    if not REPORTLAB_AVAILABLE:
        return HttpResponse("PDF export requires reportlab library", status=500)

    # Filter parametrlari
    class_id = request.GET.get('class_id')
    period = request.GET.get('period', 'weekly')
    
    # O'quvchilarni filter qilish
    students = Student.objects.select_related('class_assigned').all()
    if class_id and class_id != 'None':
        try:
            class_id = int(class_id)
            students = students.filter(class_assigned_id=class_id)
        except (ValueError, TypeError):
            pass  # class_id noto'g'ri bo'lsa, barcha o'quvchilarni ko'rsatamiz
    
    # Period bo'yicha evaluationlarni filter qilish
    now = timezone.now().date()
    
    if period == 'weekly':
        # Oxirgi hafta
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        evaluations_filter = {'created_at__date__range': [week_start, week_end]}
        period_title = f"Haftalik hisobot ({week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')})"
        
    elif period == 'monthly':
        # Oxirgi oy
        month_start = now.replace(day=1)
        next_month = month_start.replace(month=month_start.month + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
        month_end = next_month - timedelta(days=1)
        evaluations_filter = {'created_at__date__range': [month_start, month_end]}
        period_title = f"Oylik hisobot ({month_start.strftime('%B %Y')})"
        
    elif period == 'yearly':
        # Oxirgi yil
        evaluations_filter = {'created_at__year': now.year}
        period_title = f"Yillik hisobot ({now.year} yil)"
    else:
        # Default: haftalik
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        evaluations_filter = {'created_at__date__range': [week_start, week_end]}
        period_title = f"Haftalik hisobot ({week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')})"
    
    # PDF yaratish
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Sarlavha
    elements.append(Paragraph(f"📊 O'quvchilar statistikasi", styles['Heading1']))
    elements.append(Paragraph(period_title, styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    # Umumiy statistika
    total_students = students.count()
    total_evaluations = Evaluation.objects.filter(
        student__in=students,
        **evaluations_filter
    ).count()
    
    summary_data = [
        ["Ko'rsatkich", "Qiymat"],
        ["Jami o'quvchilar", str(total_students)],
        ["Jami baholashlar", str(total_evaluations)],
    ]
    
    summary_table = Table(summary_data, repeatRows=1)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Har bir o'quvchi uchun batafsil ma'lumot
    elements.append(Paragraph("📋 Batafsil ma'lumotlar", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    for student in students:
        # O'quvchi ma'lumotlari
        elements.append(Paragraph(f"👨‍🎓 {student.full_name} ({student.student_id})", styles['Heading3']))
        elements.append(Paragraph(f"🏫 Sinf: {student.class_assigned.name}", styles['Normal']))
        
        # Bu period uchun baholashlar
        student_evaluations = Evaluation.objects.filter(
            student=student,
            **evaluations_filter
        ).select_related('teacher__user').order_by('-created_at')
        
        if student_evaluations.exists():
            for eval in student_evaluations:
                # Baholash sarlavhasi
                elements.append(Paragraph(
                    f"📅 {eval.created_at.strftime('%d.%m.%Y %H:%M')} - "
                    f"O'qituvchi: {eval.teacher.user.get_full_name()}",
                    styles['Heading4']
                ))
                
                # Kriteriya bo'yicha ballar
                if eval.scores.exists():
                    criteria_data = [["Kriteriya", "Ball", "Maksimal", "Foiz"]]
                    for score in eval.scores.all():
                        percentage = (score.value / score.criterion.max_score * 100) if score.criterion.max_score > 0 else 0
                        criteria_data.append([
                            score.criterion.name,
                            str(score.value),
                            str(score.criterion.max_score),
                            f"{percentage:.1f}%"
                        ])
                    
                    criteria_table = Table(criteria_data, repeatRows=1)
                    criteria_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ]))
                    elements.append(criteria_table)
                
                # O'qituvchi izohi
                if eval.comment:
                    elements.append(Paragraph(f"💬 Izoh: {eval.comment}", styles['Normal']))
                
                elements.append(Spacer(1, 8))
        else:
            elements.append(Paragraph("❌ Bu period uchun baholashlar mavjud emas", styles['Normal']))
        
        elements.append(Spacer(1, 15))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"students_statistics_{period}_{now.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    return response

@login_required
def manager_classes_create(request):
    """Yangi sinf yaratish"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')
    if request.method == 'POST':
        form = ClassCreateForm(request.POST)
        if form.is_valid():
            cls = form.save()
            messages.success(request, f"Sinf {cls.name} muvaffaqiyatli yaratildi!")
            return redirect('feedback:manager_classes')
    else:
        form = ClassCreateForm()
    return render(request, 'manager/classes_create.html', {'form': form})

@login_required
def manager_classes(request):
    """Sinflar monitoring"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    # Annotate classes with number of students and avg score
    classes = Class.objects.annotate(
        student_count_annotated=Count('students'),
        avg_score=Avg('students__evaluations__scores__value')
    ).prefetch_related('students', 'teacher_set')

    week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())

    for cls in classes:
        cls.teacher = cls.teacher_set.first()

        # Weekly evaluated students
        weekly_evaluated = Evaluation.objects.filter(
            student__class_assigned=cls,
            created_at__date__gte=week_start
        ).values('student').distinct().count()

        cls.weekly_evaluated = weekly_evaluated
        cls.weekly_percentage = (
            (weekly_evaluated / cls.student_count_annotated * 100)
            if cls.student_count_annotated > 0 else 0
        )

        # Top student in the class
        cls.top_student = cls.students.annotate(
            avg_score=Avg('evaluations__scores__value')
        ).order_by('-avg_score').first()

    # Summary
    total_classes = classes.count()
    total_students = sum(cls.student_count_annotated for cls in classes)
    avg_score = (
        sum(cls.avg_score or 0 for cls in classes) / total_classes
        if total_classes > 0 else 0
    )

    context = {
        'classes': classes,
        'total_classes': total_classes,
        'total_students': total_students,
        'avg_score': round(avg_score or 0, 1),
    }

    return render(request, 'manager/classes.html', context)

@login_required
def manager_class_delete(request, id):
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu amalni bajarish huquqi yo'q.")
        return redirect('feedback:manager_classes')  # sinflar ro'yxati sahifangizning URL nomi

    class_obj = get_object_or_404(Class, id=id)
    class_name = class_obj.name
    class_obj.delete()
    messages.success(request, f"{class_name} sinfi muvaffaqiyatli o'chirildi.")
    return redirect('feedback:manager_classes')

@login_required
def manager_statistics(request):
    """Tizim statistikasi"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    # Baholashlar umumiy balli bilan (output_field qo'shildi)
    evaluations = Evaluation.objects.annotate(
        total_score_calc=Coalesce(Sum('scores__value'), 0.0, output_field=FloatField())
    )

    # Umumiy statistikalar
    total_teachers = Teacher.objects.filter(user__is_active=True).count()
    total_students = Student.objects.count()
    total_evaluations = evaluations.count()
    avg_score = evaluations.aggregate(
        avg=Avg('total_score_calc', output_field=FloatField())
    )['avg'] or 0

    # Haftalik trend (so'nggi 4 hafta)
    weekly_trends = []
    for i in range(4):
        week_start = timezone.now().date() - timedelta(days=timezone.now().weekday() + i * 7)
        week_end = week_start + timedelta(days=6)
        week_evals = evaluations.filter(created_at__date__range=[week_start, week_end])
        weekly_trends.append({
            'week': f'{4 - i}-hafta',
            'evaluations': week_evals.count(),
            'avg_score': week_evals.aggregate(
                avg=Avg('total_score_calc', output_field=FloatField())
            )['avg'] or 0
        })

    # Sinf statistikasi
    class_stats = list(
        Class.objects.annotate(
            avg_score=Coalesce(Avg('students__evaluations__scores__value', output_field=FloatField()), 0.0, output_field=FloatField())
        ).values('name', 'avg_score')
    )

    # O'qituvchi statistikasi (top 10)
    teacher_stats = Teacher.objects.annotate(
        evaluation_count=Count('evaluations')
    ).order_by('-evaluation_count')[:10]

    context = {
        'total_teachers': total_teachers,
        'total_students': total_students,
        'total_evaluations': total_evaluations,
        'avg_score': round(avg_score, 1),
        'weekly_trends': weekly_trends,
        'class_stats': class_stats,
        'teacher_stats': teacher_stats,
        'trends': weekly_trends,  # Template uchun trends o'zgaruvchisi
    }

    return render(request, 'manager/statistics.html', context)

# ========================
# Criterion Management Views
# ========================

@login_required
def manager_criteria(request):
    """Kriteriyalar ro'yxati"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    search = request.GET.get('search', '')
    criteria = Criterion.objects.all().order_by('-created_at')

    if search:
        criteria = criteria.filter(name__icontains=search)

    # Pagination
    paginator = Paginator(criteria, 10)
    page_number = request.GET.get('page')
    criteria = paginator.get_page(page_number)

    context = {
        'criteria': criteria,
        'search': search,
    }

    return render(request, 'manager/criteria.html', context)

@login_required
def manager_criteria_create(request):
    """Yangi kriteriya qo'shish"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    if request.method == 'POST':
        form = CriterionForm(request.POST)
        if form.is_valid():
            criterion = form.save()
            messages.success(request, f"Kriteriya '{criterion.name}' muvaffaqiyatli qo'shildi!")
            return redirect('feedback:manager_criteria')
        else:
            messages.error(request, "Formada xatoliklar mavjud. Iltimos, tekshirib ko'ring.")
    else:
        form = CriterionForm()

    return render(request, 'manager/criterion_create.html', {'form': form})

@login_required
def manager_criteria_edit(request, criterion_id):
    """Kriteriya ma'lumotlarini tahrirlash"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    criterion = get_object_or_404(Criterion, id=criterion_id)

    if request.method == 'POST':
        form = CriterionForm(request.POST, instance=criterion)
        if form.is_valid():
            criterion = form.save()
            messages.success(request, f"Kriteriya '{criterion.name}' ma'lumotlari yangilandi!")
            return redirect('feedback:manager_criteria')
        else:
            messages.error(request, "Formada xatoliklar mavjud. Iltimos, tekshirib ko'ring.")
    else:
        form = CriterionForm(instance=criterion)

    return render(request, 'manager/criterion_edit.html', {
        'form': form,
        'criterion': criterion
    })

@login_required
def manager_criteria_delete(request, criterion_id):
    """Kriteriyani o'chirish (soft delete)"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    criterion = get_object_or_404(Criterion, id=criterion_id)

    if request.method == 'POST':
        # Check if criterion is used in evaluations
        if EvaluationScore.objects.filter(criterion=criterion).exists():
            # Soft delete - set is_active to False
            criterion.is_active = False
            criterion.save()
            messages.success(request, f"Kriteriya '{criterion.name}' nofaollashtirildi (baholashlarda ishlatilgan)")
        else:
            # Hard delete - no evaluations use this criterion
            criterion_name = criterion.name
            criterion.delete()
            messages.success(request, f"Kriteriya '{criterion_name}' o'chirildi!")
        
        return redirect('feedback:manager_criteria')

    # Check usage
    usage_count = EvaluationScore.objects.filter(criterion=criterion).count()
    
    context = {
        'criterion': criterion,
        'usage_count': usage_count,
    }
    return render(request, 'manager/criterion_delete.html', context)

@login_required
def manager_criteria_toggle_status(request, criterion_id):
    """Kriteriya holatini o'zgartirish"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        criterion = Criterion.objects.get(id=criterion_id)
        criterion.is_active = not criterion.is_active
        criterion.save()

        return JsonResponse({
            'success': True,
            'is_active': criterion.is_active
        })
    except Criterion.DoesNotExist:
        return JsonResponse({'error': 'Criterion not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def export_statistics_pdf(request):
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    # Baholashlar umumiy balli bilan
    evaluations = Evaluation.objects.annotate(
        total_score_calc=Coalesce(Sum('scores__value'), 0.0, output_field=FloatField())
    )

    # Umumiy statistikalar
    total_teachers = Teacher.objects.filter(user__is_active=True).count()
    total_students = Student.objects.count()
    total_evaluations = evaluations.count()
    avg_score = evaluations.aggregate(
        avg=Avg('total_score_calc', output_field=FloatField())
    )['avg'] or 0

    today = timezone.now().date()

    # Haftalik statistikalar (oxirgi 4 hafta)
    weekly_stats = []
    for i in range(4):
        week_start = today - timedelta(days=today.weekday() + i * 7)
        week_end = week_start + timedelta(days=6)
        week_evals = evaluations.filter(created_at__date__range=[week_start, week_end])
        weekly_stats.append({
            "week": f"{4 - i}-hafta",
            "evaluations": week_evals.count(),
            "avg_score": week_evals.aggregate(avg=Avg('total_score_calc', output_field=FloatField()))['avg'] or 0
        })

    # Oylik statistikalar (so‘nggi 6 oy)
    monthly_stats = []
    for i in range(6):
        month = (today.month - i - 1) % 12 + 1
        year = today.year - ((today.month - i - 1) // 12)
        month_evals = evaluations.filter(created_at__year=year, created_at__month=month)
        monthly_stats.append({
            "month": f"{year}-{month:02d}",
            "evaluations": month_evals.count(),
            "avg_score": month_evals.aggregate(avg=Avg('total_score_calc', output_field=FloatField()))['avg'] or 0
        })

    # Yillik statistikalar (oxirgi 3 yil)
    yearly_stats = []
    for i in range(3):
        year = today.year - i
        year_evals = evaluations.filter(created_at__year=year)
        yearly_stats.append({
            "year": year,
            "evaluations": year_evals.count(),
            "avg_score": year_evals.aggregate(avg=Avg('total_score_calc', output_field=FloatField()))['avg'] or 0
        })

    # --- PDF Yaratish ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="statistics.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "Tizim Statistikasi")
    y -= 40

    # Umumiy statistikalar
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Umumiy o‘qituvchilar: {total_teachers}")
    y -= 20
    p.drawString(50, y, f"Umumiy talabalar: {total_students}")
    y -= 20
    p.drawString(50, y, f"Baholashlar soni: {total_evaluations}")
    y -= 20
    p.drawString(50, y, f"O‘rtacha ball: {round(avg_score,1)}")
    y -= 40

    # Haftalik statistikalar
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Haftalik Statistikalar:")
    y -= 20
    p.setFont("Helvetica", 12)
    for w in weekly_stats:
        p.drawString(60, y, f"{w['week']} | Baholar: {w['evaluations']} | O‘rtacha ball: {round(w['avg_score'],1)}")
        y -= 20

    y -= 20
    # Oylik statistikalar
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Oylik Statistikalar:")
    y -= 20
    p.setFont("Helvetica", 12)
    for m in monthly_stats:
        p.drawString(60, y, f"{m['month']} | Baholar: {m['evaluations']} | O‘rtacha ball: {round(m['avg_score'],1)}")
        y -= 20

    y -= 20
    # Yillik statistikalar
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Yillik Statistikalar:")
    y -= 20
    p.setFont("Helvetica", 12)
    for yr in yearly_stats:
        p.drawString(60, y, f"{yr['year']} | Baholar: {yr['evaluations']} | O‘rtacha ball: {round(yr['avg_score'],1)}")
        y -= 20

    p.showPage()
    p.save()
    return response

# ======================================================================================================================================================================
#                                                                       Teacher Views
# ======================================================================================================================================================================

@login_required
def teacher_dashboard(request):
    """O'qituvchi dashboard"""
    if request.user.role != 'teacher':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, "O'qituvchi profili topilmadi")
        return redirect('feedback:login')

    # Statistika
    total_students = teacher.class_assigned.students.count() if teacher.class_assigned else 0
    total_evaluations = teacher.evaluations.count()

    # Haftalik baholashlar
    week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
    weekly_evaluations = teacher.evaluations.filter(created_at__date__gte=week_start).count()

    # O'rtacha ball (dynamic total_score)
    avg_score = Evaluation.objects.filter(teacher=teacher).annotate(
        total_score_calc=Sum('scores__value')
    ).aggregate(avg=Avg('total_score_calc'))['avg'] or 0

    # Yaqinda baholangan talabalar
    recent_evaluations = teacher.evaluations.select_related('student').order_by('-created_at')[:5]

    # Haftada baholanmagan talabalar
    evaluated_ids = teacher.evaluations.filter(
        created_at__date__gte=week_start
    ).values_list('student_id', flat=True)

    unevaluated_students = []
    if teacher.class_assigned:
        unevaluated_students = teacher.class_assigned.students.exclude(
            id__in=evaluated_ids
        )[:5]

    # Haftalik foiz
    weekly_percentage = (weekly_evaluations / total_students * 100) if total_students > 0 else 0

    context = {
        'teacher': teacher,
        'total_students': total_students,
        'total_evaluations': total_evaluations,
        'weekly_evaluations': weekly_evaluations,
        'avg_score': round(avg_score, 1),
        'recent_evaluations': recent_evaluations,
        'unevaluated_students': unevaluated_students,
        'weekly_percentage': round(weekly_percentage, 1),
    }

    return render(request, 'teacher/dashboard.html', context)

@login_required
def teacher_students(request):
    """O'qituvchining o'quvchilari ro'yxati va statistikasi"""
    if request.user.role != 'teacher':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, "O'qituvchi profili topilmadi")
        return redirect('feedback:login')

    if not teacher.class_assigned:
        messages.warning(request, "Sizga sinf biriktirilmagan")
        return redirect('feedback:teacher_dashboard')

    search = request.GET.get('search', '').strip()
    filter_type = request.GET.get('filter', '').strip()
    week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())

    students = teacher.class_assigned.students.all()

    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(student_id__icontains=search)
        )

    # Statistikani o'quvchi obyektlariga qo‘shish
    for student in students:
        evaluations = student.evaluations.filter(teacher=teacher)

        # Yig'indi orqali umumiy ball
        evaluations = evaluations.annotate(
            total_score_calc=Sum('scores__value')
        )

        student.total_evals = evaluations.count()
        student.avg_score = evaluations.aggregate(avg=Avg('total_score_calc'))['avg'] or 0
        student.latest_eval = evaluations.order_by('-created_at').first()
        student.is_evaluated_this_week = evaluations.filter(created_at__date__gte=week_start).exists()

        # Baholash asosida status belgilash
        if student.avg_score >= 85:
            student.status = "A'lo"
        elif student.avg_score >= 70:
            student.status = "Yaxshi"
        elif student.avg_score >= 55:
            student.status = "Qoniqarli"
        else:
            student.status = "Qoniqarsiz" if student.avg_score > 0 else "Baholanmagan"

    # Filter qo‘llash
    if filter_type == 'evaluated':
        students = [s for s in students if s.is_evaluated_this_week]
    elif filter_type == 'not-evaluated':
        students = [s for s in students if not s.is_evaluated_this_week]

    context = {
        'teacher': teacher,
        'students': students,
        'total_students': teacher.class_assigned.students.count(),
        'search': search,
        'filter_type': filter_type,
    }

    return render(request, 'teacher/students.html', context)

@login_required
def teacher_evaluate(request):
    """O'qituvchilar uchun o'quvchilarni baholash sahifasi"""
    if request.user.role != 'teacher':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, "O'qituvchi profili topilmadi")
        return redirect('feedback:login')

    if not teacher.class_assigned:
        messages.warning(request, "Sizga hech qanday sinf biriktirilmagan")
        return redirect('feedback:teacher_dashboard')

    students = teacher.class_assigned.students.all()

    selected_student = None
    student_id = request.GET.get('student')
    if student_id:
        selected_student = students.filter(id=student_id).first()
        if not selected_student:
            messages.error(request, "Tanlangan o'quvchi topilmadi")

    # Haftalik baholash holati
    week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
    for student in students:
        student.is_evaluated_this_week = student.evaluations.filter(
            teacher=teacher,
            created_at__date__gte=week_start
        ).exists()
        student.latest_eval = student.evaluations.filter(
            teacher=teacher
        ).order_by('-created_at').first()

    # Get active criteria
    criteria = Criterion.objects.filter(is_active=True).order_by('name')

    # Formni ikkala holatda ham e'lon qilamiz
    if request.method == "POST":
        form = DynamicEvaluationForm(request.POST, criteria=criteria)
        if form.is_valid():
            # Create or update evaluation
            evaluation, created = Evaluation.objects.get_or_create(
                student=selected_student,
                teacher=teacher,
                week_number=date.today().isocalendar()[1],
                year=date.today().year,
                defaults={'comment': form.cleaned_data.get('comment', '')}
            )
            
            if not created:
                evaluation.comment = form.cleaned_data.get('comment', '')
                evaluation.save()

            # Delete existing scores for this evaluation
            evaluation.scores.all().delete()

            # Create new scores for each criterion
            total_score = 0
            for criterion in criteria:
                score_value = form.cleaned_data.get(f'criterion_{criterion.id}', 0)
                if score_value > 0:
                    EvaluationScore.objects.create(
                        evaluation=evaluation,
                        criterion=criterion,
                        value=score_value
                    )
                    total_score += score_value

            messages.success(request, "Baholar saqlandi.")
            return redirect("feedback:teacher_dashboard")
    else:
        # GET bo'lsa, bo'sh form yaratiladi
        form = DynamicEvaluationForm(criteria=criteria)

    context = {
        'teacher': teacher,
        'students': students,
        'selected_student': selected_student,
        'form': form,
        'criteria': criteria,
    }

    return render(request, 'teacher/evaluate.html', context)

@login_required
def teacher_statistics(request):
    """O'qituvchi statistikasi"""
    if request.user.role != 'teacher':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        messages.error(request, "O'qituvchi profili topilmadi")
        return redirect('feedback:login')

    total_students = teacher.class_assigned.students.count() if teacher.class_assigned else 0

    evaluations = teacher.evaluations.annotate(
        total_scorecalc=Sum('scores__value')
    )

    total_evaluations = evaluations.count()
    avg_score = round(evaluations.aggregate(avg=Avg('total_scorecalc'))['avg'] or 0, 1)

    week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
    weekly_evaluated = evaluations.filter(created_at__date__gte=week_start).count()

    top_students = []
    if teacher.class_assigned:
        top_students = teacher.class_assigned.students.annotate(
            avg_score=Avg('evaluations__scores__value'),
            evaluation_count=Count('evaluations')
        ).filter(evaluation_count__gt=0).order_by('-avg_score')[:5]

    excellent_count = good_count = satisfactory_count = unevaluated_count = 0
    if teacher.class_assigned:
        for student in teacher.class_assigned.students.all():
            avg = student.evaluations.filter(teacher=teacher).annotate(
                total_score_calc=Sum('scores__value')
            ).aggregate(score=Avg('total_score_calc'))['score']
            if avg is None:
                unevaluated_count += 1
            elif avg >= 85:
                excellent_count += 1
            elif avg >= 70:
                good_count += 1
            else:
                satisfactory_count += 1

    # Get criteria averages
    category_averages = {}
    for criterion in Criterion.objects.filter(is_active=True):
        category_averages[criterion.name] = round(
            EvaluationScore.objects.filter(
                evaluation__teacher=teacher,
                criterion=criterion
            ).aggregate(avg=Avg('value'))['avg'] or 0, 1
        )

    weekly_progress = []
    for i in range(4):
        week_start_i = timezone.now().date() - timedelta(days=timezone.now().weekday() + i * 7)
        week_end_i = week_start_i + timedelta(days=6)

        week_evals = evaluations.filter(created_at__date__range=[week_start_i, week_end_i])
        week_avg = round(week_evals.aggregate(avg=Avg('total_scorecalc'))['avg'] or 0, 1)

        weekly_progress.append({
            'week': f'{4 - i}-hafta',
            'evaluations': week_evals.count(),
            'avg_score': week_avg
        })

    context = {
        'teacher': teacher,
        'total_students': total_students,
        'total_evaluations': total_evaluations,
        'avg_score': avg_score,
        'weekly_evaluated': weekly_evaluated,
        'top_students': top_students,
        'excellent_count': excellent_count,
        'good_count': good_count,
        'satisfactory_count': satisfactory_count,
        'unevaluated_count': unevaluated_count,
        'weekly_progress': weekly_progress,
        'category_averages': category_averages,
    }

    return render(request, 'teacher/statistics.html', context)

import io
# -------- 1) Umumiy maktab bo‘yicha barcha o‘quvchilar -------- #
def export_school_report(request):
    if not REPORTLAB_AVAILABLE:
        return HttpResponse("PDF export requires reportlab library", status=500)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("📊 Umumiy maktab hisobot", styles['Heading1']))
    elements.append(Spacer(1, 12))

    data = [["ID", "F.I.Sh", "Sinf", "Baholashlar soni", "O‘rtacha ball", "Holati"]]
    for student in Student.objects.all():
        data.append([
            student.student_id,
            student.full_name,
            student.class_assigned.name,
            student.total_evaluations,
            round(student.average_score, 1),
            student.performance_status
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="umumiy_maktab_report.pdf"'
    response.write(pdf)
    return response

def class_report_list(request):
    classes = Class.objects.all()   # barcha sinflarni olib kelamiz
    return render(request, "manager/class_report_list.html", {"classes": classes})

def export_class_report(request, class_id):
    # Agar umuman sinflar bo'lmasa
    if not Class.objects.exists():
        return HttpResponse("❌ Hali sinflar mavjud emas.", content_type="text/plain")

    try:
        class_obj = Class.objects.get(id=class_id)
    except Class.DoesNotExist:
        return HttpResponse("❌ Bu ID bo‘yicha sinf topilmadi.", content_type="text/plain")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"📘 {class_obj.name} sinf hisobot", styles['Heading1']))
    elements.append(Spacer(1, 12))

    # Jadval ma'lumotlari
    data = [["ID", "F.I.Sh", "Baholashlar soni", "O‘rtacha ball", "Holati"]]
    students = class_obj.students.all()
    if not students.exists():
        elements.append(Paragraph("❌ Ushbu sinfda hali o‘quvchilar mavjud emas.", styles['Normal']))
    else:
        for student in students:
            data.append([
                student.student_id,
                student.full_name,
                student.total_evaluations,
                round(student.average_score, 1),
                student.performance_status
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{class_obj.name}_report.pdf"'
    response.write(pdf)
    return response

# -------- 3) Har bir o‘quvchi bo‘yicha batafsil 4 haftalik hisobot -------- #
def export_student_report(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"👨‍🎓 O‘quvchi: {student.full_name}", styles['Heading1']))
    elements.append(Paragraph(f"Sinf: {student.class_assigned.name}", styles['Heading2']))
    elements.append(Spacer(1, 12))

    # Baholashlar
    evaluations = Evaluation.objects.filter(student=student).order_by('-created_at')[:4]
    for ev in evaluations:
        elements.append(Paragraph(
            f"📅 {ev.created_at.strftime('%Y-%m-%d')} - "
            f"O‘qituvchi: {ev.teacher.user.get_full_name()} - "
            f"Ball: {ev.total_score} ({ev.grade_status})", styles['Normal']
        ))
        if ev.comment:
            elements.append(Paragraph(f"Izoh: {ev.comment}", styles['Italic']))

        # Kriteriyalar jadvali
        score_data = [["Kriteriya", "Ball", "Maks."]]
        for sc in ev.scores.all():
            score_data.append([sc.criterion.name, sc.value, sc.criterion.max_score])

        score_table = Table(score_data, repeatRows=1)
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 12))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.full_name}_report.pdf"'
    response.write(pdf)
    return response

# ======================================================================================================================================================================
#                                                                       API Views
# ======================================================================================================================================================================

@login_required
def generate_student_id(request):
    """Sinf uchun keyingi o'quvchi ID ni generatsiya qilish"""
    class_name = request.GET.get('class')
    if not class_name:
        return JsonResponse({'error': 'Class name required'}, status=400)
    try:
        # Extract grade and section from class name (e.g., "7-A" -> grade=7, section="A")
        match = re.match(r'^(\d+)-([A-Z])$', class_name)
        if not match:
            return JsonResponse({'error': 'Invalid class format'}, status=400)

        grade = match.group(1)
        section = match.group(2)

        # Sinf nomidan 2 ta belgi olish
        class_code = f"{grade}{section}"
        
        # Random 6 xonali raqam generatsiya qilish
        while True:
            random_number = f"{random.randint(100000, 999999)}"
            new_id = f"{class_code}{random_number}"
            if not Student.objects.filter(student_id=new_id).exists():
                break

        return JsonResponse({'student_id': new_id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def toggle_teacher_status(request, teacher_id):
    """O'qituvchi holatini o'zgartirish"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    try:
        teacher = Teacher.objects.get(id=teacher_id)
        teacher.user.is_active = not teacher.user.is_active
        teacher.user.save()
        return JsonResponse({
            'success': True,
            'is_active': teacher.user.is_active
        })
    except Teacher.DoesNotExist:
        return JsonResponse({'error': 'Teacher not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def toggle_student_status(request, student_id):
    """O'quvchi holatini o'zgartirish"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    try:
        student = Student.objects.get(id=student_id)
        student.is_active = not student.is_active
        student.save()
        return JsonResponse({
            'success': True,
            'is_active': student.is_active
        })
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def bulk_actions(request):
    """Bulk amallar"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    try:
        data = json.loads(request.body)
        action = data.get('action')
        item_ids = data.get('item_ids', [])
        item_type = data.get('item_type')

        if not item_ids:
            return JsonResponse({'error': 'No items selected'}, status=400)

        if item_type == 'student':
            items = Student.objects.filter(id__in=item_ids)
        elif item_type == 'teacher':
            items = Teacher.objects.filter(id__in=item_ids)
        else:
            return JsonResponse({'error': 'Invalid item type'}, status=400)
        if action == 'activate':
            if item_type == 'student':
                items.update(is_active=True)
            else:
                User.objects.filter(teacher__in=items).update(is_active=True)
        elif action == 'deactivate':
            if item_type == 'student':
                items.update(is_active=False)
            else:
                User.objects.filter(teacher__in=items).update(is_active=False)
        elif action == 'delete':
            count = items.count()
            items.delete()
            return JsonResponse({'success': True, 'deleted_count': count})
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ======================================================================================================================================================================
#                                                                   Export Views
# ======================================================================================================================================================================

@login_required
def export_excel(request):
    """Excel eksport"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    wb = Workbook()

    # --- STUDENTS SHEET ---
    ws_students = wb.active
    ws_students.title = "O'quvchilar"

    student_headers = [
        "O'quvchi ID", "Ism", "Familiya", "Sinf", "Jami baholar",
        "O'rtacha ball", "Oxirgi baholash", "Holat"
    ]

    for col, header in enumerate(student_headers, 1):
        cell = ws_students.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        ws_students.column_dimensions[get_column_letter(col)].width = 20  # ← ustun kengligi

    students = Student.objects.select_related('class_assigned')
    for row, student in enumerate(students, 2):
        total_evals = student.evaluations.count()
        avg_score = student.evaluations.aggregate(
            avg=Avg('scores__value')
        )['avg'] or 0
        latest_eval = student.evaluations.order_by('-created_at').first()

        if avg_score >= 85:
            status = "A'lo"
        elif avg_score >= 70:
            status = "Yaxshi"
        elif avg_score >= 55:
            status = "Qoniqarli"
        else:
            status = "Qoniqarsiz" if avg_score > 0 else "Baholanmagan"

        ws_students.cell(row=row, column=1, value=student.student_id)
        ws_students.cell(row=row, column=2, value=student.first_name)
        ws_students.cell(row=row, column=3, value=student.last_name)
        ws_students.cell(row=row, column=4, value=student.class_assigned.name)
        ws_students.cell(row=row, column=5, value=total_evals)
        ws_students.cell(row=row, column=6, value=round(avg_score, 1))
        ws_students.cell(row=row, column=7, value=latest_eval.created_at.strftime('%d.%m.%Y') if latest_eval else "Hech qachon")
        ws_students.cell(row=row, column=8, value=status)

    # --- TEACHERS SHEET ---
    ws_teachers = wb.create_sheet("O'qituvchilar")

    teacher_headers = [
        "Ism", "Familiya", "Fan", "Sinf", "Jami baholar",
        "O'rtacha ball", "Bu hafta baholangan", "Holat"
    ]

    for col, header in enumerate(teacher_headers, 1):
        cell = ws_teachers.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        ws_teachers.column_dimensions[get_column_letter(col)].width = 18  # ← ustun kengligi

    teachers = Teacher.objects.select_related('user', 'class_assigned').filter(user__is_active=True)
    week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())

    for row, teacher in enumerate(teachers, 2):
        total_evals = teacher.evaluations.count()
        avg_score = teacher.evaluations.aggregate(
            avg=Avg('scores__value')
        )['avg'] or 0
        weekly_evals = teacher.evaluations.filter(created_at__date__gte=week_start).count()

        ws_teachers.cell(row=row, column=1, value=teacher.user.first_name)
        ws_teachers.cell(row=row, column=2, value=teacher.user.last_name)
        ws_teachers.cell(row=row, column=4, value=teacher.class_assigned.name if teacher.class_assigned else "")
        ws_teachers.cell(row=row, column=5, value=total_evals)
        ws_teachers.cell(row=row, column=6, value=round(avg_score, 1))
        ws_teachers.cell(row=row, column=7, value=weekly_evals)
        ws_teachers.cell(row=row, column=8, value="Faol" if teacher.user.is_active else "Nofaol")

    # Export
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"feedback_report_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@login_required
def export_pdf(request):
    """PDF eksport (placeholder)"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')
    # PDF export implementation would go here
    messages.info(request, "PDF eksport hozircha mavjud emas")
    return redirect('feedback:manager_dashboard')

@login_required
def export_teachers_excel(request):
    """O'qituvchilar ro'yxatini Excel faylga eksport qilish"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    wb = Workbook()
    ws = wb.active
    ws.title = "O'qituvchilar"

    headers = [
        "Ism", "Familiya", "Sinf", "Jami baholar",
        "O'rtacha ball", "Bu hafta baholangan", "Holat"
    ]

    # Ustun sarlavhalar
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        ws.column_dimensions[get_column_letter(col)].width = 22

    # Ma'lumotlar
    week_start = now().date() - timedelta(days=now().weekday())
    teachers = Teacher.objects.select_related('user', 'class_assigned').filter(user__is_active=True)

    for row, teacher in enumerate(teachers, start=2):
        total_evals = teacher.evaluations.count()
        avg_score = teacher.evaluations.aggregate(
            avg=Avg('scores__value')
        )['avg'] or 0

        weekly_evals = teacher.evaluations.filter(created_at__date__gte=week_start).count()

        ws.cell(row=row, column=1, value=teacher.user.first_name)
        ws.cell(row=row, column=2, value=teacher.user.last_name)
        ws.cell(row=row, column=3, value=teacher.class_assigned.name if teacher.class_assigned else "")
        ws.cell(row=row, column=4, value=total_evals)
        ws.cell(row=row, column=5, value=round(avg_score, 1))
        ws.cell(row=row, column=6, value=weekly_evals)
        ws.cell(row=row, column=7, value="Faol" if teacher.user.is_active else "Nofaol")

    # Javob sifatida eksport qilish
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"oqituvchilar_report_{now().strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

# ======================================================================================================================================================================
#                                                               AJAX Views for Student Detail
# ======================================================================================================================================================================

@login_required
def get_student_evaluations(request, student_id):
    """O'quvchi baholash tarixini olish (AJAX)"""
    if request.user.role not in ['manager', 'teacher']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        student = Student.objects.get(id=student_id)
        evaluations = student.evaluations.select_related('teacher__user', 'teacher__subject').order_by('-created_at')

        # If teacher, only show their evaluations
        if request.user.role == 'teacher':
            teacher = Teacher.objects.get(user=request.user)
            evaluations = evaluations.filter(teacher=teacher)
        evaluation_data = []
        for eval in evaluations:
            evaluation_data.append({
                'id': eval.id,
                'date': eval.created_at.strftime('%d.%m.%Y'),
                'teacher': eval.teacher.user.get_full_name(),
                'criteria_scores': {score.criterion.name: score.value for score in eval.scores.all()},
                'total': eval.total_score,
                'comment': eval.comment or '',
                'week': f"{eval.week_number}-hafta"
            })
        return JsonResponse({
            'success': True,
            'evaluations': evaluation_data
        })
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Teacher.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ======================================================================================================================================================================
#                                                               Parent Notification System
# ======================================================================================================================================================================
from main_app.parent_notification import send_student_data_to_parents

@csrf_exempt
def send_grades_to_parents(request):
    """Ota-onalarga o'quvchi baholarini yuborish"""
    if request.method == 'POST':
        from threading import Thread
        import asyncio
        
        def runner():
            try:
                print("🚀 Starting parent notification process...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_student_data_to_parents())
                loop.close()
                print("✅ Parent notification process completed successfully!")
            except Exception as e:
                print("❌ Error in parent notification:", e)
                import traceback
                traceback.print_exc()

        Thread(target=runner).start()
        messages.success(request, "✅ Ota-onalarga baholar yuborish jarayoni boshlandi!")
        return redirect("feedback:manager_dashboard")
    return HttpResponse("❌ POST method kerak")


# DEPRECATED: This function is replaced by parent_notification.py
# Keeping for reference but not used anymore
async def send_messages_to_parents():
    print("📱 Starting send_messages_to_parents async function...")
    if not BOT_AVAILABLE:
        print("❌ Bot is not available. Cannot send messages to parents.")
        return
    
    print("✅ Bot is available, proceeding...")
    now = timezone.now()
    # Use more inclusive week calculation - include today and last 7 days
    week_end = now.date()
    week_start = week_end - timezone.timedelta(days=6)  # Last 7 days including today
    week_number = now.isocalendar()[1]  # ISO hafta raqami

    print(f"📅 Week info: {week_start} to {week_end}, week {week_number}")

    # Oldingi hafta
    prev_week_start = week_start - timezone.timedelta(days=7)
    prev_week_end = week_start - timezone.timedelta(days=1)

    parents = await sync_to_async(
        lambda: list(Parents.objects.select_related("student__class_assigned"))
    )()
    
    print(f"👥 Found {len(parents)} parents")

    for parent in parents:
        student = parent.student
        print(f"👨‍👩‍👧‍👦 Processing parent: {parent.telegram_id}, student: {student.full_name if student else 'None'}")
        if not student:
            print("❌ No student found for parent, skipping...")
            continue

        # Joriy hafta baholari
        current_evals = await sync_to_async(
            lambda: list(
                Evaluation.objects.filter(
                    student=student,
                    created_at__date__gte=week_start,
                    created_at__date__lte=week_end
                ).select_related("teacher", "teacher__user")
            )
        )()

        # Oldingi hafta baholari
        previous_evals = await sync_to_async(
            lambda: list(
                Evaluation.objects.filter(
                    student=student,
                    created_at__date__gte=prev_week_start,
                    created_at__date__lte=prev_week_end
                )
            )
        )()

        if not current_evals:
            print(f"⚠️ No evaluations found for {student.full_name} in current week, skipping...")
            continue

        print(f"📊 Found {len(current_evals)} current evaluations for {student.full_name}")

        current_total = sum(e.total_score for e in current_evals)
        previous_total = sum(e.total_score for e in previous_evals) if previous_evals else 0

        # Ballar tafovutini hisoblash
        difference_msg = ""
        comment_msg = ""

        if previous_total:
            if current_total > previous_total:
                difference_msg = f"📈 Ballar oshgan! Oldingi hafta: {previous_total}, \nJoriy hafta: {current_total} ✅"
            elif current_total < previous_total:
                # Har bir mezon bo‘yicha farq
                # Calculate criteria totals for current and previous weeks
                current_criteria_totals = {}
                prev_criteria_totals = {}
                
                # Get active criteria first
                active_criteria_for_calc = await sync_to_async(
                    lambda: list(Criterion.objects.filter(is_active=True))
                )()
                
                for criterion in active_criteria_for_calc:
                    # Current week scores
                    current_scores = []
                    for eval in current_evals:
                        scores = await sync_to_async(
                            lambda: list(eval.scores.filter(criterion=criterion))
                        )()
                        current_scores.extend([score.value for score in scores])
                    current_criteria_totals[criterion.name] = sum(current_scores)
                    
                    # Previous week scores
                    prev_scores = []
                    for eval in previous_evals:
                        scores = await sync_to_async(
                            lambda: list(eval.scores.filter(criterion=criterion))
                        )()
                        prev_scores.extend([score.value for score in scores])
                    prev_criteria_totals[criterion.name] = sum(prev_scores)

                # Find the criterion with the biggest decrease
                criterion_diffs = []
                for criterion in active_criteria_for_calc:
                    current_total = current_criteria_totals.get(criterion.name, 0)
                    prev_total = prev_criteria_totals.get(criterion.name, 0)
                    diff = current_total - prev_total
                    criterion_diffs.append((criterion.name, diff))
                
                worst_area = min(criterion_diffs, key=lambda x: x[1])[0] if criterion_diffs else "Noma'lum"

                difference_msg = (
                    f"📉 Ballar kamaygan. Oldingi hafta: {previous_total}, Joriy hafta: {current_total} ❗"
                )
                comment_msg = f"⚠️ E’tibor bering: <b>{worst_area}</b> mezonida ko‘proq pasayish kuzatildi."
            else:
                difference_msg = "➖ Ballarda o‘zgarish yo‘q."

        else:
            difference_msg = "ℹ️ Bu hafta uchun birinchi baholash"

        # Xabarni tuzamiz
        active_criteria = await sync_to_async(
            lambda: list(Criterion.objects.filter(is_active=True))
        )()
        max_possible = sum(c.max_score for c in active_criteria)
        
        msg = (
            f"📌 <b>{student.first_name} {student.last_name}</b>\n"
            f"🏫 Sinf: {student.class_assigned.name}\n"
            f"📅 Hafta: {week_number}-hafta\n\n"
            f"{difference_msg}\n"
            f"{comment_msg}\n\n"
            f"📊 <b>Umumiy natija:</b> {current_total}/{max_possible} ball\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
        )

        for eval in current_evals:
            teacher_name = eval.teacher.user.get_full_name() if eval.teacher and eval.teacher.user else "Noma'lum"
            
            # Kriteriya bo'yicha ballar
            criteria_scores = ""
            for criterion in active_criteria:
                score_obj = await sync_to_async(
                    lambda: eval.scores.filter(criterion=criterion).first()
                )()
                score_value = score_obj.value if score_obj else 0
                criteria_scores += f"📋 <b>{criterion.name}:</b> {score_value}/{criterion.max_score}\n"
            
            # Baholash holati
            status_emoji = {
                "A'lo": "🌟",
                "Yaxshi": "👍", 
                "Qoniqarli": "👌",
                "Qoniqarsiz": "⚠️"
            }
            
            msg += (
                f"👨‍🏫 <b>O'qituvchi:</b> {teacher_name}\n"
                f"📅 <b>Sana:</b> {eval.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"{criteria_scores}"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Jami ball:</b> {eval.total_score}/{max_possible} ({eval.percentage_score}%)\n"
                f"{status_emoji.get(eval.grade_status, '📊')} <b>Holati:</b> {eval.grade_status}\n"
                f"💬 <b>Izoh:</b> {eval.comment or 'Izoh qoldirilmagan'}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            )

        try:
            print(f"📤 Sending message to parent {parent.telegram_id}...")
            await bot.send_message(parent.telegram_id, msg, parse_mode="HTML")
            print(f"✅ Message sent successfully to parent {parent.telegram_id}")
        except Exception as e:
            print(f"❌ [Xatolik] Ota-onaga yuborishda: {e}")
            import traceback
            traceback.print_exc()
    
    print("🎉 Finished processing all parents!")

# ======================================================================================================================================================================
#                                                               Enhanced PDF Reports
# ======================================================================================================================================================================

@login_required
def export_comprehensive_student_report(request, student_id):
    """Batafsil o'quvchi hisoboti PDF"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    student = get_object_or_404(Student, id=student_id)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    elements.append(Paragraph(f"👨‍🎓 O'quvchi: {student.full_name}", styles['Heading1']))
    elements.append(Paragraph(f"Sinf: {student.class_assigned.name} | ID: {student.student_id}", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    # Student info
    info_data = [
        ["Ma'lumot", "Qiymat"],
        ["Ism", student.first_name],
        ["Familiya", student.last_name],
        ["Sinf", student.class_assigned.name],
        ["O'quvchi ID", student.student_id],
        ["Tug'ilgan sana", student.date_of_birth.strftime('%d.%m.%Y')],
        ["Ota-ona telefoni", student.parent_phone or "Kiritilmagan"],
        ["Ro'yxatga olingan sana", student.enrollment_date.strftime('%d.%m.%Y')],
    ]
    
    info_table = Table(info_data, repeatRows=1)
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Evaluations with criteria
    evaluations = Evaluation.objects.filter(student=student).order_by('-created_at')
    
    if evaluations.exists():
        elements.append(Paragraph("📊 Baholash tarixi", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        for eval in evaluations:
            # Evaluation header
            elements.append(Paragraph(
                f"📅 {eval.created_at.strftime('%d.%m.%Y')} - "
                f"O'qituvchi: {eval.teacher.user.get_full_name()} - "
                f"Hafta: {eval.week_number} - "
                f"Jami ball: {eval.total_score}", 
                styles['Heading3']
            ))
            
            # Criteria scores table
            if eval.scores.exists():
                criteria_data = [["Kriteriya", "Ball", "Maksimal", "Foiz"]]
                for score in eval.scores.all():
                    percentage = (score.value / score.criterion.max_score * 100) if score.criterion.max_score > 0 else 0
                    criteria_data.append([
                        score.criterion.name,
                        str(score.value),
                        str(score.criterion.max_score),
                        f"{percentage:.1f}%"
                    ])
                
                criteria_table = Table(criteria_data, repeatRows=1)
                criteria_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ]))
                elements.append(criteria_table)
            
            # Comment
            if eval.comment:
                elements.append(Paragraph(f"💬 Izoh: {eval.comment}", styles['Normal']))
            
            elements.append(Spacer(1, 12))
    else:
        elements.append(Paragraph("❌ Hali baholashlar mavjud emas", styles['Normal']))
    
    # Statistics
    elements.append(Paragraph("📈 Statistika", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    stats_data = [
        ["Ko'rsatkich", "Qiymat"],
        ["Jami baholashlar", str(student.total_evaluations)],
        ["O'rtacha ball", f"{student.average_score:.1f}"],
        ["Holat", student.performance_status],
    ]
    
    stats_table = Table(stats_data, repeatRows=1)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(stats_table)
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.full_name}_batafsil_hisobot.pdf"'
    response.write(pdf)
    return response

@login_required
def export_weekly_report(request):
    """Haftalik hisobot PDF"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    week_number = request.GET.get('week', date.today().isocalendar()[1])
    year = request.GET.get('year', date.today().year)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    elements.append(Paragraph(f"📅 Haftalik hisobot - {year} yil {week_number}-hafta", styles['Heading1']))
    elements.append(Spacer(1, 12))
    
    # Get evaluations for the week
    evaluations = Evaluation.objects.filter(
        week_number=week_number,
        year=year
    ).select_related('student', 'teacher__user', 'student__class_assigned')
    
    if evaluations.exists():
        # Summary statistics
        total_evaluations = evaluations.count()
        total_students = evaluations.values('student').distinct().count()
        avg_score = evaluations.aggregate(avg=Avg('scores__value'))['avg'] or 0
        
        summary_data = [
            ["Ko'rsatkich", "Qiymat"],
            ["Jami baholashlar", str(total_evaluations)],
            ["Baholangan o'quvchilar", str(total_students)],
            ["O'rtacha ball", f"{avg_score:.1f}"],
        ]
        
        summary_table = Table(summary_data, repeatRows=1)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Detailed evaluations
        elements.append(Paragraph("📊 Batafsil baholashlar", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        eval_data = [["O'quvchi", "Sinf", "O'qituvchi", "Jami ball", "Holat"]]
        for eval in evaluations:
            eval_data.append([
                eval.student.full_name,
                eval.student.class_assigned.name,
                eval.teacher.user.get_full_name(),
                str(eval.total_score),
                eval.grade_status
            ])
        
        eval_table = Table(eval_data, repeatRows=1)
        eval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(eval_table)
    else:
        elements.append(Paragraph(f"❌ {year} yil {week_number}-hafta uchun baholashlar topilmadi", styles['Normal']))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="haftalik_hisobot_{year}_{week_number}.pdf"'
    response.write(pdf)
    return response

@login_required
def export_monthly_report(request):
    """Oylik hisobot PDF"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    month = request.GET.get('month', date.today().month)
    year = request.GET.get('year', date.today().year)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    elements.append(Paragraph(f"📅 Oylik hisobot - {year} yil {month}-oy", styles['Heading1']))
    elements.append(Spacer(1, 12))
    
    # Get evaluations for the month
    evaluations = Evaluation.objects.filter(
        month=month,
        year=year
    ).select_related('student', 'teacher__user', 'student__class_assigned')
    
    if evaluations.exists():
        # Summary statistics
        total_evaluations = evaluations.count()
        total_students = evaluations.values('student').distinct().count()
        avg_score = evaluations.aggregate(avg=Avg('scores__value'))['avg'] or 0
        
        # Class statistics
        class_stats = {}
        for eval in evaluations:
            class_name = eval.student.class_assigned.name
            if class_name not in class_stats:
                class_stats[class_name] = {'count': 0, 'total_score': 0}
            class_stats[class_name]['count'] += 1
            class_stats[class_name]['total_score'] += eval.total_score
        
        summary_data = [
            ["Ko'rsatkich", "Qiymat"],
            ["Jami baholashlar", str(total_evaluations)],
            ["Baholangan o'quvchilar", str(total_students)],
            ["O'rtacha ball", f"{avg_score:.1f}"],
        ]
        
        summary_table = Table(summary_data, repeatRows=1)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Class statistics
        elements.append(Paragraph("📊 Sinf bo'yicha statistika", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        class_data = [["Sinf", "Baholashlar soni", "O'rtacha ball"]]
        for class_name, stats in class_stats.items():
            avg_class_score = stats['total_score'] / stats['count'] if stats['count'] > 0 else 0
            class_data.append([
                class_name,
                str(stats['count']),
                f"{avg_class_score:.1f}"
            ])
        
        class_table = Table(class_data, repeatRows=1)
        class_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(class_table)
    else:
        elements.append(Paragraph(f"❌ {year} yil {month}-oy uchun baholashlar topilmadi", styles['Normal']))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="oylik_hisobot_{year}_{month}.pdf"'
    response.write(pdf)
    return response

@login_required
def export_yearly_report(request):
    """Yillik hisobot PDF"""
    if request.user.role != 'manager':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q")
        return redirect('feedback:login')

    year = request.GET.get('year', date.today().year)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    elements.append(Paragraph(f"📅 Yillik hisobot - {year} yil", styles['Heading1']))
    elements.append(Spacer(1, 12))
    
    # Get evaluations for the year
    evaluations = Evaluation.objects.filter(
        year=year
    ).select_related('student', 'teacher__user', 'student__class_assigned')
    
    if evaluations.exists():
        # Summary statistics
        total_evaluations = evaluations.count()
        total_students = evaluations.values('student').distinct().count()
        avg_score = evaluations.aggregate(avg=Avg('scores__value'))['avg'] or 0
        
        # Monthly statistics
        monthly_stats = {}
        for eval in evaluations:
            month = eval.month
            if month not in monthly_stats:
                monthly_stats[month] = {'count': 0, 'total_score': 0}
            monthly_stats[month]['count'] += 1
            monthly_stats[month]['total_score'] += eval.total_score
        
        summary_data = [
            ["Ko'rsatkich", "Qiymat"],
            ["Jami baholashlar", str(total_evaluations)],
            ["Baholangan o'quvchilar", str(total_students)],
            ["O'rtacha ball", f"{avg_score:.1f}"],
        ]
        
        summary_table = Table(summary_data, repeatRows=1)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Monthly statistics
        elements.append(Paragraph("📊 Oylik statistika", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        monthly_data = [["Oy", "Baholashlar soni", "O'rtacha ball"]]
        for month in sorted(monthly_stats.keys()):
            stats = monthly_stats[month]
            avg_month_score = stats['total_score'] / stats['count'] if stats['count'] > 0 else 0
            monthly_data.append([
                f"{month}-oy",
                str(stats['count']),
                f"{avg_month_score:.1f}"
            ])
        
        monthly_table = Table(monthly_data, repeatRows=1)
        monthly_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(monthly_table)
        
        # Top students
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("🏆 Eng yaxshi o'quvchilar", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        # Calculate average scores for each student
        student_scores = {}
        for eval in evaluations:
            student_id = eval.student.id
            if student_id not in student_scores:
                student_scores[student_id] = {
                    'name': eval.student.full_name,
                    'class': eval.student.class_assigned.name,
                    'scores': [],
                    'total_evaluations': 0
                }
            student_scores[student_id]['scores'].append(eval.total_score)
            student_scores[student_id]['total_evaluations'] += 1
        
        # Calculate averages and sort
        top_students = []
        for student_id, data in student_scores.items():
            avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
            top_students.append({
                'name': data['name'],
                'class': data['class'],
                'avg_score': avg_score,
                'evaluations': data['total_evaluations']
            })
        
        top_students.sort(key=lambda x: x['avg_score'], reverse=True)
        top_students = top_students[:10]  # Top 10
        
        top_data = [["O'quvchi", "Sinf", "O'rtacha ball", "Baholashlar soni"]]
        for student in top_students:
            top_data.append([
                student['name'],
                student['class'],
                f"{student['avg_score']:.1f}",
                str(student['evaluations'])
            ])
        
        top_table = Table(top_data, repeatRows=1)
        top_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(top_table)
    else:
        elements.append(Paragraph(f"❌ {year} yil uchun baholashlar topilmadi", styles['Normal']))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="yillik_hisobot_{year}.pdf"'
    response.write(pdf)
    return response
