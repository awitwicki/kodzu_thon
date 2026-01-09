from __future__ import print_function
import requests

from telethon import TelegramClient, events, types, utils
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import SendReactionRequest
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
import google.generativeai as genai

KODZIUTHON_VERSION = 'v1.17'

whisper_api_url = "http://localhost:4999/transcribe"

api_id = os.environ['TELETHON_API_ID']
api_hash = os.environ['TELETHON_API_HASH']

client = TelegramClient('session_data/session_name', api_id, api_hash)
client.start()

messages_cache = {}

# Help
@client.on(events.NewMessage(pattern='^!h$', outgoing=True))
async def help(event: events.NewMessage.Event):
    reply_text = f'**Kodzuthon help** `{KODZIUTHON_VERSION}`\n\n' \
        '`scan [optional reply]` - scan message or chat,\n' \
        '`scans [optional reply]` - silently scan message or chat,\n' \
        '`scraps (chat)` - silently scrap all members to .csv,\n' \
        '`ppo [optional reply]` - PPO map,\n' \
        '`gum [reply]` - insert emojis,\n' \
        '`cum [reply]` - khaleese message,\n' \
        '`tr [reply]` - translate message, OR transcrybe voice or video note\n' \
        '`trl {text or [reply]}` - translate to latin,\n' \
        '`!s {search text}` - google text,\n' \
        '`!t` - imitation typing for 5 minutes,\n' \
        '`year` - year info,\n' \
        '`!m {20} {m/h/d}` - mute someone for {20} {m} - minutes,\n' \
        '`🦔` - nice cartoon,\n' \
        '`loading` - loading animation,\n' \
        '`!f {text}` - print text animation,\n' \
        '`!a {text or [reply]}` - generate speech,\n' \
        '`!v {text or [reply]}` - video speech,\n' \
        '`!d {text or [reply]}` - demon speech,\n' \
        '`хня [optional reply]` - bredor video,\n' \
        '`ніх [optional reply]` - damn video,\n' \
        '`curr` - currencies report,\n' \
        '`btc` - bitcoin stock price.\n' \
        '`!lk {emoji} {count} [reply]` - reaction messages attack,\n' \
        '`ai {prompt}` - ask Gemini AI\n' \
        '`summ [reply]` - summarize messages from replied to newest\n\n' \
        '[github](https://github.com/awitwicki/kodzu_thon)'

    await event.edit(reply_text)


