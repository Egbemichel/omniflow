FROM nginx:alpine

# Copy frontend files
COPY . /usr/share/nginx/html

# Copy and enable the entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN apk add --no-cache dos2unix && \
    dos2unix /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
