FROM python:3.12-slim

WORKDIR /app

# Install PostgreSQL headers and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["hypercorn", "app.main:app", "--bind", "::"]