FROM python:3.13 AS builder
WORKDIR /app
COPY install/requirements.txt install/requirements.txt
RUN pip3 install -r install/requirements.txt

FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY . .
CMD [ "python3", "refreshMetadataServive.py"]