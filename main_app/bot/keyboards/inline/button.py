from aiogram.types import InlineKeyboardButton,InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from main_app.models import Class, Student

def CreateInline(*args,**kwargs) -> InlineKeyboardBuilder:
    bulder = InlineKeyboardBuilder()
    for i in args:
        bulder.add(InlineKeyboardButton(text=i,callback_data=i))
    for l,g in kwargs.items():
        bulder.add(InlineKeyboardButton(text=g,callback_data=l))
    bulder.adjust(2)
    return bulder.as_markup()
        
def get_class_buttons() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cls in Class.objects.all():
        builder.button(text=cls.name, callback_data=str(cls.id))
    builder.adjust(2)
    return builder.as_markup()

def get_student_name(class_id) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    students = Student.objects.filter(class_assigned_id=class_id)

    for student in students:
        builder.button(
            text=f"{student.first_name} {student.last_name}",
            callback_data=f"student_{student.id}"
        )
    builder.adjust(2)
    return builder.as_markup()