from __future__ import print_function

from telethon import TelegramClient, events, types, utils
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights, User, Channel, Chat

import time

import speech
import os
import sys
import helpers
import asyncio
import datetime
import random
import re

import khaleesi

api_id = os.environ['TELETHON_API_ID']
api_hash = os.environ['TELETHON_API_HASH']

client = TelegramClient('session_name', api_id, api_hash)
client.start()

messages_cache = {}

# Help
@client.on(events.NewMessage(pattern='^!h$', outgoing=True))
async def help(event: events.NewMessage.Event):
    reply_text = f'**Kodzuthon help** `v1.12.5`\n\n' \
        '`scan [optional reply]` - scan message or chat,\n' \
        '`scans [optional reply]` - silently scan message or chat,\n' \
        '`scraps (chat)` - silently scrap all members to .csv,\n' \
        '`ppo [optional reply]` - PPO map,\n' \
        '`gum [reply]` - insert emojis,\n' \
        '`cum [reply]` - khaleese message,\n' \
        '`tr [reply]` - translate message,\n' \
        '`tr {text or [reply]}` - translate to latin,\n' \
        '`!w` - get weather,\n' \
        '`!s {search text}` - google text,\n' \
        '`!t` - imitation typing for 5 minutes,\n' \
        '`year` - year info,\n' \
        '`covg` - covid chart info,\n' \
        '`sat` - image from satellite,\n' \
        '`!m {20} {m/h/d}` - mute someone for {20} {m} - minutes,\n' \
        '`🦔` - nice cartoon,\n' \
        '`loading` - loading animation,\n' \
        '`!f {text}` - print text animation,\n' \
        '`!a {text or [reply]}` - generate speech,\n' \
        '`!v {text or [reply]}` - video speech,\n' \
        '`!d {text or [reply]}` - demon speech,\n' \
        '`хня [optional reply]` - bredor video,\n' \
        '`ніх [optional reply]` - damn video,\n' \
        '`!yf {ticker name}` - ticker report,\n' \
        '`curr` - currencies report,\n' \
        '`btc` - bitcoin stock price.\n' \
        '`cr {optional btc}` - bitcoin stock report.\n' \
        '`!lk {emoji} {count} [reply]` - reaction messages attack,\n\n' \
        '[github](https://github.com/awitwicki/kodzu_thon)'

    await event.edit(reply_text)

