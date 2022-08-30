#!/bin/bash

if [ ! "$(command -v docker)" ]; then
  echo "Error: please install docker."
  exit 1
fi

if [ ! "$(command -v wget)" ]; then
  echo "Error: please install wget."
  exit 1
fi

if [ ! "$(command -v pip)" ]; then
  echo "Error: please install python3-pip."
  exit 1
fi

pip install docker-compose

if [ ! -f "app/php/maxit.tar.gz" ]; then
	wget https://figshare.com/ndownloader/files/36918121 -O app/php/maxit.tar.gz;
fi

docker-compose up -d