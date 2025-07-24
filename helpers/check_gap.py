import time
from configs import Config

GAP = {}


async def CheckTimeGap(user_id: int):
    """Check user time gap to prevent flooding.
    
    :param user_id: Telegram User ID
    :return: Tuple (is_in_gap, sleep_time)"""
    
    if str(user_id) in GAP:
        current_time = time.time()
        previous_time = GAP[str(user_id)]
        if round(current_time - previous_time) < Config.TIME_GAP:
            return True, round(previous_time - current_time + Config.TIME_GAP)
        else:
            del GAP[str(user_id)]
            return False, None
    GAP[str(user_id)] = time.time()
    return False, None