# frontend/Dockerfile - produção (multi-stage)
FROM node:18-alpine AS build
WORKDIR /app

# Copia package.json e package-lock para cache
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --silent

# Copia o código e gera build
COPY frontend /app
RUN npm run build

# Stage runtime com nginx
FROM nginx:stable-alpine AS runtime
# Remove default index (opcional) e copia build
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist /usr/share/nginx/html

# Opcional: adicionar configuração nginx customizada
# COPY deploy/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
