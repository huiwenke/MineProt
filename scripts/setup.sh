#!/bin/bash

if [ ! "$(command -v docker)" ]; then
  echo "Error: Please install docker."
  exit 1
fi

if [ ! "$(command -v wget)" ]; then
  echo "Error: Please install wget."
  exit 1
fi

if [ ! "$(command -v pip3)" ]; then
  echo "Error: Please install python3-pip."
  exit 1
fi

pip3 install docker-compose

if [ ! -f "app/php/maxit.tar.gz" ]; then
	wget https://figshare.com/ndownloader/files/36918121 -O app/php/maxit.tar.gz;
fi

docker-compose up -d