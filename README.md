# E-Paper Weather display
This repository contains an implementation of an E-Paper Weather Station using a Raspberry Pi and a Waveshare 6-inch e-ink display. The project fetches weather data from a public API and presents it in a dynamic layout. The left side of the display shows the current time and weather, while the right side displays a 5-day forecast along with a user-defined block. The layout's ratio and margins can be adjusted in the code to suit individual preferences.

## Features
- Partial updating clock
- Real-time weather updates
- 5-day weather forecast
- Customizable display layout

## Requirements
To get started, ensure you have the following dependencies installed:

```bash 
pip install -r requirements.txt
```
In addition to the above requirements, you will need the  [IT8951](https://github.com/GregDMeyer/IT8951) library to controll the e-ink display. 

## Configuration
Before running the program, you need to create a .env file to specify your API key and location. The file should contain the following variables:
```
OPEN_WEATHER_API_KEY=your_api_key_here
LATITUDE=your_latitude_here
LONGITUDE=your_longitude_here
```

## Hardware Connections
Connect the e-ink display to the Raspberry Pi using the following pinout:
```
5V -> 5V
GND -> GND
MISO -> GPIO 9
MOSI -> GPIO 10
SCLK -> GPIO 11
CS -> GPIO 8
RST -> GPIO 7
HDRY -> GPIO 24
```

# Running the Program
To update the display automatically every minute, you can set up a cron job using crontab. When running the program, set the auto_update argument to fetch the current weather and forecast at specified times. You can configure the update times by modifying the variables CURRENT_WEATHER_UPDATE_TIME_MINUTE and WEATHER_FORECAST_UPDATE_TIME_HOUR in constants.py. By default, the program fetches the weather forecast at 18:00 and the current weather at minute = 0.

To set up the cron job, run:
```bash
crontab -e
```
Then add the following line (update the paths accordingly):

```
* * * * * /path/to/python /path/to/weather_station.py --auto_update
```
Alternatively, you can run the program directly without setting up a cron job.



# Results
![eink](https://github.com/user-attachments/assets/ef5620a0-1e34-44e5-abe9-c68522c11cc5)


Feel free to reach out if you have any questions or need further assistance!


