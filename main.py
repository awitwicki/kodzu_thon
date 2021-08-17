from telethon import TelegramClient, events, sync, types, utils, functions
from telethon.client import messages
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import Chat, ChatBannedRights

import urllib.request, json
import time

from telethon.tl.types import Message
import speech
import os
from collections import deque
import helpers
import asyncio
import datetime
import random

import khaleesi

api_id = os.environ['TELETHON_API_ID']
api_hash = os.environ['TELETHON_API_HASH']

client = TelegramClient('session_name', api_id, api_hash)
client.start()

#userId
@client.on(events.NewMessage(pattern='(^!id$)', outgoing=True))
async def handler(event):
    if event.message.is_reply:
        chat = await event.get_chat()
        msg = await event.message.get_reply_message()
        reply_text = f'id: {msg.sender.id}, name: {msg.sender.first_name}, chat id: {chat.id}'
        await client.send_message('me', reply_text)
    await event.delete()


#chatid
@client.on(events.NewMessage(pattern='(^info$)', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        msg = await event.message.get_reply_message()
        await event.edit(f'ChatId: {chat.id}')

    except Exception as e:
        print(e)


#break message
@client.on(events.NewMessage(pattern='(^gum$)', outgoing=True))
async def handler(event):
    if event.message.is_reply:
        msg = await event.message.get_reply_message()
        reply_text = helpers.break_text(msg.text)
        await event.edit(reply_text)


#khaleesi message
@client.on(events.NewMessage(pattern='(^cum$)', outgoing=True))
async def handler(event):
    if event.message.is_reply:
        msg = await event.message.get_reply_message()
        reply_text = khaleesi.Khaleesi.khaleesi(msg.text)
        await event.edit(reply_text)


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


#covid
@client.on(events.NewMessage(pattern='(^cov$)', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        await event.edit("Loading...")
        cov = helpers.get_covid()
        await event.edit(cov)

    except Exception as e:
        print(e)


#otmazka
@client.on(events.NewMessage(pattern='(^ot$)', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        otm = helpers.random_otmazka()
        await event.edit(otm)

    except Exception as e:
        print(e)


#year progress
@client.on(events.NewMessage(pattern='(^year$)', outgoing=True))
async def handler(event):
    try:
        text = "2021 year progress:\n"
        text += helpers.get_year_progress(30)
        await event.edit(f'`{text}`')

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


#satelite image
@client.on(events.NewMessage(pattern='(^sat$)', outgoing=True))
async def handler(event):
    try:
        chat = await event.get_chat()
        await event.edit("Loading...")
        img_name = helpers.get_sat_img()
        await event.delete()
        await client.send_file(chat, img_name)

    except Exception as e:
        print(e)


#autoresponder
@client.on(events.NewMessage(incoming=True))
async def handler(event: events.NewMessage.Event):
    chat = event.chat if event.chat else (await event.get_chat()) # telegram MAY not send the chat enity

    if event.is_group:
        chat_title = chat.title.replace(' ', '\ ').replace('=', '\=')
        chat_id = chat.id
        helpers.influx_query(f'bots,botname=kodzuthon,chatname={chat_title},chat_id={chat_id} imcome_messages=1')

    if event.is_private:
        # helpers.influx_query('bots,chatname=privmessages,messagetype=incoming call=true')

        if event.voice:
            reply_text = 'Голосовое сообщение не доставлено так как пользователь заблокировал эту опцию. Это сообщение написано автоматически.'
            await client.send_message(chat, reply_text, reply_to = event.message.id)


#mute user
#TODO test
@client.on(events.NewMessage(pattern=r'!m', outgoing=True))
async def handler(event):
    chat = await event.get_chat()
    reply_to_message = await event.get_reply_message()

    if not reply_to_message:
        await event.delete()
        return

    time_flags_dict = {"m": [60, "minuts"], "h": [3600, "ours"], "d": [86400, "deys"]}
    try:
        #m or h or d
        time_type = event.message.text[-1]

        #get number
        count = int(event.message.text.split()[1][:-1])
        #convert to seconds
        count_seconds = count * time_flags_dict[time_type][0]

        rights = ChatBannedRights(
            until_date=datetime.datetime.now() + datetime.timedelta(seconds=count_seconds),
            send_messages=True
        )

        await client(EditBannedRequest(chat.id, reply_to_message.sender_id, rights))
        await event.edit(f'Muted for {count} {time_flags_dict[time_type][1]}')

    except Exception as e:
        print(e)


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
    for i in range(19):
        await event.edit('🍎'*(18 - i) + '🦔')
        await asyncio.sleep(.5)


#Loading
@client.on(events.NewMessage(pattern='loading', outgoing=True))
async def handler(event):
    try:
        percentage = 0
        while percentage < 100:
            temp = 100 - percentage
            temp = temp if temp > 5 else 5
            percentage += temp / random.randint(5, 10)
            percentage = round(percentage, 2)
            # if percentage > 100: percentage = 100
            progress = int(percentage // 5)
            await event.edit(f'`|{"█" * progress}{"-" * (20 - progress)}| {percentage}%`')
            await asyncio.sleep(.5)

        time.sleep(5)
        await event.delete()

    except Exception as e:
        print(e)


#print citate
@client.on(events.NewMessage(pattern='!f', outgoing=True))
async def handler(event):
    try:
        origin_text = event.message.text.replace('!f ', '')
        for i in range(len(origin_text)):
            if origin_text[i] == " ": continue
            await event.edit(origin_text[:i+1])
            await asyncio.sleep(.1)

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
            voicename, _duration = speech.syntese(origin_text, background = True)

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
        new_about = helpers.get_year_progress()
        raw_temp = helpers.get_raw_temp()
        new_lastname = helpers.get_temp(raw_temp)

        print(f'Update info for {new_lastname} - {new_about}')
        await client(UpdateProfileRequest(about=new_about))
        await client(UpdateProfileRequest(about=new_about, last_name=new_lastname))

        helpers.get_upload_temp_data(raw_temp)
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