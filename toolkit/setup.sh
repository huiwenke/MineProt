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
    echo 'Downloading Foldcomp...'
    curl --fail --location --retry 3 --connect-timeout 30 --max-time 600 https://mmseqs.com/foldcomp/foldcomp-linux-x86_64.tar.gz -o "$archive"
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

# Detached mode applies to container execution, not image building or waiting
# for depends_on health checks. Keep these phases visible and fail in place.
echo 'Building images (this step runs in the foreground)...'
if [[ $("$MP_CE" --version) == *podman* ]]; then
    # Compose providers differ in their pull flags and may force registry
    # access. Resolve local aliases first and build directly with Podman.
    build_podman_image() {
        local base_name=$1 dockerfile=$2 context=$3 target=$4
        local base_image="docker.io/library/$base_name" candidate
        local pull_policy=missing
        for candidate in "docker.io/library/$base_name" "localhost/$base_name" "$base_name"; do
            if "$MP_CE" image inspect "$candidate" >/dev/null 2>&1; then
                base_image=$candidate
                pull_policy=never
                break
            fi
        done
        if [ "$pull_policy" = never ]; then
            echo "Using local base image: $base_image (pull disabled)"
        else
            echo "Base image not found in current Podman storage: $base_image; downloading..."
        fi
        "$MP_CE" build --format=docker --pull="$pull_policy" \
            --build-arg "MP_BASE_IMAGE=$base_image" \
            -f "$dockerfile" -t "$target" "$context" </dev/null
    }
    build_podman_image elasticsearch:7.12.1 app/elasticsearch/Dockerfile app/elasticsearch localhost/mineprot_es:latest
    build_podman_image python:3.12-slim-bookworm app/python/Dockerfile . localhost/mineprot_web:latest
else
    "${compose[@]}" build </dev/null
fi
# Start dependencies explicitly so a Compose provider cannot wait indefinitely
# inside its service_healthy handling without printing useful diagnostics.
startup_failed() {
    echo "Error: $1 did not become ready within 180 seconds." >&2
    "$MP_CE" ps -a >&2 || true
    "$MP_CE" logs --tail 100 "$1" >&2 || true
    exit 1
}
echo 'Starting Elasticsearch in detached mode...'
"${compose[@]}" up -d --no-build es </dev/null
echo 'Waiting up to 180 seconds for Elasticsearch (yellow/green)...'
startup_deadline=$((SECONDS + 180))
until es_status=$("$MP_CE" exec elasticsearch curl --fail --silent --max-time 5 \
        'http://127.0.0.1:9200/_cat/health?h=status' 2>/dev/null) \
        && [[ "$es_status" == green || "$es_status" == yellow ]]; do
    if [ "$SECONDS" -ge "$startup_deadline" ]; then
        startup_failed elasticsearch
    fi
    sleep 2
done
echo "Elasticsearch ready ($es_status). Starting Web in detached mode..."
"${compose[@]}" up -d --no-build --no-deps --remove-orphans web </dev/null
echo 'Waiting up to 180 seconds for Web...'
startup_deadline=$((SECONDS + 180))
until "$MP_CE" exec MineWeb python -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5)" \
        >/dev/null 2>&1; do
    if [ "$SECONDS" -ge "$startup_deadline" ]; then
        startup_failed MineWeb
    fi
    sleep 2
done
echo "Setup finished. Service logs: ${compose[*]} logs -f"
