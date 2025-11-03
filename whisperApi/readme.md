docker build -t whisper-api .

docker run -p 5000:5000 whisper-api

curl -X POST -F "file=@path_to_audio_file.ogg" http://localhost:5000/transcribe