# Use an official Python base image
FROM python:3.11-slim

WORKDIR /youtube-noti-app

COPY requirements.txt . 

RUN pip install -r requirements.txt

COPY assets/ ./assets/
COPY *.py .
COPY .env .env