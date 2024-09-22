import argparse
import struct
import os

class Ntfs_dump():
    def __init__(self, fl):
        self.fl = fl
        #self.text_just = 28
        self.text_just = 32
        self.indent = 0

        self.attr_types = {
                0x10: ["$STANDARD_INFORMATION", self.dump_attr_standard_information],
                0x30: ["$FILE_NAME", self.dump_attr_file_name],
                0x80: ["$DATA", self.dump_attr_data],
        }

        self.fl.seek(0, os.SEEK_END)
        self.size = self.fl.tell()
        self.fl.seek(0, os.SEEK_SET)

    def dump_attr_standard_information(self, pos, length):
        pass

    def dump_attr_data(self, pos, length):
        if length:
            data = self.read_raw(pos, length)
            #self.label(f"[{hex(attrib_pos + name_offset)}] Data: ", name.decode("UTF16"))
            self.label(f"[{hex(pos)}] Data", data[:128])

    def dump_attr_file_name(self, pos, length):
        self.label(f"[{hex(pos)}] Parent directory", hex(self.read(pos, 8, "<Q")[0]))
        pos += 8
        self.label(f"[{hex(pos)}] Creation time", hex(self.read(pos, 8, "<Q")[0]))
        pos += 8
        self.label(f"[{hex(pos)}] Last data change time", hex(self.read(pos, 8, "<Q")[0]))
        pos += 8
        self.label(f"[{hex(pos)}] Last MFT change time", hex(self.read(pos, 8, "<Q")[0]))
        pos += 8
        self.label(f"[{hex(pos)}] Last access time", hex(self.read(pos, 8, "<Q")[0]))
        pos += 8
        self.label(f"[{hex(pos)}] Allocated size", hex(self.read(pos, 8, "<Q")[0]))
        pos += 8
        self.label(f"[{hex(pos)}] Data size", hex(self.read(pos, 8, "<Q")[0]))
        pos += 8
        self.label(f"[{hex(pos)}] File attributes", hex(self.read(pos, 4, "<L")[0]))
        pos += 4
        #self.label(f"[{hex(pos)}] Packed EA size", hex(self.read(pos, 2, "<H")[0]))
        #pos += 2
        #self.label(f"[{hex(pos)}] Reserved", hex(self.read(pos, 2, "<H")[0]))
        #pos += 2
        self.label(f"[{hex(pos)}] Reparse point tag", hex(self.read(pos, 4, "<L")[0]))
        pos += 4
        file_name_length = self.read(pos, 1, "<B")[0]
        self.label(f"[{hex(pos)}] File name length", hex(file_name_length))
        pos += 1
        self.label(f"[{hex(pos)}] File name type", hex(self.read(pos, 1, "<B")[0]))
        pos += 1
        self.label(f"[{hex(pos)}] Name", self.read_raw(pos, file_name_length*2).decode("UTF16"))

    def read(self, offset, size, fmt):
        if offset + size > self.size:
            return "\033[31mOOB\033[0m"
        self.fl.seek(offset)
        return struct.unpack(fmt, self.fl.read(size))

    def read_raw(self, offset, size):
        if offset + size > self.size:
            return "\033[31mOOB\033[0m"
        self.fl.seek(offset)
        return self.fl.read(size)

    def label(self, text, value, quote=False):
        if quote:
            print("    "*self.indent + f"\033[33m{text}:\033[0m".ljust(self.text_just), f"\"{value}\"")
        else:
            print("    "*self.indent + f"\033[33m{text}:\033[0m".ljust(self.text_just), f"{value}")

    def dump_pbs(self):
        self.label("[0x00] x86 JMP & NOP", self.read_raw(0x00, 3).hex())
        self.label("[0x03] OEM_ID", self.read_raw(0x03, 8).decode(), quote=True)
        print("BPB:")
        self.indent+=1
        self.label("[0x0b] Bytes per sector", self.read(0x0b, 2, "<H")[0])
        self.label("[0x0d] Sectors per cluster", self.read(0x0d, 1, "<B")[0])
        self.label("[0x0e] Reserved sector count", self.read(0x0e, 2, "<H")[0])
        self.label("[0x10] Table count", self.read(0x10, 1, "<B")[0])
        self.label("[0x11] Root entry count", self.read(0x11, 2, "<H")[0])
        self.label("[0x13] Sector count", self.read(0x13, 2, "<H")[0])
        self.label("[0x15] Media Descriptor", hex(self.read(0x15, 1, "<B")[0]))
        self.label("[0x16] Sectors per table", self.read(0x16, 2, "<H")[0])
        self.label("[0x18] Sectors per track", self.read(0x18, 2, "<H")[0])
        self.label("[0x1a] Number of heads", self.read(0x1a, 2, "<H")[0])
        self.label("[0x1c] Hidden Sectors", self.read(0x1c, 4, "<L")[0])
        self.label("[0x20] Sector count (32bit)", self.read(0x20, 4, "<L")[0])
        self.label("[0x24] Reserved", self.read(0x24, 4, "<L")[0])
        self.label("[0x28] Sector count (64bit)", hex(self.read(0x28, 8, "<Q")[0]))
        self.indent-=1
        print("EBPB:")
        self.indent+=1
        self.label("[0x30] $MFT cluster number", hex(self.read(0x30, 8, "<Q")[0]))
        self.label("[0x38] $MFTMirr cluster number", hex(self.read(0x38, 8, "<Q")[0]))
        self.label("[0x40] Clusters per record", hex(self.read(0x40, 1, "<B")[0]))
        self.label("[0x41] Reserved", self.read_raw(0x41, 3).hex())
        self.label("[0x44] Clusters per index buffer", hex(self.read(0x44, 1, "<B")[0]))
        self.label("[0x45] Reserved", self.read_raw(0x45, 3).hex())
        self.label("[0x48] Volume Serial Number", hex(self.read(0x48, 8, "<Q")[0]))
        self.label("[0x50] Checksum", hex(self.read(0x50, 4, "<L")[0]))
        self.indent-=1
        self.label("[0x54] Bootstrap Code", self.read_raw(0x54, 426).hex())
        self.label("[0x01fe] End-of-sector Marker", hex(self.read(0x01fe, 2, "<H")[0]))

    def dump_attrib_list(self, start_pos):
        pos = start_pos

        while 1:
            attrib_pos = pos

            attrib_type = self.read(pos, 4, "<L")[0]

            attrib_handler = self.attr_types.get(attrib_type)
            if attrib_handler:
                self.label(f"[{hex(pos)}] Attrib type", f"{hex(attrib_type)} ({attrib_handler[0]})")
            else:
                self.label(f"[{hex(pos)}] Attrib type", hex(attrib_type))

            if attrib_type == 0xffffffff:
                break

            self.indent += 1
            pos += 4
            attrib_len = self.read(pos, 4, "<L")[0]
            self.label(f"[{hex(pos)}] Attrib len", hex(attrib_len))
            pos += 4
            self.label(f"[{hex(pos)}] Non resident", hex(self.read(pos, 1, "<B")[0]))
            pos += 1
            name_length = self.read(pos, 1, "<B")[0]
            self.label(f"[{hex(pos)}] Name length", hex(name_length))
            pos += 1
            name_offset = self.read(pos, 2, "<H")[0]
            self.label(f"[{hex(pos)}] Name Offset", hex(name_offset))
            pos += 2
            if name_length:
                name = self.read_raw(attrib_pos + name_offset, name_length*2)
                self.indent += 1
                self.label(f"[{hex(attrib_pos + name_offset)}] Name", name.decode("UTF16"))
                self.indent -= 1
            self.label(f"[{hex(pos)}] Flags", hex(self.read(pos, 2, "<H")[0]))
            pos += 2
            self.label(f"[{hex(pos)}] Instance", hex(self.read(pos, 2, "<H")[0]))
            pos += 2
            value_length = self.read(pos, 4, "<L")[0]
            self.label(f"[{hex(pos)}] Value length", hex(value_length))
            pos += 4
            value_offset = self.read(pos, 2, "<H")[0]
            self.label(f"[{hex(pos)}] Value offset", hex(value_offset))
            pos += 2
            if value_length and attrib_handler:
                self.indent += 1
                attrib_handler[1](attrib_pos + value_offset, value_length)
                self.indent -= 1
            self.label(f"[{hex(pos)}] Non resident", hex(self.read(pos, 1, "<B")[0]))
            pos += 1
            self.label(f"[{hex(pos)}] Reserved", hex(self.read(pos, 1, "<B")[0]))
            pos += 1
            #if attrib_handler:
            #    attrib_handler[1](pos)
            self.indent -= 1

            pos = attrib_pos + attrib_len

    def dump_record(self, record_offset):
        pos = record_offset

        self.label(f"[{hex(pos)}] Record_type", self.read_raw(pos, 4))
        pos += 4
        self.label(f"[{hex(pos)}] Update sequence offset", hex(self.read(pos, 2, "<H")[0]))
        pos += 2
        self.label(f"[{hex(pos)}] Update sequence length", hex(self.read(pos, 2, "<H")[0]))
        pos += 2
        self.label(f"[{hex(pos)}] Log file seq number", self.read(pos, 8, "<Q")[0])
        pos += 8
        self.label(f"[{hex(pos)}] Record seq number", self.read(pos, 2, "<H")[0])
        pos += 2
        self.label(f"[{hex(pos)}] Hard link count", self.read(pos, 2, "<H")[0])
        pos += 2
        attrib_offset = self.read(pos, 2, "<H")[0]
        self.label(f"[{hex(pos)}] Attributes offset", hex(attrib_offset))
        pos += 2
        self.label(f"[{hex(pos)}] Flags", self.read(pos, 2, "<H")[0])
        pos += 2
        self.label(f"[{hex(pos)}] Bytes in use", self.read(pos, 4, "<L")[0])
        pos += 4
        self.label(f"[{hex(pos)}] Bytes allocated", self.read(pos, 4, "<L")[0])
        pos += 4
        self.label(f"[{hex(pos)}] Parent record number", self.read(pos, 8, "<Q")[0])
        pos += 8
        self.label(f"[{hex(pos)}] Next attribute index", self.read(pos, 2, "<H")[0])
        pos += 2
        self.label(f"[{hex(pos)}] Reserved", self.read(pos, 2, "<H")[0])
        pos += 2
        self.label(f"[{hex(pos)}] Record number", self.read(pos, 4, "<L")[0])
        pos += 4

        print("Attrib_list:")
        pos = record_offset + attrib_offset
        self.indent += 1
        self.dump_attrib_list(pos)
        self.indent -= 1

        print()

    def dump_mft(self):
        #mft_cluster = self.read(0x30, 8, "<Q")[0]
        #mftmirr_cluster = self.read(0x38, 8, "<Q")[0]

        #sectors_per_cluster = self.read(0x0d, 1, "<B")[0]
        #sector_size = self.read(0x0b, 2, "<H")[0]

        for i in range(self.size // 1024):
            pos = i * 1024
            if self.read_raw(pos, 4) == b"FILE":
                self.dump_record(i * 1024)

    def main(self):
        print("=== PBS ===")
        self.dump_pbs()
        print()
        print("=== MFT ===")
        self.dump_mft()

def main():
    parser = argparse.ArgumentParser(
            prog="ntfs_dump",
            description="Dump info from an ntfs image")
    parser.add_argument("image",
                        help="Location of the ntfs image file")
    args = parser.parse_args()

    with open(args.image, "rb") as fl:
        dump = Ntfs_dump(fl)
        dump.main()


if __name__ == "__main__":
    main()
