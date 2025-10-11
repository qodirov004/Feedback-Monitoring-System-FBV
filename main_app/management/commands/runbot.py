import asyncio
from django.core.management import BaseCommand

from ...bot.loader import main

class Command(BaseCommand):
    help = 'Start the Telegram bot'
    
    def handle(self, *args, **kwargs):
        asyncio.run(main())
        