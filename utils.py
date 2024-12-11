from PIL import ImageFont
from pathlib import Path
from dataclasses import dataclass
import requests
import logging

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

    lines = text.split('\n')
    while True:
        total_height = sum(font.getsize(line)[1] for line in lines)
        max_line_width = max(font.getsize(line)[0] for line in lines)
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
        logging.info("{des} fetched successfully.")
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch {des}: {e}")
        raise