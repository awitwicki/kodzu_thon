from __future__ import print_function
from logging import exception

import sys
import os
import datetime
import requests
import urllib
import json
import uuid
import random
from time import sleep

import cachetools.func
from googletrans import Translator
from googlesearch import search
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import python_weather
import pandas as pd

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as np

import yfinance as yf

from qbstyles import mpl_style

mpl_style(dark=True)

import python_weather

from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsAdmins, ChatParticipantCreator, ChannelParticipantCreator, ChannelParticipantsSearch
from telethon.tl.custom.participantpermissions import ParticipantPermissions as ParticipantPermissions

import yfinance as yf

city_name = os.environ.get('TELETHON_CITY', 'Odessa')

# create folders
if not os.path.exists('img'):
    os.makedirs('img')
    print(f"Created dir /img", file=sys.stderr)

symbols = '😂👍😉😭🧐🤷‍♂️😡💦💩😎🤯🤬🤡👨‍👨‍👦👨‍👨‍👦‍👦'


def influx_query(query_str: str):
    try:
        url = 'http://localhost:8086/write?db=bots'
        headers = {'Content-Type': 'application/Text'}

        x = requests.post(url, data=query_str.encode('utf-8'), headers=headers)
    except Exception as e:
        print(e)


def get_btc():
    r = requests.get(url = "https://api.coindesk.com/v1/bpi/currentprice.json") 

    # extracting data in json format
    data = r.json() 

    price = data['bpi']['USD']['rate']
    price = price.replace(',','')
    price = int(float(price))

    price = f'Bitcoint price: {price} USD'

    return price

# Not works
def make_crypto_report(currency_name: str ='BTC', days_count: int = 30):
    now_date = datetime.datetime.now()

    start_date_str = (now_date - datetime.timedelta(days = days_count)).strftime("%Y-%m-%dT%H:%M")
    end_date_str = now_date.strftime("%Y-%m-%dT%H:%M")

    # https://www.coindesk.com/price/bitcoin/
    request_url = 'https://www.coindesk.com/pf/api/v3/content/fetch/chart-api?query={"end_date":"' \
        + f'{end_date_str}' \
        + '","iso":"' \
        + f'{currency_name}' \
        + '","ohlc":false,"start_date":"' \
        + f'{start_date_str}' \
        + '"}&d=179&_website=coindesk'

    r = requests.get(url=request_url)

    # Extracting data in json format
    data = r.json()

    # Parse historical data and convert to datetime
    history = [(datetime.datetime.fromtimestamp(f[0] / 1000), f[1]) for f in data['entries']]

    # Convert to 2d array and split for 2 arrays
    history = np.array(history)
    dates = history[:, 0]
    values = history[:, 1]

    # Create the figure and subplots
    fig = plt.figure(figsize=(12,8))

    ax = plt.subplot()
    ax.plot(dates, values)
    ax.set_title(f'{currency_name} currencies for last {days_count} days', fontsize=20)
    ax.grid(linestyle = '--', linewidth = 0.7)

    # Rotate the x-axis labels so they don't overlap
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=20)
    plt.tight_layout()

    # Calculate extra info
    actual_currency = values[-1]
    percent_growth = 100 * (values[-1] - values[0]) / values[0]

    # Save image
    image_path = f'img/{uuid.uuid4()}.png'
    plt.savefig(image_path, bbox_inches='tight')

    return image_path, actual_currency, percent_growth


def get_weather():
    weather_string = 'Weather forecast is not completed yet'
    return weather_string


def get_upload_temp_data(raw_api_dict):
    try:
        # current weather
        temperature = raw_api_dict['current']
        humidity = raw_api_dict['humidity']

        data_str = f'iot,room=outside_rzeszow,device=kodzuthon,sensor=openweather_api temperature={temperature},humidity={humidity}'
        influx_query(data_str)

    except Exception as e:
        print(e)


async def get_raw_temp():
    raw_api_dict = {}
    raw_api_dict['current'] = 0
    raw_api_dict['humidity'] = 0

    try:
        # declare the client. format defaults to metric system (celcius, km/h, etc.)
        client = python_weather.Client(format=python_weather.METRIC)

        # fetch a weather forecast from a city
        weather = await client.find(city_name)

        # close the wrapper once done
        await client.close()

        raw_api_dict['current'] = weather.current.temperature
        raw_api_dict['humidity'] = weather.current.humidity
    except:
        pass

    return raw_api_dict


