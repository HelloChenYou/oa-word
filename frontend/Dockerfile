FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
COPY scripts ./scripts
ENV ALLOW_NPM_COMMANDS=1
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
