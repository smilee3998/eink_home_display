import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from PIL import Image, ImageDraw
import argparse

from eink_client import EinkClient
from weather_client import WeatherClient
from utils import *
from constants import *


class WeatherStation:
    def __init__(
        self,
        display: EinkClient,
        user_content: Image.Image | str | None,
        *,
        grid_horiz_ratio: float = 0.6,
        time_vert_ratio: float = 0.7,
        time_left_margin: int = 50,
        weather_icon_ratio: float = 0.4,
        weather_icon_margin: int = 50,
    ):
        """

        Args:
            display (EinkClient): display to use
            grid_horiz_ratio (float, optional): horizontal ratio of the grid to the whole display. Defaults to 0.6.
            time_vert_ratio (float, optional): vertical ratio of the time to the whole display. Defaults to 0.7.
        """
        # TODO validate ratio
        if user_content and not isinstance(user_content, (Image.Image, str)):
            raise ValueError("user_content should be Image.Image or str")

        self.display = display
        self.user_content = user_content
        self.image = Image.new("L", (display.width, display.height), 255)
        self.time_left_margin = time_left_margin
        self.weather_icon_ratio = weather_icon_ratio
        self.weather_icon_margin = weather_icon_margin

        grid_width = int(self.display.width * grid_horiz_ratio)
        grid_height = grid_width // 4 * 3  # 4:3 ratio

        self.time_block = Block(
            display.width - grid_width,
            int(display.height * time_vert_ratio),
            paste_coord=(0, 0),
        )
        self.grid_weather_block = Block(
            grid_width, grid_height, paste_coord=(self.time_block.width, 0)
        )
        self.short_weather_block = Block(
            display.width - self.grid_weather_block.width,
            int(display.height * (1 - time_vert_ratio)),
            paste_coord=(0, self.time_block.height),
        )
        self.user_content_block = Block(
            self.grid_weather_block.width,
            display.height - self.grid_weather_block.height,
            paste_coord=(
                self.time_block.width,
                self.grid_weather_block.height,
            ),
        )
        self.icon_block = Block(
            int(self.short_weather_block.width * self.weather_icon_ratio),
            self.short_weather_block.height,
            (0, self.weather_icon_margin),
        )
        self.des_block = Block(
            int(self.short_weather_block.width * (1 - self.weather_icon_ratio)),
            self.short_weather_block.height,
            (self.icon_block.width, self.short_weather_block.height // 2),
        )

    def partial_update_time(self):
        """load image from cache and update time only"""
        try:
            self.image = Image.open(CACHE_IMAGE_DIR)
            self._paste_time_block()
            self.display.partial_update(self.image)
        except FileNotFoundError:
            self.update_all()

    def partial_update_current_weather(self):
        """load image from cache and update time and current weather only"""
        try:
            self.image = Image.open(CACHE_IMAGE_DIR2)
            self._paste_time_block()

            wc = WeatherClient()
            current_weather_icon, current_weather_des = wc.get_current_weather()
            self._paste_short_weather_block(
                ICON_DIR / f"{current_weather_icon}.png", current_weather_des
            )
            self.image.save(CACHE_IMAGE_DIR)
            self.display.partial_update(self.image)

        except FileNotFoundError:
            self.update_all()

    def update_all(self):
        wc = WeatherClient()
        try:
            forecast_data = wc.get_5days_forecast()
            current_weather_icon, current_weather_des = wc.get_current_weather()
            self._generate_display_image(
                forecast_data,
                ICON_DIR / f"{current_weather_icon}.png",
                current_weather_des,
            )

            display.display_image(self.image)
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

    def _generate_display_image(
        self,
        weather_data: list[tuple[datetime, float]],
        current_weather_icon_path: Path,
        current_weather_des: str,
    ):
        self._paste_user_block()
        self._paste_grid_weather_block(weather_data)

        # cache image without current weather
        self.image.save(CACHE_IMAGE_DIR2)

        self._paste_short_weather_block(current_weather_icon_path, current_weather_des)

        # cache image with current weather
        self.image.save(CACHE_IMAGE_DIR)
        self._paste_time_block()

    def _paste_grid_weather_block(self, weather_data: list[tuple[datetime, float]]):
        block = Image.new("L", self.grid_weather_block.as_tuple(), 255)
        draw = ImageDraw.Draw(block)
        cell_width, cell_height = (
            self.grid_weather_block.width // 6,
            self.grid_weather_block.height // 4,
        )

        grid_data, days_list, time_slots = self._organize_data(weather_data)

        font = find_best_text_size("25.5°", cell_width, cell_height)

        for i, day in enumerate(days_list):
            for j, time in enumerate(time_slots):
                x0 = (i + 1) * cell_width
                y0 = (j + 1) * cell_height + cell_height // 3
                # Draw the data
                value = grid_data[i][j]
                if value is not None:
                    draw.text((x0 + 5, y0), f" {value:.1f}°", fill="black", font=font)

        # Draw the headers
        for i, day in enumerate(days_list):
            draw.text(
                ((i + 1) * cell_width + 5, cell_height // 2),
                f"  {day}",
                fill="black",
                font=font,
            )

        icon_paths = (AM_ICON_DIR, PM_ICON_DIR, NIGHT_ICON_DIR)
        for j, icon_path in enumerate(icon_paths):
            icon = Image.open(icon_path).convert("L")

            # make the icon into lighter gray
            icon = icon.point(lambda p: 70 if p == 0 else p)

            icon.thumbnail((cell_width - 20, cell_height - 20))
            # small x offset to avoid overlap with time
            block.paste(icon, (5, (j + 1) * cell_height))

        self.image.paste(block, self.grid_weather_block.paste_coord)

    def _paste_short_weather_block(self, icon_path: Path, des: str):
        block = Image.new("L", self.short_weather_block.as_tuple(), 255)
        draw = ImageDraw.Draw(block)

        icon = Image.open(icon_path)
        icon = icon.resize(self.icon_block.as_tuple())
        block.paste(icon, box=self.icon_block.paste_coord)

        font = find_best_text_size(des, self.des_block.width, self.des_block.height)
        draw.text(
            xy=self.des_block.paste_coord,
            text=des,
            font=font,
            fill="black",
        )
        self.image.paste(block, self.short_weather_block.paste_coord)

    def _paste_time_block(self):
        block = Image.new("L", self.time_block.as_tuple(), 255)
        draw = ImageDraw.Draw(block)
        now = datetime.now()
        text = f"{now.hour:02d}\n{now.minute:02d}"
        font = find_best_text_size(text, self.time_block.width, self.time_block.height)
        draw.text((self.time_left_margin, 0), text, font=font, fill="black")

        self.image.paste(block, (self.time_block.paste_coord))

    def _paste_user_block(self):
        if self.user_content:
            if isinstance(self.user_content, Image.Image):
                self.user_content.thumbnail(self.user_content_block.as_tuple())
                self.image.paste(self.user_content, self.user_content_block.paste_coord)
            else:
                raise NotImplementedError

    def _organize_data(self, weather_data: list[tuple[datetime, float]]):
        # Organizing data into a grid
        days = {}
        for dt, value in weather_data:
            day = dt.strftime("%d")
            time = dt.strftime("%H:%M")
            if day not in days:
                days[day] = {}
            days[day][time] = value

        # Prepare the grid
        time_slots = [AM_TIME, PM_TIME, NIGHT_TIME]
        days_list = sorted(days.keys())
        grid_data = []

        for day in days_list:
            row = []
            for time in time_slots:
                row.append(days[day].get(time, None))  # Fill with None if no data
            grid_data.append(row)

        return grid_data, days_list, time_slots


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update weather station")
    parser.add_argument("--time_only", action=argparse.BooleanOptionalAction)
    parser.add_argument("--weather_only", action=argparse.BooleanOptionalAction)
    parser.add_argument("--auto_update", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    # Logging configuration for both file and console
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Use RotatingFileHandler for log rotation
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3
    )  # 1MB file size, 3 backups
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    logger.addHandler(file_handler)

    # Stream handler for logging to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    logger.addHandler(console_handler)

    display = EinkClient(vcom=-1.55, rotate="flip")
    weather_station = WeatherStation(
        display, Image.open(ICON_DIR / "cat.jpg")
    )
    if args.auto_update:
        now = datetime.now()
        if (
            now.hour == WEATHER_FORECAST_UPDATE_TIME_HOUR
            and now.minute == CURRENT_WEATHER_UPDATE_TIME_MINUTE
        ):
            # update all at a specific time at a day
            logger.info("updating current weather and forecast")
            weather_station.update_all()
        elif now.minute == CURRENT_WEATHER_UPDATE_TIME_MINUTE:
            # update current weather at pre-set time in every hour
            logger.info("updating current weather.")
            weather_station.partial_update_current_weather()
        else:
            weather_station.partial_update_time()
    else:
        if args.time_only:
            weather_station.partial_update_time()
        elif args.weather_only:
            logger.info("updating current weather.")
            weather_station.partial_update_current_weather()
        else:
            logger.info("updating current weather and forecast")
            weather_station.update_all()
