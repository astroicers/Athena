FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

LABEL org.opencontainers.image.title="Athena Frontend" \
      org.opencontainers.image.description="AI-driven C5ISR cyber operations command platform" \
      org.opencontainers.image.url="https://github.com/astroicers/Athena" \
      org.opencontainers.image.source="https://github.com/astroicers/Athena" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="0.1.0"

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/messages ./messages
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/src/i18n ./src/i18n

EXPOSE 3000

CMD ["node_modules/.bin/next", "start", "--port", "3000"]
