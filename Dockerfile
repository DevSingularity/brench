# Build the React bundle so the Python image serves a self-contained UI.
FROM node:22-alpine AS ui-build
WORKDIR /build/ui
RUN corepack enable && corepack prepare pnpm@10.8.1 --activate
COPY ui/package.json ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY ui/ ./
RUN pnpm build

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system --gid 10001 brench \
    && useradd --system --uid 10001 --gid brench --home-dir /nonexistent brench

COPY harness/ ./harness/
COPY tasks/ ./tasks/
COPY examples/ ./examples/
COPY --from=ui-build /build/ui/dist/ ./ui/dist/
RUN mkdir -p /app/runs && chown -R brench:brench /app/runs

USER 10001:10001
EXPOSE 8765
CMD ["python", "-m", "harness", "serve", "--host", "0.0.0.0", "--port", "8765", "--no-browser"]
