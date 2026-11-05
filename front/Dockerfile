# syntax=docker/dockerfile:1
# Build context: front/. The final/default target remains the static runtime.
FROM node:24.18.0-bookworm-slim@sha256:6f7b03f7c2c8e2e784dcf9295400527b9b1270fd37b7e9a7285cf83b6951452d AS dependencies
WORKDIR /app
RUN npm install --global npm@11.16.0 \
    && test "$(node --version)" = "v24.18.0" \
    && test "$(npm --version)" = "11.16.0"
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm npm ci

# Compose Watch syncs source into this writable development target.
FROM dependencies AS development
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /bin/sh app \
    && chown -R 10001:10001 /app
COPY --chown=10001:10001 index.html vite.config.js ./
COPY --chown=10001:10001 src ./src
COPY --chown=10001:10001 public ./public
COPY --chown=10001:10001 tests ./tests
ENV HOME=/home/app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:8080/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "8080"]

FROM dependencies AS build
COPY index.html vite.config.js ./
COPY src ./src
COPY public ./public
RUN npm run build

# Only compiled static files go into the serving image.
FROM nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236 AS runtime
RUN addgroup -S -g 10001 app && adduser -S -D -H -u 10001 -G app app
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
