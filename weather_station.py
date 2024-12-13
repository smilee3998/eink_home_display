import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import argparse

from eink_client import EinkClient
from weather_client import OpenWeatherClient, AccuWeatherClient
from utils import *
from constants import *


class WeatherStation:
    def __init__(
        self,
        display: EinkClient,
        user_content: Image.Image | str | None,
        wc: OpenWeatherClient | AccuWeatherClient,
        *,
        grid_horiz_ratio: float = 0.6,
        time_vert_ratio: float = 0.7,
        weather_icon_ratio: float = 0.4,
        use_hrs_forecast: bool = False,
    ):
        """

        Args:
            display (EinkClient): display to use
            grid_horiz_ratio (float, optional): horizontal ratio of the grid to the whole display. Defaults to 0.6.
            time_vert_ratio (float, optional): vertical ratio of the time to the whole display. Defaults to 0.7.
            weather_icon_ratio (float, optional): horizontal ratio of the icon in the short weather block . Defaults to 0.4
            use_hrs_forecast (bool, optional): optiona to display hourly forecast or 5days forecast. Defaults to False.
        """
        # TODO validate ratio
        if user_content and not isinstance(user_content, (Image.Image, str)):
            raise ValueError("user_content should be Image.Image or str")

        self.display = display
        self.user_content = user_content
        self.image = Image.new("L", (display.width, display.height), 255)
        self.weather_icon_ratio = weather_icon_ratio
        self.wc = wc
        self.use_hrs_forecast = use_hrs_forecast

        grid_width = int(self.display.width * grid_horiz_ratio)
        if self.use_hrs_forecast:
            grid_height = grid_width // 3 * 2  # 3:2 ratio
        else:
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
            int(display.height * (1 - time_vert_ratio - 0.1)),  # smaller ratio
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
            (0, 0),
        )
        self.des_block = Block(
            int(self.short_weather_block.width * (1 - self.weather_icon_ratio)),
            self.short_weather_block.height,
            (self.icon_block.width, 0),
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

            current_weather_icon, current_weather_des = self.wc.get_current_weather()
            self._paste_short_weather_block(
                ICON_DIR / f"{current_weather_icon}.png", current_weather_des
            )
            self.image.save(CACHE_IMAGE_DIR)
            self.display.partial_update(self.image)

        except FileNotFoundError:
            self.update_all()

    def update_all(self):
        try:
            if self.use_hrs_forecast:
                forecast_data = self.wc.get_12hrs_forecast()
            else:
                forecast_data = self.wc.get_5days_forecast()

            current_weather_icon, current_weather_des = self.wc.get_current_weather()
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
        weather_data: (
            list[tuple[datetime, float]]
            | list[tuple[datetime, tuple[float, str, float]]]
        ),
        current_weather_icon_path: Path,
        current_weather_des: str,
    ):
        # TODO better type hint
        if self.use_hrs_forecast:
            self._paste_hrs_forecast_block(weather_data)
        else:
            self._paste_grid_weather_block(weather_data)
        self._paste_user_block()

        self.image.save(CACHE_IMAGE_DIR2)  # cache image without current weather

        self._paste_short_weather_block(current_weather_icon_path, current_weather_des)
        self.image.save(CACHE_IMAGE_DIR) # cache image with current weather
        self._paste_time_block()

    def _paste_hrs_forecast_block(
        self,
        weather_data: list[tuple[datetime, tuple[float, str, float]]],
        num_hrs: int = 6,
        time_vert_ratio: float = 0.2,
        temp_vert_ratio: float = 0.3,
        icon_vert_ratio: float = 0.5,
        prob_ratio: float = 0.15,
    ):
        # TODO : limit num_hrs to 1, 2,3,4,5,6, 8, 10, 12
        # define forecast block
        block = Image.new("L", self.grid_weather_block.as_tuple(), 255)
        draw = ImageDraw.Draw(block)

        # define each div size
        time_height = int(self.grid_weather_block.height * time_vert_ratio)
        temp_height = int(self.grid_weather_block.height * temp_vert_ratio)
        icon_height = int(self.grid_weather_block.height * icon_vert_ratio)
        prob_height = int(icon_height * prob_ratio)
        cell_width = self.grid_weather_block.width // num_hrs

        # define text size used
        temp_font = find_best_text_size("25.5°", cell_width, temp_height)
        time_font = find_best_text_size("10a.m", cell_width, time_height)
        prob_font = find_best_text_size("99%", cell_width, prob_height)

        for i, (time, forecast) in enumerate(weather_data):
            # draw column
            x = i * cell_width

            # define column content
            temp, icon_name, prob = forecast
            time_txt = time.strftime("%l%p").replace("PM", "pm").replace("AM", "am")
            temp_txt = f"{temp}°"
            prob_txt = f"{prob}%"
            icon = get_icon(ICON_DIR / f"{icon_name}.png", (cell_width, icon_height))

            draw_text_at_center(
                draw,
                time_txt,
                font=time_font,
                block_size=(cell_width, time_height),
                xy=(x, 0),
            )
            draw_text_at_center(
                draw,
                temp_txt,
                font=temp_font,
                block_size=(cell_width, temp_height),
                xy=(x, time_height),
            )
            block.paste(icon, (get_center_coord(
                icon, (cell_width, icon_height), (x, time_height+temp_height)
            )[0], time_height + temp_height))

            draw_text_at_center(draw, prob_txt, font=prob_font, block_size=(cell_width, prob_height), xy=(x,time_height + temp_height + icon.height))

        self.image.paste(block, self.grid_weather_block.paste_coord)

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
                y0 = (j + 1) * cell_height
                # Draw the data
                value = grid_data[i][j]
                if value is not None:
                    draw.text(
                        get_center_coord(
                            f" {value:.1f}°",
                            (cell_width, cell_height),
                            (x0, y0),
                            font=font,
                        ),
                        f" {value:.1f}°",
                        fill="black",
                        font=font,
                    )

        # Draw the headers
        for i, day in enumerate(days_list):
            draw.text(
                get_center_coord(
                    f"{day}",
                    (cell_width, cell_height),
                    ((i + 1) * cell_width, 0),
                    font=font,
                ),
                f"{day}",
                fill="black",
                font=font,
            )

        icon_paths = (AM_ICON_DIR, PM_ICON_DIR, NIGHT_ICON_DIR)
        for j, icon_path in enumerate(icon_paths):
            icon = get_icon(icon_path, size=(cell_width - 20, cell_height - 20))

            # make the icon into lighter gray
            icon = icon.point(lambda p: 70 if p == 0 else p)

            # small x offset to avoid overlap with time
            block.paste(
                icon,
                box=get_center_coord(
                    icon, (cell_width, cell_height), (0, (j + 1) * cell_height)
                ),
            )

        self.image.paste(block, self.grid_weather_block.paste_coord)

    def _paste_short_weather_block(self, icon_path: Path, des: str):
        block = Image.new("L", self.short_weather_block.as_tuple(), 255)
        draw = ImageDraw.Draw(block)

        icon = Image.open(icon_path)
        icon = icon.resize(self.icon_block.as_tuple())

        block.paste(
            icon,
            box=get_center_coord(
                icon, self.icon_block.as_tuple(), self.icon_block.paste_coord
            ),
        )

        font = find_best_text_size(des, self.des_block.width, self.des_block.height)
        draw.text(
            xy=get_center_coord(
                des, self.des_block.as_tuple(), self.des_block.paste_coord, font=font
            ),
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

        draw.text(
            get_center_coord(text, self.time_block.as_tuple(), (0, 0), font=font),
            text,
            font=font,
            fill="black",
        )

        self.image.paste(block, (self.time_block.paste_coord))

    def _paste_user_block(self):
        if self.user_content:
            if isinstance(self.user_content, Image.Image):
                self.user_content.thumbnail(self.user_content_block.as_tuple())
                x_offset, y_offset = center_image(
                    self.user_content, self.user_content_block.as_tuple()
                )
                paste_coord = (
                    self.user_content_block.paste_coord[0] + x_offset,
                    self.user_content_block.paste_coord[1] + y_offset,
                )
                self.image.paste(self.user_content, paste_coord)
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
    parser.add_argument("--use_accu", action=argparse.BooleanOptionalAction)

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
    if args.use_accu:
        wc = AccuWeatherClient()
    else:
        wc = OpenWeatherClient()

    weather_station = WeatherStation(
        display,
        Image.open(ICON_DIR / "cat.jpg"),
        wc,
        use_hrs_forecast=args.use_accu,
    )
    if args.auto_update:
        now = datetime.now()
        if not args.use_accu:
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
            if now.minute == CURRENT_WEATHER_UPDATE_TIME_MINUTE:
                # update all every hour
                logger.info("updating current weather and forecast")
                weather_station.update_all()
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
