FROM busybox:1.37.0
COPY www /www
USER 65534
EXPOSE 3000
CMD ["httpd", "-f", "-p", "3000", "-h", "/www"]
