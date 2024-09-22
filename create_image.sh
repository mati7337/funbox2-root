#!/bin/sh
set -eo pipefail

if [ "$#" -ne 1 ]; then
    echo "Please specify an output file"
    exit
fi

# mkfs.ntfs says that minimum NTFS volume size is 1MiB but it looks like
# it doesn't count the first sector
truncate --size=$((1024*1024 + 4096)) $1

lopath=$(sudo losetup --show --find $1)
echo "Image attached at $lopath"

# It has to have a label otherwise the modem doesn't see the partition
sudo mkfs.ntfs --label ntfs_usb $lopath

# Create a single file which structure will later be altered by a python script
mkdir -p ./mnt/
sudo mount $lopath ./mnt/
echo "a" > ./mnt/file
sudo umount ./mnt/
rmdir ./mnt/
echo "Wrote file to the partition"

sudo losetup --detach $lopath
echo "Image detached"

python3 ntfs_edit_offset.py $1
echo "File data offset and size altered"
