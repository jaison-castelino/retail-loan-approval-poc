FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LOAN_DB=/data/loan_demo.db

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN mkdir -p /data

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
