FROM node:22-alpine AS base

FROM base AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

FROM base AS builder
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# These are only needed to satisfy `next build`'s static analysis of routes
# that read env vars at request time; real values are supplied at runtime.
ENV BACKEND_URL=http://backend:8000
ENV SETUP_TOKEN=build-placeholder
ENV N8N_WEBHOOK_URL=http://n8n:5678/webhook/lead-intake
ENV N8N_BASE_URL=http://n8n:5678
RUN pnpm build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
