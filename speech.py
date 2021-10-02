import os, sys, time, datetime, random
from gtts import gTTS



def try_delete(filename):
    try:
        print(f'removing {filename}')
        os.remove(filename)
    except Exception as e:
        print(f'e')


def get_waveform(_min, _max, count):
    return [random.randrange(_min, _max, 1) for _ in range(count)]


def syntese(input_text, background = False, frequency = 1):
    obj = gTTS(input_text, lang='ru')

    # new_file name
    mp3_file_name = 'media/temp' + datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S') + '.mp3'

    # save voice to file
    obj.save(mp3_file_name)

    return_filename = ''

    #convert to ogg
    ogg_file_name = mp3_file_name.replace('.mp3', '.ogg')
    # os.system(f"ffmpeg.exe -i {mp3_file_name} -filter:a \"volume=13dB\" -c:a libvorbis -q:a 4 {ogg_file_name}")

    freq_params = f'asetrate=22050*{frequency},aresample=22050,atempo=1/{frequency},' if frequency != 1 else ''

    os.system(f"ffmpeg -i {mp3_file_name} -af {freq_params}volume=13dB -c:a libopus -b:a 96K {ogg_file_name}")

    # .\ffmpeg.exe -i test.mp3 -af asetrate=22050*0.6,aresample=22050,atempo=1/0.6,volume=13dB -c:a libvorbis tst11.ogg

    return_filename = ogg_file_name

    if background:
        #merge
        new_ogg_file_name = ogg_file_name.replace('ogg', '_merged.ogg')
        os.system(f'ffmpeg -filter_complex "amovie={ogg_file_name} [a0]; amovie=media/r.ogg [a1]; [a0][a1] amix=inputs=2:duration=shortest [aout]" -map [aout] -acodec libopus -b:a 96K {new_ogg_file_name}')
        return_filename = new_ogg_file_name

        try_delete(ogg_file_name)

    try_delete(mp3_file_name)

    #get duration
    duration = int(os.popen(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {return_filename}').read().split('.')[0])
    return return_filename, duration


def demon(input_text, background = False):
    obj = gTTS(input_text, lang='ru')

    # new_file name
    mp3_file_name = 'media/temp' + datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S') + '.mp3'

    # save voice to file
    obj.save(mp3_file_name)

    return_filename = ''

    #convert to ogg
    ogg_file_name = mp3_file_name.replace('.mp3', '.ogg')

    os.system(f"ffmpeg -i {mp3_file_name} -af volume=0dB -c:a libvorbis -q:a 4 {ogg_file_name}")
    # os.system(f"ffmpeg.exe -i {mp3_file_name} -af volume=13dB -c:a libvorbis -q:a 4 {ogg_file_name}")

    return_filename = ogg_file_name

    frequencies = [0.25, 0.75, 0.90, 1.05]
    soundnames = []

    for freq in frequencies:
        soundname = ogg_file_name.replace('.ogg', f'_freq{freq}.ogg')
        freq_params = f'asetrate=24000*{freq},aresample=24000,atempo=1/{freq}'

        runstring = f"ffmpeg -i {return_filename} -af {freq_params} -c:a libvorbis -q:a 4 {soundname}"
        print(runstring)
        os.system(runstring)
        soundnames.append(soundname)

    deletesoundnames = []
    # merged_queue = ogg_file_name
    for index, soundname in enumerate(soundnames):
        temp_name = ogg_file_name.replace('.ogg', f'_merged_{index}.ogg')
        os.system(f'ffmpeg -filter_complex "amovie={return_filename} [a0]; amovie={soundname} [a1]; [a0][a1] amix=inputs=2:duration=shortest [aout]" -map [aout] -acodec libvorbis {temp_name}')
        return_filename = temp_name
        deletesoundnames.append(temp_name)

    try_delete(ogg_file_name)
    for soundname in soundnames + deletesoundnames:
        if soundname != return_filename:
            try_delete(soundname)

    try_delete(mp3_file_name)

    #get duration
    duration = int(os.popen(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {return_filename}').read().split('.')[0])
    return return_filename, duration


def mount_video(sound_file):
    video_file = 'media/diesel.mp4'

    #new video file
    new_video_file = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S') + '.mp4'
    print(new_video_file)

    #mount sound
    os.system(f"ffmpeg -i {video_file} -i {sound_file} -c:v copy -map 0:v:0 -map 1:a:0 -shortest {new_video_file}")

    return new_video_file


def megre_sounds(audio_file):
    # testing
    new_name = "new_" + audio_file

    #merge
    os.system(f'ffmpeg -filter_complex "amovie={audio_file} [a0]; amovie=media/r.ogg [a1]; [a0][a1] amix=inputs=2:duration=shortest [aout]" -map [aout] -acodec libvorbis {new_name}')

    os.remove(audio_file)

    #get duration
    duration = int(os.popen(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {new_name}').read().split('.')[0])
    return new_name, duration
