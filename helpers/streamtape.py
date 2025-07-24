# (c) @savior_128

import aiohttp
from configs import Config
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helpers.display_progress import humanbytes


async def UploadToStreamtape(file: str, editable: Message, file_size: int):
    """Upload file to Streamtape."""
    try:
        async with aiohttp.ClientSession() as session:
            Main_API = "https://api.streamtape.com/file/ul?login={}&key={}"
            hit_api = await session.get(Main_API.format(Config.STREAMTAPE_API_USERNAME, Config.STREAMTAPE_API_PASS))
            json_data = await hit_api.json()
            temp_api = json_data["result"]["url"]
            files = {'file1': open(file, 'rb')}
            response = await session.post(temp_api, data=files)
            data_f = await response.json(content_type=None)
            download_link = data_f["result"]["url"]
            filename = file.split("/")[-1].replace("_", " ")
            text_edit = f"File uploaded to Streamtape!\n\n**File Name:** `{filename}`\n**Size:** `{humanbytes(file_size)}`\n**Link:** `{download_link}`"
            await editable.edit(
                text=text_edit,
                parse_mode="markdown",
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open Link", url=download_link)]])
            )
    except Exception as e:
        print(f"Error: {e}")
        await editable.edit("Sorry, something went wrong!\nCan't upload to Streamtape.")