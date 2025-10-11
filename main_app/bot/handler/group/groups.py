from aiogram import Router,F,Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart,and_f
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import Message,ChatPermissions,CallbackQuery,KeyboardButton,FSInputFile

from ...filters.chat_type import chat_type_filter
from ...states.state_user.state_us import StateUser
from ...keyboards.inline.button import CreateInline
from ...keyboards.reply.rep_button import Createreply


user_private_router = Router()
user_private_router.message.filter(chat_type_filter(['group']))


@user_private_router.message(CommandStart())
async def one_cmd(message:Message):
    await message.answer('hi bro')

@user_private_router.message(F.text=='hi',F.chat.type=='supergroup')
async def find(message:Message):
    await message.answer(f'{message.chat.title}\n{message.chat.type}\n{message.chat.id}')
    await message.delete()

@user_private_router.message(F.chat.type=='supergroup',F.new_chat_members)
async def new_users(message:Message):
    for i in message.new_chat_members:
        await message.answer(f"{i.first_name} joined our group ")
        await message.delete()

@user_private_router.message(F.chat.type=='supergroup',F.new_chat.member)
async def uot_group(message:Message):
    await message.answer(f"{message.left_chat_member.first_name} left the group")
    await message.delete()

@user_private_router.message(F.chat.type=='supergroup',and_f(F.text=='ban chat',F.reply_to_message))
async def dont_send_message(message:Message):
    user_id = message.reply_to_message.from_user.id
    per = ChatPermissions(can_send_messages=False)
    await message.chat.restrict(user_id,per)
    await message.answer(f'{message.reply_to_message.from_user.first_name} got banned')

@user_private_router.message(F.chat.type=='supergroup',and_f(F.text=='can',F.reply_to_message))
async def dont_send_message(message:Message):
    user_id = message.reply_to_message.from_user.id
    per = ChatPermissions(can_send_messages=True)
    await message.chat.restrict(user_id,per)
    await message.answer(f'{message.reply_to_message.from_user.first_name} gained access to the chat ')

@user_private_router.message(F.chat.type=='supergroup',and_f(F.text=='ban user',F.reply_to_message))
async def ban_user(message:Message):
    user_id = message.reply_to_message.from_user.id
    await message.chat.ban_sender_chat(user_id)
    await message.answer(f'{message.reply_to_message.from_user.first_name} got banned')

@user_private_router.message(F.chat.type=='supergroup',and_f(F.text=='unban user',F.reply_to_message))
async def ban_user(message:Message):
    user_id = message.reply_to_message.from_user.id
    await message.chat.unban_sender_chat(user_id)
    await message.answer(f'{message.reply_to_message.from_user.first_name} unbanned')
