from aiogram import Router,F,Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import CommandStart
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import Message,CallbackQuery,KeyboardButton,FSInputFile

from ...filters.chat_type import chat_type_filter
from ...states.state_user.state_us import StateUser
from ...keyboards.inline.button import CreateInline
from ...keyboards.reply.rep_button import Createreply


user_private_router = Router()
user_private_router.message.filter(chat_type_filter(['chanel']))

@user_private_router.message(CommandStart())
async def private_start(message:Message):
    await message.answer('hi chanel')
