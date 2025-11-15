FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

WORKDIR /app

# Install Node.js & npm so the Next.js web app can run in the same container.
RUN apt-get update \
  && apt-get install -y --no-install-recommends nodejs npm \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Copy the entire project so both backend and web app are available.
COPY . /app

# Install Python dependencies for the backend.
WORKDIR /app/backend
RUN uv sync --no-dev

# Install web app dependencies and build the Next.js app.
WORKDIR /app/apps/web
RUN npm install \
  && npm run build

EXPOSE 8000 3000

# Run backend (FastAPI) and web app (Next.js) in the same container.
CMD ["sh", "-c", "cd /app/backend && uv run ecofood-backend & cd /app/apps/web && npm run start"]
