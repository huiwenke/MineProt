#!/bin/bash -e

MP_PORT=80
MP_DATA=./data
MP_CE=docker

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
        -c)
            MP_CE=$2
            shift
        ;;
        -h)
            echo "Usage: setup.sh [options...]"
            echo "-d <dir>        MineProt data directory (default: ./data)"
            echo "-p <port>       MineProt port (default: 80)"
            echo "-c <CE>         Container Engine (default: docker)"
            exit
        ;;
        *)
            echo "Invalid parameter. try '-h' for more information."
            exit
        ;;
    esac
    shift
done

if [ ! "$(command -v curl)" ]; then
  echo "Error: Please install curl."
  exit 1
fi

if [ ! "$(command -v $MP_CE)" ]; then
  echo "Error: Please install $MP_CE."
  exit 1
fi

if [ ! "$(command -v $MP_CE-compose)" ]; then
  echo "Error: Please install $MP_CE-compose."
  exit 1
fi

if [ ! -f "docker-compose.yml" ]; then
  echo "Error: Please run this script where MineProt docker-compose.yml is located."
  exit 1
fi

if [ ! -f "app/php/maxit.tar.gz" ]; then
	curl -L https://figshare.com/ndownloader/files/36918121 -o app/php/maxit.tar.gz;
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
MP_CE=$MP_CE
EOF

$MP_CE-compose up -d