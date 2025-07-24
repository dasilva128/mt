# (c) @savior_128

import os
import time
import asyncio
import subprocess
from configs import Config


async def MergeVideo(input_file, user_id, message, format_):
    """Merge videos using FFmpeg."""
    try:
        merged_file_name = f"{Config.DOWN_PATH}/{str(user_id)}/[@{(await message._client.get_me()).username}]_Merged.{format_}"
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", input_file,
            "-c:v", "copy",  # استفاده از copy برای جلوگیری از رمزگذاری مجدد
            "-c:a", "copy",
            "-threads", "4",  # استفاده از 4 رشته برای افزایش سرعت
            "-y", merged_file_name
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        if os.path.exists(merged_file_name):
            return merged_file_name
        await message.edit(f"Failed to Merge Videos!\nCheck your videos.")
        return None
    except Exception as e:
        print(f"Error in MergeVideo: {e}")
        await message.edit(f"Failed to Merge Videos!\nError: {e}")
        return None


async def generate_screen_shots(video_file, output_directory, no_of_ss, duration):
    """Generate screenshots from video."""
    images = []
    ttl = duration // no_of_ss
    for i in range(0, no_of_ss):
        file_generate_cmd = [
            "ffmpeg",
            "-ss", str(i * ttl),
            "-i", video_file,
            "-vframes", "1",
            f"{output_directory}/{str(time.time() + i)}.jpg",
            "-y"
        ]
        process = await asyncio.create_subprocess_exec(
            *file_generate_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if os.path.exists(f"{output_directory}/{str(time.time() + i)}.jpg"):
            images.append(f"{output_directory}/{str(time.time() + i)}.jpg")
    return images if images else None


async def cult_small_video(video_file, output_directory, start_time, end_time, format_):
    """Generate a sample video clip."""
    out_put_file_name = f"{output_directory}/Sample_{str(start_time)}.{format_}"
    file_generator_command = [
        "ffmpeg",
        "-i", video_file,
        "-ss", str(start_time),
        "-to", str(end_time),
        "-c:v", "copy",  # استفاده از copy برای افزایش سرعت
        "-c:a", "copy",
        "-threads", "4",  # استفاده از 4 رشته
        "-y", out_put_file_name
    ]
    process = await asyncio.create_subprocess_exec(
        *file_generator_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return out_put_file_name if os.path.exists(out_put_file_name) else None