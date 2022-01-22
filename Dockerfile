FROM python:3.9-buster
WORKDIR /app

# Install ffmpeg
RUN apt-get -y update
RUN apt-get install -y ffmpeg

# Install python requirements
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["python"]
CMD ["main.py"]
