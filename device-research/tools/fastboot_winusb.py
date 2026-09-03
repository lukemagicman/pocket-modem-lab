"""Minimal fastboot client for a generic WinUSB/libusb interface.

Supports ordinary commands, ``boot-file PATH`` for a RAM-only boot test, and
``flash-file PARTITION PATH`` for an explicitly requested partition write.
"""

import pathlib
import sys
import usb1


VID = 0x18D1
PID = 0xD00D


def exchange(handle, endpoint_out, endpoint_in, command, timeout=5000):
    handle.bulkWrite(endpoint_out, command.encode("ascii"), timeout=3000)
    messages = []
    while True:
        response = bytes(handle.bulkRead(endpoint_in, 4096, timeout=timeout)).decode("utf-8", "replace")
        status, payload = response[:4], response[4:]
        messages.append((status, payload))
        if status in ("OKAY", "FAIL"):
            return messages


def read_reply(handle, endpoint_in, timeout=10000):
    response = bytes(handle.bulkRead(endpoint_in, 4096, timeout=timeout)).decode("utf-8", "replace")
    return response[:4], response[4:]


def download_file(handle, endpoint_out, endpoint_in, image_path):
    image_size = image_path.stat().st_size
    handle.bulkWrite(endpoint_out, f"download:{image_size:08x}".encode("ascii"), timeout=3000)
    status, payload = read_reply(handle, endpoint_in)
    print(f"{status}{payload}")
    if status != "DATA":
        raise SystemExit("device refused download")
    with image_path.open("rb") as stream:
        while chunk := stream.read(64 * 1024):
            handle.bulkWrite(endpoint_out, chunk, timeout=10000)
    status, payload = read_reply(handle, endpoint_in, timeout=30000)
    print(f"{status}{payload}")
    if status != "OKAY":
        raise SystemExit("download failed")


action = sys.argv[1] if len(sys.argv) > 1 else "getvar:product"

with usb1.USBContext() as context:
    device = context.getByVendorIDAndProductID(VID, PID)
    if device is None:
        raise SystemExit("fastboot device not found")
    handle = device.open()
    interface = 0
    handle.claimInterface(interface)
    setting = next(device.iterSettings())
    endpoint_in = None
    endpoint_out = None
    for endpoint in setting.iterEndpoints():
        address = endpoint.getAddress()
        if address & 0x80:
            endpoint_in = address
        else:
            endpoint_out = address
    if endpoint_in is None or endpoint_out is None:
        raise SystemExit("bulk endpoints not found")
    if action == "read-once":
        status, payload = read_reply(handle, endpoint_in, timeout=120000)
        print(f"{status}{payload}")
        raise SystemExit(0)

    if action not in ("boot-file", "flash-file"):
        for status, payload in exchange(handle, endpoint_out, endpoint_in, action):
            print(f"{status}{payload}")
        raise SystemExit(0)

    if action == "flash-file":
        if len(sys.argv) != 4:
            raise SystemExit("usage: fastboot_winusb.py flash-file PARTITION PATH")
        partition = sys.argv[2]
        image_path = pathlib.Path(sys.argv[3])
        download_file(handle, endpoint_out, endpoint_in, image_path)
        for status, payload in exchange(handle, endpoint_out, endpoint_in, f"flash:{partition}", timeout=120000):
            print(f"{status}{payload}")
        raise SystemExit(0)

    if len(sys.argv) != 3:
        raise SystemExit("usage: fastboot_winusb.py boot-file PATH")
    image_path = pathlib.Path(sys.argv[2])
    download_file(handle, endpoint_out, endpoint_in, image_path)
    handle.bulkWrite(endpoint_out, b"boot", timeout=3000)
    try:
        status, payload = read_reply(handle, endpoint_in, timeout=10000)
        print(f"{status}{payload}")
        if status == "FAIL":
            raise SystemExit("boot failed")
    except usb1.USBErrorNoDevice:
        print("INFOdevice disconnected for RAM boot")
