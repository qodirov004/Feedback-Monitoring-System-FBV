from aiogram import Bot,Dispatcher
from set_app.settings import BOT_TOKEN
from aiogram.client.bot import DefaultBotProperties

from .handler.users.private import user_private_router

bot = Bot(token=BOT_TOKEN,default=DefaultBotProperties(parse_mode='HTML'))
ds = Dispatcher()

ds.include_router(user_private_router)

async def on_startup(bot):
    print('I work')

async def main():
    ds.startup.register(on_startup)
    await ds.start_polling(bot)