def get_temp(raw_api_dict):
    # current weather
    current = raw_api_dict['current']
    temp = f"{current}cm"

    return temp


def get_covid():
    def make_countrystring(country):
        return f"{country['Country']}: +{country['NewConfirmed']}/{country['TotalConfirmed']}"

    try:
        url = urllib.request.urlopen('https://api.covid19api.com/summary')
        output = url.read().decode('utf-8')
        raw_api_dict = json.loads(output)
        url.close()

        countries = raw_api_dict['Countries']
        countries = {f['CountryCode']:f for f in countries}

        pl = countries['PL']
        ua = countries['UA']

        pl = make_countrystring(pl)
        ua = make_countrystring(ua)

        ret = f'{pl}\n{ua}\n\ncovid19api.com'
        return ret
    except:
        return 'Caching in progress...'


def get_year_progress(length=20):
    def progress_bar(value, total = 100, prefix = '', suffix = '', decimals = 2, length = 100, fill = '█'):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (value / float(total)))
        filledLength = int(length * value // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        return f'{prefix} |{bar}| {percent}% {suffix}'

    from datetime import datetime
    day_of_year = datetime.now().timetuple().tm_yday
    timenow = datetime.now().strftime("%H:%M")
    yr = progress_bar(day_of_year, 365, length=length)
    yr = f'{yr} {day_of_year}/365'
    # yr = f'2020:{yr}{timenow} {day_of_year}/365 days'

    return yr


def get_life_progress():
    date_time_obj = datetime.datetime.strptime('2003-05-08', '%Y-%m-%d')
    day_of_year = (datetime.datetime.now() - date_time_obj)
    days = day_of_year.days
    percent = ("{0:." + str(5) + "f}").format(100 * (days / float(29200)))
    yr = f'Uptime {days} days. Progress {percent}%'

    return yr


def get_new_cases(country):
    try:
        url = urllib.request.urlopen(f'https://api.covid19api.com/dayone/country/{country}/status/confirmed/live')
        output = url.read().decode('utf-8')
        raw_api_dict = json.loads(output)
        url.close()

        cases = [f['Cases'] for f in raw_api_dict]
        cases = list(map(lambda i: i[0] - i[1], zip(cases, [0] + cases)))

        #datetime format => '2020-03-27T00:00:00Z'
        days = [ datetime.datetime.strptime(f['Date'], '%Y-%m-%dT%H:%M:%SZ') for f in raw_api_dict]

        # Remove todays day because its always zeros
        days = days[:-1]
        cases = cases[:-1]

        # Take last 2 months
        fr = 60
        days = days[-fr:]
        cases = cases[-fr:]

        return days, cases
    except:
        return [], []


def covid_graph():
    ukraine_days, ukraine_cases = get_new_cases(country='ukraine')
    poland_days, poland_cases = get_new_cases(country='poland')

    # Calculate per population
    ukraine_cases = [case / 41.98e6 * 1e6 for case in ukraine_cases]
    poland_cases = [case / 37.97e6 * 1e6 for case in poland_cases]

    # Make chart
    fig = plt.figure()
    plt.plot(ukraine_days, ukraine_cases, color = 'cadetblue')
    plt.plot(poland_days, poland_cases, color = 'gold')

    plt.legend(('Ukraine', 'Poland'), loc='upper left')

    plt.title(f"Covid new cases trends per population", loc='left')

    fig.autofmt_xdate()
    plt.grid(linestyle = '--', linewidth = 0.7)


    image_path = 'img/' + str(uuid.uuid4()) + '.png'
    plt.savefig(image_path, bbox_inches='tight')
    print(f'Image saved to {image_path}', file=sys.stderr)
    return image_path


def get_sat_img():
    fname = 'img/' + datetime.datetime.now().strftime("%m%d%Y%H_%M_%S") + '.jpg'

    with open(fname, 'wb') as handle:
        response = requests.get('https://en.sat24.com/image?type=visual&region=eu', stream=True)

        if not response.ok:
            print(response)

        for block in response.iter_content(1024):
            if not block:
                break

            handle.write(block)

        return fname


def random_emoji():
    f = open(file = 'emojis.txt',mode = 'r', encoding = 'utf-8')
    emojis = f.readline()
    f.close()
    return random.choice(emojis)


def random_otmazka():
    f = open(file = 'otmazki.txt', mode = 'r', encoding = 'utf-8')
    lines = f.readlines()
    f.close()
    return random.choice(lines)


def break_text(msg_text):
    count = int(len(msg_text)/4)

    for i in range(count):
        emotion = random.choice(symbols)
        ind = random.randint(0, len(msg_text))
        msg_text = msg_text[:ind] + emotion + msg_text[ind:]

    return msg_text


def translate_text(msg_text, dest = 'uk', silent_mode = False) -> str:
    try:
        translator = Translator()
        result = translator.translate(msg_text, dest=dest)

        return_text = '' if silent_mode else f'Translated from: {result.src}\n\n'
        return_text += f'{result.text}'
        return return_text
    except:
        return "Can't translate"


def google_search(text: str) -> str:
    try:
        result = search(text, num_results=1)

        # Fix bug for python 3.7
        result = list(result)

        result = result[0].replace('https://','').replace('http://','')
        return result
    except Exception as e:
        return str(e)


async def build_message_chat_info(event: events.NewMessage.Event, client: TelegramClient):
    try:
        reply_msg = await event.message.get_reply_message()

        # If reply_msg then scan sender
        if reply_msg:
            try:
                sender_name = f'{reply_msg.sender.title}'
            except:
                sender_name = f'{reply_msg.sender.first_name} {reply_msg.sender.last_name}'

            reply_text = f'┌ Scan info:\n'\
                         f'├ Username: @{reply_msg.sender.username}\n'\
                         f'├ User id: {reply_msg.sender.id}\n'\
                         f'├ Full name: {sender_name}\n'\
                         f'├ Chat id: {event.chat_id}\n'\
                         f'└ Message id: {event._message_id}'
        # Else scan chat
        else:
            chat = await event.get_chat()

            reply_text = f'┌ Scan info:\n'

            try:
                if chat.username:
                    reply_text +=  f'├ Chat username: @{chat.username}\n'
            except:
                pass

            reply_text += f'├ Chat name: {chat.title}\n'\
                    f'├ Chat id: {chat.id}\n'

            try:
                admins = await client.get_participants(chat, filter=ChannelParticipantsAdmins)
                creator = [admin for admin in admins if isinstance(admin.participant, ChatParticipantCreator) or isinstance(admin.participant, ChannelParticipantCreator)][0]

                reply_text +=  f'├ Owner Username: {"@" + creator.username if creator.username else "-"}\n'\
                            f'├ Owner id: {creator.id}\n'

                try:
                    creator_name = f'{creator.title}'
                except:
                    creator_name = f'{creator.first_name} {creator.last_name}'

                reply_text += f'└ Owner Full name: {creator_name}'
            except:
                reply_text += f'└ Owner not found'

        return reply_text

    except Exception as e:
        print(e)
        return f'ERROR!\n\n{e}'


async def scrap_chat_users(event: events.NewMessage.Event, client: TelegramClient):
    try:
        chat = await event.get_chat()
        path = f'{chat.title}_{chat.id}_members.csv'

        offset = 0
        limit = 100
        all_participants = []

        while True:
            participants = await client(GetParticipantsRequest(chat, ChannelParticipantsSearch(''), offset, limit, hash=0))
            if not participants.users:
                break
            all_participants.extend(participants.users)
            offset += len(participants.users)
            sleep(1)

        with open(path, 'w', encoding='utf8') as f:
            f.write('user_id,user_name')

            for participant in all_participants:
                try:
                    participant_name = f'{participant.id},{participant.title}'
                except:
                    participant_name = f'{participant.id},{participant.first_name} {participant.last_name}'

                f.write(f'{participant_name}\n')

        return True, path

    except Exception as e:
        print(e)
        return False, f'ERROR!\n\n{e}'


# Finances
def get_ticker_info(ticker):
    return ticker.info


def get_ticker_data(ticker):
    ticker_info = f'' \
        f"**{ticker['symbol']}**\n" \
        f"[{ticker['shortName']}]({ticker['website']})\n" \
        f"\n" \
        f"Market price: **{ticker['regularMarketPrice']}$**"

    return ticker_info


def get_ticker_history(ticker):
    hist = ticker.history(period="1mo", interval="30m")
    hist = hist.reset_index()
    # print(hist.to_string(index=None), file=sys.stderr)
    return hist


def get_ticker_growth(ticker_history):
    growth_dollar = ticker_history.iloc[-1].Close - ticker_history.iloc[0].Close
    growth_percent = (growth_dollar / ticker_history.iloc[0].Close) * 100

    return growth_dollar, growth_percent


def get_ticker_recommendations(ticker):
    from datetime import datetime
    label_text = '**Recommendations:**\n'

    df = ticker.recommendations
    df = df.reset_index()
    df['Date'] = df['Date'].apply(lambda x: datetime.strftime(x, '%d/%m/%Y'))
    df = df.tail(5)
    df = df.drop(columns=['From Grade', 'Action'])
    recommendations = df.to_string(index=None)

    # Transform to monospace
    recommendations = ''.join([f'`{line}`\n' for line in recommendations.split('\n')])

    return label_text + recommendations


def make_ticker_plot(ticker_history, ticker_name):
    fig = plt.figure()
    plt.plot(ticker_history['Datetime'].values, ticker_history['Close'].values)

    plt.title(f"{ticker_name} ticker price", loc='left')
    plt.ylabel('Close price USD')

    fig.autofmt_xdate()
    plt.grid(linestyle = '--', linewidth = 0.7)

    # Save image
    image_path = 'img/' + str(uuid.uuid4()) + '.png'
    plt.savefig(image_path, bbox_inches='tight')
    print(f'Image saved to {image_path}', file=sys.stderr)
    return image_path


def make_ticker_report(ticker_name):
    ticker = yf.Ticker(ticker_name)
    ticker_info = get_ticker_info(ticker)
    ticker_name = ticker_info['symbol']

    ticker_main_info = get_ticker_data(ticker_info)

    ticker_history = get_ticker_history(ticker)
    ticker_history_image_path = make_ticker_plot(ticker_history, ticker_name)

    ticker_growth_dollar, ticker_growth_percent = get_ticker_growth(ticker_history)

    ticker_recommendations = get_ticker_recommendations(ticker)

    return ticker_main_info + f' {ticker_growth_percent:.2f}% ({ticker_growth_dollar:.2f}$)' + '\n\n' + ticker_recommendations, ticker_history_image_path


def make_currency_report():
    # Prepare data
    date_now = datetime.datetime.utcnow()
    start_date = date_now - datetime.timedelta(days = 30)
    end_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    data_EURUSD = yf.download('EURUSD=X', start=start_date, end=end_date)
    data_USDPLN = yf.download('USDPLN=X', start=start_date, end=end_date)
    data_USDUAH = yf.download('USDUAH=X', start=start_date, end=end_date)

    # Calculate PLN/UAH currency
    data_PLNUAH = pd.concat([data_USDPLN.rename(columns={"Close": "Close_usd_pln"}), data_USDUAH], axis=1).rename(columns={"Close": "Close_usd_uah"})
    data_PLNUAH['Close'] = data_PLNUAH.apply(lambda x: 1/x.Close_usd_pln * x.Close_usd_uah, axis=1)

    # Get old values
    data_EURUSD_old = data_EURUSD.iloc[0].Close
    data_USDUAH_old = data_USDUAH.iloc[0].Close
    data_USDPLN_old = data_USDPLN.iloc[0].Close
    data_PLNUAH_old = data_PLNUAH.iloc[0].Close

    # Get last actual values
    data_EURUSD_last = data_EURUSD.iloc[-1].Close
    data_USDUAH_last = data_USDUAH.iloc[-1].Close
    data_USDPLN_last = data_USDPLN.iloc[-1].Close
    data_PLNUAH_last = data_PLNUAH.iloc[-1].Close

    # Calculate delta percent
    vals = pd.DataFrame()
    vals = vals.append({'pair_name': 'EUR/USD', 'old_elem': data_EURUSD_old, 'last_elem': data_EURUSD_last}, ignore_index=True)
    vals = vals.append({'pair_name': 'USD/PLN', 'old_elem': data_USDPLN_old, 'last_elem': data_USDPLN_last}, ignore_index=True)
    vals = vals.append({'pair_name': 'USD/UAH', 'old_elem': data_USDUAH_old, 'last_elem': data_USDUAH_last}, ignore_index=True)
    vals = vals.append({'pair_name': 'PLN/UAH', 'old_elem': data_PLNUAH_old, 'last_elem': data_PLNUAH_last}, ignore_index=True)

    vals['delta'] = vals.apply(lambda x: (x.last_elem - x.old_elem), axis=1)
    vals['delta_percent'] = vals.apply(lambda x: (100 * x.delta / x.old_elem), axis=1)

    # Build percent growth strings
    build_percent_growth_strings = '\n'.join([f'`{x.pair_name}: {x.last_elem:.2f} ({x.delta_percent:.2f}%)`' for x in vals.iloc])

    # Draw chart
    def plot_chart(ax, df, title):
        ax.plot(df.index.values, df['Close'].values)
        ax.set_title(title)
        ax.grid(linestyle = '--', linewidth = 0.7)

        # Rotate the x-axis labels so they don't overlap
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=20)

    # Create the figure and subplots
    fig = plt.figure(figsize=(12,8))

    fig.suptitle('Currencies for last 30 days', fontsize=20)

    # Rename the axes for ease of use
    ax11 = plt.subplot(2, 2, 1)
    ax12 = plt.subplot(2, 2, 2)
    ax21 = plt.subplot(2, 2, 3)
    ax22 = plt.subplot(2, 2, 4)

    plot_chart(ax11, data_USDPLN, 'USD/PLN')
    plot_chart(ax12, data_EURUSD, 'EUR/USD')
    plot_chart(ax21, data_USDUAH, 'USD/UAH')
    plot_chart(ax22, data_PLNUAH, 'PLN/UAH')

    plt.tight_layout()

    # Save image
    image_path = f'img/{uuid.uuid4()}.png'
    plt.savefig(image_path, bbox_inches='tight')
    return image_path, build_percent_growth_strings


