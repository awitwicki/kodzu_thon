FROM python:buster
WORKDIR /app
RUN apt-get -y update
RUN apt-get install -y ffmpeg
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
ENTRYPOINT ["python"]
CMD ["main.py"]
