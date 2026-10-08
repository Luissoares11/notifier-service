FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py store.py rules.py deliver.py main.py ./

EXPOSE 8030
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8030"]