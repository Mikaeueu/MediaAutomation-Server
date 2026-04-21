FROM node:18-alpine AS build
WORKDIR /app

# copia package.json e package-lock para cache
COPY frontend/package*.json ./

# instala dependências
RUN if [ -f package-lock.json ]; then npm ci --silent --prefer-offline; else npm install --silent --prefer-offline; fi

# copia todo o frontend (inclui src/index.html)
COPY frontend/ ./

# roda build (Vite usará root: "src" conforme vite.config.ts)
RUN npm run build

FROM nginx:stable-alpine AS runtime
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
