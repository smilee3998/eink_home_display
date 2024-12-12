from PIL import ImageFont, Image
from pathlib import Path
from dataclasses import dataclass
import requests
import logging
from datetime import timedelta

from constants import *


@dataclass
class Block:
    width: int
    height: int
    paste_coord: tuple[int, int]

    def as_tuple(self) -> tuple[int, int]:
        return (self.width, self.height)

    def __str__(self):
        return f"width={self.width} height={self.height}"


def find_best_text_size(text: str, max_width: int, max_height: int):
    """Find the largest text size that fit in the given limit

    Args:
        text (str): text to be checked
        max_width (int): maximum width of the text
        max_height (int): maximum height of the text

    Returns:
        image font
    """
    font_size = 10
    font = ImageFont.truetype(FONT_DIR, font_size)

    while True:
        max_line_width, total_height = get_text_size(text, font)
        if max_line_width < max_width and total_height < max_height:
            font_size += 10
            font = ImageFont.truetype(FONT_DIR, font_size)
        else:
            break

        if font_size > 1000:
            print("reach max font size")
            break

    return ImageFont.truetype(FONT_DIR, font_size - 10)


def fetch(url: str, des: str) -> dict:
    try:
        response = requests.get(url)
        response.raise_for_status()
        logging.info(f"{des} fetched successfully.")
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch {des}: {e}")
        raise


def get_icon(path: Path, size: tuple[int, int]) -> Image.Image:
    icon = Image.open(path)
    icon.thumbnail(size)

    return icon


def timedelta_to_hours(td: timedelta) -> int:
    """ get the number of hours between the time difference 
    """
    return int(td.total_seconds() // 3600)


def center_text(txt: str, block_size: tuple[int, int], font) -> tuple[int, int]:
    """calculate the offsets for centering the text
    """
    width, height = get_text_size(txt, font)
    x_offset = int((block_size[0] - width) // 2)
    y_offset = int((block_size[1] - height) // 2)
    
    return x_offset, y_offset

def center_image(icon: Image.Image, block_size: tuple[int, int]) -> tuple[int, int]:
    """calculate the offsets for centering the image
    """
    return int((block_size[0] - icon.width) // 2), int((block_size[1] - icon.height) // 2), 
    
def get_center_coord(content: str | Image.Image, block_size: tuple[int, int], old_coord: tuple[int, int],**kwargs) -> tuple[int, int]:
    """get the new coord to paste the content at the center of block 

    Args:
        content (str | Image.Image): content to put in the block 
        block_size (tuple[int, int]): the size of the block for the content 
        old_coord (tuple[int, int]): old coordintes to paste the content

    Raises:
        TypeError: Not implemented type of content

    Returns:
        tuple[int, int]: new coordinates 
    """
    if isinstance(content, str):
        x_off, y_off = center_text(content, block_size, **kwargs)
    elif isinstance(content, Image.Image):
        x_off, y_off = center_image(content, block_size, **kwargs)
    else:
        raise TypeError(f"Unknown type {type(content)=}")
    
    return (old_coord[0] + x_off, old_coord[1] + y_off)
    
    
def get_text_size(txt: str, font) -> tuple[int, int]:
    """return the max width and height of the given text

    Args:
        txt (str): text can be one line or multiple line
        font (_type_): font used

    Returns:
        tuple[int, int]: max width, total height
    """
    lines = txt.split("\n")
    total_height = sum(font.getsize(line)[1] for line in lines)
    max_line_width = max(font.getsize(line)[0] for line in lines)
    
    return (max_line_width, total_height)