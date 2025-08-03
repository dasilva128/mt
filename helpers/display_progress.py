# helpers/display_progress.py
import math
import time
import asyncio
from configs import Config
from pyrogram.types import Message
from pyrogram import enums
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def show_loading_animation(message: Message, base_text: str = "لطفاً صبر کنید ...\nPlease Wait ..."):
    """Display a loading animation with moving dots."""
    dots = [".", "..", "...", "...."]
    for i in range(4):  # 4 چرخه برای انیمیشن
        try:
            new_text = f"{base_text}{dots[i % len(dots)]}{'‌' * i}"
            await message.edit(
                text=new_text,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            await asyncio.sleep(0.8)  # فاصله زمانی 0.8 ثانیه
        except Exception as e:
            if "MESSAGE_NOT_MODIFIED" in str(e):
                try:
                    await message.delete()
                    message = await message.reply_text(
                        text=new_text,
                        parse_mode=enums.ParseMode.MARKDOWN
                    )
                except Exception as delete_err:
                    logger.error(f"Error in loading animation after delete: {delete_err}")
                    break
            else:
                logger.error(f"Error in loading animation: {e}")
                break
    return message

async def progress_for_pyrogram(current, total, ud_type, message: Message, start):
    """Display progress for file upload/download."""
    now = time.time()
    diff = now - start
    if round(diff % 2.00) == 0 or current == total:
        try:
            percentage = current * 100 / total
            speed = current / diff if diff > 0 else 0
            elapsed_time = round(diff) * 1000
            time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
            estimated_total_time = elapsed_time + time_to_completion

            elapsed_time = TimeFormatter(milliseconds=elapsed_time)
            estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

            filled = ''.join(["●" for _ in range(math.floor(percentage / 5))])
            blower = ''.join(["○" for _ in range(20 - math.floor(percentage / 5))])
            progress = f"[{filled}{blower}] \n"

            tmp = progress + Config.PROGRESS.format(
                round(percentage, 2),
                humanbytes(current),
                humanbytes(total),
                humanbytes(speed),
                estimated_total_time if estimated_total_time != '' else "0 s"
            )
            await message.edit(
                text=f"**{ud_type}**\n\n{tmp}",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error in progress_for_pyrogram: {e}")
            pass

def humanbytes(size):
    """Convert bytes to human-readable format."""
    if not size:
        return ""
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}B"

def TimeFormatter(milliseconds: int) -> str:
    """Convert milliseconds to human-readable time format."""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((f"{days}d, ") if days else "") + \
          ((f"{hours}h, ") if hours else "") + \
          ((f"{minutes}m, ") if minutes else "") + \
          ((f"{seconds}s, ") if seconds else "") + \
          ((f"{milliseconds}ms, ") if milliseconds else "")
    return tmp[:-2]