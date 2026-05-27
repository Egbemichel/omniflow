#!/bin/sh
# Generates config.js from environment variables at container startup
cat > /usr/share/nginx/html/config.js << EOF
window.PK_CONFIG = {
  GOOGLE_CLIENT_ID: "${GOOGLE_CLIENT_ID}",
  GOOGLE_REDIRECT_URI: "${GOOGLE_REDIRECT_URI}"
};
EOF
exec nginx -g "daemon off;"
