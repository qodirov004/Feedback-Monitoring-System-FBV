# ========================
# Parent Notification System
# ========================
"""
Bu modul ota-onalarga o'quvchi baholarini yuborish uchun yozilgan.
Models strukturasiga mos ravishda ishlaydi:
- Student: O'quvchi ma'lumotlari
- Evaluation: Baholash ma'lumotlari (week_number, year bilan)
- EvaluationScore: Har bir kriteriya bo'yicha ballar
- Parents: Ota-ona va Telegram ID bog'lanishi
- Criterion: Baholash kriteriyalari
"""

# Standard library imports
import asyncio
from threading import Thread

# Django imports
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

# Third-party imports
from asgiref.sync import sync_to_async

# Local imports
from .models import Parents, Evaluation, Criterion, Student

# Bot import - to'g'ridan-to'g'ri yaratish
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


@csrf_exempt
def send_grades_to_parents(request):
    """Ota-onalarga o'quvchi baholarini yuborish"""
    if request.method == 'POST':
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


async def send_student_data_to_parents():
    """Ota-onalarga o'quvchi ma'lumotlarini yuborish"""
    print("📱 Starting send_student_data_to_parents async function...")
    
    if not BOT_AVAILABLE:
        print("❌ Bot is not available. Cannot send messages to parents.")
        return
    
    print("✅ Bot is available, proceeding...")
    
    # Joriy hafta ma'lumotlari
    now = timezone.now()
    week_start = now.date() - timezone.timedelta(days=6)  # 7 kun oldin
    week_end = now.date()
    
    # Oyning hafta raqamini hisoblash
    def get_week_of_month(date):
        """Oyning hafta raqamini olish"""
        first_day = date.replace(day=1)
        first_weekday = first_day.weekday()  # 0 = Dushanba, 6 = Yakshanba
        # Birinchi haftada nechta kun bor
        first_week_days = 7 - first_weekday
        # Joriy kunning oy ichidagi pozitsiyasi
        day_of_month = date.day
        if day_of_month <= first_week_days:
            return 1
        else:
            return ((day_of_month - first_week_days - 1) // 7) + 2
    
    current_week = get_week_of_month(now.date())  # Oyning hafta raqami
    current_year = now.year
    current_month = now.month
    
    print(f"📅 Week range: {week_start} to {week_end}, week: {current_week}, year: {current_year}")
    
    # Barcha ota-onalarni olish
    parents = await sync_to_async(
        lambda: list(Parents.objects.select_related("student__class_assigned"))
    )()
    
    print(f"👥 Found {len(parents)} parents")
    
    if not parents:
        print("⚠️ No parents found in the system")
        return
    
    # Aktiv kriteriyalarni olish
    active_criteria = await sync_to_async(
        lambda: list(Criterion.objects.filter(is_active=True))
    )()
    
    print(f"📋 Found {len(active_criteria)} active criteria")
    
    if not active_criteria:
        print("⚠️ No active criteria found")
        return
    
    max_possible_score = sum(c.max_score for c in active_criteria)
    print(f"📊 Max possible score: {max_possible_score}")
    
    # Har bir ota-onaga xabar yuborish
    for parent in parents:
        student = parent.student
        print(f"👨‍👩‍👧‍👦 Processing parent: {parent.telegram_id}, student: {student.full_name}")
        
        if not student:
            print("❌ No student found for parent, skipping...")
            continue
        
        # Joriy hafta baholashlarini olish (sana bo'yicha)
        current_evaluations = await sync_to_async(
            lambda: list(
                Evaluation.objects.filter(
                    student=student,
                    created_at__date__gte=week_start,
                    created_at__date__lte=week_end
                ).select_related("teacher__user").prefetch_related("scores__criterion")
            )
        )()
        
        print(f"📊 Found {len(current_evaluations)} evaluations for {student.full_name} in week {current_week}")
        
        if not current_evaluations:
            print(f"⚠️ No evaluations found for {student.full_name} in current week, skipping...")
            continue
        
        # Oldingi hafta baholashlarini olish (taqqoslash uchun)
        prev_week_start = week_start - timezone.timedelta(days=7)
        prev_week_end = week_start - timezone.timedelta(days=1)
        
        previous_evaluations = await sync_to_async(
            lambda: list(
                Evaluation.objects.filter(
                    student=student,
                    created_at__date__gte=prev_week_start,
                    created_at__date__lte=prev_week_end
                ).prefetch_related("scores__criterion")
            )
        )()
        
        # Joriy va oldingi hafta umumiy ballarni hisoblash
        current_total = 0
        for eval_obj in current_evaluations:
            current_total += await sync_to_async(lambda obj: obj.total_score)(eval_obj)
        
        previous_total = 0
        if previous_evaluations:
            for eval_obj in previous_evaluations:
                previous_total += await sync_to_async(lambda obj: obj.total_score)(eval_obj)
        
        print(f"📈 Current week total: {current_total}, Previous week total: {previous_total}")
        
        # Xabar matnini tuzish
        message = await build_parent_message(
            student, 
            current_evaluations, 
            current_total, 
            previous_total, 
            max_possible_score,
            current_week,
            current_year,
            current_month,
            active_criteria
        )
        
        # Telegram orqali xabar yuborish
        try:
            print(f"📤 Sending message to parent {parent.telegram_id}...")
            await bot.send_message(parent.telegram_id, message, parse_mode="HTML")
            print(f"✅ Message sent successfully to parent {parent.telegram_id}")
        except Exception as e:
            print(f"❌ Error sending message to parent {parent.telegram_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print("🎉 Finished processing all parents!")


async def build_parent_message(student, evaluations, current_total, previous_total, max_possible_score, week_number, year, month, active_criteria):
    """Ota-ona uchun xabar matnini tuzish"""
    
    # Ballar o'zgarishini hisoblash
    difference_msg = ""
    comment_msg = ""
    
    if previous_total > 0:
        if current_total > previous_total:
            diff = current_total - previous_total
            difference_msg = f"📈 Ballar oshgan! Oldingi hafta: {previous_total}, Joriy hafta: {current_total} ✅"
            comment_msg = "🎉 Ajoyib! Farzandingiz yaxshilandi!"
        elif current_total < previous_total:
            diff = previous_total - current_total
            difference_msg = f"📉 Ballar kamaygan. Oldingi hafta: {previous_total}, Joriy hafta: {current_total} ❗"
            comment_msg = "💪 Keyingi hafta yanada yaxshiroq bo'lishga harakat qiling!"
        else:
            difference_msg = "➖ Ballarda o'zgarish yo'q"
    else:
        difference_msg = "ℹ️ Bu hafta uchun birinchi baholash"
    
    # Oy nomlarini olish
    month_names = {
        1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
        7: "Iyul", 8: "Avgust", 9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
    }
    
    # Asosiy xabar
    message = f"""📌 <b>{student.full_name}</b>
🏫 Sinf: {student.class_assigned.name}
📅 Hafta: {year} yil {month_names[month]} oyi {week_number}-hafta
🆔 ID: {student.student_id}

{difference_msg}
{comment_msg}

📊 <b>Umumiy natija:</b> {current_total}/{max_possible_score} ball ({round((current_total/max_possible_score)*100, 1)}%)
━━━━━━━━━━━━━━━━━━━━━
"""
    
    # Har bir baholash uchun batafsil ma'lumot
    for evaluation in evaluations:
        teacher_name = evaluation.teacher.user.get_full_name() if evaluation.teacher and evaluation.teacher.user else "Noma'lum"
        
        # Kriteriya bo'yicha ballar
        criteria_details = ""
        for criterion in active_criteria:
            score_obj = await sync_to_async(
                lambda: evaluation.scores.filter(criterion=criterion).first()
            )()
            score_value = score_obj.value if score_obj else 0
            criteria_details += f"📋 <b>{criterion.name}:</b> {score_value}/{criterion.max_score} ball\n"
        
        # Baholash holati emoji
        status_emoji = {
            "A'lo": "🌟",
            "Yaxshi": "👍", 
            "Qoniqarli": "👌",
            "Qoniqarsiz": "⚠️"
        }
        
        # Evaluation ma'lumotlarini async tarzda olish
        eval_total_score = await sync_to_async(lambda obj: obj.total_score)(evaluation)
        eval_percentage_score = await sync_to_async(lambda obj: obj.percentage_score)(evaluation)
        eval_grade_status = await sync_to_async(lambda obj: obj.grade_status)(evaluation)
        
        message += f"""
👨‍🏫 <b>O'qituvchi:</b> {teacher_name}
📅 <b>Sana:</b> {evaluation.created_at.strftime('%d.%m.%Y %H:%M')}
━━━━━━━━━━━━━━━━━━━━━
{criteria_details}
━━━━━━━━━━━━━━━━━━━━━
📊 <b>Jami ball:</b> {eval_total_score}/{max_possible_score} ({eval_percentage_score}%)
{status_emoji.get(eval_grade_status, '📊')} <b>Holati:</b> {eval_grade_status}
💬 <b>Izoh:</b> {evaluation.comment or 'Izoh qoldirilmagan'}
━━━━━━━━━━━━━━━━━━━━━

"""
    
    message += f"""
📞 <b>Aloqa:</b> {student.parent_phone or 'Telefon raqami kiritilmagan'}

<i>Bu xabar avtomatik tarzda yuborilgan. Savollar bo'yicha maktab bilan bog'laning.</i>
"""
    
    return message


# ========================
# Bot Handler Updates
# ========================

async def register_parent_with_student(telegram_id, student_id):
    """Ota-onani o'quvchi bilan bog'lash"""
    try:
        # Student borligini tekshirish
        student = await sync_to_async(Student.objects.filter(student_id=student_id).first)()
        if not student:
            return False, "❌ Bunday IDga ega o'quvchi topilmadi. Iltimos, to'g'ri ID kiriting."
        
        # Parentni olish
        parent = await sync_to_async(Parents.objects.filter(telegram_id=telegram_id).select_related("student").first)()
        
        if parent:
            # Agar allaqachon shu o'quvchi bilan bog'langan bo'lsa
            if parent.student.id == student.id:
                return True, "ℹ️ Siz allaqachon shu o'quvchi ID'sini saqlagansiz."
            else:
                # Yangi o'quvchi bilan bog'lash
                parent.student = student
                await sync_to_async(parent.save)()
                return True, "✅ Farzandingiz ID yangilandi. Endi sizga har hafta yangi baholari yuboriladi."
        else:
            # Yangi yozuv yaratish
            await sync_to_async(Parents.objects.create)(
                telegram_id=telegram_id,
                student=student
            )
            return True, "✅ Farzandingiz ID muvaffaqiyatli saqlandi. Endi sizga har hafta baholari yuboriladi."
    
    except Exception as e:
        return False, f"❌ Xatolik yuz berdi: {str(e)}"


# ========================
# Utility Functions
# ========================

def get_student_weekly_summary(student, week_number, year):
    """O'quvchi uchun haftalik xulosa"""
    evaluations = Evaluation.objects.filter(
        student=student,
        week_number=week_number,
        year=year
    ).select_related("teacher__user").prefetch_related("scores__criterion")
    
    if not evaluations.exists():
        return None
    
    total_score = sum(eval.total_score for eval in evaluations)
    max_possible = sum(c.max_score for c in Criterion.objects.filter(is_active=True))
    percentage = round((total_score / max_possible) * 100, 1) if max_possible > 0 else 0
    
    return {
        'evaluations': evaluations,
        'total_score': total_score,
        'max_possible': max_possible,
        'percentage': percentage,
        'count': evaluations.count()
    }


def get_parent_notification_stats():
    """Ota-ona bildirishnomalari statistikasi"""
    total_parents = Parents.objects.count()
    parents_with_students = Parents.objects.filter(student__isnull=False).count()
    parents_without_students = total_parents - parents_with_students
    
    return {
        'total_parents': total_parents,
        'parents_with_students': parents_with_students,
        'parents_without_students': parents_without_students
    }