# AI with Gemini
@client.on(events.NewMessage(pattern='^ai ', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        # Extract prompt from message
        prompt = event.message.text.replace('ai ', '', 1).strip()
        
        if not prompt:
            await event.edit('Please provide a prompt')
            return
        
        # Show loading message
        await event.edit(f'Loading...')
        
        # Get API key from environment
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            await event.edit(f'ai {prompt}\nError: GEMINI_API_KEY not set in environment')
            return
        
        # Initialize Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        result = response.text
        
        # Edit message with result
        await event.edit(result)
        
    except Exception as e:
        await event.edit(f'Error: {str(e)}')
        print(e, file=sys.stderr)


# Summarize messages from a point
@client.on(events.NewMessage(pattern='^summ$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        if not event.message.is_reply:
            await event.edit('Reply to a message to summarize from')
            return
        
        chat = await event.get_chat()
        reply_to_message = await event.message.get_reply_message()
        
        await event.edit('Collecting messages...')
        
        # Collect all messages from replied message to newest
        messages_text = []
        message_count = 0
        max_messages = 1000
        
        async for message in client.iter_messages(chat, min_id=reply_to_message.id - 1):
            if message_count >= max_messages:
                break
            
            # Get text or caption
            text = message.text if message.text else None
            if text:
                messages_text.append(text)
                message_count += 1
        
        if not messages_text:
            await event.edit('No messages found to summarize')
            return
        
        await event.edit(f'Summarizing {message_count} messages...')
        
        messages_text.reverse()

        # Combine all messages
        combined_text = '\n---\n'.join(messages_text)
        
        # Prepare prompt for Gemini
        prompt = f'Please provide a concise brief summary of the following messages in ukrainian language:\n\n{combined_text}'
        
        # Get API key from environment
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            await event.edit('Error: GEMINI_API_KEY not set in environment')
            return
        
        # Initialize Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        result = response.text
        
        # Edit message with result
        summary_text = f'**Summary ({message_count} messages):**\n\n{result}'
        await event.edit(summary_text)
        
    except Exception as e:
        await event.edit(f'Error: {str(e)}')
        print(e, file=sys.stderr)


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

        available_emojis = "💩👍👎🔥🥰👏😁🤔🤯🤬😱😢🤩🤮🎉❤️"

        if emoji not in available_emojis :
            await event.edit(available_emojis)
            return

        if count > 1000:
            await event.edit('Too much messages')
            return

        await event.edit("...")
        i = 0

        async for message in client.iter_messages(chat, from_user=reply_to_message.sender):
            if i > count:
                break
            i += 1

            try:
                reactions = message.reactions
                if reactions and any(x.reaction == emoji for x in reactions.results):
                    continue

                await client(SendReactionRequest(
                    peer=chat,
                    msg_id=message.id,
                    reaction=[types.ReactionEmoji(
                        emoticon=emoji
                    )]
                ))

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
        helpers.remove_file(csv_path_or_error)
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
        helpers.remove_file(img_name)

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
        # If message is text
        msg = await event.message.get_reply_message()
        if msg.text:
            await event.edit('Translating...')
            reply_text = await helpers.translate_text(msg.message)
            await event.edit(reply_text)
        # If message is voice or video note
        if msg.voice or msg.video_note:
            await event.edit('Transcrybing...')

            try:
                file_path = await msg.download_media()

                with open(file_path, "rb") as file:
                    files = {"file": file}
                    response = requests.post(whisper_api_url, files=files)

                os.remove(file_path)

                if response.status_code == 200:
                    print("Transcrybed text:")
                    reply_text = response.json().get("text")
                    print(reply_text)
                    await event.edit(reply_text)
                else:
                    print(f"Transcrybing error: {response.status_code}")
                    print(response.json())
                    await event.edit(response.json())
            except Exception as e:
                print(f"Transcrybing error: {e}")
                await event.edit(f"Transcrybing error: {e}")


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

    except Exception as e:
        print(e, file=sys.stderr)


# Year progress
@client.on(events.NewMessage(pattern='^year$', outgoing=True))
async def handler(event: events.NewMessage.Event):
    try:
        text = "Year progress:\n"
        text += helpers.get_year_progress(30)
        await event.edit(f'`{text}`')

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

                tags_dict = {
                    "botname": "kodzuthon",
                    "chatname": msg["chat_title"],
                    "chat_id": chat_id,
                    "user_id": msg["sender_id"],
                    "user_name": msg["sender_name"],
                    "message_type": "deleted_text_message"
                }

                fields_dict = {
                    "deleted_message_text": message_text
                }

                helpers.influx_query(tags_dict, fields_dict)

    except Exception as e:
        print(e, file=sys.stderr)


# Autoresponder
@client.on(events.NewMessage(incoming=True))
async def handler_autoresponder(event: events.NewMessage.Event):
    chat = event.chat if event.chat else (await event.get_chat()) # telegram MAY not send the chat enity

    if event.is_private and event.voice:
        reply_text = 'Голосове повідомлення не доставлено, бо користувач заблокував цю опцію. Це повідомлення надіслано автоматично.'
        await client.send_message(chat, reply_text, reply_to = event.message.id)

    if event.is_group:
        try:
            msg = event.message

            chat_title = chat.title
            chat_id = chat.id
            user_id = None
            user_name = None
            full_name = 'unknown'

            if type(msg.sender) is User:
                user: User = msg.sender

                if user.username:
                    user_name = '@' + user.username

                first_name = user.first_name if user.first_name else ''
                last_name = user.last_name if user.last_name else ''

                full_name = ' '.join([first_name, last_name])

                user_id = user.id

            if type(msg.sender) is Channel:
                channel: Channel = msg.sender
                full_name = channel.title
                user_id = channel.id

            if type(msg.sender) is Chat:
                chat: Chat = msg.sender
                full_name = chat.title
                user_id = chat.id

            if (msg.is_channel or msg.is_group) and not user_id:
                user_id = chat_id
                user_name = chat_title

            user_name = user_name if user_name else full_name


            tags_dict = {
                "botname": "kodzuthon",
                "chatname": chat_title,
                "chat_id": chat_id,
                "user_id": user_id,
                "user_name": user_name,
            }

            fields_dict = {
                "income_messages": 1.0
            }

            helpers.influx_query(tags_dict, fields_dict)

            # Add to messages cache
            # If sender is not bot
            if msg.text and not msg.sender.bot:
                cached_message = {
                    'message_id': msg.id,
                    'chat_id': chat_id,
                    'sender_id': user_id,
                    'sender_name': user_name,
                    'chat_title': chat_title,
                    'text': msg.text
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
        helpers.remove_file(img_name)

    except Exception as e:
        print(e, file=sys.stderr)
        await event.edit('Fail')


# Update bio
async def update_bio():
    while True:
        new_about = helpers.get_year_progress()
        new_lastname = f'{helpers.two_hundred_count():.2f}'

        print(f'Update info for {new_lastname} - {new_about}')
        await client(UpdateProfileRequest(about=new_about))
        await client(UpdateProfileRequest(about=new_about, last_name=new_lastname))

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
