FROM python:3.12-slim

WORKDIR /usr/src/app

RUN echo "precedence ::ffff:0:0/96  100" >> /etc/gai.conf

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .


CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]