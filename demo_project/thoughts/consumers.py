from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async

from .models import Thought


class ThoughtStdInConsumer(AsyncConsumer):
    async def cli_parse(self, msg):
        """
        Extract command from incoming message and parse appropriately
        """
        if not 'text' in msg or not  msg['text']:
            raise ValueError('No valid command passed')

        text = msg['text']
        command = text.split(' ')[0].lower()

        if command == 'count':
            count = await self.get_thought_count()
            await self.send_msg('There are {} deep thoughts!'.format(count))
        elif command == 'random':
            thought = await self.get_random_thought()
            await self.send_msg(thought)
        elif command == 'add':
            thought_text = text[4:]
            thought = await self.record_thought(thought_text)
            await self.send_msg('Recorded thought "{}"'.format(thought.content))
        else:
            await self.send_msg('"{}" does not contain a valid command'.format(text))

    async def send_msg(self, text):
        await self.send({
            'type': 'cli.print',
            'text': text,
        })

    @database_sync_to_async
    def get_thought_count(self):
        return Thought.objects.count()

    @database_sync_to_async
    def get_random_thought(self):
        return Thought.objects.order_by('?')[0].content

    @database_sync_to_async
    def record_thought(self, thought_text):
        return Thought.objects.create(content=thought_text)
