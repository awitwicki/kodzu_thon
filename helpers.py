import os
import datetime
import requests
import urllib
import json
import uuid

from matplotlib import pyplot as plt
import matplotlib.dates as mdates

# create folders
if not os.path.exists('img'):
    os.makedirs('img')
    print(f"Created dir /img")

# load api keys
OPEN_WEATHER_API_KEY = os.environ['OPEN_WEATHER_API_KEY']

def get_btc():
    r = requests.get(url = "https://api.coindesk.com/v1/bpi/currentprice.json") 

    # extracting data in json format
    data = r.json() 

    price = data['bpi']['USD']['rate']
    price = price.replace(',','')
    price = int(float(price))

    price = f'Bitcoint price: {price} USD'

    return price

def get_weather():
    url = urllib.request.urlopen(f'https://api.openweathermap.org/data/2.5/onecall?lat=50.04&lon=21.99&APPID={OPEN_WEATHER_API_KEY}')
    output = url.read().decode('utf-8')
    raw_api_dict = json.loads(output)
    url.close()

    # current weather
    current = raw_api_dict['current']
    temp = f"{round(current['temp'] - 273.15, 1)}"
    humidity = f"{current['humidity']}"

    weather_string = "Weather in **Rzeszów**\n"
    weather_string += f"Temperature: `{temp}C` Humidity: `{humidity}%`\n"

    for weather in current["weather"]:
        weather_string += f'{weather["main"]}: `{weather["description"]}`\n'

    weather_string += f"\nForecast:\n"

    #hourly forecast
    hourly = raw_api_dict['hourly']
    for forecast in hourly[:12]:
        time = str(datetime.datetime.fromtimestamp(forecast["dt"]))[11:]
        temp = f"{round(forecast['temp'] - 273.15, 1)}C"
        descriptions = [description['description'] for description in forecast['weather']]
        description_string = ', '.join(descriptions)
        forecast_line = f"{time} - `{temp}`, {description_string}\n"
        weather_string += forecast_line

    return weather_string

def get_covid():
    def make_countrystring(country):
        return f"{country['Country']}: +{country['NewConfirmed']}/{country['TotalConfirmed']}"

    url = urllib.request.urlopen('https://api.covid19api.com/summary')
    output = url.read().decode('utf-8')
    raw_api_dict = json.loads(output)
    url.close()

    countries = raw_api_dict['Countries']
    countries = {f['CountryCode']:f for f in countries}

    pl = countries['PL']
    ua = countries['UA']
    br = countries['BY']

    pl = make_countrystring(pl)
    ua = make_countrystring(ua)
    br = make_countrystring(br)

    ret = f'{pl}\n{ua}\n{br}'
    return ret

def get_year_progress():
    def progressBar(value, total = 100, prefix = '', suffix = '', decimals = 2, length = 100, fill = '█'):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (value / float(total)))
        filledLength = int(length * value // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        return f'{prefix} |{bar}| {percent}% {suffix}'

    from datetime import datetime
    day_of_year = datetime.now().timetuple().tm_yday
    timenow = datetime.now().strftime("%H:%M")
    yr = progressBar(day_of_year, 365, length=20)
    yr = f'2020:{yr}{timenow} {day_of_year}/365 days'

    return yr

def get_life_progress():
    def progressBar(value, total = 100, prefix = '', suffix = '', decimals = 2, length = 100, fill = '█'):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (value / float(total)))
        filledLength = int(length * value // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        return f'{prefix} |{bar}| {percent}% {suffix}'

    # from datetime import datetime
    date_time_obj = datetime.datetime.strptime('2003-05-08', '%Y-%m-%d')
    day_of_year = (datetime.datetime.now() - date_time_obj)
    days = day_of_year.days
    # pb = progressBar(days, 29200, prefix = 'Life progress: ', length=20)
    percent = ("{0:." + str(5) + "f}").format(100 * (days / float(29200)))
    yr = f'Uptime {days} days. Progress {percent}%'

    return yr

def get_new_cases(country = 'ukraine'):
    try:
        url = urllib.request.urlopen(f'https://api.covid19api.com/dayone/country/{country}/status/confirmed/live')
        output = url.read().decode('utf-8')
        raw_api_dict = json.loads(output)
        url.close()

        cases = [f['Cases'] for f in raw_api_dict]
        cases = list(map(lambda i: i[0] - i[1], zip(cases, [0] + cases)))

        #datetime format => '2020-03-27T00:00:00Z'
        days = [ datetime.datetime.strptime(f['Date'], '%Y-%m-%dT%H:%M:%SZ') for f in raw_api_dict]

        fr = 30
        days = days[-fr:]
        cases = cases[-fr:]

        return days, cases
    except:
        return [],[]

def covid_graph():
    ukraine_days, ukraine_cases = get_new_cases()
    poland_days, poland_cases = get_new_cases(country='poland')

    # import numpy as np
    # import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot(ukraine_days, ukraine_cases)
    ax.plot(poland_days, poland_cases)
    ax.legend(('Ukraine', 'Poland'), loc='upper left')

    # rotate and align the tick labels so they look better
    fig.autofmt_xdate()

    ax.set_title('Covid new cases trends')

    fname = 'img/' + str(uuid.uuid4()) + '.png'
    fig.savefig(fname)
    return fname

def get_rosir():
    r = requests.get('http://rosir.eu/news.php')
    return r.text