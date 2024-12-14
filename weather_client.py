from abc import ABC, abstractmethod
import os
import logging
from datetime import datetime
import json
from typing import Callable

from constants import *
from utils import fetch, timedelta_to_hours


class WeatherClient(ABC):
    def __init__(
        self,
        *,
        check_expired: bool = True,
        cache_forecast_path: Path = CACHE_DIR / "forecast.json",
        cache_current_path: Path = CACHE_DIR / "current.json",
    ):
        self.cache_forecast_path = cache_forecast_path
        self.cache_current_path = cache_current_path
        self.check_expired = check_expired

        self._load_api_parameters()
        self._setup_api_url()

    def _get_weather(
        self,
        cache_path: Path,
        check_expir: Callable[[dict], bool] | Callable[[list[dict]], bool],
        fetch: Callable[[], dict],
        load: Callable,
    ):
        cache_current = self._load_cached_data(cache_path)
        try:
            if self.check_expired and (cache_current and check_expir(cache_current)):
                # delete expired weather cache
                cache_current = None
        except (TypeError, KeyError):
            logging.info("Cache is not in the right format. Delete.")
            cache_current = None

        if cache_current is None:
            # fetch new data
            weather_data = fetch()
            self._save(weather_data, cache_path)
            return load(weather_data)
        else:
            logging.info("using cache")
            return load(cache_current)

    def get_current_weather(self) -> tuple[str, str]:
        """get current weather from cache data or fetch from api if cache expired

        Returns:
            tuple[str, str]: icon name and short description
        """
        return self._get_weather(
            self.cache_current_path,
            self._check_cache_current_expired,
            self._fetch_current_weather,
            self._load_current_weather,
        )

    def get_5days_forecast(self) -> list[tuple[datetime, float]]:
        """get 5days forecast from cache data or fetch from api if cahce expired

        Returns:
            list[tuple[datetime, float]]: sorted list of tuple with datetime and temperature
        """
        return self._get_weather(
            self.cache_forecast_path,
            self._check_cache_day_expired,
            self._fetch_5days_forecast,
            self._load_5days_forecast,
        )

    def get_12hrs_forecast(self) -> list[tuple[datetime, tuple[float, str, float]]]:
        # TODO add percentage if rainning
        return self._get_weather(
            self.cache_forecast_path,
            self._check_cache_hours_forecast_expired,
            self._fetch_12hrs_forecast,
            self._load_12hrsforecast,
        )

    def _save(self, data: dict, cache_path: Path) -> None:
        # save the fetched data to given path
        with open(cache_path, "w") as f:
            json.dump(data, f)

    def _load_api_parameters(self):
        from dotenv import load_dotenv

        load_dotenv()

        self.api_key = self._get_api_key()
        self.latitude = os.environ.get("LATITUDE")
        self.longitude = os.environ.get("LONGITUDE")

    @abstractmethod
    def _load_current_weather(self, data: dict) -> tuple[str, str]:
        """get weather icon and short description from data fetched from current weather API

        Args:
            data (dict): _description_

        Returns:
            tuple[str, str]: _description_
        """
        pass

    def _load_cached_data(self, cache_path: Path) -> dict | list[dict] | None:
        """load data from given cache path"""
        if cache_path.is_file():
            with open(cache_path, "r") as f:
                return json.load(f)
        return None

    @abstractmethod
    def _load_5days_forecast(self, data: dict) -> list[tuple[datetime, float]]:
        """load 9am, 3pm and 9pm weather from fetched data

        Args:
            data (dict): feteched data

        Returns:
            sorted list of tuple with datetime and temperature
        """
        pass

    def _fetch_current_weather(self):
        """fetch current weather condition"""
        return fetch(self.fetch_current_url, "current weather data")

    def _fetch_5days_forecast(self) -> dict:
        """fetch 5days_forecast from OpenWeather"""
        return fetch(self.fetch_5daysforecast_url, "forecast data")

    def _fetch_12hrs_forecast(self):
        return fetch(self.fetch_12hrforecasts_url, "hourly data")

    def _check_cache_day_expired(self, cache: dict) -> bool:
        """check if the cache is one day or more ago

        Args:
            cache (dict): cache from OpenWeather forecast api

        Returns:
            bool: is cache expired
        """
        return datetime.now().date() > self._load_forecast_timestamp(cache).date()

    def _check_cache_current_expired(self, cache: dict) -> bool:
        """check if the cache is an hour or more ago

        Args:
            cache (dict): cache from OpenWeather current weather api

        Returns:
            bool: is cache expired
        """
        return (
            timedelta_to_hours(
                datetime.now() - self._load_current_weather_timestamp(cache)
            )
            >= 1
        )

    def _check_cache_hours_forecast_expired(self, cache: list[dict]) -> bool:
        """check if the cache is an hour or more ago

        Args:
            cache (dict): cache from OpenWeather current weather api

        Returns:
            bool: is cache expired
        """
        return (
            timedelta_to_hours(
                datetime.now() - self._load_hours_forecast_timestamp(cache)
            )
            >= 1
        )

    @abstractmethod
    def _get_api_key(self):
        pass

    @abstractmethod
    def _setup_api_url(self):
        pass

    @property
    @abstractmethod
    def fetch_current_url(self) -> str:
        pass

    @property
    @abstractmethod
    def fetch_5daysforecast_url(self) -> str:
        pass

    @property
    @abstractmethod
    def fetch_12hrforecasts_url(self) -> str:
        pass

    @abstractmethod
    def _load_forecast_timestamp(self, cache: dict) -> datetime:
        pass

    @abstractmethod
    def _load_current_weather_timestamp(self, cache: dict) -> datetime:
        pass

    @abstractmethod
    def _load_hours_forecast_timestamp(self, cache: list[dict]) -> datetime:
        pass

    @abstractmethod
    def _load_12hrsforecast(self, data: list[dict]) -> list[tuple[datetime, float]]:
        pass


