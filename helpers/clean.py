# (c) @savior128

import shutil


async def delete_all(root: str):
    """Delete a folder and its contents.

    :param root: Path to the folder as string.
    """
    try:
        shutil.rmtree(root)
    except Exception as e:
        print(f"Error deleting folder: {e}")