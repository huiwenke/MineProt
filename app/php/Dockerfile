FROM php:7.2-fpm

COPY maxit.tar.gz /
COPY foldcomp.tar.gz /
COPY usalign.tar.xz /

RUN cd / && tar -zxvf maxit.tar.gz && rm -rf maxit.tar.gz
RUN tar -zxvf /foldcomp.tar.gz -C /app/bin/ && rm -rf foldcomp.tar.gz
RUN tar -xf /usalign.tar.xz -C /app/bin/ && rm -rf usalign.tar.xz
CMD chown www-data /var/www/data && php-fpm