# Like all user messages
@client.on(events.NewMessage(pattern='^!lk', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        reply_to_message = await event.get_reply_message()

        if not reply_to_message:
            await event.delete()
            return

        params = event.message.text.split()
        emoji = params[1]
        count = int(params[2])

        avaliable_emojis = "💩👍👎🔥🥰👏😁🤔🤯🤬😱😢🤩🤮🎉❤️"

        if emoji not in avaliable_emojis :
            await event.edit(avaliable_emojis)
            return

        await event.edit("...")
        i = 0

        async for message in client.iter_messages(chat, from_user=reply_to_message.sender):
            try:
                reactions = message.reactions
                if reactions and any(x.reaction == emoji for x in reactions.results):
                    continue

                await client.send_reaction(chat, message, emoji)

                if i > count:
                    break
                i += 1

            except Exception as e:
                print(e, file=sys.stderr)

        await event.delete()
        # await event.edit(f"Накидано {count} {emoji}")

    except Exception as e:
        await event.edit('Fail')
        print(e, file=sys.stderr)


# UserId
@client.on(events.NewMessage(pattern='^scans$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    reply_text = await helpers.build_message_chat_info(event, client)
    await event.delete()
    await client.send_message('me', reply_text)


# Chatid
@client.on(events.NewMessage(pattern='^scan$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    reply_text = await helpers.build_message_chat_info(event, client)
    await event.edit(reply_text)


@client.on(events.NewMessage(pattern='^scraps$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    await event.delete()
    msg = await client.send_message('me', 'Scrapping...')
    is_success, csv_path_or_error = await helpers.scrap_chat_users(event, client)
    if is_success:
        await msg.delete()
        await client.send_file('me', csv_path_or_error, caption=csv_path_or_error)
        os.remove('csv_path')
    else:
        await msg.edit(csv_path_or_error)


# PPO map
@client.on(events.NewMessage(pattern='^ppo$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.edit("Loading...")

        img_name, state_dict = helpers.make_alarm_map()

        text='Повітряна тривога в областях:\n\n'

        for district_name in state_dict.keys():
            if state_dict[district_name]:
                text += f'{district_name} ⚠️\n'

        text += '\nair-save.ops.ajax.systems'

        await event.delete()
        await client.send_file(chat, img_name, caption=text, reply_to=event.message.reply_to_msg_id)

    except Exception as e:
        await event.edit('Fail')
        print(e, file=sys.stderr)


# Break message
@client.on(events.NewMessage(pattern='^gum$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    if event.message.is_reply:
        msg = await event.message.get_reply_message()
        reply_text = helpers.break_text(msg.text)
        await event.edit(reply_text)


# Khaleesi message
@client.on(events.NewMessage(pattern='^cum$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    if event.message.is_reply:
        msg = await event.message.get_reply_message()
        reply_text = khaleesi.Khaleesi.khaleesi(msg.text)
        await event.edit(reply_text)


# Translate message
@client.on(events.NewMessage(pattern=re.compile(r'^tr$', re.IGNORECASE), outgoing=True))
async def handler(event: events.NewMessage.Event):
    if event.message.is_reply:
        msg = await event.message.get_reply_message()
        await event.edit('Translating...')
        reply_text = helpers.translate_text(msg.message)
        await event.edit(reply_text)


# Translate message latin
@client.on(events.NewMessage(pattern='^trl', outgoing=True))
async def handler(event: events.NewMessage.Event):
    msg_text = (await event.message.get_reply_message()).text if event.message.is_reply else event.message.text.replace('trl', '').strip()
    await event.edit('👹')
    reply_text = helpers.translate_text(msg_text, dest='la', silent_mode=True)
    await event.edit(reply_text)


# Search text
@client.on(events.NewMessage(pattern='^!s', outgoing=True))
async def handler(event: events.NewMessage.Event):
    origin_text = event.message.text.replace('!s', '').strip()
    await event.edit('Googling...')
    reply_text = helpers.google_search(origin_text)
    await event.edit(reply_text, link_preview = True)


# Send typing
@client.on(events.NewMessage(pattern='^!t$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'typing'):
            await asyncio.sleep(300)
            pass

    except Exception as e:
        print(e, file=sys.stderr)


# Weather
@client.on(events.NewMessage(pattern='^!w$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    weather = helpers.get_weather()
    await event.edit(weather)


# Year progress
@client.on(events.NewMessage(pattern='^year$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        text = "Year progress:\n"
        text += helpers.get_year_progress(30)
        await event.edit(f'`{text}`')

    except Exception as e:
        print(e, file=sys.stderr)


# Covid
@client.on(events.NewMessage(pattern='^covg$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.edit("Loading...")
        img_name = helpers.covid_graph()
        await event.delete()
        cov = helpers.get_covid()
        await client.send_file(chat, img_name, caption=cov)

    except Exception as e:
        print(e, file=sys.stderr)


# Satellite image
@client.on(events.NewMessage(pattern='^sat$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.edit("Loading...")
        img_name = helpers.get_sat_img()
        await event.delete()
        await client.send_file(chat, img_name)

    except Exception as e:
        print(e, file=sys.stderr)


# Removed message
@client.on(events.MessageDeleted())
async def handler(event: events.MessageDeleted.Event):
    try:
        chat_id = int(f'{event.chat_id}'[4:])
        _message_id = event._message_id

        # Try find message in cache
        chat = messages_cache.get(chat_id)
        if chat:
            msg = chat['messages'].get(_message_id)
            if msg:
                message_text = msg["text"]
                print(f'deleted message {_message_id} in chat {chat_id}, user: {msg["sender_id"]} {msg["sender_name"]}, text: {msg["text"]}', file=sys.stderr)
                helpers.influx_query(f'bots,botname=kodzuthon,chatname={msg["chat_title"]},chat_id={chat_id},user_id={msg["sender_id"]},user_name={msg["sender_name"]},message_type=deleted_text_message deleted_message_text=\"{message_text}\"')

    except Exception as e:
        print(e, file=sys.stderr)


# Autoresponder
@client.on(events.NewMessage(incoming=True))
async def handler(event: events.NewMessage.Event):
    chat = event.chat if event.chat else (await event.get_chat()) # telegram MAY not send the chat enity

    if event.is_private and event.voice:
        reply_text = 'Голосове повідомлення не доставлено, бо користувач заблокував цю опцію. Це повідомлення надіслано автоматично.'
        await client.send_message(chat, reply_text, reply_to = event.message.id)

    if event.is_group:
        try:
            msg = event.message
            chat_title = chat.title.replace('\\', '\\\\').replace(' ', '\ ').replace('=', '\=')

            user_name = '@' + msg.sender.username if msg.sender.username else msg.sender.username
            full_name = 'unknown'

            if type(msg.sender) is User:
                user: User = msg.sender
                first_name = user.first_name if user.first_name else ''
                last_name = user.last_name if user.last_name else ''

                full_name = ' '.join([first_name, last_name])

            if type(msg.sender) is Channel:
                channel: Channel = msg.sender
                full_name = channel.title

            if type(msg.sender) is Chat:
                chat: Chat = msg.sender
                full_name = chat.title


            user_name = user_name if user_name else full_name
            user_name = user_name.strip().replace('\\', '\\\\').replace(' ', '\ ').replace('=', '\=')

            chat_id = chat.id
            user_id = msg.sender.id
            helpers.influx_query(f'bots,botname=kodzuthon,chatname={chat_title},chat_id={chat_id},user_id={user_id},user_name={user_name} income_messages=1')

            # Add to messages cache
            # If sender is not bot
            if msg.text and not msg.sender.bot:
                cached_message = {
                    'message_id': msg.id,
                    'chat_id': chat_id,
                    'sender_id': user_id,
                    'sender_name': user_name,
                    'chat_title': chat_title,
                    'text': msg.text.replace('\\', '\\\\').replace('"', '\\"')
                }

                cached_chat = {
                    'chat_id': chat_id,
                    'chat_title': user_name if event.is_private else chat_title,
                    'messages': {}
                }

                # Create new chat entity
                if not chat_id in messages_cache.keys():
                    messages_cache[chat_id] = cached_chat

                # Append message
                messages_cache[chat_id]['messages'][msg.id] = cached_message

        except Exception as e:
            print(e, file=sys.stderr)


# Mute user
@client.on(events.NewMessage(pattern=r'^!m', outgoing=True))
async def handler(event: events.NewMessage.Event):
    chat = await event.get_chat()
    reply_to_message = await event.get_reply_message()

    if not reply_to_message:
        await event.delete()
        return

    time_flags_dict = {
        "m": [60, "minuts"],
        "h": [3600, "ours"],
        "d": [86400, "deys"]
        }

    try:
        #m or h or d
        time_type = event.message.text[-1]

        #get number
        count = int(event.message.text.split()[1][:-1])

        #convert to seconds
        count_seconds = count * time_flags_dict[time_type][0]

        rights = ChatBannedRights(
            until_date=datetime.datetime.utcnow() + datetime.timedelta(seconds=count_seconds),
            send_messages=True
        )

        await client(EditBannedRequest(chat.id, reply_to_message.sender_id, rights))
        await event.edit(f'Muted for {count} {time_flags_dict[time_type][1]}')

    except Exception as e:
        print(e, file=sys.stderr)


# 🦔🍎
@client.on(events.NewMessage(pattern='^🦔$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    for i in range(19):
        await event.edit('🍎'*(18 - i) + '🦔')
        await asyncio.sleep(.5)


# Loading
@client.on(events.NewMessage(pattern='^loading$', outgoing=True))
async def handler(event: events.NewMessage.Event):
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
        print(e, file=sys.stderr)


# Print citate
@client.on(events.NewMessage(pattern='^!f', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        origin_text = event.message.text.replace('!f ', '')
        for i in range(len(origin_text)):
            if origin_text[i] == " ": continue
            await event.edit(origin_text[:i+1])
            await asyncio.sleep(.1)

    except Exception as e:
        print(e, file=sys.stderr)


# Voice note
@client.on(events.NewMessage(pattern='^!a', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'record-voice'):
            origin_text = event.message.text.replace('!a', '').strip()

            if event.message.is_reply and origin_text == '':
                msg = await event.message.get_reply_message()
                origin_text = msg.text

            voicename, _duration = speech.syntese(origin_text, background = True)

            wafe_form = speech.get_waveform(0, 31, 100)
            await client.send_file(chat, voicename, reply_to = event.message.reply_to_msg_id, attributes=[types.DocumentAttributeAudio(duration=_duration, voice=True, waveform=utils.encode_waveform(bytes(wafe_form)))]) # 2**5 because 5-bit

            speech.try_delete(voicename)

    except Exception as e:
        print(e, file=sys.stderr)


# Video note
@client.on(events.NewMessage(pattern='^!v', outgoing=True))
async def handler(event: events.NewMessage.Event):
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
        print(e, file=sys.stderr)


# Video "same shit"
@client.on(events.NewMessage(pattern='^хня$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'record-round'):
            chat = await event.get_chat()
            await client.send_file(chat, 'media/same.mp4', reply_to=event.message.reply_to_msg_id, video_note=True)

    except Exception as e:
        print(e, file=sys.stderr)


# Video "damn"
@client.on(events.NewMessage(pattern='^ніх$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'record-round'):
            chat = await event.get_chat()
            await client.send_file(chat, 'media/nih.mp4', reply_to=event.message.reply_to_msg_id, video_note=True)

    except Exception as e:
        print(e, file=sys.stderr)


# Demon voice note
@client.on(events.NewMessage(pattern='^!d', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.delete()
        async with client.action(chat, 'record-voice'):
            origin_text = event.message.text.replace('!d ', '')
            voicename, _duration = speech.demon(origin_text)

            wafe_form = speech.get_waveform(0, 31, 100)
            await client.send_file(chat, voicename, reply_to = event.message.reply_to_msg_id, attributes=[types.DocumentAttributeAudio(duration=_duration, voice=True, waveform=utils.encode_waveform(bytes(wafe_form)))]) # 2**5 because 5-bit

            speech.try_delete(voicename)

    except Exception as e:
        print(e, file=sys.stderr)


# Background voice note
@client.on(events.NewMessage(outgoing=True, forwards=False))
async def handler(event: events.NewMessage.Event):
    if event.voice:
        event_media_date = event.message.file.media.date
        datenow = datetime.datetime.now(event_media_date.tzinfo)
        if (datenow - event_media_date).seconds < 60:
            chat = await event.get_chat()
            await event.delete()
            async with client.action(chat, 'record-voice'):
                path_to_voice = await event.download_media()
                voicename, _duration = speech.megre_sounds(path_to_voice)

                wafe_form = speech.get_waveform(0, 31, 100)
                await client.send_file(chat, voicename, reply_to = event.message.reply_to_msg_id, attributes=[types.DocumentAttributeAudio(duration=_duration, voice=True, waveform=utils.encode_waveform(bytes(wafe_form)))]) # 2**5 because 5-bit

                speech.try_delete(voicename)


# btc price
@client.on(events.NewMessage(pattern='(?i)(^btc$)', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        btc_price = helpers.get_btc()
        await event.edit(btc_price)

    except Exception as e:
        print(e, file=sys.stderr)


# Crypto report
# Not works
@client.on(events.NewMessage(pattern='^cr', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.edit("Not works")
        return

        await event.edit("Loading...")

        args = event.message.text.split()
        if len(args) > 1:
            currency_name = args[1].upper()
        else:
            currency_name = 'BTC'

        img_name, actual_currency, percent_growth = helpers.make_crypto_report(currency_name)

        text = f'**{currency_name}** `{actual_currency:.2f} USD ({percent_growth:.2f}%)`'

        await event.delete()
        await client.send_file(chat, img_name, caption=text)

    except Exception as e:
        await event.edit('Fail')
        print(e, file=sys.stderr)


# Ticker info report
@client.on(events.NewMessage(pattern='^yf', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.edit("Loading...")

        ticker_name = event.message.text.replace('yf', '').strip()
        text, img_name = helpers.make_ticker_report(ticker_name)

        await event.delete()
        await client.send_file(chat, img_name, caption=text)

    except Exception as e:
        await event.edit('Fail')
        print(e, file=sys.stderr)


# Currencies info report
@client.on(events.NewMessage(pattern='^curr$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        chat = await event.get_chat()
        await event.edit("Loading...")

        img_name, text = helpers.make_currency_report()

        text = f'**Currencies for last 30 days:**\n\n{text}'

        await event.delete()
        await client.send_file(chat, img_name, caption=text)

    except Exception as e:
        print(e, file=sys.stderr)
        await event.edit('Fail')


# Update bio
async def update_bio():
    while True:
        new_about = helpers.get_year_progress()
        # raw_temp = await helpers.get_raw_temp()
        new_lastname = f'{helpers.two_hundred_count():.2f}'

        print(f'Update info for {new_lastname} - {new_about}')
        await client(UpdateProfileRequest(about=new_about))
        await client(UpdateProfileRequest(about=new_about, last_name=new_lastname))

        # helpers.get_upload_temp_data(raw_temp)
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