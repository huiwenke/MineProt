FROM php:7.2-fpm

COPY maxit.tar.gz /
COPY usalign.tar.xz /

RUN cd / && tar -zxvf maxit.tar.gz && rm -rf maxit.tar.gz
RUN tar -xf /usalign.tar.xz -C /app/bin/ && rm -rf usalign.tar.xz
CMD chown www-data /var/www/data && php-fpm