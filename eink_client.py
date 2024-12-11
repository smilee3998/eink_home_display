from PIL import Image

from IT8951.display import AutoEPDDisplay
from IT8951.constants import DisplayModes


class EinkClient:
    def __init__(self, vcom: float, rotate: str | None = None):
        self.display = AutoEPDDisplay(vcom=vcom, rotate=rotate)

    def display_image(self, img: Image.Image, paste_coords: tuple[int, int] = (0, 0)):
        self.paste_image(img, paste_coords)
        self.display.draw_full(DisplayModes.GC16)

    def partial_update(self, img: Image.Image, paste_coords: tuple[int, int] = (0, 0)):
        self.paste_image(img, paste_coords)
        self.display.draw_partial(DisplayModes.DU)

    def paste_image(self, img: Image.Image, paste_coords: tuple[int, int]):
        # clearing image to white
        self.display.frame_buf.paste(
            0xFF, box=(0, 0, self.display.width, self.display.height)
        )
        self.display.frame_buf.paste(img, (paste_coords))

    @property
    def width(self) -> int:
        return self.display.width

    @property
    def height(self) -> int:
        return self.display.height
