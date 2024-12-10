import os
import requests
import logging
from datetime import datetime
import json

from constants import *


class WeatherClient:
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

    def get_current_weather(self) -> tuple[str, str]:
        """get current weather from cache data or fetch from api if cache expired

        Returns:
            tuple[str, str]: icon name and short description
        """
        cache_current = self._load_cached_data(self.cache_current_path)
        if self.check_expired and (
            cache_current and self._check_cache_current_expired(cache_current)
        ):
            # delete expired weather cache
            cache_current = None
            
        if cache_current is None:
            # fetch new data
            weather_data = self._fetch_current_weather()
            self._save(weather_data, self.cache_current_path)
            return self._load_current_weather(weather_data)
        else:
            logging.info("using cache current forecast")
            return self._load_current_weather(cache_current)
    
    def get_5days_forecast(self) -> list[tuple[datetime, float]]:
        """get 5days forecast from cache data or fetch from api if cahce expired

        Returns:
            list[tuple[datetime, float]]: sorted list of tuple with datetime and temperature
        """
        cache_forecast = self._load_cached_data(self.cache_forecast_path)
        if self.check_expired and (
            cache_forecast and self._check_cache_forecast_expired(cache_forecast)
        ):
            # delete expired weather cache
            cache_forecast = None

        if cache_forecast is None:
            # fetch new data
            weather_data = self._fetch_5days_forecast()
            self._save(weather_data, self.cache_forecast_path)
            return self._load_5days_forecast(weather_data)
        else:
            logging.info("using cache 5days forecast")
            return self._load_5days_forecast(cache_forecast)

    def _save(self, data: dict, cache_path: Path) -> None:
        # save the fetched data to given path
        with open(cache_path, "w") as f:
            json.dump(data, f)

    def _load_api_parameters(self):
        from dotenv import load_dotenv

        load_dotenv()

        self.api_key = os.environ.get("OPEN_WEATHER_API_KEY")
        self.latitude = os.environ.get("LATITUDE")
        self.longitude = os.environ.get("LONGITUDE")

    def _load_current_weather(self, data: dict) -> tuple[str, str]:
        """get weather icon and short description from data fetched from current weather API 

        Args:
            data (dict): _description_

        Returns:
            tuple[str, str]: _description_
        """
        current_weather = data["weather"][0]
        current_weather_icon: str = current_weather["icon"]
        current_weather_des: str = current_weather["description"]

        return current_weather_icon, current_weather_des

    def _load_cached_data(self, cache_path: Path) -> dict | None:
        """load data from given cache path"""
        if cache_path.is_file():
            with open(cache_path, "r") as f:
                return json.load(f)
        return None

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
        
    def _fetch_current_weather(self):
        """fetch current weather data from OpenWeather"""
        api_url = f"https://api.openweathermap.org/data/2.5/weather"
        url = f"{api_url}?lat={self.latitude}&lon={self.longitude}&units={UNITS}&appid={self.api_key}"

        try:
            response = requests.get(url)
            response.raise_for_status()
            logging.info("Current weather data fetched successfully.")
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch weather data: {e}")
            raise

    def _fetch_5days_forecast(self) -> dict:
        """fetch 5days_forecast from OpenWeather"""
        api_url = f"https://api.openweathermap.org/data/2.5/forecast"

        url = f"{api_url}?lat={self.latitude}&lon={self.longitude}&units={UNITS}&appid={self.api_key}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            logging.info("forecast data fetched successfully.")
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Failed to fetch weather data: {e}")
            raise

    def _check_cache_forecast_expired(self, cache: dict) -> bool:
        """check if the cache is one day or more ago

        Args:
            cache (dict): cache from OpenWeather forecast api

        Returns:
            bool: is cache expired
        """
        now = datetime.now()
        cache_time = datetime.strptime(cache["list"][0]["dt_txt"], "%Y-%m-%d %H:%M:%S")

        return now.date() > cache_time.date()
    
    def _check_cache_current_expired(self, cache: dict) -> bool:
        """check if the cache is an hour or more ago

        Args:
            cache (dict): cache from OpenWeather current weather api

        Returns:
            bool: is cache expired
        """
        now = datetime.now()
        cache_time = datetime.fromtimestamp(cache['dt'])

        return now.hour > cache_time.hour


# TODO OPENWEATHER CLIENT
# TODO ACCUWEATHER CLIENT
