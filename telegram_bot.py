import asyncio
import datetime
import logging
import time
from typing import Callable, List

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackContext, CommandHandler


log = logging.getLogger(__name__)


class TelegramBot:
    _instance: "TelegramBot" = None  # type: ignore
    _initialized: bool = False

    _app: Application
    _app_warning: Application

    group_id: int
    commander_ids: List[int]

    token: str
    token_warning: str
    commands: List[str]

    command_queue: asyncio.Queue
    _message_buffer: str = ""

    @classmethod
    def get_instance(cls) -> "TelegramBot":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(
        self,
    ):
        if TelegramBot._initialized:
            return
        TelegramBot._initialized = True

    def initialize(
        self,
        username: str,
        token: str,
        group_id: int,
        commander_ids: List[int],
        token_warning: str,
    ):
        self.username = username
        self.token = token
        self.group_id = group_id
        self.commander_ids = commander_ids
        self.token_warning = token_warning
        self.command_queue = asyncio.Queue()

        self.message_queue: asyncio.Queue[tuple[int, str, float]] = asyncio.Queue()
        self.warning_queue: asyncio.Queue[tuple[int, str, float]] = asyncio.Queue()

        self._app = Application.builder().token(self.token).build()
        self._app.add_handler(CommandHandler("whereami", self.cmd_default))
        self._app.add_handler(CommandHandler("whoami", self.cmd_default))
        self._app_warning = Application.builder().token(self.token_warning).build()

    def add_commands(self, commands):
        self._app.add_handler(CommandHandler(commands, self.cmd_auth))

    def cron(self, job: Callable, interval: int):
        if not self._app.job_queue:
            raise Exception("Job queue is not initialized")

        self._app.job_queue.run_repeating(
            callback=job,
            interval=interval,
            first=10,
        )

    def run(self, job: Callable | None = None):
        if not self._app.job_queue:
            raise Exception("Job queue is not initialized")

        if job is not None:
            self._app.job_queue.run_once(job, 2)
        self._app.job_queue.run_repeating(self.message_loop, 2)
        self._app.job_queue.run_repeating(self.warning_loop, 3)
        self._app.run_polling()

    async def cmd_default(self, update: Update, context: CallbackContext):
        if not update.message:
            return

        if time.time() - update.message.date.timestamp() > 10:
            return
        command = update.message.text
        if command == "/whereami":
            chat_id = update.message.chat_id
            await update.message.reply_text(f"{chat_id}")
        if update.message.from_user and command == "/whoami":
            username = update.message.from_user.username
            user_id = update.message.from_user.id
            await update.message.reply_text(f"Hello, {username}! ({user_id}) :]")

    async def cmd_auth(self, update: Update, context: CallbackContext):
        if not update.message:
            return

        if time.time() - update.message.date.timestamp() > 10:
            return
        if (
            update.message.from_user
            and update.message.from_user.id not in self.commander_ids
        ):
            await update.message.reply_text("You're not commander :(")
            return

        if self.command_queue.qsize() > 2:
            q_text = "\n".join(self.command_queue._queue)  # type: ignore
            await update.message.reply_text(
                f"I'm busy :(\nPlease wait a moment.\n\n{q_text}"
            )
            return

        msg_text = update.message.text
        if msg_text and "@" in msg_text:
            msg_text = msg_text.split("@")[0]

        await self.command_queue.put(msg_text)

    def append_message(self, message: str = ""):
        if len(self._message_buffer) == 0:
            self._message_buffer = message + "\n"
        else:
            self._message_buffer += message + "\n"

    async def send_message(
        self,
        title: str = "",
        message: str = "",
        warning: bool = False,
        owner_only: bool = False,
    ):
        # Use buffered message if available
        if len(self._message_buffer) != 0:
            message = self._message_buffer
            self._message_buffer = ""

        # Prepend title if provided
        if not title:
            title = "No title"

        if title and not message:
            message = f"## {title} ##"
        else:
            message = f"## {title} ##\n\n{message}"

        # Escape HTML in the message text
        safe_message = message.replace("<", "&lt;").replace(">", "&gt;")
        formatted_message = f"<code>{safe_message}\n\n{datetime.datetime.now()}</code>"

        await self.message_queue.put((self.group_id, formatted_message, time.time()))
        if warning:
            if not owner_only:
                for commander_id in self.commander_ids:
                    await self.warning_queue.put(
                        (commander_id, formatted_message, time.time())
                    )
            else:
                await self.warning_queue.put(
                    (self.commander_ids[0], formatted_message, time.time())
                )

    async def message_loop(self, _):
        if self.message_queue.qsize() == 0:
            return

        chat_id, message, ts = await self.message_queue.get()

        delay = time.time() - ts
        log.debug(f"send_message({chat_id}) {delay:.3f}s")
        log.debug(f"send_message({chat_id}) {message.replace('\n', ' ')}")

        await self._app.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
        )

    async def warning_loop(self, _):
        if self.warning_queue.qsize() == 0:
            return

        chat_id, message, ts = await self.warning_queue.get()

        delay = time.time() - ts
        log.debug(f"send_warning({chat_id}) {delay:.3f}s")
        log.debug(f"send_warning({chat_id}) {message.replace('\n', ' ')}")

        try:
            await self._app_warning.bot.send_message(
                chat_id=chat_id,
                text=f"{self.username} {message}",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            message = f"Failed to send warning message to {chat_id}"
            await self.send_message("Telegram failed", message, warning=False)


# TODO: Run time of job "main_loop was missed by 뜨는 문제 해결
# Run time of job "main_loop (trigger: date[2025-02-20 03:38:14 UTC],
# next run at: 2025-02-20 03:38:14 UTC)" was missed by 0:00:01.901449
