from telethon import TelegramClient, events, sync, types, utils, functions
from telethon.tl.functions.account import UpdateProfileRequest

import urllib.request, json
import time
import speech
import os
from collections import deque
import helpers
import asyncio
import datetime

api_id = os.environ['TELETHON_API_ID']
api_hash = os.environ['TELETHON_API_HASH']

client = TelegramClient('session_name', api_id, api_hash)
client.start()

#userId
@client.on(events.NewMessage(pattern='(^!id$)', outgoing=True))
async def handler(event):
    if event.message.is_reply:
        msg = await event.message.get_reply_message()
        reply_text = f'id: {msg.sender.id}, name: {msg.sender.first_name}'
        await client.send_message('me', reply_text)
    await event.delete()

#send typing
@client.on(events.NewMessage(pattern='!t', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'typing'):
            await asyncio.sleep(300)
            pass

    except Exception as e:
        print(e)

#weather
@client.on(events.NewMessage(pattern='(^!w$)', outgoing=True))
async def handler(event):
    weather = helpers.get_weather()
    await event.edit(weather)

# basen
@client.on(events.NewMessage(pattern='(^basen$)', outgoing=True))
async def handler(event):
    rosir = helpers.get_rosir()
    await event.edit(rosir)

#covid
@client.on(events.NewMessage(pattern='(^cov$)', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        cov = helpers.get_covid()
        await event.edit(cov)

    except Exception as e:
        print(e)

#covid
@client.on(events.NewMessage(pattern='(^covg$)', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        await event.edit("Loading...")
        img_name = helpers.covid_graph()
        await event.delete()
        cov = helpers.get_covid()
        await client.send_file(chat, img_name, caption=cov)

    except Exception as e:
        print(e)

#audio
@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if event.voice:
        if event.is_private:
            reply_text = 'Голосовое сообщение не доставлено так как пользователь заблокировал эту опцию. Это сообщение написано автоматически.'
            chat = await event.get_chat()
            await client.send_message(chat, reply_text, reply_to = event.message.id)

#snake text
@client.on(events.NewMessage(pattern='!s', outgoing=True))
async def handler(event):
    try:
        origin_text = event.message.text.replace('!s ', '')

        for index, char in enumerate(origin_text):
            newtext = list(origin_text)
            newtext.insert(index, '**')
            newtext.insert(index+2, '**')
            newtext = ''.join(newtext)
            print(newtext)
            await event.edit(newtext)
            time.sleep(0.5)

        await event.edit(origin_text)

    except Exception as e:
        print(e)

#🦔🍎
@client.on(events.NewMessage(pattern='🦔', outgoing=True))
async def handler(event):
    try:
        origin_text = ''

        for i in range(19, -1, -1):
            edit_text = origin_text
            for r in range(i):
                edit_text += '🍎'
            edit_text += '🦔'
            print(origin_text)
            await event.edit(edit_text)
            time.sleep(0.5)

    except Exception as e:
        print(e)

#taco text
@client.on(events.NewMessage(pattern='(^тако$)', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        time.sleep(0.5)
        await event.delete()
        for i in range(5):
            msg = await client.send_message(chat, 'тако')
            time.sleep(0.5)
            await msg.delete()

    except Exception as e:
        print(e)

#voice note
@client.on(events.NewMessage(pattern='!a', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'record-voice'):
            origin_text = event.message.text.replace('!a ', '')
            voicename, _duration = speech.syntese(origin_text, background = True)

            chat = await event.get_chat()
            wafe_form = speech.get_waveform(0, 31, 100)
            await client.send_file(chat, voicename, reply_to = event.message.reply_to_msg_id, attributes=[types.DocumentAttributeAudio(duration=_duration, voice=True, waveform=utils.encode_waveform(bytes(wafe_form)))]) # 2**5 because 5-bit

            speech.try_delete(voicename)

    except Exception as e:
        print(e)

#video note
@client.on(events.NewMessage(pattern='!v', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'record-round'):
            # make sound
            origin_text = event.message.text.replace('!v ', '')
            voicename, _duration = speech.syntese(origin_text)

            # mount to video
            video_file = speech.mount_video(voicename)

            chat = await event.get_chat()
            await client.send_file(chat, video_file, reply_to = event.message.reply_to_msg_id, video_note=True)

            speech.try_delete(voicename)
            speech.try_delete(video_file)

    except Exception as e:
        print(e)

#demon voice note
@client.on(events.NewMessage(pattern='!d', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'record-voice'):
            origin_text = event.message.text.replace('!d ', '')
            voicename, _duration = speech.demon(origin_text)

            chat = await event.get_chat()
            wafe_form = speech.get_waveform(0, 31, 100)
            await client.send_file(chat, voicename, reply_to = event.message.reply_to_msg_id, attributes=[types.DocumentAttributeAudio(duration=_duration, voice=True, waveform=utils.encode_waveform(bytes(wafe_form)))]) # 2**5 because 5-bit

            speech.try_delete(voicename)

    except Exception as e:
        print(e)

#background voice note
@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    if event.voice:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'record-voice'):
            path_to_voice = await event.download_media()
            voicename, _duration = speech.megre_sounds(path_to_voice)

            chat = await event.get_chat()
            wafe_form = speech.get_waveform(0, 31, 100)
            await client.send_file(chat, voicename, reply_to = event.message.reply_to_msg_id, attributes=[types.DocumentAttributeAudio(duration=_duration, voice=True, waveform=utils.encode_waveform(bytes(wafe_form)))]) # 2**5 because 5-bit

            speech.try_delete(voicename)

#btc price
@client.on(events.NewMessage(pattern='(^btc$)|(^Btc$)|(^BTC$)', outgoing=True))
async def handler(event):
    try:
        btc_price = helpers.get_btc() 
        await event.edit(btc_price)

    except Exception as e:
        print(e)

#update bio
async def update_bio():
    while True:
        # delta = int((datetime.datetime(2020, 9, 17) - datetime.datetime.now()).total_seconds())
        # string = f'In {delta} seconds'

        string = helpers.get_life_progress()
        print(string)

        await client(UpdateProfileRequest(about=string))
        await asyncio.sleep(300)
        # https://github.com/gawel/aiocron CRON <====================================

try:
    print('(Press Ctrl+C to stop this)')
    loop = asyncio.get_event_loop()
    task = loop.create_task(update_bio())
    loop.run_until_complete(task)
    client.run_until_disconnected()
finally:
    client.disconnect()