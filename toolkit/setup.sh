#!/bin/bash
set -euo pipefail

MP_PORT=80
MP_DATA=./data
MP_CE=docker

# Load only the supported setup options as data, without executing .env.
# Priority: explicit command-line options > existing .env > defaults above.
if [ -f .env ]; then
    single_quoted="^'([^']*)'[[:space:]]*(#.*)?$"
    double_quoted='^"([^"]*)"[[:space:]]*(#.*)?$'
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^[[:space:]]*(MP_PORT|MP_DATA|MP_CE)[[:space:]]*=(.*)$ ]]; then
            key=${BASH_REMATCH[1]}
            value=${BASH_REMATCH[2]}
            value=${value#"${value%%[![:space:]]*}"}
            value=${value%"${value##*[![:space:]]}"}
            if [[ "$value" =~ $single_quoted ]] || [[ "$value" =~ $double_quoted ]]; then
                value=${BASH_REMATCH[1]}
            elif [[ "$value" == \"* || "$value" == \'* ]]; then
                echo "Error: invalid quoted value for $key in .env." >&2
                exit 1
            else
                value=${value%%[[:space:]]#*}
                value=${value%"${value##*[![:space:]]}"}
            fi
            case "$key" in
                MP_PORT) MP_PORT=$value ;;
                MP_DATA) MP_DATA=$value ;;
                MP_CE) MP_CE=$value ;;
            esac
        fi
    done < .env
fi

usage() {
    echo "Usage: toolkit/setup.sh [-d data-directory] [-p port] [-c container-engine]"
    echo "Unspecified options use .env values, then defaults: port 80, ./data, docker."
}
while getopts ':d:p:c:h' option; do
    case "$option" in
        d) MP_DATA=$OPTARG ;;
        p) MP_PORT=$OPTARG ;;
        c) MP_CE=$OPTARG ;;
        h) usage; exit 0 ;;
        *) usage >&2; exit 1 ;;
    esac
done
shift $((OPTIND - 1))
if [ "$#" -ne 0 ] || ! [[ "$MP_PORT" =~ ^[0-9]+$ ]] || [ "$MP_PORT" -lt 1 ] || [ "$MP_PORT" -gt 65535 ]; then
    echo 'Error: provide a port between 1 and 65535.' >&2
    exit 1
fi
if ! command -v "$MP_CE" >/dev/null; then
    echo "Error: Please install $MP_CE." >&2
    exit 1
fi
if [ ! -f docker-compose.yml ] || [ ! -d web/mineprot ]; then
    echo 'Error: Run this script from the MineProt project root.' >&2
    exit 1
fi
if "$MP_CE" compose version >/dev/null 2>&1; then
    compose=("$MP_CE" compose)
elif command -v "$MP_CE-compose" >/dev/null; then
    compose=("$MP_CE-compose")
else
    echo "Error: Please install a Compose plugin for $MP_CE." >&2
    exit 1
fi

# The bundled Foldcomp and US-align archives are Linux x86-64 executables.
# Query the engine's architecture, which may differ from the client machine.
# Docker exposes Architecture; Podman exposes Host.Arch. Probe both schemas
# so wrappers and Docker-compatible Podman commands also work.
if server_arch=$("$MP_CE" info --format '{{.Architecture}}' 2>/dev/null) && [ -n "$server_arch" ]; then
    :
elif server_arch=$("$MP_CE" info --format '{{.Host.Arch}}') && [ -n "$server_arch" ]; then
    :
else
    echo "Error: unable to determine the architecture using $MP_CE info." >&2
    exit 1
fi
case "$server_arch" in
    amd64|x86_64) ;;
    *) echo "Error: bundled Foldcomp/US-align require a Linux x86-64 daemon (found $server_arch)." >&2; exit 1 ;;
esac
if [ ! -s app/php/foldcomp.tar.gz ]; then
    if ! command -v curl >/dev/null; then
        echo 'Error: curl is required to download Foldcomp.' >&2
        exit 1
    fi
    archive=$(mktemp app/php/foldcomp.tar.gz.XXXXXX)
    trap 'rm -f -- "$archive"' EXIT
    curl --fail --location --retry 3 https://mmseqs.com/foldcomp/foldcomp-linux-x86_64.tar.gz -o "$archive"
    mv -- "$archive" app/php/foldcomp.tar.gz
    trap - EXIT
fi
if [ ! -s app/php/usalign.tar.xz ]; then
    echo 'Error: missing app/php/usalign.tar.xz. Supply the project US-align archive.' >&2
    exit 1
fi
if ! command -v sha256sum >/dev/null; then
    echo 'Error: sha256sum is required to verify dependency archives.' >&2
    exit 1
fi
# Fail on changed downloads rather than building with an unreviewed binary.
sha256sum --check app/python/tools.sha256

mkdir -p -- "$MP_DATA"
MP_DATA=$(cd -- "$MP_DATA" && pwd -P)
mkdir -p -- "$MP_DATA/repo" "$MP_DATA/cache"
if [ ! -d "$MP_DATA/es" ]; then
    cp -a app/elasticsearch/init "$MP_DATA/es"
fi
# Existing ES/repository contents and ownership are never reset here.
# Ensure the application user can use an existing bind-mounted data directory.
if [ ! -w "$MP_DATA/repo" ] || [ ! -w "$MP_DATA/cache" ]; then
    echo "Error: $MP_DATA/repo and $MP_DATA/cache must be writable by UID $(id -u)." >&2
    exit 1
fi
if [[ "$MP_DATA" == *"'"* || "$MP_DATA" == *$'\n'* ]]; then
    echo 'Error: data directory cannot contain quotes or newlines.' >&2
    exit 1
fi
# Single quotes preserve spaces, dollar signs and # in Compose .env values.
# Update only managed settings; keep any custom timeout/concurrency variables.
if [ -f .env ]; then
    env_tmp=$(mktemp .env.XXXXXX)
    sed '/^MP_PORT=/d; /^MP_DATA=/d; /^MP_CE=/d; /^MP_UID=/d; /^MP_GID=/d' .env > "$env_tmp"
    cat "$env_tmp" > .env
    rm -f -- "$env_tmp"
fi
printf "\n" >> .env
cat >> .env <<ENV
MP_PORT=$MP_PORT
MP_DATA='$MP_DATA'
MP_CE=$MP_CE
MP_UID=$(id -u)
MP_GID=$(id -g)
ENV

# No fallback on an actual build/start failure: preserve its original error.
"${compose[@]}" up -d --build --remove-orphans
