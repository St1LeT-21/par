FROM python:3.12-slim

WORKDIR /usr/scr/app

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./ .

RUN chmod +x ./start