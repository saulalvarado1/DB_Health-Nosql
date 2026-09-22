# syntax=docker/dockerfile:1.7

FROM node:22.22.2-alpine3.23 AS builder

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build


FROM nginxinc/nginx-unprivileged:1.29.1-alpine AS runtime

LABEL org.opencontainers.image.title="DB Health Monitor Frontend" \
      org.opencontainers.image.description="Static React client and same-origin API proxy"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

USER 101:101
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
