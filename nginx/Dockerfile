# Stage 1 — build the React app
# This is called a "multi-stage build": use a heavy Node image just to compile,
# then throw it away and only keep the small compiled output.
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build
# After this stage, /app/dist/ contains the compiled HTML/CSS/JS

# Stage 2 — serve compiled files with nginx (tiny image, no Node runtime)
FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/app.conf
# Copy only the compiled output from Stage 1 — Node itself is discarded
COPY --from=builder /app/dist /usr/share/nginx/html
