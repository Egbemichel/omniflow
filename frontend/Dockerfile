FROM nginx:alpine

# Copy the frontend files
COPY . /usr/share/nginx/html

# The standard Nginx configuration serves from /usr/share/nginx/html on port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
