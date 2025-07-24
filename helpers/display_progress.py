import math
import time
from configs import Config


async def progress_for_pyrogram(current, total, ud_type, message, start):
    """Display progress for file upload/download."""
    
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[{0}{1}] \n".format(
            ''.join(["●" for _ in range(math.floor(percentage / 5))]),
            ''. blower = ''.join(["○" for _ in range(20 - math.floor(percentage / 5))])
        )

        tmp = progress + Config.PROGRESS.format(
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text=f"**{ud_type}**\n\n{tmp}",
                parse_mode='markdown'
            )
        except:
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