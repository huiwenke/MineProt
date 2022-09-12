#!/bin/bash -e

MP_PORT=80
MP_DATA=./data

while [ -n "$1" ]
do
    case "$1" in
        -d)
            MP_DATA=$2
            shift
        ;;
        -p)
            MP_PORT=$2
            shift
        ;;
        -h)
            echo "Usage: setup.sh [options...]"
            echo "-d <dir>        MineProt data directory (default: ./data)"
            echo "-p <port>       MineProt port (default: 80)"
            exit
        ;;
        *)
            echo "Invalid paramter. try '-h' for more information."
            exit
        ;;
    esac
    shift
done

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

if [ ! -f "docker-compose.yml" ]; then
  echo "Error: Please run this script where MineProt docker-compose.yml is located."
  exit 1
fi

pip3 install docker-compose

if [ ! -f "app/php/maxit.tar.gz" ]; then
	wget https://figshare.com/ndownloader/files/36918121 -O app/php/maxit.tar.gz;
fi

if [ ! -d $MP_DATA ]; then
	mkdir $MP_DATA
fi

if [ ! -d $MP_DATA/es ]; then
	cp -r app/elasticsearch/init $MP_DATA/es
fi

tee .env <<EOF
MP_PORT=$MP_PORT
MP_DATA=$MP_DATA
EOF

docker-compose up -d