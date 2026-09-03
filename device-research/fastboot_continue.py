# -*- coding: utf-8 -*-
"""通过 pyusb/libusb 直连 Qualcomm fastboot 9006，发 continue 命令引导 boot"""
import os, sys, time, struct

DLL_DIR = 'D:/4G/UFI003-analysis/edl/edl-master/edlclient/Windows'
os.add_dll_directory(DLL_DIR)

import usb.core
import usb.util
import usb.backend.libusb1

backend = usb.backend.libusb1.get_backend(
    find_library=lambda x: os.path.join(DLL_DIR, 'libusb-1.0.dll'))

dev = usb.core.find(idVendor=0x05C6, idProduct=0x9006, backend=backend)
if dev is None:
    print('ERROR: 05C6:9006 not found')
    sys.exit(1)

print('found device:', dev.manufacturer, dev.product)

# 找 bulk IN/OUT endpoints
ep_out = None
ep_in = None
for cfg in dev:
    for intf in cfg:
        for ep in intf:
            attr = usb.util.endpoint_type(ep.bmAttributes)
            if attr == usb.util.ENDPOINT_TYPE_BULK:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    if ep_out is None:
                        ep_out = ep
                else:
                    if ep_in is None:
                        ep_in = ep

if ep_out is None or ep_in is None:
    print('ERROR: bulk endpoints not found')
    sys.exit(1)

print(f'bulk OUT: 0x{ep_out.bEndpointAddress:02x}, bulk IN: 0x{ep_in.bEndpointAddress:02x}')

# detach kernel driver 若需要
try:
    dev.set_configuration()
except Exception:
    pass

def fb_cmd(cmd, timeout=5000):
    dev.write(ep_out, cmd.encode('utf-8'), timeout=timeout)
    buf = b''
    # 读响应直到 OKAY/FAIL/DATA 完整
    data = bytearray()
    while True:
        try:
            chunk = bytes(dev.read(ep_in, 512, timeout=timeout))
        except usb.core.USBError:
            break
        if not chunk:
            break
        data += chunk
        # 判断是否已收到完整响应头
        if len(data) >= 4:
            h = data[:4].decode('ascii', 'ignore')
            if h in ('OKAY', 'FAIL', 'INFO', 'DATA'):
                break
    return bytes(data)

print('\n=== getvar:version ===')
try:
    r = fb_cmd('getvar:version')
    print('resp:', r[:64])
except Exception as e:
    print('getvar error:', e)

print('\n=== getvar:product ===')
try:
    r = fb_cmd('getvar:product')
    print('resp:', r[:128])
except Exception as e:
    print('getvar error:', e)

print('\n=== sending continue ===')
try:
    dev.write(ep_out, b'continue', timeout=5000)
    # 读最后响应
    try:
        r = bytes(dev.read(ep_in, 64, timeout=3000))
        print('continue resp:', r[:64])
    except usb.core.USBError as e:
        print('read after continue (expected disconnect/pipe):', e)
except Exception as e:
    print('continue error:', e)

print('\nDONE - continue sent, watch for device reboot / Debian USB enum')
