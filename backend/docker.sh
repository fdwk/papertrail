docker build -t fastapi-backend ./backend
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/mydb \
  fastapi-backend