class AccuWeatherClient(WeatherClient):
    def _get_api_key(self):
        return os.environ.get("ACCU_WEATHER_API_KEY")

    def _get_location_key(self) -> str:
        location_key = os.environ.get("LOCATION_KEY")

        if location_key is None:
            location_key = self._fetch_location_key()
            self._save_location_key(location_key)

        return location_key

    def _save_location_key(self, key: str):
        from dotenv import set_key

        set_key(PJ_DIR / ".env", key_to_set="LOCATION_KEY", value_to_set=key)

    def _fetch_location_key(self) -> str:
        """fetch location key used for accuweather by latitude and longitude"""
        url = f"http://dataservice.accuweather.com/locations/v1/cities/geoposition/search?apikey={self.api_key}&q={self.latitude},{self.longitude}"
        location_key = fetch(url, "location key")["Key"]

        return location_key

    def _setup_api_url(self):
        self.fetch_base_url = f"http://dataservice.accuweather.com/"
        self.location_key = self._get_location_key()
        self.url_para = f"{self.location_key}?apikey={self.api_key}"

    @property
    def fetch_current_url(self):
        return self.fetch_base_url + "currentconditions/v1/" + self.url_para

    @property
    def fetch_12hrforecasts_url(self):
        unit_para = "&metric=true" if UNITS == "metric" else ""
        return (
            self.fetch_base_url
            + "forecasts/v1/hourly/12hour/"
            + self.url_para
            + unit_para
        )

    @property
    def fetch_5daysforecasts_url(self):
        raise NotImplementedError(
            "5 days forecast has not implemented for AccuWeatherClient"
        )

    def _load_hours_forecast_timestamp(self, cache: list[dict]) -> datetime:
        return datetime.fromtimestamp(cache[0]["EpochDateTime"])

    def _load_5days_forecast(self, data: dict) -> list[tuple[datetime, float]]:
        raise NotImplementedError()

    def _load_current_weather_timestamp(self, cache: list[dict]) -> datetime:
        return datetime.fromtimestamp(cache[0]["EpochTime"])

    def _load_current_weather(self, data: dict) -> tuple[str, str]:
        """get weather icon and short description from data fetched from current weather API

        Args:
            data (dict): data returned from current weather API

        Returns:
            tuple[str, str]: icon name, short description
        """
        current_weather = data[0]
        current_weather_icon: str = self.match_openweather_icon(
            current_weather["WeatherIcon"]
        )
        current_weather_des: str = current_weather["WeatherText"]
        return current_weather_icon, current_weather_des

    def _load_12hrsforecast(
        self, data: list[dict]
    ) -> list[tuple[datetime, tuple[float, str, float]]]:
        """load 12 hrs forecast temperature, icon and PrecipitationProbability

        Args:
            data (list[dict]):  data fetched from AccuWeather

        Raises:
            KeyError: unknown format

        Returns:
            list[tuple[datetime, tuple[float, str]]]: a list of sorted forecast in (time, (temp, icon, PrecipitationProbability))
        """
        weather_data = {}
        try:
            for item in data:
                dt = datetime.strptime(item["DateTime"], "%Y-%m-%dT%H:%M:%S%z")
                if item["WeatherIcon"] == 18 and dt.hour > 18:
                    item["WeatherIcon"] = -18
                
                weather_data[dt] = (
                    item["Temperature"]["Value"],
                    self.match_openweather_icon(item["WeatherIcon"]),
                    item["PrecipitationProbability"]
                )

            return sorted(weather_data.items())

        except KeyError as e:
            logging.error(f"Error when processing forecast data: {e}")
            raise e

    def fetch_5daysforecast_url(self):
        raise NotImplementedError

    def _load_forecast_timestamp(self, cache: dict) -> datetime:
        """load the most recent time of the forecast

        Args:
            cache (dict): cache from AccuWeather forecast api

        Returns:
            datetime:  timestamp of the most recent data
        """
        raise NotImplementedError

    def match_openweather_icon(self, icon_num: int) -> str:
        """use openweather icon to replace accuweather icon

        Args:
            icon_num (int): icon num of accuweather

        Raises:
            ValueError: not support / unknown icon_num

        Returns:
            str: icon name of openweather
        """
        if icon_num in (1, 2):
            # sunny / mostly sunny -> sunny
            return "01d"
        elif icon_num in (33, 34):
            # sunny / mostly sunny -> sunny
            return "01n"
        elif icon_num in (3, 4):
            # Partly sunny / intermittent clouds -> few clouds
            return "02d"
        elif icon_num in (35, 36):
            # Partly sunny / intermittent clouds -> few clouds
            return "02n"
        elif icon_num in (5, 6):
            # Hazy Sunshine, Mostly Cloudy -> scattered clouds
            return "03d"
        elif icon_num in (37, 38):
            # Hazy Sunshine, Mostly Cloudy -> scattered clouds
            return "03n"
        elif icon_num in (7, 8):
            # Cloudy, Dreary -> broken clouds
            return "04d"
        elif icon_num in (11,):
            # Fog -> mist
            return "50d"
        elif icon_num in (12, 13, 14 ):
            # Showesr, Mostly Cloudy w Showers, Partly Sunny W Showers -> shower rain
            return "09d"
        elif icon_num in (39, 40):
            # Showesr, Mostly Cloudy w Showers, Partly Sunny W Showers -> shower rain
            return "09n"
        elif icon_num in (15, 16, 17):
            # T-Storms, Mostly Cloudy w T-Storms, Partly Sunny w T-Storms -> thunderstorm
            return "11d"
        elif icon_num in (41, 42):
            # T-Storms, Mostly Cloudy w T-Storms, Partly Sunny w T-Storms -> thunderstorm
            return "11n"
        elif icon_num in (18,):
            # rain -> rain
            return "10d"
        elif icon_num in (-18,):
            # rain -> rain
            return "10n"
        elif icon_num in (19, 20, 21, 22, 23, 24, 25, 26, 29, 43, 44):
            # snow -> snow
            return "13d"
        else:
            raise ValueError(f"unknown icon num {icon_num}")


