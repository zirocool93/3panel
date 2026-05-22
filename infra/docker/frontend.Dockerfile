FROM node:22-alpine AS build

WORKDIR /app
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    NODE_OPTIONS=--max-old-space-size=512 \
    npm_config_audit=false \
    npm_config_fund=false \
    npm_config_loglevel=warn

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