@cachetools.func.ttl_cache(maxsize=128, ttl=60 * 60)
def get_200_stat():
    print("hi")
    resp =  requests.get('https://russianwarship.rip/api/v1/statistics/latest')
    return resp.json()


def two_hundred_count():
    import datetime
    from datetime import timedelta

    def timedelta_percentage(input_datetime):
        TOTAL_DAY_SECS = 86400.0
        d = input_datetime - datetime.datetime.combine(input_datetime.date(), datetime.time())
        return d.total_seconds() / TOTAL_DAY_SECS

    started = datetime.datetime(2022, 2, 24)
    last_date = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())

    _200_stat = get_200_stat()['data']
    last_value = _200_stat['stats']['personnel_units']
    last_increase = _200_stat['increase']['personnel_units']

    total_calculated_days = (last_date - started).days
    days_delta = (datetime.datetime.utcnow() - last_date).days
    average = last_value / total_calculated_days

    today_value = last_increase * timedelta_percentage(datetime.datetime.utcnow() + timedelta(hours=2))
    result = last_value + today_value + (average * days_delta)

    return result


# Air alarm map tools
def centroid(vertexes):
    _x_list = vertexes[:, 0]
    _y_list = vertexes[:, 1]

    _len = len(vertexes)
    _x = sum(_x_list) / _len
    _y = sum(_y_list) / _len

    return(_x, _y)


