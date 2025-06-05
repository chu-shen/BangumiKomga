ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION} AS builder
WORKDIR /app
COPY install/requirements.txt install/requirements.txt
RUN pip3 install -r install/requirements.txt

FROM python:${PYTHON_VERSION}-slim
ARG PYTHON_VERSION
WORKDIR /app
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages
COPY . .
CMD [ "python3", "main.py"]