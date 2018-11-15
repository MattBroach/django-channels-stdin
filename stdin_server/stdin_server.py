import argparse
import importlib
import asyncio
import sys
import traceback
from contextlib import suppress

from daphne.utils import import_by_path


class StdInServer:
    # Time, in seconds, that any active futures should be inspected for exceptions
    exception_check_frequency = 1

    def __init__(self, application):
        """
        Loads the correct consumer by instantiating the application
        """
        self.loop = asyncio.get_event_loop()

        application_instance = application(scope={
            'type': 'stdin',
        })
        self.application_queue = asyncio.Queue()
        self.application_future = asyncio.ensure_future(application_instance(
                receive=self.application_queue.get,
                send=self.print_response
            ), loop=self.loop,
        )

    async def print_response(self, msg):
        """
        Receives messages from the conumser and prints them to back to the console.  In this case,
        it's expecting messages of the format:
            {
                'type': 'cli.print',
                'text': 'MESSAGE TO PRINT'
            }
        """
        if 'type' not in msg:
            raise ValueError("Message has no `type` defined")

        elif msg['type'] == 'cli.print':
            print('--> {}'.format(msg['text']))

        else:
            raise ValueError("Server cannot handle message type {}".format(msg['type']))

    async def handle_input(self):
        """
        Read input from the console and send it to channels. `run_in_executor` is used
        to wait for the input in another thread, thereby not blocking the loop until
        the user hits enter
        """
        print("Enter commands:")
        while True:
            line = await self.loop.run_in_executor(None, sys.stdin.readline)
            line = line.strip()

            if line == 'q' or line == 'quit':
                break

            await self.send_message(line.strip())
            
    async def send_message(self, text):
        """
        Formats the message from console input for consumption by the consumer
        """
        msg = {
            'type': 'cli.parse',
            'text': text,
        }
        self.application_queue.put_nowait(msg)

    def start(self):
        """
        Initiates exception checking for the futures and begins processing them
        """
        self.input_future = asyncio.ensure_future(self.handle_input(), loop=self.loop)
        self.loop.call_later(self.exception_check_frequency, self.exception_checker)
        self.loop.run_until_complete(self.input_future)

        self.stop()

    def exception_checker(self):
        """
        Because asyncio Futures don't surface exceptions on there own, we need to periodically 
        inspect all active future objects and suface any exceptions found
        """
        futures = [self.application_future, self.input_future]

        for future in futures:
            if future and future.done():
                try:
                    exception = future.exception()
                except asyncio.CancelledError:
                    # Future cancellation. We can ignore this.
                    pass
                else:
                    if exception:
                        exception_output = "{}\n{}{}".format(
                            exception,
                            "".join(traceback.format_tb(
                                exception.__traceback__,
                            )),
                            "  {}".format(exception),
                        )
                        print(
                            "Exception inside application: %s",
                            exception_output,
                        )

        self.loop.call_later(self.exception_check_frequency, self.exception_checker)

    def stop(self):
        """
        Stop all outstanding futures and wind down loop
        """
        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        tasks = asyncio.gather(
            *asyncio.Task.all_tasks(loop=self.loop), loop=self.loop, return_exceptions=True
        )
        tasks.add_done_callback(lambda t: self.loop.stop())
        tasks.cancel()

        with suppress(asyncio.CancelledError):
            self.loop.run_until_complete(tasks)

        print('Goodbye!')

    def close(self):
        self.loop.close()


def get_application():
    """
    Loads the projects ASGI application, as passed from the command line
    """
    parser = argparse.ArgumentParser(
        description='A simple command-line Django Channels interface server'
    )
    parser.add_argument(
        'application',
        help=(
            'The ASGI Application in your Django project, in the form of '
            '`path.to.module:instance.path`'
        )
    )
    args = parser.parse_args()

    application = import_by_path(args.application)
    return application


if __name__ == '__main__':
    application = get_application()
    server = StdInServer(application)

    try:
        server.start()
    finally:
        server.close()