state_library = {
    'Khmelnytskyi Oblast': 'Хмельницька область',
    'Vinnytsia Oblast': 'Вінницька область',
    'Rivne Oblast': 'Рівненська область',
    'Volyn Oblast': 'Волинська область',
    'Dnipropetrovsk Oblast': 'Дніпропетровська область',
    'Zhytomyr Oblast': 'Житомирська область',
    'Zakarpattia Oblast': 'Закарпатська область',
    'Zaporizhia Oblast': 'Запорізька область',
    'Ivano-Frankivsk Oblast': 'Івано-Франківська область',
    'Kiev Oblast': 'Київська область',
    'Kirovohrad Oblast': 'Кіровоградська область',
    'Luhansk Oblast': 'Луганська область',
    'Mykolaiv Oblast': 'Миколаївська область',
    'Odessa Oblast': 'Одеська область',
    'Poltava Oblast': 'Полтавська область',
    'Sumy Oblast': 'Сумська область',
    'Ternopil Oblast': 'Тернопільська область',
    'Kharkiv Oblast': 'Харківська область',
    'Kherson Oblast': 'Херсонська область',
    'Cherkasy Oblast': 'Черкаська область',
    'Chernihiv Oblast': 'Чернігівська область',
    'Chernivtsi Oblast': 'Чернівецька область',
    'Lviv Oblast': 'Львівська область',
    'Donetsk Oblast': 'Донецька область'
}


