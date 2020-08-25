# kodzu_thon

Telethon implementarion

## Installing

1. `pip install -r requirements.txt`

2. Set environment variables for API keys:
    * `OPEN_WEATHER_API_KEY` [method one call](https://openweathermap.org/api/one-call-api) API
    * `TELETHON_API_HASH` (get [api_hash](https://my.telegram.org/auth?to=apps), under API Development)
    * `TELETHON_API_ID`

3. Change **lat, lon** in line 35 `helpers.py` to your coordinates for get weather.

4. Place google-cloud-speech `.json` keyfile in this folder and name it `jsonkey.json`, or if You already have installed that key in Your system, just **comment line 2** in `speech.py`

5. Install **ffmpeg** and **ffprobe**
    * [windows](https://ffmpeg.zeranoe.com/builds/) install and place `ffmpeg.exe`, `ffprobe.exe` in **PATH**
    * [linux](https://www.tecmint.com/install-ffmpeg-in-linux/) (just install, it will work)
    
6. Also You can use `telethon.service` template to install it as systemctl daemon