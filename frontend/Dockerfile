FROM nginx:alpine

# Copy frontend files
COPY . /usr/share/nginx/html

# Override default nginx server config (adds /submit/* → end_user.html rewrite)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy and enable the entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN apk add --no-cache dos2unix && \
    dos2unix /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
