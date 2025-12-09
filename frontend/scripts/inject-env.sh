#!/bin/sh
# Environment variable injection script for Optimus Frontend

set -e

# Default values
API_URL=${API_URL:-"http://localhost:8000"}
VERSION=${VERSION:-"1.0.0"}
BUILD_ENV=${BUILD_ENV:-"production"}

echo "Injecting runtime configuration..."
echo "API_URL: $API_URL"
echo "VERSION: $VERSION"
echo "BUILD_ENV: $BUILD_ENV"

# Create runtime configuration file
cat > /usr/share/nginx/html/config.runtime.js << EOF
window.__RUNTIME_CONFIG__ = {
  API_URL: "$API_URL",
  VERSION: "$VERSION",
  BUILD_ENV: "$BUILD_ENV",
  TIMESTAMP: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
};
EOF

echo "Runtime configuration injected successfully"