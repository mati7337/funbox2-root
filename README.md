## funbox2-root

Root your funbox 2.0 modem by using CVE-2021-33287 in NTFS-3G.

To root it you need to have a usb stick on which you'll write a specially prepared ntfs image, and you need to be connected to the router's LAN.

This CAN'T be used to attack someone else's modem, as you not only need to be on the LAN but also have physical access, and if you have malicious intent and physical access you can just replace the whole device with a tampered one anyways.

Funbox 2.0 isn't as easy to root as some other devices on the market, as it's impossible to interrupt u-boot during boot and there's no trivial vulnerability in the config panel.

```diff
- WARNING: running this will expose a passwordless telnet on your LAN
- It's recommended to only run this with Wi-Fi either disabled or with
- a strong password and only with trusted devices on the network.
- While the exploit itself shouldn't cause any harm to the device I'm also
- not responsible for bricking your modem.
```

### Technical writeup

You can find a technical writeup in [WRITEUP.md](https://github.com/mati7337/funbox2-root/blob/master/WRITEUP.md).

### How to use it

These instructions apply to linux, but they also might work on Windows Subsystem for Linux.

#### Preparations

Before you begin you have to enable SMBv1 support, because that's the only version supported by funbox 2.0

```shell
echo "client min protocol = NT1" | sudo tee -a /etc/samba/smb.conf
```

Then you have to create the image that will later be written to the usb stick.

```shell
./create_image.sh usb.img
```

This image will contain a file that exploits the vulnerability, but has a wrong offset set. We'll calculate and set the correct offset using `ntfs_edit_offset.py` in later steps.

You now have to write the image to a usb stick. Create a partition with your favourite partitioning software which is at least 2MiB. Then write the image to the newly created partition

```shell
dd if=usb.img of=/dev/YOUR_USB_STICK
eject /dev/YOUR_USB_STICK
```

Compile exploit.c using any c compiler. It only uses clib and linux calls, so it doesn't require any additional libraries. Running it writes the exploit into ntfs-3g stack's memory which executes when unmounting.

```shell
gcc exploit.c -o exploit
```

#### Exploitation

Plug in the usb stick into the modem. There's 1 port in the front and 1 in the back, any port should work.

`Fun fact: these ports aren't USB 3.0, they're actually USB 2.0, but the connector is colored blue`

The modem should automatically mount it and share it through samba. The name should be set to `ntfs_usb`, but you can also check it using the `list.sh` script.

```shell
./list.sh IP
```

Mount the smb share using the `./remount.sh` script.

```shell
sudo ./remount.sh IP ntfs_usb
```

Then try running the exploit

```shell
./exploit
```

The first time you run it you should get a `Incorrect alignment:` error message. Copy the hex string after that, and run

```shell
python3 ntfs_edit_offset.py usb.img --ntfs-3g ./bin/ntfs-3g --ident HEX_STRING
```

This will set the correct offset in the ntfs-3g image. Now write the edited image to the usb stick and plug it again into the modem. Running it again should finish successfully. If you still get an error try unplugging and plugging back in the usb stick, as sometimes it can result in different heap addresses. If that still doesn't work, try creating the image again.

If you see a success message you can unplug the usb stick. This will activate the exploit stored in memory which will kill the cupsd process and run telnetd on it's port (other ports are blocked by the firewall). You can then connect to it

```shell
telnet 192.168.1.1 631
```
