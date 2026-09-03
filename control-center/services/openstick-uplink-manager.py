#!/usr/bin/python3
import fcntl
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


USB_INTERFACE = 'usb0'
USB_ADDRESS = '192.168.137.28/24'
USB_GATEWAY = '192.168.137.1'
USB_DNS = '192.168.137.1'
USB_PROXY_URL = 'http://192.168.137.1:17897'
DOWNSTREAM_PROFILE = 'usb-failsafe'
UPLINK_PROFILE = 'openstick-usb-uplink'
STATE_FILE = Path('/run/openstick-uplink-transition.json')
LOCK_FILE = Path('/run/openstick-uplink-manager.lock')
MANAGER = '/usr/local/sbin/openstick-uplink-manager.py'
ROLLBACK_SECONDS = 30
HTTP_CHECKS = (
    ('https://connect.rom.miui.com/generate_204', (200, 204)),
    ('https://www.msftconnecttest.com/connecttest.txt', (200,)),
)


def run(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def write_state(status, **details):
    payload = {'status': status, 'updated_at': time.time(), **details}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, STATE_FILE)
    return payload


def profile_exists(name):
    result = run(['nmcli', '-t', '-f', 'NAME', 'connection', 'show'], timeout=5)
    return result.returncode == 0 and name in result.stdout.splitlines()


def usb_proxy_available():
    try:
        with socket.create_connection((USB_GATEWAY, 17897), timeout=2):
            return True
    except OSError:
        return False


def prepare():
    if not Path(f'/sys/class/net/{USB_INTERFACE}').exists():
        raise RuntimeError('USB RNDIS 接口不存在')
    if not profile_exists(DOWNSTREAM_PROFILE):
        raise RuntimeError('原 USB 管理配置不存在，拒绝创建上游配置')
    if not profile_exists(UPLINK_PROFILE):
        result = run([
            'nmcli', 'connection', 'add', 'type', 'ethernet',
            'ifname', USB_INTERFACE, 'con-name', UPLINK_PROFILE,
            'connection.autoconnect', 'no',
            'ipv4.method', 'manual',
            'ipv4.addresses', USB_ADDRESS,
            'ipv4.gateway', USB_GATEWAY,
            'ipv4.dns', USB_DNS,
            'ipv4.ignore-auto-dns', 'yes',
            'ipv4.never-default', 'no',
            'ipv4.route-metric', '50',
            'ipv6.method', 'disabled',
        ], timeout=15)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or '无法创建 USB 上游配置').strip())
    else:
        result = run([
            'nmcli', 'connection', 'modify', UPLINK_PROFILE,
            'connection.interface-name', USB_INTERFACE,
            'connection.autoconnect', 'no',
            'ipv4.method', 'manual',
            'ipv4.addresses', USB_ADDRESS,
            'ipv4.gateway', USB_GATEWAY,
            'ipv4.dns', USB_DNS,
            'ipv4.ignore-auto-dns', 'yes',
            'ipv4.never-default', 'no',
            'ipv4.route-metric', '50',
            'ipv6.method', 'disabled',
        ], timeout=10)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or '无法校验 USB 上游配置').strip())
    return write_state('prepared', profile=UPLINK_PROFILE, rollback_seconds=ROLLBACK_SECONDS)


def stop_unit(name):
    run(['systemctl', 'stop', f'{name}.timer', f'{name}.service'], timeout=8)
    run(['systemctl', 'reset-failed', f'{name}.timer', f'{name}.service'], timeout=8)


def schedule_rollback():
    stop_unit('openstick-uplink-rollback')
    result = run([
        'systemd-run', '--unit=openstick-uplink-rollback',
        f'--on-active={ROLLBACK_SECONDS}s', '--timer-property=AccuracySec=1s',
        MANAGER, 'rollback',
    ], timeout=10)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or '无法建立自动回滚任务').strip())


def default_route():
    result = run(['ip', '-j', '-4', 'route', 'show', 'default'], timeout=4)
    if result.returncode:
        return {}
    try:
        routes = json.loads(result.stdout)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return next((item for item in routes if item.get('dev') == USB_INTERFACE), {})


def connectivity_check():
    route = default_route()
    gateway = route.get('gateway')
    result = {
        'gateway': gateway,
        'gateway_available': False,
        'dns_available': False,
        'internet': False,
        'endpoint': None,
    }
    if not gateway:
        return result
    ping = run(['ping', '-c', '1', '-W', '2', gateway], timeout=4)
    result['gateway_available'] = ping.returncode == 0
    proxy_available = usb_proxy_available()
    if proxy_available:
        result['dns_available'] = True
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({
            'http': USB_PROXY_URL,
            'https': USB_PROXY_URL,
        }))
    else:
        dns = run(['getent', 'ahostsv4', 'www.msftconnecttest.com'], timeout=5)
        result['dns_available'] = dns.returncode == 0 and bool(dns.stdout.strip())
        opener = urllib.request.build_opener()
    # Windows ICS may not answer ICMP on its private gateway.  Treat the ping
    # as diagnostic evidence only and use DNS + an actual HTTP request to
    # decide whether Internet access works.
    if not result['dns_available']:
        return result
    for endpoint, expected in HTTP_CHECKS:
        try:
            request = urllib.request.Request(endpoint, headers={'User-Agent': 'OpenStick-Uplink/1.0'})
            with opener.open(request, timeout=6) as response:
                if response.status in expected:
                    result['internet'] = True
                    result['endpoint'] = endpoint
                    break
        except Exception:
            continue
    return result


def rollback(reason='automatic'):
    run(['nmcli', 'connection', 'down', UPLINK_PROFILE], timeout=12)
    restored = run(['nmcli', 'connection', 'up', DOWNSTREAM_PROFILE], timeout=25)
    if restored.returncode:
        return write_state(
            'error', reason=reason,
            error=(restored.stderr or restored.stdout or 'USB 管理网络恢复失败').strip(),
        )
    return write_state('rolled_back', reason=reason, management='192.168.68.1')


def activate():
    prepare()
    schedule_rollback()
    write_state('switching', rollback_seconds=ROLLBACK_SECONDS)
    run(['nmcli', 'connection', 'down', DOWNSTREAM_PROFILE], timeout=12)
    activated = run(['nmcli', 'connection', 'up', UPLINK_PROFILE], timeout=28)
    if activated.returncode:
        stop_unit('openstick-uplink-rollback')
        return rollback('activation_failed')
    checks = connectivity_check()
    if not checks['internet']:
        write_state('checking', checks=checks, rollback_seconds=ROLLBACK_SECONDS)
        return {'status': 'checking', 'checks': checks, 'rollback_seconds': ROLLBACK_SECONDS}
    stop_unit('openstick-uplink-rollback')
    return write_state('online', checks=checks, active='usb')


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open('w', encoding='utf-8') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if action == 'prepare':
            result = prepare()
        elif action == 'activate':
            result = activate()
        elif action == 'disable':
            stop_unit('openstick-uplink-rollback')
            result = rollback(action)
        elif action == 'rollback':
            result = rollback(action)
        elif action == 'status':
            try:
                result = json.loads(STATE_FILE.read_text(encoding='utf-8'))
            except (OSError, ValueError, json.JSONDecodeError):
                result = {'status': 'idle'}
        else:
            raise SystemExit('unsupported action')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
