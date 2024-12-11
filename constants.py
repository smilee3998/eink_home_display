from pathlib import Path


PJ_DIR = Path(__file__).parent.resolve()

# icons dir
ICON_DIR = PJ_DIR /  "icon"
AM_ICON_DIR = ICON_DIR / "am.png"
PM_ICON_DIR = ICON_DIR / "pm.png"
NIGHT_ICON_DIR = ICON_DIR / "sleepy.png"

# cache dir
CACHE_DIR = PJ_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_IMAGE_DIR = CACHE_DIR / "image_w_current_weather.png"
CACHE_IMAGE_DIR2 = CACHE_DIR / "image_wo_current_weather.png"


FONT_DIR = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
AM_TIME = "09:00"
PM_TIME = "15:00"
NIGHT_TIME = "21:00"
UNITS = "metric"

LOG_FILE = "weather_display.log"
CURRENT_WEATHER_UPDATE_TIME_MINUTE = 0  # used for auto update current weather at minute = 0 
WEATHER_FORECAST_UPDATE_TIME_HOUR = 0  # used for auto update weather forecast at 24:00 