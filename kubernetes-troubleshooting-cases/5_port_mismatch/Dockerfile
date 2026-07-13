FROM python:3.9-slim

WORKDIR /app

RUN pip install flask

COPY server.py /app

# WRONG: Should be 5000
EXPOSE 8080

CMD ["python", "server.py"]
