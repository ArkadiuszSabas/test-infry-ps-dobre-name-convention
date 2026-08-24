FROM node:24-alpine AS deps

ENV NEXT_TELEMETRY_DISABLED=1 \
    PNPM_CONFIG_UPDATE_NOTIFIER=false \
    PNPM_HOME=/pnpm
ENV PATH="${PNPM_HOME}:${PATH}"

WORKDIR /app/apps/web

RUN corepack enable

COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM deps AS builder

ARG DOCMIND_CONNECTOR_PROFILE_ID=product
ENV DOCMIND_CONNECTOR_PROFILE_ID=${DOCMIND_CONNECTOR_PROFILE_ID}

COPY apps/web ./
COPY deployments /app/deployments
COPY packages/connectors /app/packages/connectors

RUN pnpm build

FROM node:24-alpine AS runtime

ENV HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    PORT=3000

WORKDIR /app

RUN addgroup -S nodejs \
    && adduser -S nextjs -G nodejs

COPY --from=builder /app/apps/web/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
