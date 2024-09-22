#!/bin/sh
set -eo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: ./mount.sh IP SHARE_NAME"
    exit
fi

mkdir -p ./smb
mount -o vers=1.0,guest,cache=none,nohandlecache -t cifs //$1/$2 ./smb