class OpenWeatherClient(WeatherClient):
    def _get_api_key(self):
        return os.environ.get("OPEN_WEATHER_API_KEY")

    def _setup_api_url(self):
        self.fetch_base_url = f"https://api.openweathermap.org/data/2.5"
        self.url_para = f"?lat={self.latitude}&lon={self.longitude}&units={UNITS}&appid={self.api_key}"

    @property
    def fetch_current_url(self) -> str:
        return f"{self.fetch_base_url}/weather" + self.url_para

    @property
    def fetch_12hrforecasts_url(self) -> str:
        raise NotImplementedError(
            "12 hour forecast has not implemented for OpenWeatherClient"
        )

    def _load_hours_forecast_timestamp(self) -> datetime:
        raise NotImplementedError(
            "12 hour forecast has not implemented for OpenWeatherClient"
        )

    def _load_12hrsforecast(self, data: list[dict]) -> list[tuple[datetime, float]]:
        raise NotImplementedError(
            "12 hour forecast has not implemented for OpenWeatherClient"
        )

    @property
    def fetch_5daysforecast_url(self) -> str:
        return f"{self.fetch_base_url}/forecast" + self.url_para

    def _load_forecast_timestamp(self, cache: dict) -> datetime:
        """load the most recent time of the forecast

        Args:
            cache (dict): cache from OpenWeather forecast api

        Returns:
            datetime:  timestamp of the most recent data
        """
        return datetime.strptime(cache["list"][0]["dt_txt"], "%Y-%m-%d %H:%M:%S")

    def _load_current_weather_timestamp(self, cache: dict) -> datetime:
        """_summary_

        Args:
            cache (dict): cache from OpenWeather current weather api

        Returns:
            datetime: timestamp of the most recent data
        """
        return datetime.fromtimestamp(cache["dt"])

    def _load_5days_forecast(self, data: dict) -> list[tuple[datetime, float]]:
        """load 9am, 3pm and 9pm weather from fetched data

        Args:
            data (dict): feteched data

        Returns:
            sorted list of tuple with datetime and temperature
        """
        weather_data = {}
        data = data["list"]
        try:
            for item in data:
                dt_txt_time = datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S")
                if dt_txt_time.hour in (9, 15, 21):
                    weather_data[dt_txt_time] = item["main"]["temp"]

            return sorted(weather_data.items())

        except KeyError as e:
            logging.error(f"Error when processing forecast data: {e}")
            raise e

    def _load_current_weather(self, data: dict) -> tuple[str, str]:
        """get weather icon and short description from data fetched from current weather API

        Args:
            data (dict): data returned from current weather API

        Returns:
            tuple[str, str]: icon name, short description
        """
        current_weather = data["weather"][0]
        current_weather_icon: str = current_weather["icon"]
        current_weather_des: str = current_weather["description"]

        return current_weather_icon, current_weather_des
