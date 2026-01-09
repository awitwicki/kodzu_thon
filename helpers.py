from __future__ import print_function

import sys
import os
import datetime
import requests
import json
import uuid
import random
from time import sleep

import cachetools.func
from googletrans import Translator
from googlesearch import search
import pandas as pd

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import numpy as np

import yfinance as yf

from qbstyles import mpl_style

mpl_style(dark=True)

from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import Channel, User, ChannelParticipantsAdmins, ChatParticipantCreator, ChannelParticipantCreator, ChannelParticipantsSearch
from influxdb import InfluxDBClient

# Connect to InfluxDB
client = InfluxDBClient(host='monitoring_influxdb', port=8086)
influx_db_name = 'bots'
# client.create_database(influx_db_name)
client.switch_database(influx_db_name)


# create folders
if not os.path.exists('img'):
    os.makedirs('img')
    print("Created dir /img", file=sys.stderr)

symbols = '😂👍😉😭🧐🤷‍♂️😡💦💩😎🤯🤬🤡👨‍👨‍👦👨‍👨‍👦‍👦'

def influx_query(tags_dict: dict, fields_dict: dict):
    try:
        json_body = [
            {
                "measurement": "bots",
                "tags": tags_dict,
                "fields": fields_dict
            }
        ]

        client.write_points(json_body)

    except Exception as e:
        print(e, file=sys.stderr)


def get_btc():
    r = requests.get(url = "https://api.coindesk.com/v1/bpi/currentprice.json") 

    # extracting data in json format
    data = r.json() 

    price = data['bpi']['USD']['rate']
    price = price.replace(',','')
    price = int(float(price))

    price = f'Bitcoint price: {price} USD'

    return price


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


def random_emoji():
    f = open(file = 'emojis.txt',mode = 'r', encoding = 'utf-8')
    emojis = f.readline()
    f.close()
    return random.choice(emojis)


def break_text(msg_text):
    count = int(len(msg_text)/4)

    for i in range(count):
        emotion = random.choice(symbols)
        ind = random.randint(0, len(msg_text))
        msg_text = msg_text[:ind] + emotion + msg_text[ind:]

    return msg_text


async def translate_text(msg_text, dest='uk', silent_mode=False) -> str:
    try:
        translator = Translator()
        result = await translator.translate(msg_text, dest=dest)

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
            user_name = '@' + reply_msg.sender.username if reply_msg.sender.username else reply_msg.sender.username
            first_name = reply_msg.sender.first_name if reply_msg.sender.first_name else ''
            last_name = reply_msg.sender.last_name if reply_msg.sender.last_name else ''
            full_name = ' '.join([first_name, last_name])

            reply_text = f'┌ Scan info:\n'\
                         f'├ Username: {user_name}\n'\
                         f'├ User id: {reply_msg.sender.id}\n'\
                         f'├ Full name: {full_name}\n'\
                         f'├ Chat id: {event.chat_id}\n'\
                         f'└ Message id: {event._message_id}'

        # Else scan chat
        else:
            chat = await event.get_chat()

            if not isinstance(chat, Channel):
                return 'Scan only chats'

            chat_user_name = '@' + chat.username if chat.username else chat.username

            owner_id = ''
            owner_user_name = ''
            owner_full_name = ''

            try:
                admins = await client.get_participants(chat, filter=ChannelParticipantsAdmins)
                creator = [admin for admin in admins if isinstance(admin.participant, ChatParticipantCreator) or isinstance(admin.participant, ChannelParticipantCreator)][0]

                if creator:
                    owner_id = creator.id
                    owner_user_name = '@' + creator.username if creator.username else creator.username

                    owner_first_name = creator.first_name if creator.first_name else ''
                    owner_last_name = creator.last_name if creator.last_name else ''

                    owner_full_name = ' '.join([owner_first_name, owner_last_name])
            except Exception as e:
                print(e, file=sys.stderr)

            reply_text = '┌ Scan info:\n'\
                        f'├ Chat username: {chat_user_name}\n'\
                        f'├ Chat title: {chat.title}\n'\
                        f'├ Chat id: {chat.id}\n'\
                        f'├ Creation date: {chat.date}\n'\
                        f'├ Owner id: {owner_id}\n'\
                        f'├ Owner Username: {owner_user_name}\n'\
                        f'└ Owner Full name: {owner_full_name}\n'

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


def make_currency_report():
    market_data = yf.download(['EURUSD=X', 'USDPLN=X', 'USDUAH=X'], period='1mo')

    # Calculate PLN/UAH currency
    df = market_data['Close']
    df['PLNUAH=X'] = df.apply(lambda x: 1 / x['USDPLN=X'] * x['USDUAH=X'], axis=1)

    # Get old values
    data_EURUSD_old = df['EURUSD=X'].iloc[0]
    data_USDUAH_old = df['USDUAH=X'].iloc[0]
    data_USDPLN_old = df['USDPLN=X'].iloc[0]
    data_PLNUAH_old = df['PLNUAH=X'].iloc[0]

    # Get last actual values
    data_EURUSD_last = df['EURUSD=X'].iloc[-1]
    data_USDUAH_last = df['USDUAH=X'].iloc[-1]
    data_USDPLN_last = df['USDPLN=X'].iloc[-1]
    data_PLNUAH_last = df['PLNUAH=X'].iloc[-1]

    # Calculate delta percent
    new_rows = pd.DataFrame([
        {'pair_name': 'EUR/USD', 'old_elem': data_EURUSD_old, 'last_elem': data_EURUSD_last},
        {'pair_name': 'USD/PLN', 'old_elem': data_USDPLN_old, 'last_elem': data_USDPLN_last},
        {'pair_name': 'USD/UAH', 'old_elem': data_USDUAH_old, 'last_elem': data_USDUAH_last},
        {'pair_name': 'PLN/UAH', 'old_elem': data_PLNUAH_old, 'last_elem': data_PLNUAH_last}
    ])

    vals = pd.concat([pd.DataFrame(), new_rows], ignore_index=True)
    vals['delta'] = vals.apply(lambda x: (x.last_elem - x.old_elem), axis=1)
    vals['delta_percent'] = vals.apply(lambda x: (100 * x.delta / x.old_elem), axis=1)

    # Build percent growth strings
    build_percent_growth_strings = '\n'.join(
        [f'`{x.pair_name}: {x.last_elem:.2f} ({x.delta_percent:.2f}%)`' for x in vals.itertuples()])

    # Draw chart

    # Define the plot function
    def plot_chart(ax, df, title):
        ax.plot(df.index.values, df.values)
        ax.set_title(title)

        # Override grid settings for individual subplots
        ax.grid(True, linestyle='--', linewidth=0.7)  # Ensure grid is applied only to the specific subplot
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=20)

    # Create the figure and subplots
    fig, ((ax11, ax12), (ax21, ax22)) = plt.subplots(2, 2, figsize=(12, 8))

    # Plot each chart
    plot_chart(ax11, df['USDPLN=X'], 'USD/PLN')
    plot_chart(ax12, df['EURUSD=X'], 'EUR/USD')
    plot_chart(ax21, df['USDUAH=X'], 'USD/UAH')
    plot_chart(ax22, df['PLNUAH=X'], 'PLN/UAH')

    # Adjust layout
    plt.tight_layout()

    # Save image
    image_path = f'img/{uuid.uuid4()}.png'
    plt.savefig(image_path, bbox_inches='tight')
    plt.close()

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


def remove_file(path):
    try:
        os.remove(path)
    except Exception as e:
        print(e, file=sys.stderr)
