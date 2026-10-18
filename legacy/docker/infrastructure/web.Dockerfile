FROM node:22-alpine AS deps
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci || npm install

FROM node:22-alpine AS builder
WORKDIR /web
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_OUTPUT=standalone
COPY --from=deps /web/node_modules ./node_modules
COPY apps/web ./
COPY packages/contracts /contracts
RUN mkdir -p public && cp /contracts/product.json public/product.json || true
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /web
ENV NODE_ENV=production
    RUN apk add --no-cache wget && addgroup -S nextjs && adduser -S nextjs -G nextjs
COPY --from=builder /web/public ./public
COPY --from=builder /web/.next/standalone ./
COPY --from=builder /web/.next/static ./.next/static
USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --retries=8 CMD wget -qO- http://127.0.0.1:3000 >/dev/null || exit 1
CMD ["node", "server.js"]
