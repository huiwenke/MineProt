#!/bin/bash
# Keep the archive outside the source directory until it is complete.
set -eu
cd -- "$1"
printf 'packaging\n' > status.txt
archive=''
finish() {
    code=$?
    if [ -n "$archive" ]; then
        rm -f -- "$archive"
    fi
    if [ "$code" -ne 0 ]; then
        printf 'failed\n' > status.txt
    fi
}
trap finish EXIT
archive=$(mktemp "${TMPDIR:-/tmp}/MP_SALIGN_ARCHIVE_XXXXXX")
tar -zcf "$archive" --exclude=./result.tar.gz --exclude=./result.tar.gz.part \
    --exclude=./query.err --exclude=./status.txt .
mv -- "$archive" result.tar.gz
archive=''
printf 'complete\n' > status.txt
