FROM python:3.9-buster
WORKDIR /app

# Install ffmpeg
RUN apt-get -y update
RUN apt-get install -y ffmpeg

# Prepare for install kaleido
RUN apt install -y libnss3-dev libgdk-pixbuf2.0-dev libgtk-3-dev libxss-dev

# Install python requirements
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["python"]
CMD ["main.py"]
