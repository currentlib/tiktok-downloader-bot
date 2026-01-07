FROM python:3.13.9

WORKDIR /usr/src/app

COPY . .

RUN pip install -r req.txt

CMD ["python", "-u", "./index.py"]