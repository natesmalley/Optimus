# Dockerfile for Optimus Frontend Dashboard
# Multi-stage build: Build React app + Serve with Nginx

# ===================================
# Stage 1: Build Stage
# ===================================
FROM node:18-alpine as builder

# Set build arguments
ARG BUILD_ENV=production
ARG API_URL=http://localhost:8000
ARG VERSION=1.0.0

# Set working directory
WORKDIR /app

# Copy package files for better caching
COPY package*.json ./
COPY tsconfig.json ./
COPY vite.config.ts ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Install dependencies
RUN npm ci --only=production --silent

# Copy source code
COPY src/ ./src/
COPY public/ ./public/ 2>/dev/null || true

# Create environment file for build
RUN echo "VITE_API_URL=$API_URL" > .env.production && \
    echo "VITE_APP_VERSION=$VERSION" >> .env.production && \
    echo "VITE_BUILD_ENV=$BUILD_ENV" >> .env.production

# Build the application
RUN npm run build

# ===================================
# Stage 2: Production Nginx Stage
# ===================================
FROM nginx:1.25-alpine as production

# Install additional tools for health checks
RUN apk add --no-cache curl

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S optimus -u 1001 -G nodejs

# Copy custom nginx configuration
COPY frontend/nginx/nginx.conf /etc/nginx/nginx.conf
COPY frontend/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder --chown=optimus:nodejs /app/dist /usr/share/nginx/html

# Copy environment variable injection script
COPY frontend/scripts/inject-env.sh /docker-entrypoint.d/inject-env.sh
RUN chmod +x /docker-entrypoint.d/inject-env.sh

# Create runtime config template for environment variables
RUN echo 'window.__RUNTIME_CONFIG__ = { API_URL: "${API_URL}", VERSION: "${VERSION}" };' \
    > /usr/share/nginx/html/config.template.js

# Set proper permissions
RUN chown -R optimus:nodejs /usr/share/nginx/html && \
    chown -R optimus:nodejs /var/cache/nginx && \
    chown -R optimus:nodejs /var/log/nginx && \
    chown -R optimus:nodejs /etc/nginx/conf.d

# Create nginx PID directory with proper permissions
RUN mkdir -p /var/run && \
    chown -R optimus:nodejs /var/run

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Labels
LABEL maintainer="Optimus DevOps <devops@optimus.ai>" \
      version="${VERSION}" \
      description="Optimus Dashboard Frontend" \
      build-env="${BUILD_ENV}"

# Expose port
EXPOSE 80

# Switch to non-root user
USER optimus

# Start nginx
CMD ["nginx", "-g", "daemon off;"]