def parse_geojson_data(path='media/ukraine-with-regions_1530.geojson'):
    data = None
    with open(path, 'r') as file:
        data = file.read()

    geojson = json.loads(data)

    districts = {}

    for f in geojson['features']:
        polygons = f['geometry']['coordinates']
        # print(f"{f['properties']['name']}, polygons count: {len(polygons)}")

        polygons = [np.array(p, dtype=np.float16) for p in polygons]
        districts[f['properties']['name']] = { 'polygons': polygons }

    return districts


districts = parse_geojson_data()


def get_alarms_dict():
    request_url = 'https://air-save.ops.ajax.systems/api/mobile/regions'
    r = requests.get(url=request_url)
    alarm_data = r.json()['regions']
    alarm_data = [f for f in alarm_data if f['regionType'] == 'STATE']

    alarms_in_regions = {}
    inv_state_library = {v: k for k, v in state_library.items()}

    for f in alarm_data:
        if f['name'] in inv_state_library.keys():
            normalized_name = inv_state_library[f['name']]
            alarms_in_regions[f['name']] = len(f['alarmsInRegion']) > 0

    return alarms_in_regions


def make_alarm_map():
    alarms_dict = get_alarms_dict()

    fig = plt.figure(figsize=(15, 8))
    render_map = Basemap(projection='lcc', lat_0=48.4, lon_0=31.25, width=14E5, height=1E6,resolution='l') # 'c','l','i','h' or 'f'

    # Draw coastlines, country boundaries, fill continents.
    render_map.drawcoastlines(linewidth=0.25)
    render_map.drawcountries(linewidth=1)
    render_map.fillcontinents(color='DarkSlateGray', lake_color='LightSeaGreen')
    render_map.drawmapboundary(fill_color='LightSeaGreen')

    # Draw lat/lon grid lines every 30 degrees.
    render_map.drawmeridians(np.arange(0, 360, 3))
    render_map.drawparallels(np.arange(-90, 90, 3))

    for district_name in list(districts.keys()):
        # Get alarm status
        state_fill_color = 'Gray'
        if district_name in state_library.keys():
            normalized_district_name = state_library[district_name]
            # print(normalized_district_name)
            state_fill_color = 'Red' if alarms_dict[normalized_district_name] else 'Gray'

        for polygon in districts[district_name]['polygons']:
            data = np.array([render_map(x[0], x[1]) for x in polygon])
            plt.fill(data[:, 0], data[:, 1], facecolor=state_fill_color, edgecolor='black', linewidth=1, alpha=0.5)

        # Place text with state name
        # x, y = centroid(districts[district_name]['polygons'][-1])
        # x, y = render_map(x, y)
        # print(f'{district_name} centroid coords: {x}, {y}')
        # plt.text(x, y, district_name, fontsize=8)

    # plt.title('Повітряна тривога')

    # Save image
    image_path = 'img/' + str(uuid.uuid4()) + '.png'
    plt.savefig(image_path, bbox_inches='tight')
    print(f'Image saved to {image_path}', file=sys.stderr)
    return image_path, alarms_dict
