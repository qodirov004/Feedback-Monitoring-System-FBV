from aiogram import Router,F,Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import CommandStart
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import Message,CallbackQuery,KeyboardButton,FSInputFile

from ...filters.chat_type import chat_type_filter
from ...states.state_user.state_us import StateUser
from ...keyboards.inline.button import CreateInline, get_class_buttons, get_student_name
from ...keyboards.reply.rep_button import Createreply
from asgiref.sync import sync_to_async
from main_app.models import Parents, Student

user_private_router = Router()
user_private_router.message.filter(chat_type_filter(['private']))

@user_private_router.message(CommandStart())
async def private_start(message: Message, state: FSMContext):
    await message.answer(
        f'Salom <a href="{message.from_user.url}">{message.from_user.full_name}</a>',
        parse_mode="HTML"
    )
    await message.answer("Iltimos farzandingiz ID sini kiriting!")
    await state.set_state(StateUser.idsi)

@user_private_router.message()
async def save_student_id(message: Message, state: FSMContext):
    student_id = message.text.strip()

    # Student borligini tekshirish
    student = await sync_to_async(Student.objects.filter(student_id=student_id).first)()
    if not student:
        await message.answer("❌ Bunday IDga ega o‘quvchi topilmadi. Iltimos, to‘g‘ri ID kiriting.")
        return

    # Parent mavjudligini tekshirish
    parent = await sync_to_async(Parents.objects.filter(
        telegram_id=message.from_user.id
    ).first)()

    if parent:
        if parent.student == student:
            await message.answer("ℹ️ Siz allaqachon shu o‘quvchi ID’sini saqlagansiz.")
        else:
            parent.student = student
            await sync_to_async(parent.save)()
            await message.answer("✅ Farzandingiz ID yangilandi. Endi sizga har hafta yangi baholari yuboriladi.")
    else:
        # Yangi parent yozuvi yaratish
        await sync_to_async(Parents.objects.create)(
            telegram_id=message.from_user.id,
            student=student
        )
        await message.answer("✅ Farzandingiz ID muvaffaqiyatli saqlandi. Endi sizga har hafta baholari yuboriladi.")

    await state.clear()

