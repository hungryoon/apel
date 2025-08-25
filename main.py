import asyncio
import signal
import time
import traceback
import dotenv
import os

from apel_client import ApelClient
from telegram_bot import TelegramBot

dotenv.load_dotenv()

username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

if not username or not password:
    raise ValueError("USERNAME and PASSWORD must be set")

t = TelegramBot.get_instance()


async def main_loop(_):
    await t.send_message("프로그램 시작")

    client = ApelClient()

    login_ts = 0
    origin_hash = ""

    while True:
        try:
            if login_ts - time.time() > 1800:
                login_ts = time.time()
                client.login(username, password)
                await asyncio.sleep(10)

            new_slots = client.search(
                brand=os.getenv("SEARCH_BRAND"),
                branch=os.getenv("SEARCH_BRANCH"),
                hall=os.getenv("SEARCH_HALL"),
                st_dt=os.getenv("SEARCH_ST_DT"),
                ed_dt=os.getenv("SEARCH_ED_DT"),
                time=os.getenv("SEARCH_TIME"),
                yoil=os.getenv("SEARCH_YOIL"),
            )
            new_hash = "".join([f"{slot.name}{slot.price}" for slot in new_slots])
            # print(new_hash)

            if origin_hash == new_hash:
                await asyncio.sleep(60)
                continue

            if origin_hash == "":
                for new_slot in new_slots:
                    t.append_message(f"{new_slot.name} {new_slot.price}")
                await t.send_message("검색시작")

            else:
                while True:
                    for new_slot in new_slots:
                        t.append_message(f"{new_slot.name} {new_slot.price}")
                    await t.send_message("변경확인")

                    await asyncio.sleep(10)

            origin_hash = new_hash
            await asyncio.sleep(60)

        except Exception as e:
            print(e)
            print(traceback.format_exc())

            t.append_message(str(e))
            t.append_message(traceback.format_exc()[:1000])
            await t.send_message("에러발생")

            await asyncio.sleep(300)


def signal_handler(signum, frame):
    print("SIGINT or SIGTERM received")
    t.send_message("프로그램 종료")
    exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    t.initialize(
        username=os.getenv("TELEGRAM_USERNAME"),
        token=os.getenv("TELEGRAM_TOKEN"),
        group_id=int(os.getenv("TELEGRAM_GROUP_ID")),
        commander_ids=[],
        token_warning=os.getenv("TELEGRAM_TOKEN_WARNING"),
    )
    t.run(main_loop)


if __name__ == "__main__":
    main()
