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

from googletrans import Translator
from googlesearch import search

from matplotlib import pyplot as plt
import matplotlib.dates as mdates
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
        cz = countries['CZ']
        br = countries['BY']

        pl = make_countrystring(pl)
        ua = make_countrystring(ua)
        cz = make_countrystring(cz)
        br = make_countrystring(br)

        ret = f'{pl}\n{ua}\n{cz}\n{br}\n\ncovid19api.com'
        return ret
    except:
        return 'Caching in progress...'


def get_year_progress(length=20):
    def progressBar(value, total = 100, prefix = '', suffix = '', decimals = 2, length = 100, fill = '█'):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (value / float(total)))
        filledLength = int(length * value // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        return f'{prefix} |{bar}| {percent}% {suffix}'

    from datetime import datetime
    day_of_year = datetime.now().timetuple().tm_yday
    timenow = datetime.now().strftime("%H:%M")
    yr = progressBar(day_of_year, 365, length=length)
    yr = f'{yr} {day_of_year}/365'
    # yr = f'2020:{yr}{timenow} {day_of_year}/365 days'

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
        return [],[]


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
    # ticker = yf.Ticker(ticker_name)
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


def two_hundred_count():
    import datetime
    from datetime import timedelta

    def timedelta_percentage(input_datetime):
        TOTAL_DAY_SECS = 86400.0
        d = input_datetime - datetime.datetime.combine(input_datetime.date(), datetime.time())
        return d.total_seconds() / TOTAL_DAY_SECS

    started = datetime.datetime(2022, 2, 24)
    last_date = datetime.datetime(2022, 5, 30)

    total_calculated_days = (last_date - started).days
    last_value = 30350

    days_delta = (datetime.datetime.utcnow() - last_date).days
    average = last_value / total_calculated_days

    today_value = average * timedelta_percentage(datetime.datetime.utcnow() + timedelta(hours=2))
    result = last_value + today_value + (average * days_delta) 

    return result

make_ticker_report('meta')
covid_graph()
