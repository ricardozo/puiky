# Imagen de la web de Puiky: build del SPA (Vite) servido por nginx.
# nginx también hace de reverse-proxy de /api → app:8000, así web y API
# comparten el mismo origen (una sola ruta de túnel, sin CORS).

# --- Etapa 1: build del SPA con pnpm ---
FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable

# Dependencias primero (capa cacheada mientras no cambie el lock)
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Código y build. VITE_API_URL se hornea en el bundle: "/api" = mismo origen.
COPY . .
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN pnpm build

# --- Etapa 2: nginx sirve los estáticos + proxy de la API ---
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
