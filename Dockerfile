FROM python:3.13.9

WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install -r req.txt

CMD ["python", "-u", "./index.py"]