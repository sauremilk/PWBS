# PWBS Frontend  Production Dockerfile
# Multi-stage build with Next.js standalone output

FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app

RUN addgroup --system pwbs && adduser --system --ingroup pwbs pwbs

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER pwbs

EXPOSE 3000

CMD ["node", "server.js"]