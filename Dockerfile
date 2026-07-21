#Stage 1: Base img
FROM python:3.12-slim

#Stage 2: Environment setup
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

#Stage 3: Working directory 
WORKDIR /app

#Stage 4: Install depencies 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Stage 5: Copy project 
COPY . .

#Stage 6: Run the server 
