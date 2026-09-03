#!/usr/bin/python3
import json
import base64
import binascii
import hashlib
import hmac
import ipaddress
import os
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
import urllib.request

try:
    import yaml
except ImportError:
    yaml = None
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

INBOX = Path('/var/lib/openstick-sms/inbox')
EMAIL_CONFIG = Path('/etc/openstick-sms/email.json')
EMAIL_RETRY_DISABLED = Path('/etc/openstick-sms/retry.disabled')
AUTH_CONFIG = Path('/etc/openstick-sms/web-auth.json')
CONTACTS_FILE = Path('/var/lib/openstick-sms/contacts.json')
NOTIFY_CONFIG = Path('/etc/openstick-notify/config.json')
NOTIFY_HISTORY = Path('/var/lib/openstick-notify/history.json')
NOTIFY_QUEUE = Path('/var/lib/openstick-notify/queue')
NOTIFY_PROGRAM = '/usr/local/sbin/openstick-notify.py'
UI_FILE = Path('/usr/local/share/openstick-ui/index.html')
MANIFEST_FILE = Path('/usr/local/share/openstick-ui/manifest.webmanifest')
ICON_FILE = Path('/usr/local/share/openstick-ui/icon.svg')
MOBILE_CONFIG = Path('/etc/openstick-control/mobile.json')
UPLINK_TRANSITION_STATE = Path('/run/openstick-uplink-transition.json')
UPLINK_MANAGER = '/usr/local/sbin/openstick-uplink-manager.py'
TRAFFIC_STATE = Path('/var/lib/openstick-control/traffic.json')
THERMAL_HISTORY_FILE = Path('/var/lib/openstick-control/thermal-history.json')
TRAFFIC_HISTORY_FILE = Path('/var/lib/openstick-control/traffic-history.json')
AUTO_CELLULAR_MARKER = Path('/run/openstick-auto-cellular.last')
PROXY_CONFIG_FILE = Path('/etc/openstick-control/proxy.json')
PROXY_HISTORY_DIR = Path('/var/lib/openstick-control/proxy-history')
SINGBOX_CONFIG_FILE = Path('/etc/sing-box/config.json')
SINGBOX_BINARY = '/usr/local/lib/sing-box/sing-box'
PROXY_RULE_DIR = Path('/etc/sing-box/rules')
PROXY_RULE_URLS = {
    'geosite-cn.srs': 'https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-cn.srs',
    'geoip-cn.srs': 'https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/geoip-cn.srs',
}
BACKUP_MAGIC = b'OPENSTICK-BACKUP-1\x00'
BACKUP_MAX_BYTES = 4 * 1024 * 1024
BACKUP_ITERATIONS = 200000
CONTROL_VERSION = '2026.09.01.3'
BUILD_DATE = '2026-09-01'
UPLINK_MANAGER_VERSION = '2026.09.01.1'
ESIM_USB_PROXY_URL = os.environ.get(
    'OPENSTICK_ESIM_USB_PROXY', 'http://192.168.137.1:17897'
)
PORT = 8080
PROXY_SERVICES = {
    'socks': ('openstick-socks-proxy.service', 1080),
    'http': ('openstick-http-proxy.service', 8081),
    'singbox': ('openstick-sing-box.service', 2080),
}
ESIM_LOCK = threading.Lock()
THERMAL_LOCK = threading.Lock()
THERMAL_HISTORY = deque(maxlen=900)
THERMAL_ARCHIVE = deque(maxlen=2880)
TRAFFIC_LOCK = threading.Lock()
PROXY_LOCK = threading.Lock()
PROXY_HEALTH = {
    'node_id': '',
    'latency_ms': None,
    'failures': 0,
    'last_check': '',
    'last_failover': '',
}
TRAFFIC_HISTORY = deque(maxlen=900)
TRAFFIC_ARCHIVE = deque(maxlen=2880)
TRAFFIC_LIVE = {
    'initialized': False,
    'rx_bytes': 0,
    'tx_bytes': 0,
    'rx_bps': 0.0,
    'tx_bps': 0.0,
    'started_at': '',
}
THERMAL_STATE = {
    'temperature': None,
    'level': 'unknown',
    'action': '正在读取温度',
    'cellular_cutoff': False,
    'cpu_limit_mhz': None,
    'ipad_limit_mbps': None,
}
ORIGINAL_CPU_LIMITS = {}
THERMAL_WARN_C = 60.0
THERMAL_THROTTLE_C = 63.0
THERMAL_CRITICAL_C = 67.0
THERMAL_CUTOFF_C = 72.0
THERMAL_RECOVER_C = 57.0

PAGE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pocket Modem Lab 短信</title><style>
:root{color-scheme:light;--bg:#f4f7fb;--card:#fff;--ink:#172033;--muted:#738096;--accent:#2563eb;--ok:#0f9f6e;--line:#e5eaf2}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--ink)}
.wrap{max-width:860px;margin:auto;padding:24px 16px 48px}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:20px}
h1{font-size:26px;margin:0 0 6px}.sub,.meta,.empty{color:var(--muted)}.status{background:#e8fff6;color:var(--ok);padding:7px 11px;border-radius:99px;font-weight:650;font-size:13px;white-space:nowrap}
.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}.stat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}.stat b{display:block;font-size:18px;margin-top:3px}.stat span{font-size:12px;color:var(--muted)}
.tools{display:flex;justify-content:space-between;align-items:center;margin:18px 2px 10px}.tools h2{font-size:16px;margin:0}.tools button,.send button{border:1px solid var(--line);background:#fff;border-radius:9px;padding:9px 13px;cursor:pointer;color:var(--ink)}
.send{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:17px;margin:0 0 20px}.send h2{font-size:16px;margin:0 0 12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.send label{display:block;font-size:12px;color:var(--muted);margin:8px 0 5px}.send input,.send textarea{width:100%;border:1px solid #cfd7e5;border-radius:9px;padding:10px;font:inherit;background:#fff}.send textarea{min-height:88px;resize:vertical}.send button{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:650;margin-top:12px}.send button:disabled{opacity:.55}.notice{font-size:13px;margin-left:10px}.badge{display:inline-block;font-size:11px;padding:3px 7px;border-radius:99px;background:#eef3ff;color:var(--accent);margin-left:7px}
.msg{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:17px;margin:10px 0;box-shadow:0 5px 18px rgba(30,50,90,.04)}
.head{display:flex;justify-content:space-between;gap:12px;align-items:baseline}.from{font-weight:700}.time{font-size:12px;color:var(--muted);white-space:nowrap}.text{margin-top:12px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}.empty{background:#fff;border:1px dashed #cdd6e4;border-radius:16px;padding:40px;text-align:center}
@media(max-width:560px){.summary,.grid{grid-template-columns:1fr}.top{align-items:center}.head{display:block}.time{display:block;margin-top:4px}}
</style></head><body><main class="wrap">
<div class="top"><div><h1>短信收件箱</h1><div class="sub">UFI003 · 本地管理页面</div></div><div class="status" id="status">正在连接</div></div>
<section class="summary"><div class="stat"><span>已保存短信</span><b id="count">—</b></div><div class="stat"><span>4G 数据</span><b id="cell">—</b></div><div class="stat"><span>LTE 信号</span><b id="signal">—</b></div><div class="stat"><span>设备温度</span><b id="temperature">—</b></div><div class="stat"><span>存储空间</span><b id="storage">—</b></div><div class="stat"><span>运行时间</span><b id="uptime">—</b></div></section>
<section class="send"><h2>发送短信</h2><div class="grid"><div><label for="number">收件号码</label><input id="number" inputmode="tel" placeholder="例如：13800138000"></div><div><label for="password">管理员密码</label><input id="password" type="password" placeholder="默认：admin"></div></div><label for="body">短信内容</label><textarea id="body" maxlength="500" placeholder="输入短信内容"></textarea><button id="sendButton" onclick="sendSms()">确认并发送</button><span class="notice" id="sendNotice"></span></section>
<section class="send"><h2>邮箱自动转发 <span class="badge" id="emailStatus">未配置</span></h2><div class="grid"><div><label for="emailRecipient">接收邮箱</label><input id="emailRecipient" type="email" placeholder="name@qq.com"></div><div><label for="emailCode">QQ 邮箱 SMTP 授权码</label><input id="emailCode" type="password" placeholder="不是 QQ 登录密码"></div></div><label for="emailAdmin">管理员密码</label><input id="emailAdmin" type="password" placeholder="默认：admin"><br><button id="emailButton" onclick="configureEmail()">保存并发送测试邮件</button><span class="notice" id="emailNotice"></span></section>
<section class="send"><h2>管理安全</h2><div class="grid"><div><label for="currentAdmin">当前管理员密码</label><input id="currentAdmin" type="password"></div><div><label for="newAdmin">新密码（至少 8 位）</label><input id="newAdmin" type="password"></div></div><button id="passwordButton" onclick="changeAdminPassword()">修改管理员密码</button><span class="notice" id="passwordNotice"></span></section>
<div class="tools"><h2>全部短信</h2><button onclick="loadMessages()">刷新</button></div><section id="messages"><div class="empty">正在读取短信…</div></section>
</main><script>
const esc=v=>String(v??'');
function card(m){const d=document.createElement('article');d.className='msg';const h=document.createElement('div');h.className='head';const f=document.createElement('div');f.className='from';f.textContent=m.number||'未知号码';const badge=document.createElement('span');badge.className='badge';badge.textContent=m.pdu_type==='submit'?'已发送':'已收到';f.append(badge);const t=document.createElement('div');t.className='time';t.textContent=m.timestamp||m.saved_at||'';h.append(f,t);const b=document.createElement('div');b.className='text';b.textContent=m.text||'[非文本短信]';d.append(h,b);return d}
async function loadMessages(){try{const r=await fetch('/api/messages',{cache:'no-store'});if(!r.ok)throw Error();const x=await r.json();count.textContent=x.messages.length;messages.replaceChildren(...(x.messages.length?x.messages.map(card):[Object.assign(document.createElement('div'),{className:'empty',textContent:'暂时没有短信'})]));status.textContent='设备在线';status.style.background='#e8fff6';status.style.color='#0f9f6e';const s=await (await fetch('/api/status',{cache:'no-store'})).json();cell.textContent=s.cellular?'已连接':'未连接';signal.textContent=s.rsrp===null?'—':`${s.rsrp} dBm`;temperature.textContent=s.temperature===null?'—':`${s.temperature} °C`;storage.textContent=`${s.storage_free} 可用`;uptime.textContent=s.uptime}catch(e){status.textContent='连接中断';status.style.background='#fff1f2';status.style.color='#d14343'}}
async function sendSms(){const n=number.value.trim(),t=body.value,p=password.value;if(!n||!t){sendNotice.textContent='请填写号码和内容';return}sendButton.disabled=true;sendNotice.textContent='正在发送…';try{const r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'admin',password:p,number:n,text:t})});const x=await r.json();if(!r.ok)throw Error(x.error||'发送失败');sendNotice.textContent='发送成功';body.value='';setTimeout(loadMessages,2000)}catch(e){sendNotice.textContent=e.message}finally{sendButton.disabled=false}}
async function loadEmailStatus(){try{const x=await (await fetch('/api/email-status',{cache:'no-store'})).json();emailStatus.textContent=x.configured?'已启用':'未配置';if(x.recipient)emailRecipient.value=x.recipient}catch(e){}}
async function configureEmail(){const c=emailCode.value.trim(),p=emailAdmin.value,rp=emailRecipient.value.trim();if(!rp){emailNotice.textContent='请输入接收邮箱';return}if(!c){emailNotice.textContent='请输入 SMTP 授权码';return}emailButton.disabled=true;emailNotice.textContent='正在验证并发送测试邮件…';try{const r=await fetch('/api/email-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'admin',password:p,recipient:rp,authorization_code:c})});const x=await r.json();if(!r.ok)throw Error(x.error||'验证失败');emailNotice.textContent='配置成功，请检查邮箱';emailCode.value='';loadEmailStatus()}catch(e){emailNotice.textContent=e.message}finally{emailButton.disabled=false}}
async function changeAdminPassword(){const current=currentAdmin.value,next=newAdmin.value;if(next.length<8){passwordNotice.textContent='新密码至少 8 位';return}passwordButton.disabled=true;passwordNotice.textContent='正在修改…';try{const r=await fetch('/api/admin-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'admin',password:current,new_password:next})});const x=await r.json();if(!r.ok)throw Error(x.error||'修改失败');passwordNotice.textContent='密码已修改';currentAdmin.value='';newAdmin.value=''}catch(e){passwordNotice.textContent=e.message}finally{passwordButton.disabled=false}}
loadMessages();loadEmailStatus();setInterval(loadMessages,5000);
</script></body></html>'''


def parse_message(path):
    values = {}
    try:
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                values[key.strip()] = value.strip()
    except OSError:
        return None
    text = values.get('sms.content.text', '')
    if re.search(r'\\[0-7]{3}', text):
        try:
            byte_text = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), text)
            text = byte_text.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return {
        'id': values.get('message-id', path.stem),
        'number': values.get('sms.content.number', ''),
        'text': text,
        'timestamp': values.get('sms.properties.timestamp', ''),
        'saved_at': values.get('received-by-openstick', ''),
        'pdu_type': values.get('sms.properties.pdu-type', ''),
        'state': values.get('sms.properties.state', ''),
        'error': values.get('sms.error', ''),
    }


def messages():
    result = [m for m in (parse_message(p) for p in INBOX.glob('*.txt')) if m]
    result = [m for m in result if m['state'] != 'receiving']
    unique = {}
    for message in result:
        key = (message['number'], message['text'], message['timestamp'], message['pdu_type'])
        unique.setdefault(key, message)
    result = list(unique.values())
    result.sort(key=lambda m: (m['timestamp'], m['saved_at']), reverse=True)
    return result


def current_modem_id():
    listed = run_command(['mmcli', '-L'], timeout=8)
    match = re.search(r'/org/freedesktop/ModemManager1/Modem/([0-9]+)', listed.stdout + listed.stderr)
    if listed.returncode or not match:
        raise RuntimeError('当前没有检测到可用的短信 modem')
    return match.group(1)


def write_outgoing_message(target, message_id, number, text, timestamp, state, error=''):
    error_line = f'sms.error: {error[:300]}\n' if error else ''
    temporary = target.with_suffix('.tmp')
    temporary.write_text(
        f'received-by-openstick: {timestamp}\n'
        f'message-id: {message_id}\n'
        f'sms.content.number: {number}\n'
        f'sms.content.text: {text}\n'
        f'sms.properties.timestamp: {timestamp}\n'
        'sms.properties.pdu-type: submit\n'
        f'sms.properties.state: {state}\n'
        f'{error_line}',
        encoding='utf-8'
    )
    temporary.replace(target)


def save_outgoing_message(number, text, state='sending'):
    timestamp = datetime.now().astimezone().isoformat(timespec='seconds')
    digest = hashlib.sha256(
        f'{number}\n{text}\n{timestamp}\n{secrets.token_hex(6)}\nsubmit'.encode('utf-8')
    ).hexdigest()
    target = INBOX / f'{digest}.txt'
    write_outgoing_message(target, digest, number, text, timestamp, state)
    return target, digest, timestamp


def prepare_sms_retry(message_id):
    message_id = str(message_id or '').strip().lower()
    if not re.fullmatch(r'[0-9a-f]{64}', message_id):
        raise ValueError('短信记录编号不正确')
    target = INBOX / f'{message_id}.txt'
    message = parse_message(target) if target.is_file() else None
    if not message or message.get('pdu_type') != 'submit':
        raise ValueError('没有找到可重发的短信')
    if message.get('state') != 'failed':
        raise ValueError('只有明确发送失败的短信可以重发')
    number = normalize_number(message.get('number', ''))
    text = str(message.get('text', ''))
    if not re.fullmatch(r'[+0-9][0-9 -]{2,24}', number) or not text or len(text) > 500:
        raise ValueError('原短信号码或内容不完整')
    timestamp = datetime.now().astimezone().isoformat(timespec='seconds')
    write_outgoing_message(target, message_id, number, text, timestamp, 'sending')
    return target, message_id, timestamp, number, text


def send_sms_background(target, message_id, timestamp, number, text):
    modem_id = None
    sms_path = None
    try:
        modem_id = current_modem_id()
        quote = lambda value: "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"
        spec = 'text=' + quote(text) + ',number=' + quote(number)
        created = subprocess.run(
            ['mmcli', '-m', modem_id, '--messaging-create-sms=' + spec],
            capture_output=True, text=True, timeout=25, check=False
        )
        found = re.search(r'/org/freedesktop/ModemManager1/SMS/[0-9]+', created.stdout + created.stderr)
        if created.returncode or not found:
            raise RuntimeError((created.stderr or created.stdout or '无法创建短信').strip())
        sms_path = found.group(0)
        sent = subprocess.run(
            ['mmcli', '-s', sms_path, '--send'],
            capture_output=True, text=True, timeout=180, check=False
        )
        if sent.returncode:
            if modem_id:
                subprocess.run(
                    ['mmcli', '-m', modem_id, '--messaging-delete-sms=' + sms_path],
                    timeout=10, check=False
                )
            raise RuntimeError((sent.stderr or sent.stdout or '运营商发送失败').strip())
        write_outgoing_message(target, message_id, number, text, timestamp, 'sent')
    except subprocess.TimeoutExpired:
        write_outgoing_message(
            target, message_id, number, text, timestamp, 'unknown',
            '运营商长时间未返回结果；为避免重复扣费，请先向收件人确认'
        )
    except (OSError, RuntimeError) as exc:
        write_outgoing_message(target, message_id, number, text, timestamp, 'failed', str(exc))


def normalize_number(number):
    return str(number or '').replace(' ', '').replace('-', '')


def contacts():
    data = read_json(CONTACTS_FILE, {'contacts': []})
    items = data.get('contacts', [])
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if isinstance(item, dict) and item.get('name') and item.get('number'):
            result.append({
                'name': str(item['name']),
                'number': normalize_number(item['number']),
                'note': str(item.get('note', ''))[:80],
                'tag': str(item.get('tag', ''))[:24],
            })
    return sorted(result, key=lambda item: item['name'].casefold())


def save_contact(name, number, note='', tag=''):
    name = name.strip()
    number = normalize_number(number)
    note = note.strip()
    tag = tag.strip()
    if not name or len(name) > 40:
        raise ValueError('联系人姓名应为 1–40 个字符')
    if not re.fullmatch(r'[+0-9][0-9]{2,24}', number):
        raise ValueError('联系人号码格式不正确')
    if len(note) > 80:
        raise ValueError('联系人备注不能超过 80 个字符')
    if len(tag) > 24:
        raise ValueError('联系人标签不能超过 24 个字符')
    items = contacts()
    existing = next((item for item in items if item['number'] == number), None)
    if existing:
        existing.update({'name': name, 'note': note, 'tag': tag})
    else:
        items.append({'name': name, 'number': number, 'note': note, 'tag': tag})
    write_json(CONTACTS_FILE, {'contacts': items})
    return contacts()


def delete_contact(number):
    number = normalize_number(number)
    items = [item for item in contacts() if item['number'] != number]
    write_json(CONTACTS_FILE, {'contacts': items})
    return contacts()


def sms_number_key(value):
    number = re.sub(r'\D', '', str(value or ''))
    if number.startswith('86') and len(number) == 13:
        number = number[2:]
    return number


def delete_sms_records(message_id='', number=''):
    message_id = str(message_id or '').strip()
    number = str(number or '').strip()
    if bool(message_id) == bool(number):
        raise ValueError('请选择删除单条短信或整个对话')
    selected = []
    target_number = sms_number_key(number)
    for path in INBOX.glob('*.txt'):
        message = parse_message(path)
        if not message:
            continue
        if message_id and message.get('id') == message_id:
            selected.append(path)
        elif number and sms_number_key(message.get('number')) == target_number:
            selected.append(path)
    if not selected:
        raise ValueError('短信不存在或已经删除')
    for path in selected:
        path.unlink(missing_ok=True)
        path.with_suffix('.forward-pending').unlink(missing_ok=True)
        path.with_suffix('.forwarded').unlink(missing_ok=True)
    return {'deleted': len(selected), 'messages': messages()}


def default_notify_config():
    return {
        'enabled': False,
        'rules': {'mode': 'all', 'numbers': [], 'keywords': [], 'contacts_only': False, 'verification_codes': True},
        'channels': {
            'bark': {'enabled': False, 'server': 'https://api.day.app', 'device_key': ''},
            'telegram': {'enabled': False, 'bot_token': '', 'chat_id': ''},
            'webhook': {'enabled': False, 'url': ''},
        },
    }


def notify_config():
    base = default_notify_config()
    saved = read_json(NOTIFY_CONFIG, {})
    if not isinstance(saved, dict):
        return base
    base['enabled'] = saved.get('enabled') is True
    if isinstance(saved.get('rules'), dict):
        base['rules'].update(saved['rules'])
    if isinstance(saved.get('channels'), dict):
        for key in base['channels']:
            if isinstance(saved['channels'].get(key), dict):
                base['channels'][key].update(saved['channels'][key])
    return base


def mask_destination(value, prefix=3, suffix=3):
    value = str(value or '')
    if not value:
        return ''
    if len(value) <= prefix + suffix:
        return '已保存'
    return value[:prefix] + '••••••' + value[-suffix:]


def public_notify_config():
    config = notify_config()
    channels = config['channels']
    pending = sum(1 for _ in NOTIFY_QUEUE.glob('*.json')) if NOTIFY_QUEUE.exists() else 0
    history = read_json(NOTIFY_HISTORY, [])
    return {
        'enabled': config['enabled'], 'rules': config['rules'], 'pending': pending,
        'history_count': len(history) if isinstance(history, list) else 0,
        'channels': {
            'bark': {
                'enabled': channels['bark'].get('enabled') is True,
                'configured': bool(channels['bark'].get('device_key')),
                'destination': mask_destination(channels['bark'].get('device_key')),
                'server': channels['bark'].get('server', 'https://api.day.app'),
            },
            'telegram': {
                'enabled': channels['telegram'].get('enabled') is True,
                'configured': bool(channels['telegram'].get('bot_token') and channels['telegram'].get('chat_id')),
                'destination': mask_destination(channels['telegram'].get('chat_id')),
            },
            'webhook': {
                'enabled': channels['webhook'].get('enabled') is True,
                'configured': bool(channels['webhook'].get('url')),
                'destination': ('已保存 HTTPS 地址' if channels['webhook'].get('url') else ''),
            },
        },
    }


def split_filter_values(value, maximum, item_length):
    if isinstance(value, str):
        items = re.split(r'[,\n\r]+', value)
    elif isinstance(value, list):
        items = value
    else:
        items = []
    cleaned = []
    for item in items:
        item = str(item).strip()
        if item and item not in cleaned:
            if len(item) > item_length:
                raise ValueError('筛选条件内容过长')
            cleaned.append(item)
    if len(cleaned) > maximum:
        raise ValueError('筛选条件数量过多')
    return cleaned


def validate_https_url(value, label, default=''):
    value = str(value or default).strip().rstrip('/')
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError(f'{label}必须是完整的 HTTPS 地址')
    if len(value) > 2048:
        raise ValueError(f'{label}过长')
    return value


def save_notify_config(request):
    previous = notify_config()
    mode = str(request.get('mode', 'all'))
    if mode not in ('all', 'match', 'codes'):
        raise ValueError('转发范围不正确')
    numbers = split_filter_values(request.get('numbers', []), 100, 30)
    for number in numbers:
        if not re.fullmatch(r'\+?[0-9][0-9 -]{2,28}', number):
            raise ValueError('筛选号码格式不正确')
    keywords = split_filter_values(request.get('keywords', []), 100, 60)
    channels = previous['channels']
    bark = channels['bark']
    telegram = channels['telegram']
    webhook = channels['webhook']
    bark_key = str(request.get('bark_device_key', '')).strip()
    telegram_token = str(request.get('telegram_bot_token', '')).strip()
    telegram_chat = str(request.get('telegram_chat_id', '')).strip()
    webhook_url = str(request.get('webhook_url', '')).strip()
    if bark_key:
        if not re.fullmatch(r'[A-Za-z0-9_-]{6,200}', bark_key):
            raise ValueError('Bark Device Key 格式不正确')
        bark['device_key'] = bark_key
    if telegram_token:
        if not re.fullmatch(r'[0-9]{5,20}:[A-Za-z0-9_-]{20,100}', telegram_token):
            raise ValueError('Telegram Bot Token 格式不正确')
        telegram['bot_token'] = telegram_token
    if telegram_chat:
        if not re.fullmatch(r'-?[0-9]{3,24}|@[A-Za-z0-9_]{5,32}', telegram_chat):
            raise ValueError('Telegram Chat ID 格式不正确')
        telegram['chat_id'] = telegram_chat
    if webhook_url:
        webhook['url'] = validate_https_url(webhook_url, 'Webhook 地址')
    bark['server'] = validate_https_url(request.get('bark_server', bark.get('server')), 'Bark 服务器', 'https://api.day.app')
    for key, channel in channels.items():
        channel['enabled'] = request.get(f'{key}_enabled') is True
    if request.get('clear_bark') is True:
        bark.update({'enabled': False, 'device_key': ''})
    if request.get('clear_telegram') is True:
        telegram.update({'enabled': False, 'bot_token': '', 'chat_id': ''})
    if request.get('clear_webhook') is True:
        webhook.update({'enabled': False, 'url': ''})
    requirements = {
        'bark': bool(bark.get('device_key')),
        'telegram': bool(telegram.get('bot_token') and telegram.get('chat_id')),
        'webhook': bool(webhook.get('url')),
    }
    for key, channel in channels.items():
        if channel['enabled'] and not requirements[key]:
            raise ValueError(f'{key} 尚未填写完整，不能开启')
    if mode == 'match' and not (numbers or keywords or request.get('contacts_only') is True or request.get('verification_codes') is True):
        raise ValueError('按条件转发时至少选择一个条件')
    saved = {
        'enabled': request.get('enabled') is True,
        'rules': {
            'mode': mode, 'numbers': numbers, 'keywords': keywords,
            'contacts_only': request.get('contacts_only') is True,
            'verification_codes': request.get('verification_codes') is True,
        },
        'channels': channels,
    }
    write_json(NOTIFY_CONFIG, saved)
    return public_notify_config()


def notify_history():
    history = read_json(NOTIFY_HISTORY, [])
    if not isinstance(history, list):
        return []
    allowed = {'id', 'message_id', 'channel', 'number', 'text', 'timestamp', 'matched_by', 'status', 'attempts', 'created_at', 'last_attempt_at', 'sent_at', 'last_error'}
    return [{key: item.get(key) for key in allowed if key in item} for item in history[:300] if isinstance(item, dict)]


def run_notify(action, value):
    if action == 'test' and value not in ('bark', 'telegram', 'webhook'):
        raise ValueError('通知渠道不正确')
    if action == 'retry' and not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('通知记录编号不正确')
    result = run_command([NOTIFY_PROGRAM, action, value], timeout=30)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or '通知发送失败').strip()[:300])
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {'ok': True}


def cellular_connected():
    try:
        out = subprocess.run(
            ['nmcli', '-t', '-f', 'DEVICE,STATE', 'device'],
            capture_output=True, text=True, timeout=3, check=False
        ).stdout
        return any(line.startswith('wwan0qmi0:connected') for line in out.splitlines())
    except (OSError, subprocess.TimeoutExpired):
        return False


def format_bytes(value):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            return f'{value:.1f} {unit}'
        value /= 1024


def device_status():
    cellular = cellular_connected()
    rsrp = None
    try:
        signal = subprocess.run(
            ['qmicli', '-d', '/dev/wwan0qmi0', '--device-open-proxy', '--nas-get-signal-info'],
            capture_output=True, text=True, timeout=5, check=False
        ).stdout
        match = re.search(r"RSRP:\s*'(-?[0-9]+) dBm'", signal)
        if match:
            rsrp = int(match.group(1))
    except (OSError, subprocess.TimeoutExpired):
        pass
    thermal = thermal_details()
    temperature = thermal.get('temperature')
    disk = shutil.disk_usage('/')
    try:
        seconds = int(float(Path('/proc/uptime').read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        seconds = 0
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    uptime = (f'{days} 天 ' if days else '') + f'{hours} 小时 {minutes} 分'
    return {
        'cellular': cellular,
        'rsrp': rsrp,
        'temperature': temperature,
        'thermal_level': thermal.get('level', 'unknown'),
        'storage_free': format_bytes(disk.free),
        'storage_total': format_bytes(disk.total),
        'uptime': uptime,
        'server_time': time.time(),
    }


def check_admin(username, password):
    if username != 'admin':
        return False
    try:
        config = json.loads(AUTH_CONFIG.read_text(encoding='utf-8'))
        salt = bytes.fromhex(config['salt'])
        expected = bytes.fromhex(config['hash'])
        iterations = int(config.get('iterations', 200000))
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return secrets.compare_digest(actual, expected)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return secrets.compare_digest(password, os.environ.get('SMS_WEB_PASSWORD', 'admin'))


def save_admin_password(password):
    salt = secrets.token_bytes(16)
    iterations = 200000
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    config = {'username': 'admin', 'salt': salt.hex(), 'hash': digest.hex(), 'iterations': iterations}
    AUTH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = AUTH_CONFIG.with_suffix('.tmp')
    temporary.write_text(json.dumps(config), encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(AUTH_CONFIG)


def run_command(args, timeout=8):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def command_json(args, default):
    result = run_command(args, timeout=4)
    if result.returncode:
        return default
    try:
        return json.loads(result.stdout)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def nm_device_status():
    result = run_command(['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device', 'status'], timeout=4)
    devices = {}
    if result.returncode:
        return devices
    for line in result.stdout.splitlines():
        values = line.split(':', 3)
        if len(values) == 4:
            devices[values[0]] = {
                'type': values[1],
                'state': values[2],
                'connection': values[3],
            }
    return devices


def connection_ipv4_method(name):
    result = run_command(['nmcli', '-g', 'ipv4.method', 'connection', 'show', name], timeout=4)
    return result.stdout.strip() if result.returncode == 0 else ''


def interface_snapshot(name, links, addresses, routes, nm_devices):
    link = links.get(name, {})
    address = addresses.get(name, {})
    ipv4 = [
        f"{item.get('local')}/{item.get('prefixlen')}"
        for item in address.get('addr_info', [])
        if item.get('family') == 'inet' and item.get('local')
    ]
    route = next((item for item in routes if item.get('dev') == name), {})
    flags = set(link.get('flags', []))
    nm = nm_devices.get(name, {})
    link_up = (
        link.get('operstate') == 'UP' or 'LOWER_UP' in flags or
        (not link and nm.get('state') == 'connected')
    )
    has_ip = bool(ipv4)
    gateway = route.get('gateway')
    if link_up and has_ip and gateway:
        state = 'limited'
    elif link_up and has_ip:
        state = 'limited'
    elif link_up:
        state = 'connecting'
    else:
        state = 'offline'
    return {
        'interface': name,
        'available': bool(link) or bool(nm),
        'link_up': link_up,
        'has_ip': has_ip,
        'addresses': ipv4,
        'gateway': gateway,
        'metric': route.get('metric'),
        'network_manager_state': nm.get('state', 'unknown'),
        'connection': nm.get('connection', ''),
        'state': state,
        'internet': None,
        'connectivity_check': 'not_run',
    }


def apply_transition_status(active, active_interface, uplinks, transition):
    """Merge the last real connectivity check into the active uplink.

    Link/IP discovery alone can only report ``limited``.  A completed Uplink
    Manager transition is the authoritative source for DNS/Internet status.
    """
    internet = None
    connectivity_check = 'not_run'
    if not active or transition.get('active') != active:
        return internet, connectivity_check

    status = transition.get('status')
    target = uplinks.get(active)
    if not isinstance(target, dict):
        return internet, connectivity_check

    if status == 'checking':
        target['state'] = 'connecting'
        target['connectivity_check'] = 'running'
        return internet, 'running'
    if status != 'online':
        return internet, connectivity_check

    checks = transition.get('checks') if isinstance(transition.get('checks'), dict) else {}
    internet = checks.get('internet')
    if internet is True:
        target['state'] = 'online'
        connectivity_check = 'passed'
    elif internet is False:
        target['state'] = 'limited'
        connectivity_check = 'failed'
    target['internet'] = internet
    target['connectivity_check'] = connectivity_check

    if active == 'usb':
        target['role'] = 'uplink'
        target['reverse_ready'] = True
        for item in target.get('interfaces', []):
            if item.get('interface') == active_interface:
                item['state'] = target['state']
                item['internet'] = internet
                item['connectivity_check'] = connectivity_check

    return internet, connectivity_check


def uplink_details():
    link_items = command_json(['ip', '-j', 'link', 'show'], [])
    address_items = command_json(['ip', '-j', '-4', 'address', 'show'], [])
    routes = command_json(['ip', '-j', '-4', 'route', 'show', 'default'], [])
    links = {item.get('ifname'): item for item in link_items if item.get('ifname')}
    addresses = {item.get('ifname'): item for item in address_items if item.get('ifname')}
    nm_devices = nm_device_status()

    usb_interfaces = [
        interface_snapshot(name, links, addresses, routes, nm_devices)
        for name in ('usb0', 'usb1') if name in links
    ]
    usb_primary = next((item for item in usb_interfaces if item['link_up']), usb_interfaces[0] if usb_interfaces else None)
    usb = dict(usb_primary or {
        'interface': 'usb0', 'available': False, 'link_up': False, 'has_ip': False,
        'addresses': [], 'gateway': None, 'metric': None, 'network_manager_state': 'unavailable',
        'connection': '', 'state': 'offline', 'internet': None, 'connectivity_check': 'not_run',
    })
    usb['interfaces'] = usb_interfaces
    usb['role'] = 'downstream' if any(
        connection_ipv4_method(item['connection']) == 'shared'
        for item in usb_interfaces if item.get('connection')
    ) else 'candidate'
    usb['reverse_ready'] = usb['available'] and usb['role'] != 'downstream'

    wifi = interface_snapshot('wlan0', links, addresses, routes, nm_devices)
    wifi_mode = wifi_details().get('mode', '')
    wifi['mode'] = wifi_mode or 'unknown'
    wifi['role'] = 'downstream' if wifi_mode in ('ap', 'hotspot') else 'uplink'
    wifi['ssid'] = wifi_details().get('ssid', '')

    cellular_name = next((name for name in nm_devices if name.startswith('wwan')), 'wwan0qmi0')
    cellular = interface_snapshot(cellular_name, links, addresses, routes, nm_devices)
    cellular['role'] = 'uplink'
    cellular['connection'] = cellular.get('connection') or 'unicom-4g'

    default_route = routes[0] if routes else {}
    active_interface = default_route.get('dev')
    if active_interface in ('usb0', 'usb1'):
        active = 'usb'
    elif active_interface == 'wlan0' and wifi['role'] == 'uplink':
        active = 'wifi'
    elif active_interface and active_interface.startswith('wwan'):
        active = 'cellular'
    else:
        active = None

    iw_info = run_command(['iw', 'phy', 'phy0', 'info'], timeout=4)
    concurrent = None
    if iw_info.returncode == 0:
        concurrent = 'interface combinations are not supported' not in iw_info.stdout

    dns = []
    try:
        for line in Path('/etc/resolv.conf').read_text(encoding='utf-8').splitlines():
            values = line.split()
            if len(values) == 2 and values[0] == 'nameserver':
                dns.append(values[1])
    except OSError:
        pass

    try:
        transition = json.loads(UPLINK_TRANSITION_STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError, json.JSONDecodeError):
        transition = {'status': 'idle'}

    uplinks = {
        'usb': usb,
        'wifi': wifi,
        'cellular': cellular,
    }
    internet, connectivity_check = apply_transition_status(
        active, active_interface, uplinks, transition
    )

    return {
        'mode': 'observe',
        'selection_enabled': False,
        'active': active,
        'active_interface': active_interface,
        'preferred_order': ['usb', 'wifi', 'cellular'],
        'internet': internet,
        'connectivity_check': connectivity_check,
        'dns': dns,
        'uplinks': uplinks,
        'capabilities': {
            'wifi_ap_sta_concurrent': concurrent,
            'wifi_uplink_requires_hotspot_off': concurrent is False,
            'usb_reverse_requires_role_switch': usb['role'] == 'downstream',
        },
        'management': {
            'usb_rndis': '192.168.68.1/24',
            'wifi_hotspot': '192.168.69.1/24',
            'usb_ecm': '192.168.70.1/24',
        },
        'transition': transition,
        'server_time': time.time(),
    }


def usb_uplink_action(action):
    if action not in ('prepare', 'enable', 'disable'):
        raise ValueError('USB 上游操作不支持')
    if not Path(UPLINK_MANAGER).is_file():
        raise RuntimeError('Uplink Manager 尚未安装')
    if action == 'prepare':
        result = run_command([UPLINK_MANAGER, 'prepare'], timeout=20)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or 'USB 上游准备失败').strip())
        try:
            return json.loads(result.stdout)
        except (ValueError, json.JSONDecodeError):
            return {'status': 'prepared'}
    manager_action = 'activate' if action == 'enable' else 'disable'
    unit = f'openstick-usb-uplink-{manager_action}-{int(time.time())}'
    result = run_command([
        'systemd-run', f'--unit={unit}', '--collect',
        UPLINK_MANAGER, manager_action,
    ], timeout=10)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or '无法启动 USB 上游任务').strip())
    return {
        'status': 'accepted',
        'action': action,
        'rollback_seconds': 30 if action == 'enable' else 0,
    }


def read_thermal_sensors():
    sensors = {}
    for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:
            name = (zone / 'type').read_text().strip()
            value = round(int((zone / 'temp').read_text().strip()) / 1000, 1)
            sensors[name] = value
        except (OSError, ValueError):
            continue
    return sensors


def set_cpu_limit(maximum_khz=None):
    applied = []
    for policy in Path('/sys/devices/system/cpu/cpufreq').glob('policy*'):
        target = policy / 'scaling_max_freq'
        try:
            if policy.name not in ORIGINAL_CPU_LIMITS:
                source = policy / 'cpuinfo_max_freq'
                ORIGINAL_CPU_LIMITS[policy.name] = int(source.read_text().strip())
            value = ORIGINAL_CPU_LIMITS[policy.name] if maximum_khz is None else min(
                int(maximum_khz), ORIGINAL_CPU_LIMITS[policy.name]
            )
            target.write_text(str(value))
            applied.append(int(target.read_text().strip()))
        except (OSError, ValueError):
            continue
    return min(applied) if applied else None


def set_ipad_rate_limit(mbps=None):
    if not Path('/sys/class/net/usb1').exists():
        return False
    if mbps is None:
        result = run_command(['tc', 'qdisc', 'replace', 'dev', 'usb1', 'root', 'fq_codel'])
    else:
        result = run_command([
            'tc', 'qdisc', 'replace', 'dev', 'usb1', 'root', 'tbf',
            'rate', f'{int(mbps)}mbit', 'burst', '64kb', 'latency', '400ms'
        ])
    return result.returncode == 0


def thermal_details(include_archive=False):
    with THERMAL_LOCK:
        result = dict(THERMAL_STATE)
        result['history'] = list(THERMAL_HISTORY)
        if include_archive:
            result['archive'] = list(THERMAL_ARCHIVE)
    result['thresholds'] = {
        'warning': THERMAL_WARN_C,
        'throttle': THERMAL_THROTTLE_C,
        'critical': THERMAL_CRITICAL_C,
        'cutoff': THERMAL_CUTOFF_C,
        'recover': THERMAL_RECOVER_C,
    }
    result['server_time'] = time.time()
    return result


def domestic_auto_reconnect_allowed():
    saved = read_json(MOBILE_CONFIG, {})
    if saved.get('auto_connect_domestic', True) is not True:
        return False
    modem = run_command(['mmcli', '-m', '0'], timeout=10)
    if modem.returncode:
        return False
    return (
        re.search(r'operator id:\s*460\d+', modem.stdout) is not None and
        re.search(r'registration:\s*home', modem.stdout, re.IGNORECASE) is not None
    )


def thermal_monitor():
    last_mode = None
    cutoff_latched = False
    with THERMAL_LOCK:
        THERMAL_ARCHIVE.extend(read_history(THERMAL_HISTORY_FILE))
    last_archive_time = int(THERMAL_ARCHIVE[-1].get('time', 0)) if THERMAL_ARCHIVE else 0
    last_archive_write = time.monotonic()
    while True:
        try:
            sensors = read_thermal_sensors()
            temperature = max(sensors.values()) if sensors else None
            previous_level = THERMAL_STATE.get('level', 'unknown')
            if temperature is None:
                level, mode, action = 'unknown', 'normal', '无法读取温度'
            elif temperature >= THERMAL_CUTOFF_C:
                level, mode = 'emergency', 'critical'
                action = '紧急高温：已临时断开蜂窝数据，等待降温后安全恢复'
                if not cutoff_latched:
                    run_command(['nmcli', 'connection', 'down', 'unicom-4g'], timeout=20)
                    cutoff_latched = True
            elif temperature >= THERMAL_CRITICAL_C:
                level, mode = 'critical', 'critical'
                action = '数据保持连接；CPU 已降至最低，iPad USB 限制为 1 Mbps'
            elif temperature >= THERMAL_THROTTLE_C:
                level, mode = 'throttle', 'throttle'
                action = '已降低 CPU 频率，并将 iPad USB 下载限制为 5 Mbps'
            elif temperature >= THERMAL_WARN_C:
                level, mode = 'warning', 'normal'
                action = '温度偏高，请保持通风并减少高流量任务'
            elif previous_level in ('throttle', 'critical', 'emergency', 'cooling') and temperature >= THERMAL_RECOVER_C:
                level = 'cooling'
                mode = 'critical' if previous_level in ('critical', 'emergency') else 'throttle'
                action = '正在降温，低于 57℃ 后解除限速'
            else:
                level, mode, action = 'normal', 'normal', '温度正常'
                if temperature is not None and temperature < THERMAL_RECOVER_C:
                    if cutoff_latched and domestic_auto_reconnect_allowed():
                        restored = run_command(['nmcli', 'connection', 'up', 'unicom-4g'], timeout=75)
                        if restored.returncode == 0:
                            cutoff_latched = False
                            action = '温度已恢复，中国本地卡蜂窝数据已自动重连'

            if mode != last_mode:
                if mode == 'throttle':
                    applied = set_cpu_limit(533333)
                    set_ipad_rate_limit(5)
                elif mode == 'critical':
                    applied = set_cpu_limit(200000)
                    set_ipad_rate_limit(1)
                else:
                    applied = set_cpu_limit(None)
                    set_ipad_rate_limit(None)
                last_mode = mode
            else:
                applied = int(THERMAL_STATE.get('cpu_limit_mhz') or 0) * 1000 if mode in ('throttle', 'critical') else None

            sample_time = int(time.time())
            with THERMAL_LOCK:
                THERMAL_HISTORY.append({
                    'time': sample_time,
                    'temperature': temperature,
                })
                if temperature is not None and sample_time - last_archive_time >= 30:
                    THERMAL_ARCHIVE.append({'time': sample_time, 'temperature': temperature})
                    last_archive_time = sample_time
                THERMAL_STATE.update({
                    'temperature': temperature,
                    'sensors': sensors,
                    'level': level,
                    'action': action,
                    'cellular_cutoff': cutoff_latched,
                    'cpu_limit_mhz': round(applied / 1000) if applied else None,
                    'ipad_limit_mbps': 5 if mode == 'throttle' else (1 if mode == 'critical' else None),
                })
                archive_snapshot = list(THERMAL_ARCHIVE)
            if not THERMAL_HISTORY_FILE.exists() or time.monotonic() - last_archive_write >= 300:
                write_history(THERMAL_HISTORY_FILE, archive_snapshot)
                last_archive_write = time.monotonic()
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        time.sleep(2)


def read_json(path, default):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else default.copy()
    except (OSError, ValueError, json.JSONDecodeError):
        return default.copy()


def write_json(path, value, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.chmod(mode)
    temporary.replace(path)


def read_history(path):
    try:
        values = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(values, list):
            return []
        cutoff = int(time.time()) - 86400
        return [item for item in values if isinstance(item, dict) and int(item.get('time', 0)) >= cutoff]
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return []


def write_history(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(list(values), separators=(',', ':')), encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(path)


def mobile_settings():
    result = {
        'apn': '',
        'roaming_allowed': True,
        'autoconnect': False,
        'traffic_limit_mb': 0,
        'disconnect_at_limit': False,
    }
    profile = run_command([
        'nmcli', '-g', 'connection.autoconnect,gsm.apn,gsm.home-only',
        'connection', 'show', 'unicom-4g'
    ])
    values = profile.stdout.splitlines()
    if values:
        result['autoconnect'] = values[0].strip().lower() == 'yes'
    if len(values) > 1:
        result['apn'] = values[1].strip()
    if len(values) > 2:
        result['roaming_allowed'] = values[2].strip().lower() != 'yes'
    saved = read_json(MOBILE_CONFIG, {})
    result['traffic_limit_mb'] = int(saved.get('traffic_limit_mb', 0) or 0)
    result['disconnect_at_limit'] = saved.get('disconnect_at_limit') is True
    result['auto_connect_domestic'] = saved.get('auto_connect_domestic', True) is True
    return result


def save_mobile_settings(apn, roaming_allowed, traffic_limit_mb, disconnect_at_limit):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', apn):
        raise ValueError('APN 格式不正确')
    if traffic_limit_mb < 0 or traffic_limit_mb > 1048576:
        raise ValueError('流量上限应为 0–1048576 MB')
    changed = run_command([
        'nmcli', 'connection', 'modify', 'unicom-4g',
        'connection.autoconnect', 'no',
        'gsm.apn', apn,
        'gsm.home-only', 'no' if roaming_allowed else 'yes',
    ], timeout=15)
    if changed.returncode:
        raise RuntimeError((changed.stderr or changed.stdout or '移动网络配置保存失败').strip())
    saved = read_json(MOBILE_CONFIG, {})
    saved.update({
        'traffic_limit_mb': traffic_limit_mb,
        'disconnect_at_limit': disconnect_at_limit,
    })
    write_json(MOBILE_CONFIG, saved)
    return mobile_settings()


def set_auto_connect_domestic(enabled):
    saved = read_json(MOBILE_CONFIG, {})
    saved['auto_connect_domestic'] = enabled is True
    write_json(MOBILE_CONFIG, saved)
    try:
        AUTO_CELLULAR_MARKER.unlink()
    except FileNotFoundError:
        pass
    return mobile_settings()


def proxy_details():
    result = {}
    for kind, (service, port) in PROXY_SERVICES.items():
        active = run_command(['systemctl', 'is-active', service], timeout=5).returncode == 0
        enabled = run_command(['systemctl', 'is-enabled', service], timeout=5).returncode == 0
        result[kind] = {'active': active, 'enabled': enabled, 'port': port}
    return result


def set_proxy_enabled(kind, enabled):
    if kind not in PROXY_SERVICES:
        raise ValueError('未知代理类型')
    service = PROXY_SERVICES[kind][0]
    action = ['systemctl', 'enable', '--now', service] if enabled else ['systemctl', 'disable', '--now', service]
    changed = run_command(action, timeout=20)
    if changed.returncode:
        raise RuntimeError((changed.stderr or changed.stdout or '代理状态修改失败').strip())
    return proxy_details()


def proxy_settings():
    saved = read_json(PROXY_CONFIG_FILE, {})
    mode = saved.get('mode', 'direct')
    if mode not in ('direct', 'rule', 'global'):
        mode = 'direct'
    nodes = saved.get('nodes', [])
    subscriptions = saved.get('subscriptions', [])
    strategy = str(saved.get('strategy', 'manual'))
    if strategy not in ('manual', 'latency', 'fallback'):
        strategy = 'manual'
    candidates = saved.get('strategy_candidates', [])
    if not isinstance(candidates, list):
        candidates = []
    return {
        'mode': mode,
        'selected_node': str(saved.get('selected_node', 'direct')),
        'nodes': nodes if isinstance(nodes, list) else [],
        'subscriptions': subscriptions if isinstance(subscriptions, list) else [],
        'health_check': saved.get('health_check') is True,
        'strategy': strategy,
        'strategy_candidates': [str(item) for item in candidates],
    }


def public_proxy_settings():
    saved = proxy_settings()
    nodes = []
    for node in saved['nodes']:
        if not isinstance(node, dict):
            continue
        nodes.append({
            'id': str(node.get('id', '')),
            'name': str(node.get('name', '未命名节点')),
            'type': str(node.get('type', 'unknown')),
            'server': str(node.get('server', '')),
            'port': int(node.get('port', 0) or 0),
            'source': str(node.get('source', 'manual')),
            'subscription_id': str(node.get('subscription_id', '')),
        })
    subscriptions = []
    for item in saved['subscriptions']:
        if not isinstance(item, dict):
            continue
        subscriptions.append({
            'id': str(item.get('id', '')),
            'name': str(item.get('name', '未命名订阅')),
            'updated_at': str(item.get('updated_at', '')),
            'node_count': sum(1 for node in nodes if node['subscription_id'] == item.get('id')),
            'url_saved': bool(item.get('url')),
        })
    selected = saved['selected_node']
    if selected != 'direct' and not any(node['id'] == selected for node in nodes):
        selected = 'direct'
    return {
        'mode': saved['mode'],
        'selected_node': selected,
        'nodes': nodes,
        'subscriptions': subscriptions,
        'service': proxy_details().get('singbox', {}),
        'mixed_port': 2080,
        'rules': proxy_rule_status(),
        'health_check': saved.get('health_check') is True,
        'health': dict(PROXY_HEALTH),
        'strategy': saved.get('strategy', 'manual'),
        'strategy_candidates': saved.get('strategy_candidates', []),
        'tailscale': tailscale_status(saved),
    }


def proxy_history():
    entries = []
    try:
        paths = sorted(PROXY_HISTORY_DIR.glob('*.json'), reverse=True)[:20]
    except OSError:
        paths = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            config = data.get('config', {}) if isinstance(data, dict) else {}
            entries.append({
                'id': path.stem,
                'created_at': str(data.get('created_at', '')),
                'reason': str(data.get('reason', '配置变更')),
                'mode': str(config.get('mode', 'direct')),
                'node_count': len(config.get('nodes', [])) if isinstance(config.get('nodes'), list) else 0,
            })
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return entries


def save_proxy_snapshot(config, reason):
    if not isinstance(config, dict) or not config:
        return
    PROXY_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    path = PROXY_HISTORY_DIR / f'{stamp}.json'
    write_json(path, {
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'reason': str(reason)[:100],
        'config': config,
    })
    path.chmod(0o600)
    for old in sorted(PROXY_HISTORY_DIR.glob('*.json'), reverse=True)[20:]:
        old.unlink(missing_ok=True)


def proxy_logs():
    result = run_command(['journalctl', '-u', 'openstick-sing-box.service', '-n', '160', '--no-pager', '--output=short-iso'], timeout=8)
    raw = result.stdout if result.returncode == 0 else result.stderr
    raw = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', raw or '')
    raw = re.sub(r'(?i)(password|token|uuid|private[_ -]?key|authorization)([=: ]+)[^\s,}]+', r'\1\2<已隐藏>', raw)
    raw = re.sub(r'https?://[^\s]+', '<链接已隐藏>', raw)
    return {'lines': raw.splitlines()[-160:], 'service': proxy_details().get('singbox', {})}


def proxy_rule_status():
    details = []
    for name in ('geosite-cn.srs', 'geoip-cn.srs'):
        path = PROXY_RULE_DIR / name
        try:
            payload = path.read_bytes()
            details.append({
                'name': name,
                'size': len(payload),
                'sha256': hashlib.sha256(payload).hexdigest()[:12],
                'updated_at': datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds'),
            })
        except OSError:
            details.append({'name': name, 'size': 0, 'sha256': '', 'updated_at': ''})
    return {'installed': all(item['size'] > 0 for item in details), 'files': details}


def clean_proxy_id(value, prefix='node'):
    cleaned = re.sub(r'[^a-zA-Z0-9_-]+', '-', str(value)).strip('-').lower()
    return (cleaned[:44] or f'{prefix}-{secrets.token_hex(4)}')


def proxy_node_outbound(node):
    kind = str(node.get('type', ''))
    tag = f"node-{clean_proxy_id(node.get('id', ''))}"
    common = {
        'type': kind,
        'tag': tag,
        'server': str(node.get('server', '')),
        'server_port': int(node.get('port', 0)),
        'bind_interface': 'wwan0',
    }
    if kind == 'shadowsocks':
        common.update({
            'method': str(node.get('method', '')),
            'password': str(node.get('password', '')),
        })
    elif kind == 'trojan':
        common['password'] = str(node.get('password', ''))
        common['tls'] = {
            'enabled': True,
            'server_name': str(node.get('server_name') or node.get('server', '')),
            'insecure': node.get('insecure') is True,
        }
    elif kind in ('vless', 'vmess'):
        common['uuid'] = str(node.get('uuid', ''))
        if kind == 'vless' and node.get('flow'):
            common['flow'] = str(node['flow'])
        if kind == 'vmess':
            common['security'] = str(node.get('security') or 'auto')
            common['alter_id'] = int(node.get('alter_id', 0) or 0)
        if node.get('tls', True) is True:
            common['tls'] = {
                'enabled': True,
                'server_name': str(node.get('server_name') or node.get('server', '')),
                'insecure': node.get('insecure') is True,
            }
            if node.get('reality_public_key'):
                common['tls']['utls'] = {
                    'enabled': True,
                    'fingerprint': str(node.get('client_fingerprint') or 'chrome'),
                }
                common['tls']['reality'] = {
                    'enabled': True,
                    'public_key': str(node['reality_public_key']),
                    'short_id': str(node.get('reality_short_id', '')),
                }
        if node.get('transport_type') == 'ws':
            transport = {'type': 'ws', 'path': str(node.get('transport_path') or '/')}
            if node.get('transport_host'):
                transport['headers'] = {'Host': str(node['transport_host'])}
            common['transport'] = transport
    else:
        raise ValueError('当前只支持 Shadowsocks、Trojan、VLESS 和 VMess 节点')
    return common


def proxy_wireguard_endpoint(node):
    tag = f"node-{clean_proxy_id(node.get('id', ''))}"
    peers = []
    for peer in node.get('peers', []):
        item = {
            'address': str(peer.get('address', '')),
            'port': int(peer.get('port', 0)),
            'public_key': str(peer.get('public_key', '')),
            'allowed_ips': list(peer.get('allowed_ips', [])),
        }
        if peer.get('pre_shared_key'):
            item['pre_shared_key'] = str(peer['pre_shared_key'])
        if int(peer.get('persistent_keepalive_interval', 0) or 0) > 0:
            item['persistent_keepalive_interval'] = int(peer['persistent_keepalive_interval'])
        peers.append(item)
    return {
        'type': 'wireguard',
        'tag': tag,
        'system': False,
        'mtu': int(node.get('mtu', 1408) or 1408),
        'address': list(node.get('address', [])),
        'private_key': str(node.get('private_key', '')),
        'peers': peers,
        'bind_interface': 'wwan0',
    }


def proxy_tailscale_endpoint(node):
    endpoint = {
        'type': 'tailscale',
        'tag': f"node-{clean_proxy_id(node.get('id', 'tailscale'))}",
        'state_directory': '/var/lib/openstick-sing-box/tailscale',
        'hostname': str(node.get('hostname') or 'openstick-ufi003'),
        'accept_routes': node.get('accept_routes') is True,
        'exit_node': str(node.get('exit_node', '')),
        'exit_node_allow_lan_access': True,
        'advertise_exit_node': node.get('advertise_exit_node') is True,
        'bind_interface': 'wwan0',
    }
    if node.get('auth_key'):
        endpoint['auth_key'] = str(node['auth_key'])
    return endpoint


def tailscale_status(saved=None):
    saved = saved or proxy_settings()
    node = next((item for item in saved.get('nodes', []) if item.get('type') == 'tailscale'), None)
    log = run_command(['journalctl', '-u', 'openstick-sing-box.service', '-n', '100', '--no-pager'], timeout=5)
    match = re.findall(r'https://login\.tailscale\.com/[A-Za-z0-9/_?=&.-]+', log.stdout if log.returncode == 0 else '')
    return {
        'configured': node is not None,
        'hostname': str(node.get('hostname', '')) if node else '',
        'exit_node': str(node.get('exit_node', '')) if node else '',
        'accept_routes': node.get('accept_routes') is True if node else False,
        'advertise_exit_node': node.get('advertise_exit_node') is True if node else False,
        'auth_key_saved': bool(node.get('auth_key')) if node else False,
        'login_url': match[-1] if match else '',
    }


def parse_wireguard_config(name, text):
    if not name or len(name) > 80:
        raise ValueError('WireGuard 名称应为 1–80 个字符')
    if not text or len(text) > 16384:
        raise ValueError('WireGuard 配置为空或过大')
    interface = {}
    peers = []
    current = None
    for original in text.splitlines():
        line = original.strip()
        if not line or line.startswith(('#', ';')):
            continue
        if line.lower() == '[interface]':
            current = interface
            continue
        if line.lower() == '[peer]':
            current = {}
            peers.append(current)
            continue
        if current is None or '=' not in line:
            continue
        key, value = (part.strip() for part in line.split('=', 1))
        current[key.lower()] = value
    private_key = interface.get('privatekey', '')
    addresses = [item.strip() for item in interface.get('address', '').split(',') if item.strip()]
    if not private_key or not addresses or not peers:
        raise ValueError('配置需要 Interface 的 PrivateKey、Address 和至少一个 Peer')
    parsed_peers = []
    for peer in peers:
        endpoint = peer.get('endpoint', '')
        if endpoint.startswith('[') and ']:' in endpoint:
            host, port = endpoint[1:].rsplit(']:', 1)
        elif ':' in endpoint:
            host, port = endpoint.rsplit(':', 1)
        else:
            raise ValueError('WireGuard Peer Endpoint 格式不正确')
        allowed_ips = [item.strip() for item in peer.get('allowedips', '').split(',') if item.strip()]
        if not peer.get('publickey') or not allowed_ips:
            raise ValueError('WireGuard Peer 需要 PublicKey 和 AllowedIPs')
        try:
            port_number = int(port)
            keepalive = int(peer.get('persistentkeepalive', '0') or 0)
        except ValueError:
            raise ValueError('WireGuard 端口或保活时间格式不正确')
        parsed_peers.append({
            'address': host,
            'port': port_number,
            'public_key': peer['publickey'],
            'pre_shared_key': peer.get('presharedkey', ''),
            'allowed_ips': allowed_ips,
            'persistent_keepalive_interval': keepalive,
        })
    try:
        mtu = int(interface.get('mtu', '1408') or 1408)
    except ValueError:
        raise ValueError('WireGuard MTU 格式不正确')
    node = {
        'id': clean_proxy_id(f'wireguard-{secrets.token_hex(5)}'),
        'name': name,
        'type': 'wireguard',
        'source': 'manual',
        'subscription_id': '',
        'server': parsed_peers[0]['address'],
        'port': parsed_peers[0]['port'],
        'private_key': private_key,
        'address': addresses,
        'mtu': mtu,
        'peers': parsed_peers,
    }
    return validate_proxy_node(node)


def validate_proxy_node(node):
    kind = str(node.get('type', '')).lower()
    if kind not in ('shadowsocks', 'trojan', 'vless', 'vmess', 'wireguard', 'tailscale'):
        raise ValueError('请选择受支持的节点类型')
    name = str(node.get('name', '')).strip()
    server = str(node.get('server', '')).strip()
    if not name or len(name) > 80:
        raise ValueError('节点名称应为 1–80 个字符')
    if not server or len(server) > 255 or re.search(r'\s', server):
        raise ValueError('服务器地址格式不正确')
    try:
        port = int(node.get('port', 0))
    except (TypeError, ValueError):
        raise ValueError('端口格式不正确')
    if port < 1 or port > 65535:
        raise ValueError('端口应在 1–65535 之间')
    result = {
        'id': clean_proxy_id(node.get('id') or f'manual-{secrets.token_hex(5)}'),
        'name': name,
        'type': kind,
        'server': server,
        'port': port,
        'source': str(node.get('source', 'manual')),
        'subscription_id': str(node.get('subscription_id', '')),
    }
    if kind == 'wireguard':
        private_key = str(node.get('private_key', '')).strip()
        addresses = node.get('address', [])
        peers = node.get('peers', [])
        if not private_key or not isinstance(addresses, list) or not addresses or not isinstance(peers, list) or not peers:
            raise ValueError('WireGuard 配置缺少密钥、地址或 Peer')
        result.update({
            'private_key': private_key,
            'address': [str(item) for item in addresses],
            'mtu': int(node.get('mtu', 1408) or 1408),
            'peers': peers,
        })
        return result
    if kind == 'tailscale':
        result.update({
            'hostname': str(node.get('hostname') or 'openstick-ufi003').strip()[:63],
            'auth_key': str(node.get('auth_key', '')).strip(),
            'exit_node': str(node.get('exit_node', '')).strip(),
            'accept_routes': node.get('accept_routes') is True,
            'advertise_exit_node': node.get('advertise_exit_node') is True,
        })
        return result
    if kind == 'shadowsocks':
        method = str(node.get('method', '')).strip()
        password = str(node.get('password', ''))
        if method not in ('aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm', 'chacha20-ietf-poly1305', 'xchacha20-ietf-poly1305', '2022-blake3-aes-128-gcm', '2022-blake3-aes-256-gcm', '2022-blake3-chacha20-poly1305'):
            raise ValueError('Shadowsocks 加密方式不受支持')
        if not password:
            raise ValueError('请填写 Shadowsocks 密码')
        result.update({'method': method, 'password': password})
    elif kind == 'trojan':
        password = str(node.get('password', ''))
        if not password:
            raise ValueError('请填写 Trojan 密码')
        result.update({
            'password': password,
            'server_name': str(node.get('server_name') or server).strip(),
            'insecure': node.get('insecure') is True,
        })
    else:
        uuid = str(node.get('uuid', '')).strip()
        if not re.fullmatch(r'[0-9a-fA-F-]{32,36}', uuid):
            raise ValueError('VLESS UUID 格式不正确')
        result.update({
            'uuid': uuid,
            'flow': str(node.get('flow', '')).strip() if kind == 'vless' else '',
            'security': str(node.get('security', 'auto')).strip() if kind == 'vmess' else '',
            'alter_id': int(node.get('alter_id', 0) or 0) if kind == 'vmess' else 0,
            'tls': node.get('tls') is not False,
            'server_name': str(node.get('server_name') or server).strip(),
            'insecure': node.get('insecure') is True,
            'transport_type': str(node.get('transport_type', '')).strip(),
            'transport_path': str(node.get('transport_path', '')).strip(),
            'transport_host': str(node.get('transport_host', '')).strip(),
            'reality_public_key': str(node.get('reality_public_key', '')).strip(),
            'reality_short_id': str(node.get('reality_short_id', '')).strip(),
            'client_fingerprint': str(node.get('client_fingerprint', '')).strip(),
        })
        if result['client_fingerprint'] and not re.fullmatch(r'[A-Za-z0-9._-]{1,32}', result['client_fingerprint']):
            raise ValueError('TLS 客户端指纹格式不正确')
    return result


def build_singbox_config(saved):
    direct = {'type': 'direct', 'tag': 'cellular-direct', 'bind_interface': 'wwan0'}
    outbounds = [direct]
    endpoints = []
    node_map = {}
    for node in saved['nodes']:
        if node.get('type') == 'wireguard':
            endpoint = proxy_wireguard_endpoint(node)
            endpoints.append(endpoint)
            node_map[str(node.get('id'))] = endpoint['tag']
        elif node.get('type') == 'tailscale':
            endpoint = proxy_tailscale_endpoint(node)
            endpoints.append(endpoint)
            node_map[str(node.get('id'))] = endpoint['tag']
        else:
            outbound = proxy_node_outbound(node)
            outbounds.append(outbound)
            node_map[str(node.get('id'))] = outbound['tag']
    selected_id = saved.get('selected_node', 'direct')
    selected_tag = node_map.get(selected_id, 'cellular-direct')
    mode = saved.get('mode', 'direct')
    target = selected_tag if mode in ('rule', 'global') else 'cellular-direct'
    allowed = ['127.0.0.0/8', '192.168.68.0/24', '192.168.69.0/24', '192.168.70.0/24']
    rules = []
    rule_sets = []
    rule_status = proxy_rule_status()
    if rule_status['installed']:
        rule_sets = [
            {'type': 'local', 'tag': 'geosite-cn', 'format': 'binary', 'path': str(PROXY_RULE_DIR / 'geosite-cn.srs')},
            {'type': 'local', 'tag': 'geoip-cn', 'format': 'binary', 'path': str(PROXY_RULE_DIR / 'geoip-cn.srs')},
        ]
    if mode == 'rule' and selected_tag != 'cellular-direct':
        if not rule_status['installed']:
            raise ValueError('中国直连规则库尚未安装')
        rules.extend([
            {'source_ip_cidr': allowed, 'action': 'sniff'},
            {'source_ip_cidr': allowed, 'ip_is_private': True, 'action': 'route', 'outbound': 'cellular-direct'},
            {'source_ip_cidr': allowed, 'rule_set': ['geosite-cn', 'geoip-cn'], 'action': 'route', 'outbound': 'cellular-direct'},
        ])
    rules.extend([
        {'source_ip_cidr': allowed, 'action': 'route', 'outbound': target},
        {'action': 'reject'},
    ])
    route = {'rules': rules, 'final': target}
    if rule_sets:
        route['rule_set'] = rule_sets
    config = {
        'log': {'level': 'info', 'timestamp': True},
        'inbounds': [{'type': 'mixed', 'tag': 'local-mixed-in', 'listen': '0.0.0.0', 'listen_port': 2080}],
        'outbounds': outbounds,
        'route': route,
    }
    if endpoints:
        config['endpoints'] = endpoints
    return config


def apply_proxy_settings(saved, reason='配置变更', record_history=True):
    with PROXY_LOCK:
        config = build_singbox_config(saved)
        SINGBOX_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = SINGBOX_CONFIG_FILE.with_suffix('.new')
        temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.chmod(0o640)
        shutil.chown(temporary, user='root', group='sing-box')
        checked = run_command([SINGBOX_BINARY, 'check', '-c', str(temporary)], timeout=15)
        if checked.returncode:
            temporary.unlink(missing_ok=True)
            detail = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', checked.stderr or checked.stdout or 'sing-box 配置检查失败')
            raise ValueError(detail.strip()[:500])
        previous = SINGBOX_CONFIG_FILE.read_bytes() if SINGBOX_CONFIG_FILE.exists() else None
        previous_preferences = read_json(PROXY_CONFIG_FILE, {})
        temporary.replace(SINGBOX_CONFIG_FILE)
        write_json(PROXY_CONFIG_FILE, saved)
        active = run_command(['systemctl', 'is-active', 'openstick-sing-box.service'], timeout=5).returncode == 0
        if active:
            restarted = run_command(['systemctl', 'restart', 'openstick-sing-box.service'], timeout=20)
            time.sleep(1)
            healthy = run_command(['systemctl', 'is-active', 'openstick-sing-box.service'], timeout=5).returncode == 0
            if restarted.returncode or not healthy:
                if previous is not None:
                    rollback = SINGBOX_CONFIG_FILE.with_suffix('.rollback')
                    rollback.write_bytes(previous)
                    rollback.chmod(0o640)
                    shutil.chown(rollback, user='root', group='sing-box')
                    rollback.replace(SINGBOX_CONFIG_FILE)
                    if previous_preferences:
                        write_json(PROXY_CONFIG_FILE, previous_preferences)
                    run_command(['systemctl', 'restart', 'openstick-sing-box.service'], timeout=20)
                raise RuntimeError('新配置无法启动，已恢复原配置')
        if record_history and previous_preferences and previous_preferences != saved:
            save_proxy_snapshot(previous_preferences, reason)
    return public_proxy_settings()


def eligible_strategy_nodes(saved):
    usable = [node for node in saved.get('nodes', []) if node.get('type') not in ('wireguard', 'tailscale')]
    wanted = [str(item) for item in saved.get('strategy_candidates', [])]
    if wanted:
        by_id = {str(node.get('id')): node for node in usable}
        usable = [by_id[item] for item in wanted if item in by_id]
    return usable


def select_strategy_node(saved, results=None):
    candidates = eligible_strategy_nodes(saved)
    if not candidates:
        raise ValueError('策略组中没有可用的普通代理节点')
    checked = results or {}
    if not checked:
        for node in candidates:
            node_id = str(node.get('id', ''))
            try:
                checked[node_id] = {'ok': True, 'latency_ms': tcp_node_latency(node, timeout=5)}
            except RuntimeError as exc:
                checked[node_id] = {'ok': False, 'error': str(exc)}
    healthy = [node for node in candidates if checked.get(str(node.get('id')), {}).get('ok')]
    if not healthy:
        raise RuntimeError('策略组内没有可连接的节点')
    if saved.get('strategy') == 'latency':
        healthy.sort(key=lambda node: checked[str(node.get('id'))].get('latency_ms', 10**9))
    chosen = healthy[0]
    saved['selected_node'] = str(chosen.get('id'))
    return chosen, checked


def restore_proxy_snapshot(snapshot_id):
    if not re.fullmatch(r'[0-9-]{20,32}', snapshot_id):
        raise ValueError('配置历史编号不正确')
    path = PROXY_HISTORY_DIR / f'{snapshot_id}.json'
    if not path.exists():
        raise ValueError('配置历史不存在或已过期')
    data = json.loads(path.read_text(encoding='utf-8'))
    saved = data.get('config')
    if not isinstance(saved, dict):
        raise ValueError('配置历史内容不正确')
    return apply_proxy_settings(saved, reason='恢复历史配置')


def save_proxy_preferences(request):
    saved = proxy_settings()
    action = str(request.get('action', ''))
    if action == 'set_mode':
        mode = str(request.get('mode', ''))
        if mode not in ('direct', 'rule', 'global'):
            raise ValueError('未知代理模式')
        if mode != 'direct' and saved.get('selected_node', 'direct') == 'direct':
            raise ValueError('请先添加并选择一个代理节点')
        selected = next((node for node in saved['nodes'] if str(node.get('id')) == str(saved.get('selected_node'))), None)
        if mode != 'direct' and selected and selected.get('type') == 'tailscale' and not selected.get('exit_node'):
            raise ValueError('Tailscale 尚未配置出口节点')
        saved['mode'] = mode
    elif action == 'select_node':
        node_id = str(request.get('node_id', 'direct'))
        if node_id != 'direct' and not any(str(node.get('id')) == node_id for node in saved['nodes']):
            raise ValueError('节点不存在')
        selected = next((node for node in saved['nodes'] if str(node.get('id')) == node_id), None)
        if selected and selected.get('type') == 'tailscale' and not selected.get('exit_node'):
            raise ValueError('请先为 Tailscale 填写出口节点')
        saved['selected_node'] = node_id
        if node_id == 'direct':
            saved['mode'] = 'direct'
    elif action == 'save_node':
        node = validate_proxy_node(request.get('node') if isinstance(request.get('node'), dict) else {})
        saved['nodes'] = [item for item in saved['nodes'] if str(item.get('id')) != node['id']]
        saved['nodes'].append(node)
        if saved.get('selected_node') in ('', 'direct'):
            saved['selected_node'] = node['id']
    elif action == 'save_wireguard':
        node = parse_wireguard_config(str(request.get('name', '')).strip(), str(request.get('config', '')))
        saved['nodes'].append(node)
        if saved.get('selected_node') in ('', 'direct'):
            saved['selected_node'] = node['id']
    elif action == 'save_tailscale':
        hostname = str(request.get('hostname') or 'openstick-ufi003').strip()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,62}', hostname):
            raise ValueError('Tailscale 设备名称格式不正确')
        existing_tailscale = next((item for item in saved['nodes'] if item.get('type') == 'tailscale'), {})
        auth_key = str(request.get('auth_key', '')).strip() or str(existing_tailscale.get('auth_key', ''))
        node = validate_proxy_node({
            'id': 'tailscale-exit',
            'name': 'Tailscale' + (f" · {request.get('exit_node')}" if request.get('exit_node') else ''),
            'type': 'tailscale',
            'server': 'controlplane.tailscale.com',
            'port': 443,
            'source': 'manual',
            'hostname': hostname,
            'auth_key': auth_key,
            'exit_node': str(request.get('exit_node', '')).strip(),
            'accept_routes': request.get('accept_routes') is True,
            'advertise_exit_node': request.get('advertise_exit_node') is True,
        })
        saved['nodes'] = [item for item in saved['nodes'] if item.get('type') != 'tailscale'] + [node]
    elif action == 'delete_node':
        node_id = str(request.get('node_id', ''))
        saved['nodes'] = [item for item in saved['nodes'] if str(item.get('id')) != node_id]
        if saved.get('selected_node') == node_id:
            saved['selected_node'] = 'direct'
            saved['mode'] = 'direct'
    elif action == 'save_subscription':
        name = str(request.get('name', '')).strip()
        url = str(request.get('url', '')).strip()
        parsed = urllib.parse.urlsplit(url)
        if not name or len(name) > 80:
            raise ValueError('订阅名称应为 1–80 个字符')
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or len(url) > 2048:
            raise ValueError('订阅链接格式不正确')
        item_id = clean_proxy_id(request.get('id') or f'sub-{secrets.token_hex(5)}', 'sub')
        saved['subscriptions'] = [item for item in saved['subscriptions'] if str(item.get('id')) != item_id]
        saved['subscriptions'].append({'id': item_id, 'name': name, 'url': url, 'updated_at': ''})
    elif action == 'set_health_check':
        saved['health_check'] = request.get('enabled') is True
    elif action == 'set_strategy':
        strategy = str(request.get('strategy', 'manual'))
        if strategy not in ('manual', 'latency', 'fallback'):
            raise ValueError('未知节点策略')
        candidates = request.get('candidates', [])
        if not isinstance(candidates, list) or len(candidates) > 500:
            raise ValueError('策略组节点格式不正确')
        existing = {str(node.get('id')) for node in saved['nodes']}
        saved['strategy'] = strategy
        saved['strategy_candidates'] = [str(item) for item in candidates if str(item) in existing]
        if strategy != 'manual' and request.get('run_now') is True:
            chosen, _ = select_strategy_node(saved)
            if saved.get('mode') == 'direct':
                saved['mode'] = 'global'
    elif action == 'delete_subscription':
        item_id = str(request.get('subscription_id', ''))
        removed_ids = {str(node.get('id')) for node in saved['nodes'] if str(node.get('subscription_id')) == item_id}
        saved['subscriptions'] = [item for item in saved['subscriptions'] if str(item.get('id')) != item_id]
        saved['nodes'] = [node for node in saved['nodes'] if str(node.get('subscription_id')) != item_id]
        if saved.get('selected_node') in removed_ids:
            saved['selected_node'] = 'direct'
            saved['mode'] = 'direct'
    else:
        raise ValueError('未知代理设置操作')
    return apply_proxy_settings(saved, reason={
        'set_mode': '切换运行模式', 'select_node': '切换节点', 'save_node': '保存节点',
        'save_wireguard': '导入 WireGuard', 'save_tailscale': '保存 Tailscale',
        'delete_node': '删除节点', 'save_subscription': '保存订阅',
        'delete_subscription': '删除订阅', 'set_health_check': '调整健康检查',
        'set_strategy': '调整节点策略',
    }.get(action, '代理配置变更'))


def parse_proxy_uri(link, subscription_id=''):
    link = link.strip()
    scheme = link.split(':', 1)[0].lower() if ':' in link else ''
    if scheme not in ('ss', 'trojan', 'vless', 'vmess'):
        return None
    if scheme == 'vmess':
        raw = link[8:].split('#', 1)[0]
        try:
            item = json.loads(base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)).decode('utf-8'))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        source = {
            'name': str(item.get('ps') or item.get('add') or 'VMess'),
            'type': 'vmess',
            'server': str(item.get('add', '')),
            'port': item.get('port', 443),
            'uuid': str(item.get('id', '')),
            'security': str(item.get('scy') or 'auto'),
            'alter_id': item.get('aid', 0),
            'tls': str(item.get('tls', '')).lower() in ('tls', '1', 'true'),
            'server_name': str(item.get('sni') or item.get('host') or item.get('add', '')),
            'transport_type': 'ws' if str(item.get('net', '')).lower() == 'ws' else '',
            'transport_path': str(item.get('path', '')),
            'transport_host': str(item.get('host', '')),
        }
    elif scheme == 'ss':
        raw = link[5:]
        fragment = ''
        if '#' in raw:
            raw, fragment = raw.split('#', 1)
        raw = raw.split('?', 1)[0]
        if '@' not in raw:
            try:
                raw = base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)).decode('utf-8')
            except (ValueError, UnicodeDecodeError):
                return None
        credentials, address = raw.rsplit('@', 1)
        try:
            decoded = base64.urlsafe_b64decode(credentials + '=' * (-len(credentials) % 4)).decode('utf-8')
            if ':' in decoded:
                credentials = decoded
        except (ValueError, UnicodeDecodeError):
            pass
        if ':' not in credentials or ':' not in address:
            return None
        method, password = credentials.split(':', 1)
        server, port = address.rsplit(':', 1)
        source = {'name': urllib.parse.unquote(fragment) or server, 'type': 'shadowsocks', 'server': server.strip('[]'), 'port': port, 'method': method, 'password': urllib.parse.unquote(password)}
    else:
        parsed = urllib.parse.urlsplit(link)
        query = urllib.parse.parse_qs(parsed.query)
        source = {
            'name': urllib.parse.unquote(parsed.fragment) or (parsed.hostname or scheme),
            'type': scheme,
            'server': parsed.hostname or '',
            'port': parsed.port or 443,
            'server_name': (query.get('sni') or query.get('peer') or [parsed.hostname or ''])[0],
            'insecure': (query.get('allowInsecure') or ['0'])[0] in ('1', 'true'),
        }
        if scheme == 'trojan':
            source['password'] = urllib.parse.unquote(parsed.username or '')
        else:
            source.update({
                'uuid': urllib.parse.unquote(parsed.username or ''),
                'flow': (query.get('flow') or [''])[0],
                'tls': (query.get('security') or ['tls'])[0] != 'none',
                'transport_type': (query.get('type') or [''])[0],
                'transport_path': urllib.parse.unquote((query.get('path') or [''])[0]),
                'transport_host': (query.get('host') or [''])[0],
                'reality_public_key': (query.get('pbk') or [''])[0],
                'reality_short_id': (query.get('sid') or [''])[0],
                'client_fingerprint': (query.get('fp') or [''])[0],
            })
    source['source'] = 'subscription'
    source['subscription_id'] = subscription_id
    digest = hashlib.sha256(link.encode('utf-8')).hexdigest()[:12]
    source['id'] = clean_proxy_id(f'{subscription_id}-{digest}')
    return validate_proxy_node(source)


def clash_proxy_node(item, subscription_id, index=0):
    if not isinstance(item, dict):
        return None
    clash_type = str(item.get('type', '')).lower()
    kind = {'ss': 'shadowsocks', 'shadowsocks': 'shadowsocks', 'trojan': 'trojan', 'vless': 'vless', 'vmess': 'vmess'}.get(clash_type)
    if kind is None:
        return None
    ws = item.get('ws-opts') if isinstance(item.get('ws-opts'), dict) else {}
    headers = ws.get('headers') if isinstance(ws.get('headers'), dict) else {}
    reality = item.get('reality-opts') if isinstance(item.get('reality-opts'), dict) else {}
    name = str(item.get('name') or f'{kind}-{index + 1}')
    source = {
        'name': name,
        'type': kind,
        'server': str(item.get('server', '')),
        'port': item.get('port', 0),
        'source': 'subscription',
        'subscription_id': subscription_id,
        'insecure': item.get('skip-cert-verify') is True,
        'server_name': str(item.get('servername') or item.get('sni') or item.get('server', '')),
        'transport_type': 'ws' if str(item.get('network', '')).lower() == 'ws' else '',
        'transport_path': str(ws.get('path', '')),
        'transport_host': str(headers.get('Host') or headers.get('host') or ''),
    }
    if kind == 'shadowsocks':
        source.update({'method': str(item.get('cipher', '')), 'password': str(item.get('password', ''))})
    elif kind == 'trojan':
        source['password'] = str(item.get('password', ''))
    else:
        source.update({
            'uuid': str(item.get('uuid', '')),
            'tls': item.get('tls') is True or str(item.get('security', '')).lower() in ('tls', 'reality'),
        })
        if kind == 'vless':
            source.update({
                'flow': str(item.get('flow', '')),
                'reality_public_key': str(reality.get('public-key') or reality.get('public_key') or ''),
                'reality_short_id': str(reality.get('short-id') or reality.get('short_id') or ''),
                'client_fingerprint': str(item.get('client-fingerprint') or item.get('fingerprint') or 'chrome'),
            })
        else:
            source.update({'security': str(item.get('cipher') or 'auto'), 'alter_id': item.get('alterId', 0)})
    digest = hashlib.sha256(json.dumps(item, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]
    source['id'] = clean_proxy_id(f'{subscription_id}-{digest}')
    return validate_proxy_node(source)


def decode_subscription_nodes(payload, subscription_id):
    text = payload.decode('utf-8', errors='replace').strip()
    nodes = []
    if yaml is not None and re.search(r'(?m)^\s*proxies\s*:', text):
        try:
            document = yaml.safe_load(text)
            proxies = document.get('proxies', []) if isinstance(document, dict) else []
            for index, item in enumerate(proxies):
                try:
                    node = clash_proxy_node(item, subscription_id, index)
                    if node:
                        nodes.append(node)
                except (ValueError, TypeError):
                    continue
        except yaml.YAMLError:
            pass
    if not any(token in text for token in ('ss://', 'trojan://', 'vless://', 'vmess://')):
        try:
            compact = ''.join(text.split())
            text = base64.urlsafe_b64decode(compact + '=' * (-len(compact) % 4)).decode('utf-8')
        except (ValueError, UnicodeDecodeError):
            pass
    for match in re.findall(r'(?:ss|trojan|vless|vmess)://[^\s"\']+', text):
        try:
            node = parse_proxy_uri(match.rstrip(',;'), subscription_id)
            if node:
                nodes.append(node)
        except (ValueError, TypeError):
            continue
    unique = {node['id']: node for node in nodes}
    return list(unique.values())


def update_proxy_subscription(subscription_id):
    saved = proxy_settings()
    item = next((entry for entry in saved['subscriptions'] if str(entry.get('id')) == subscription_id), None)
    if item is None:
        raise ValueError('订阅不存在')
    request = urllib.request.Request(str(item.get('url', '')), headers={'User-Agent': 'OpenStick-Control/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            length = int(response.headers.get('Content-Length', '0') or 0)
            if length > 2 * 1024 * 1024:
                raise ValueError('订阅内容超过 2 MB，已停止下载')
            payload = response.read(2 * 1024 * 1024 + 1)
    except OSError as exc:
        raise RuntimeError(f'订阅下载失败：{exc}')
    if len(payload) > 2 * 1024 * 1024:
        raise ValueError('订阅内容超过 2 MB，已停止下载')
    nodes = decode_subscription_nodes(payload, subscription_id)
    if not nodes:
        raise ValueError('没有识别到 SS、Trojan、VLESS 或 VMess 节点')
    old_ids = {str(node.get('id')) for node in saved['nodes'] if str(node.get('subscription_id')) == subscription_id}
    saved['nodes'] = [node for node in saved['nodes'] if str(node.get('subscription_id')) != subscription_id] + nodes
    item['updated_at'] = datetime.now().isoformat(timespec='seconds')
    if saved.get('selected_node') in old_ids:
        saved['selected_node'] = nodes[0]['id']
    valid_ids = {str(node.get('id')) for node in saved['nodes']}
    saved['strategy_candidates'] = [item for item in saved.get('strategy_candidates', []) if str(item) in valid_ids]
    return apply_proxy_settings(saved, reason='更新订阅')


def update_proxy_rules():
    """Download both official SagerNet China rule sets atomically and roll back on failure."""
    PROXY_RULE_DIR.mkdir(parents=True, exist_ok=True)
    temporary_paths = {}
    for name, url in PROXY_RULE_URLS.items():
        request = urllib.request.Request(url, headers={'User-Agent': 'OpenStick-Control/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                length = int(response.headers.get('Content-Length', '0') or 0)
                if length > 1024 * 1024:
                    raise ValueError(f'{name} 超过 1 MB，已停止下载')
                payload = response.read(1024 * 1024 + 1)
        except OSError as exc:
            for path in temporary_paths.values():
                path.unlink(missing_ok=True)
            raise RuntimeError(f'规则下载失败：{exc}')
        if not payload or len(payload) > 1024 * 1024:
            for path in temporary_paths.values():
                path.unlink(missing_ok=True)
            raise ValueError(f'{name} 内容为空或超过 1 MB')
        temporary = PROXY_RULE_DIR / f'.{name}.new'
        temporary.write_bytes(payload)
        temporary.chmod(0o640)
        shutil.chown(temporary, user='root', group='sing-box')
        temporary_paths[name] = temporary

    candidate = build_singbox_config(proxy_settings())
    for item in candidate.get('route', {}).get('rule_set', []):
        name = Path(str(item.get('path', ''))).name
        if name in temporary_paths:
            item['path'] = str(temporary_paths[name])
    check_file = SINGBOX_CONFIG_FILE.with_name('rules-update-check.json')
    check_file.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding='utf-8')
    check_file.chmod(0o640)
    shutil.chown(check_file, user='root', group='sing-box')
    checked = run_command([SINGBOX_BINARY, 'check', '-c', str(check_file)], timeout=20)
    check_file.unlink(missing_ok=True)
    if checked.returncode:
        for path in temporary_paths.values():
            path.unlink(missing_ok=True)
        raise ValueError((checked.stderr or checked.stdout or '国内规则格式检查失败').strip())

    previous = {}
    try:
        for name, temporary in temporary_paths.items():
            destination = PROXY_RULE_DIR / name
            previous[name] = destination.read_bytes() if destination.exists() else None
            temporary.replace(destination)
        apply_proxy_settings(proxy_settings())
    except Exception:
        for name, payload in previous.items():
            destination = PROXY_RULE_DIR / name
            if payload is None:
                destination.unlink(missing_ok=True)
            else:
                destination.write_bytes(payload)
                destination.chmod(0o640)
                shutil.chown(destination, user='root', group='sing-box')
        apply_proxy_settings(proxy_settings())
        raise
    return public_proxy_settings()


def test_proxy_node(node_id):
    saved = proxy_settings()
    node = next((item for item in saved['nodes'] if str(item.get('id')) == node_id), None)
    if node is None:
        raise ValueError('节点不存在')
    if node.get('type') in ('wireguard', 'tailscale'):
        raise ValueError('隧道节点请开启后通过出口 IP 验证')
    latency = tcp_node_latency(node, timeout=8)
    return {'ok': True, 'latency_ms': latency, 'node_id': node_id}


def tcp_node_latency(node, timeout=8):
    started = time.monotonic()
    try:
        with socket.create_connection((str(node.get('server')), int(node.get('port'))), timeout=timeout):
            pass
    except OSError as exc:
        raise RuntimeError(f'连接失败：{exc}')
    return round((time.monotonic() - started) * 1000)


def test_all_proxy_nodes():
    saved = proxy_settings()
    results = {}
    for node in saved['nodes'][:100]:
        node_id = str(node.get('id', ''))
        if node.get('type') in ('wireguard', 'tailscale'):
            results[node_id] = {'ok': False, 'error': '隧道节点需通过出口 IP 验证'}
            continue
        try:
            results[node_id] = {'ok': True, 'latency_ms': tcp_node_latency(node, timeout=5)}
        except RuntimeError as exc:
            results[node_id] = {'ok': False, 'error': str(exc)}
    selected = ''
    if saved.get('strategy') in ('latency', 'fallback'):
        try:
            chosen, _ = select_strategy_node(saved, results)
            selected = str(chosen.get('id'))
            if selected != str(proxy_settings().get('selected_node')):
                apply_proxy_settings(saved, reason='节点策略自动选择')
        except (ValueError, RuntimeError):
            pass
    return {'results': results, 'selected_node': selected}


def proxy_health_monitor():
    tracked = ''
    failures = 0
    while True:
        time.sleep(60)
        try:
            saved = proxy_settings()
            active = run_command(['systemctl', 'is-active', 'openstick-sing-box.service'], timeout=5).returncode == 0
            node_id = str(saved.get('selected_node', 'direct'))
            if not active or not saved.get('health_check') or saved.get('mode') == 'direct' or node_id == 'direct':
                tracked, failures = '', 0
                continue
            node = next((item for item in saved['nodes'] if str(item.get('id')) == node_id), None)
            if node is None:
                continue
            if node.get('type') in ('wireguard', 'tailscale'):
                continue
            if tracked != node_id:
                tracked, failures = node_id, 0
            checked_at = datetime.now().isoformat(timespec='seconds')
            try:
                latency = tcp_node_latency(node, timeout=5)
                failures = 0
                PROXY_HEALTH.update({'node_id': node_id, 'latency_ms': latency, 'failures': 0, 'last_check': checked_at})
            except RuntimeError:
                failures += 1
                PROXY_HEALTH.update({'node_id': node_id, 'latency_ms': None, 'failures': failures, 'last_check': checked_at})
                if failures >= 3:
                    switched = False
                    if saved.get('strategy') in ('latency', 'fallback'):
                        try:
                            candidates = [item for item in eligible_strategy_nodes(saved) if str(item.get('id')) != node_id]
                            probe = dict(saved)
                            probe['strategy_candidates'] = [str(item.get('id')) for item in candidates]
                            chosen, _ = select_strategy_node(probe)
                            saved['selected_node'] = str(chosen.get('id'))
                            apply_proxy_settings(saved, reason='故障自动切换')
                            switched = True
                        except (ValueError, RuntimeError):
                            switched = False
                    if not switched:
                        saved['mode'] = 'direct'
                        apply_proxy_settings(saved, reason='节点故障回直连')
                    PROXY_HEALTH['last_failover'] = checked_at
                    failures = 0
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            continue


def proxy_exit_ip():
    handlers = []
    if run_command(['systemctl', 'is-active', 'openstick-sing-box.service'], timeout=5).returncode == 0:
        handlers.append(urllib.request.ProxyHandler({'http': 'http://127.0.0.1:2080', 'https': 'http://127.0.0.1:2080'}))
    opener = urllib.request.build_opener(*handlers)
    providers = (
        ('AWS', 'https://checkip.amazonaws.com', 'text'),
        ('ipify', 'https://api64.ipify.org?format=json', 'json'),
        ('icanhazip', 'https://icanhazip.com', 'text'),
    )
    failures = []
    for name, url, response_type in providers:
        request = urllib.request.Request(url, headers={
            'User-Agent': 'OpenStick-Control/1.0',
            'Accept': 'application/json,text/plain',
        })
        try:
            with opener.open(request, timeout=10) as response:
                raw = response.read(2048).decode('utf-8').strip()
            value = str(json.loads(raw).get('ip', '')).strip() if response_type == 'json' else raw.splitlines()[0].strip()
            address = ipaddress.ip_address(value)
            return {
                'ip': str(address), 'ip_version': address.version,
                'via_proxy': bool(handlers), 'provider': name,
            }
        except (OSError, ValueError, IndexError, json.JSONDecodeError) as exc:
            failures.append(type(exc).__name__)
    route = '当前代理' if handlers else '蜂窝直连'
    raise RuntimeError(f'{route}可以联网，但三个轻量查询服务均未返回有效 IP，请稍后重试')


def traffic_details(include_archive=False):
    with TRAFFIC_LOCK:
        if TRAFFIC_LIVE.get('initialized'):
            state = dict(TRAFFIC_LIVE)
            history = list(TRAFFIC_HISTORY)
            archive = list(TRAFFIC_ARCHIVE) if include_archive else []
        else:
            state = read_json(TRAFFIC_STATE, {
                'rx_bytes': 0, 'tx_bytes': 0,
                'started_at': datetime.now().isoformat(timespec='seconds')
            })
            history = []
            archive = []
    rx = int(state.get('rx_bytes', 0) or 0)
    tx = int(state.get('tx_bytes', 0) or 0)
    rx_bps = float(state.get('rx_bps', 0) or 0)
    tx_bps = float(state.get('tx_bps', 0) or 0)
    limit = int(read_json(MOBILE_CONFIG, {}).get('traffic_limit_mb', 0) or 0)
    return {
        'rx_bytes': rx,
        'tx_bytes': tx,
        'total_bytes': rx + tx,
        'rx': format_bytes(rx),
        'tx': format_bytes(tx),
        'total': format_bytes(rx + tx),
        'rx_bps': round(rx_bps, 1),
        'tx_bps': round(tx_bps, 1),
        'rx_rate': f'{format_bytes(rx_bps)}/s',
        'tx_rate': f'{format_bytes(tx_bps)}/s',
        'history': history,
        'archive': archive,
        'started_at': state.get('started_at', ''),
        'limit_mb': limit,
        'limit_percent': min(100, round((rx + tx) * 100 / (limit * 1024 * 1024), 1)) if limit else 0,
        'server_time': time.time(),
    }


def traffic_monitor():
    saved = read_json(TRAFFIC_STATE, {
        'rx_bytes': 0, 'tx_bytes': 0,
        'started_at': datetime.now().isoformat(timespec='seconds')
    })
    with TRAFFIC_LOCK:
        TRAFFIC_ARCHIVE.extend(read_history(TRAFFIC_HISTORY_FILE))
        TRAFFIC_LIVE.update({
            'initialized': True,
            'rx_bytes': int(saved.get('rx_bytes', 0) or 0),
            'tx_bytes': int(saved.get('tx_bytes', 0) or 0),
            'rx_bps': 0.0,
            'tx_bps': 0.0,
            'started_at': saved.get('started_at') or datetime.now().isoformat(timespec='seconds'),
        })
    previous_rx = None
    previous_tx = None
    previous_time = time.monotonic()
    last_flush = previous_time
    last_settings_read = 0.0
    last_archive_time = int(TRAFFIC_ARCHIVE[-1].get('time', 0)) if TRAFFIC_ARCHIVE else 0
    last_archive_write = time.monotonic()
    archive_rx_sum = 0.0
    archive_tx_sum = 0.0
    archive_count = 0
    settings = {}
    while True:
        iteration_started = time.monotonic()
        try:
            statistics = run_command([
                'qmicli', '-d', '/dev/wwan0qmi0', '--device-open-proxy',
                '--wds-get-packet-statistics'
            ], timeout=5)
            rx_match = re.search(r'RX bytes OK:\s*(\d+)', statistics.stdout)
            tx_match = re.search(r'TX bytes OK:\s*(\d+)', statistics.stdout)
            if statistics.returncode == 0 and rx_match and tx_match:
                current_rx = int(rx_match.group(1))
                current_tx = int(tx_match.group(1))
                now = time.monotonic()
                elapsed = max(0.1, now - previous_time)
                if previous_rx is None:
                    delta_rx = delta_tx = 0
                else:
                    delta_rx = current_rx - previous_rx if current_rx >= previous_rx else current_rx
                    delta_tx = current_tx - previous_tx if current_tx >= previous_tx else current_tx
                previous_rx, previous_tx, previous_time = current_rx, current_tx, now
                rx_bps = max(0, delta_rx) / elapsed
                tx_bps = max(0, delta_tx) / elapsed
                sample_time = int(time.time())
                archive_rx_sum += rx_bps
                archive_tx_sum += tx_bps
                archive_count += 1
                with TRAFFIC_LOCK:
                    TRAFFIC_LIVE['rx_bytes'] += max(0, delta_rx)
                    TRAFFIC_LIVE['tx_bytes'] += max(0, delta_tx)
                    TRAFFIC_LIVE['rx_bps'] = rx_bps
                    TRAFFIC_LIVE['tx_bps'] = tx_bps
                    TRAFFIC_HISTORY.append({
                        'time': sample_time,
                        'rx_bps': round(rx_bps, 1),
                        'tx_bps': round(tx_bps, 1),
                    })
                    if sample_time - last_archive_time >= 30 and archive_count:
                        TRAFFIC_ARCHIVE.append({
                            'time': sample_time,
                            'rx_bps': round(archive_rx_sum / archive_count, 1),
                            'tx_bps': round(archive_tx_sum / archive_count, 1),
                        })
                        last_archive_time = sample_time
                        archive_rx_sum = archive_tx_sum = 0.0
                        archive_count = 0
                    snapshot = dict(TRAFFIC_LIVE)
                    archive_snapshot = list(TRAFFIC_ARCHIVE)

                if now - last_flush >= 30:
                    write_json(TRAFFIC_STATE, {
                        'rx_bytes': snapshot['rx_bytes'],
                        'tx_bytes': snapshot['tx_bytes'],
                        'started_at': snapshot['started_at'],
                    })
                    last_flush = now
                if not TRAFFIC_HISTORY_FILE.exists() or now - last_archive_write >= 300:
                    write_history(TRAFFIC_HISTORY_FILE, archive_snapshot)
                    last_archive_write = now
                if now - last_settings_read >= 10:
                    settings = mobile_settings()
                    last_settings_read = now
                limit = int(settings.get('traffic_limit_mb', 0) or 0) * 1024 * 1024
                if settings.get('disconnect_at_limit') and limit and snapshot['rx_bytes'] + snapshot['tx_bytes'] >= limit:
                    run_command(['nmcli', 'connection', 'down', 'unicom-4g'], timeout=20)
            else:
                raise ValueError('packet statistics unavailable')
        except (OSError, ValueError, subprocess.TimeoutExpired):
            # 蜂窝数据关闭或基带暂不可用时仍记录真实的零速率，
            # 避免监控图表因没有采样点而看起来像坏掉。
            now = time.monotonic()
            sample_time = int(time.time())
            archive_rx_sum += 0.0
            archive_tx_sum += 0.0
            archive_count += 1
            with TRAFFIC_LOCK:
                TRAFFIC_LIVE['rx_bps'] = 0.0
                TRAFFIC_LIVE['tx_bps'] = 0.0
                TRAFFIC_HISTORY.append({'time': sample_time, 'rx_bps': 0.0, 'tx_bps': 0.0})
                if sample_time - last_archive_time >= 30 and archive_count:
                    TRAFFIC_ARCHIVE.append({'time': sample_time, 'rx_bps': 0.0, 'tx_bps': 0.0})
                    last_archive_time = sample_time
                    archive_rx_sum = archive_tx_sum = 0.0
                    archive_count = 0
                archive_snapshot = list(TRAFFIC_ARCHIVE)
            if not TRAFFIC_HISTORY_FILE.exists() or now - last_archive_write >= 300:
                write_history(TRAFFIC_HISTORY_FILE, archive_snapshot)
                last_archive_write = now
        time.sleep(max(0.2, 2 - (time.monotonic() - iteration_started)))


def cellular_details():
    details = {
        'connected': cellular_connected(),
        'autoconnect': False,
        'apn': '',
        'operator': '',
        'roaming': False,
        'packet_status': 'disconnected',
    }
    try:
        profile = run_command(['nmcli', '-g', 'connection.autoconnect,gsm.apn', 'connection', 'show', 'unicom-4g'])
        values = profile.stdout.splitlines()
        if values:
            details['autoconnect'] = values[0].strip().lower() == 'yes'
        if len(values) > 1:
            details['apn'] = values[1].strip()
        packet = run_command([
            'qmicli', '-d', '/dev/wwan0qmi0', '--device-open-proxy', '--wds-get-packet-service-status'
        ])
        match = re.search(r"Connection status:\s*'([^']+)'", packet.stdout)
        if match:
            details['packet_status'] = match.group(1)
        serving = run_command([
            'qmicli', '-d', '/dev/wwan0qmi0', '--device-open-proxy', '--nas-get-serving-system'
        ])
        operator = re.search(r"Description:\s*'([^']+)'", serving.stdout)
        roaming = re.search(r"Roaming status:\s*'([^']+)'", serving.stdout)
        if operator:
            details['operator'] = operator.group(1)
        if roaming:
            details['roaming'] = roaming.group(1).lower() not in ('off', 'unknown')
    except (OSError, subprocess.TimeoutExpired):
        pass
    return details


def wifi_details():
    result = {
        'connected': False,
        'autoconnect': False,
        'ssid': 'openstick-failsafe',
        'mode': 'ap',
        'channel': '',
        'address': '192.168.69.1',
    }
    try:
        active = run_command(['nmcli', '-t', '-f', 'DEVICE,STATE', 'device'])
        result['connected'] = any(line.startswith('wlan0:connected') for line in active.stdout.splitlines())
        profile = run_command([
            'nmcli', '-g', 'connection.autoconnect,802-11-wireless.ssid,802-11-wireless.mode,802-11-wireless.channel',
            'connection', 'show', 'openstick-failsafe'
        ])
        values = profile.stdout.splitlines()
        if values:
            result['autoconnect'] = values[0].strip().lower() == 'yes'
        if len(values) > 1:
            result['ssid'] = values[1].strip()
        if len(values) > 2:
            result['mode'] = values[2].strip()
        if len(values) > 3:
            result['channel'] = values[3].strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def set_wifi_enabled(enabled):
    persisted = run_command([
        'nmcli', 'connection', 'modify', 'openstick-failsafe',
        'connection.autoconnect', 'no',
    ], timeout=15)
    if persisted.returncode:
        raise RuntimeError((persisted.stderr or persisted.stdout or '无法保存 Wi‑Fi 默认关闭设置').strip())
    command = ['nmcli', 'connection', 'up' if enabled else 'down', 'openstick-failsafe']
    changed = run_command(command, timeout=30)
    if changed.returncode:
        raise RuntimeError((changed.stderr or changed.stdout or 'Wi‑Fi 状态切换失败').strip())
    time.sleep(1)
    return wifi_details()


def update_wifi(ssid, passphrase, channel):
    if not ssid or len(ssid.encode('utf-8')) > 32:
        raise ValueError('热点名称应为 1–32 字节')
    if channel not in range(1, 14):
        raise ValueError('2.4 GHz 信道应为 1–13')

    was_connected = wifi_details()['connected']
    current = run_command([
        'nmcli', '--show-secrets', '-g',
        '802-11-wireless.ssid,802-11-wireless.channel,802-11-wireless-security.psk',
        'connection', 'show', 'openstick-failsafe'
    ])
    old_values = current.stdout.splitlines()
    if current.returncode or len(old_values) < 3:
        raise RuntimeError('无法读取当前 Wi‑Fi 配置')
    if passphrase is None:
        passphrase = old_values[2]
    if len(passphrase) < 8 or len(passphrase) > 63:
        raise ValueError('热点密码应为 8–63 个字符')

    def apply(values):
        return run_command([
            'nmcli', 'connection', 'modify', 'openstick-failsafe',
            'connection.autoconnect', 'no',
            '802-11-wireless.ssid', values[0],
            '802-11-wireless.channel', values[1],
            '802-11-wireless-security.key-mgmt', 'wpa-psk',
            '802-11-wireless-security.psk', values[2],
        ], timeout=15)

    requested = [ssid, str(channel), passphrase]
    changed = apply(requested)
    if changed.returncode:
        raise RuntimeError((changed.stderr or changed.stdout or 'Wi‑Fi 配置保存失败').strip())
    if not was_connected:
        return wifi_details()
    activated = run_command(['nmcli', 'connection', 'up', 'openstick-failsafe'], timeout=30)
    if activated.returncode:
        apply(old_values[:3])
        run_command(['nmcli', 'connection', 'up', 'openstick-failsafe'], timeout=30)
        raise RuntimeError('新 Wi‑Fi 配置无法启动，已恢复原设置')
    return wifi_details()


def mask_identifier(value, left=6, right=4):
    value = str(value or '')
    if len(value) <= left + right:
        return value
    return value[:left] + '•' * 8 + value[-right:]


def lpac_payload(command, timeout=20):
    environment = os.environ.copy()
    environment.update({
        'LPAC_APDU': 'qmi',
        'LPAC_APDU_QMI_DEVICE': '/dev/wwan0qmi0',
        'LPAC_APDU_QMI_UIM_SLOT': '1',
        'LPAC_HTTP': 'curl',
    })
    proxy_url = esim_usb_proxy_url()
    if proxy_url:
        environment.update({
            'http_proxy': proxy_url,
            'https_proxy': proxy_url,
            'HTTP_PROXY': proxy_url,
            'HTTPS_PROXY': proxy_url,
        })
    completed = subprocess.run(
        ['/usr/local/bin/lpac'] + command,
        capture_output=True, text=True, timeout=timeout, check=False, env=environment
    )
    if completed.returncode:
        raise RuntimeError('lpac unavailable')
    records = []
    for line in completed.stdout.splitlines():
        try:
            record = json.loads(line)
            if isinstance(record, dict):
                records.append(record)
        except json.JSONDecodeError:
            continue
    parsed = next((item for item in reversed(records) if item.get('type') == 'lpa'), records[-1] if records else {})
    if not parsed:
        raise RuntimeError('lpac returned no result')
    if parsed.get('payload', {}).get('code') != 0:
        raise RuntimeError(parsed.get('payload', {}).get('message', 'lpac failed'))
    return parsed['payload']['data']


def profile_token(iccid):
    return hashlib.sha256(str(iccid).encode('utf-8')).hexdigest()[:20]


def raw_esim_profiles():
    return lpac_payload(['profile', 'list'])


def resolve_esim_profile(token):
    for item in raw_esim_profiles():
        if profile_token(item.get('iccid', '')) == token:
            return item
    raise ValueError('找不到指定的 eSIM Profile，请刷新页面后重试')


def wait_esim_profiles(timeout=35):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            return raw_esim_profiles()
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            last_error = exc
            time.sleep(3)
    raise RuntimeError(f'eUICC 重新读取超时: {last_error or "unknown"}')


def esim_usb_proxy_url():
    try:
        parsed = urllib.parse.urlparse(ESIM_USB_PROXY_URL)
        if parsed.scheme != 'http' or not parsed.hostname or not parsed.port:
            return ''
        with socket.create_connection((parsed.hostname, parsed.port), timeout=2):
            return ESIM_USB_PROXY_URL
    except (OSError, ValueError):
        return ''


def esim_network_path():
    route = run_command(['ip', '-4', 'route', 'get', '1.1.1.1'])
    match = re.search(r'\bdev\s+(\S+)', route.stdout)
    interface = match.group(1) if route.returncode == 0 and match else ''
    cellular = interface.startswith('wwan')
    proxy_url = esim_usb_proxy_url() if interface == 'usb0' else ''
    safe_for_download = bool(interface) and not cellular
    if interface == 'usb0':
        safe_for_download = bool(proxy_url)
    return {
        'available': bool(interface),
        'interface': interface,
        'cellular': cellular,
        'safe_for_download': safe_for_download,
        'transport': 'usb_proxy' if proxy_url else ('direct' if interface else ''),
    }


def esim_profile_action(action, token):
    if action not in ('enable', 'disable'):
        raise ValueError('不支持的 eSIM 操作')
    if cellular_connected():
        raise RuntimeError('请先关闭蜂窝数据，再切换 eSIM Profile')
    if not ESIM_LOCK.acquire(blocking=False):
        raise RuntimeError('另一个 eSIM 操作正在进行')
    try:
        before = raw_esim_profiles()
        profile = next((item for item in before if profile_token(item.get('iccid', '')) == token), None)
        if not profile:
            raise ValueError('找不到指定的 eSIM Profile，请刷新页面后重试')
        previously_enabled = next((item for item in before if item.get('profileState') == 'enabled'), None)
        state = profile.get('profileState')
        if action == 'enable' and state == 'enabled':
            return esim_details()
        if action == 'disable' and state != 'enabled':
            return esim_details()
        lpac_payload(['profile', action, profile.get('iccid', ''), '1'], timeout=60)
        time.sleep(4)
        after = wait_esim_profiles()
        changed = next((item for item in after if profile_token(item.get('iccid', '')) == token), None)
        expected = 'enabled' if action == 'enable' else 'disabled'
        if not changed or changed.get('profileState') != expected:
            restored = False
            if action == 'enable' and previously_enabled and previously_enabled.get('iccid') != profile.get('iccid'):
                try:
                    lpac_payload(['profile', 'enable', previously_enabled.get('iccid', ''), '1'], timeout=60)
                    restored = True
                except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
                    pass
            raise RuntimeError('Profile 状态校验失败' + ('，已尝试恢复原 Profile' if restored else ''))
        return esim_details()
    finally:
        ESIM_LOCK.release()


def esim_download(activation_code, confirmation_code=''):
    if not re.fullmatch(r'LPA:1\$[^$\s]{1,253}\$[^\s]{1,253}', activation_code):
        raise ValueError('eSIM 激活码格式不正确，应以 LPA:1$ 开头')
    if len(confirmation_code) > 64:
        raise ValueError('确认码过长')
    network = esim_network_path()
    if not network['safe_for_download']:
        if network['cellular']:
            raise RuntimeError('当前互联网出口是蜂窝网络，为避免漫游费用已阻止下载')
        raise RuntimeError('棒子当前没有可验证的安全互联网出口，请先连接 Wi‑Fi 或启动 USB 下载代理')
    if not ESIM_LOCK.acquire(blocking=False):
        raise RuntimeError('另一个 eSIM 操作正在进行')
    try:
        command = ['profile', 'download', '-a', activation_code]
        if confirmation_code:
            command += ['-c', confirmation_code]
        lpac_payload(command, timeout=300)
        return esim_details()
    finally:
        ESIM_LOCK.release()


def esim_details():
    chip = lpac_payload(['chip', 'info'])
    profiles = raw_esim_profiles()
    own_numbers = []
    try:
        modem = current_modem_id()
        details = run_command(['mmcli', '-m', modem, '-K'])
        own_numbers = [
            match.strip() for match in re.findall(
                r'modem\.generic\.own-numbers\.value\[[^]]+\]\s*:\s*([^\r\n]+)',
                details.stdout
            ) if match.strip() and match.strip() != '--'
        ]
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        pass
    return {
        'detected': True,
        'eid': mask_identifier(chip.get('eidValue'), 8, 4),
        'firmware': chip.get('EUICCInfo2', {}).get('euiccFirmwareVer'),
        'profiles': [{
            'name': item.get('profileNickname') or item.get('profileName') or item.get('serviceProviderName') or 'Unnamed',
            'provider': item.get('serviceProviderName') or '',
            'state': item.get('profileState') or 'unknown',
            'iccid': mask_identifier(item.get('iccid'), 6, 4),
            'phone_number': own_numbers[0] if item.get('profileState') == 'enabled' and own_numbers else '',
            'profile_id': profile_token(item.get('iccid', '')),
        } for item in profiles],
    }


def service_state(service, required=True):
    active = run_command(['systemctl', 'is-active', service], timeout=5).stdout.strip()
    enabled = run_command(['systemctl', 'is-enabled', service], timeout=5).stdout.strip()
    shown = run_command([
        'systemctl', 'show', service, '--property=Result,ExecMainStatus,SubState', '--value'
    ], timeout=5)
    values = shown.stdout.splitlines()
    return {
        'name': service.removesuffix('.service'),
        'active': active == 'active',
        'enabled': enabled == 'enabled',
        'required': required,
        'result': values[0].strip() if values else '',
        'exit_status': values[1].strip() if len(values) > 1 else '',
        'sub_state': values[2].strip() if len(values) > 2 else '',
    }


def file_build_info(path, version):
    path = Path(path)
    digest = hashlib.sha256()
    try:
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(128 * 1024), b''):
                digest.update(chunk)
        return {
            'version': version,
            'sha256': digest.hexdigest(),
            'size': path.stat().st_size,
            'available': True,
        }
    except OSError:
        return {
            'version': version,
            'sha256': '',
            'size': 0,
            'available': False,
        }


def build_details():
    return {
        'release': CONTROL_VERSION,
        'build_date': BUILD_DATE,
        'components': {
            'webui': file_build_info(UI_FILE, CONTROL_VERSION),
            'backend': file_build_info(Path(__file__).resolve(), CONTROL_VERSION),
            'uplink_manager': file_build_info(
                Path(UPLINK_MANAGER), UPLINK_MANAGER_VERSION
            ),
        },
    }


def health_details():
    required_names = [
        'openstick-sms-web.service',
        'openstick-sms-inbox.service',
        'openstick-notify.service',
        'openstick-auto-cellular.service',
        'openstick-windows-rndis.service',
        'openstick-mdns.service',
        'openstick-firewall.service',
    ]
    optional_names = [
        'openstick-sing-box.service',
        'openstick-socks-proxy.service',
        'openstick-http-proxy.service',
    ]
    services = [service_state(name, True) for name in required_names]
    services.extend(service_state(name, False) for name in optional_names)
    modem_list = run_command(['mmcli', '-L'], timeout=10)
    modem = modem_list.returncode == 0 and '/Modem/' in modem_list.stdout
    config_check = run_command([SINGBOX_BINARY, 'check', '-c', str(SINGBOX_CONFIG_FILE)], timeout=15)
    disk = shutil.disk_usage('/')
    thermal = thermal_details()
    temperature = thermal.get('temperature')
    issues = []
    for item in services:
        if item['required'] and not item['active']:
            issues.append({'level': 'error', 'message': f"{item['name']} 未运行"})
    if not modem:
        issues.append({'level': 'error', 'message': '未检测到高通蜂窝 Modem'})
    if config_check.returncode:
        issues.append({'level': 'error', 'message': 'sing-box 当前配置检查失败'})
    if not proxy_rule_status()['installed']:
        issues.append({'level': 'warning', 'message': '国内分流规则不完整'})
    if disk.free < 256 * 1024 * 1024:
        issues.append({'level': 'warning', 'message': '可用存储低于 256 MB'})
    if temperature is not None and temperature >= THERMAL_CRITICAL_C:
        issues.append({'level': 'error', 'message': f'设备温度达到 {temperature}℃'})
    elif temperature is not None and temperature >= THERMAL_WARN_C:
        issues.append({'level': 'warning', 'message': f'设备温度偏高：{temperature}℃'})
    return {
        'healthy': not any(item['level'] == 'error' for item in issues),
        'checked_at': datetime.now().isoformat(timespec='seconds'),
        'version': CONTROL_VERSION,
        'build': build_details(),
        'services': services,
        'modem': modem,
        'singbox_config': config_check.returncode == 0,
        'rules': proxy_rule_status()['installed'],
        'temperature': temperature,
        'thermal_level': thermal.get('level', 'unknown'),
        'storage_free': format_bytes(disk.free),
        'issues': issues,
    }


def diagnostic_details():
    interfaces = []
    for path in sorted(Path('/sys/class/net').glob('*')):
        try:
            interfaces.append({
                'name': path.name,
                'state': (path / 'operstate').read_text().strip(),
                'carrier': (path / 'carrier').read_text().strip() == '1' if (path / 'carrier').exists() else None,
            })
        except OSError:
            continue
    files = []
    for path in (
        MOBILE_CONFIG, PROXY_CONFIG_FILE, SINGBOX_CONFIG_FILE, EMAIL_CONFIG, NOTIFY_CONFIG,
        CONTACTS_FILE, UI_FILE, PROXY_RULE_DIR / 'geosite-cn.srs',
        PROXY_RULE_DIR / 'geoip-cn.srs',
    ):
        try:
            stat = path.stat()
            files.append({'path': str(path), 'exists': True, 'mode': oct(stat.st_mode & 0o777), 'size': stat.st_size})
        except OSError:
            files.append({'path': str(path), 'exists': False, 'mode': '', 'size': 0})
    memory = {}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            key, value = line.split(':', 1)
            if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
                memory[key] = value.strip()
    except (OSError, ValueError):
        pass
    package_audit = run_command(['dpkg', '--audit'], timeout=15)
    return {
        'format': 'openstick-diagnostic-v1',
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'privacy': {
            'sms_content': 'excluded',
            'phone_numbers': 'excluded',
            'email_authorization_code': 'excluded',
            'notification_credentials_and_destinations': 'excluded',
            'proxy_credentials': 'excluded',
            'subscription_urls': 'excluded',
            'esim_identifiers_and_activation_codes': 'excluded',
            'ip_addresses': 'excluded',
        },
        'build': build_details(),
        'health': health_details(),
        'device': device_status(),
        'kernel': run_command(['uname', '-r'], timeout=5).stdout.strip(),
        'machine': run_command(['uname', '-m'], timeout=5).stdout.strip(),
        'load_average': list(os.getloadavg()),
        'memory': memory,
        'interfaces': interfaces,
        'files': files,
        'package_audit_clean': package_audit.returncode == 0 and not package_audit.stdout.strip(),
    }


def wifi_backup_details():
    profile = run_command([
        'nmcli', '--show-secrets', '-g',
        '802-11-wireless.ssid,802-11-wireless.channel,802-11-wireless-security.psk',
        'connection', 'show', 'openstick-failsafe'
    ], timeout=10)
    values = profile.stdout.splitlines()
    if profile.returncode or len(values) < 3:
        raise RuntimeError('无法读取 Wi‑Fi 备份配置')
    current = wifi_details()
    return {
        'ssid': values[0],
        'channel': int(values[1] or 6),
        'passphrase': values[2],
        'enabled': current.get('connected') is True,
    }


def collect_configuration():
    email = read_json(EMAIL_CONFIG, {})
    contacts = read_json(CONTACTS_FILE, {'contacts': []})
    return {
        'format': 'openstick-config-v1',
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'device': 'UFI003-MSM8916',
        'mobile': mobile_settings(),
        'wifi': wifi_backup_details(),
        'email': email,
        'email_retry_enabled': not EMAIL_RETRY_DISABLED.exists(),
        'contacts': contacts,
        'notifications': notify_config(),
        'proxy': proxy_settings(),
        'proxy_services': {
            key: value.get('enabled') is True for key, value in proxy_details().items()
        },
    }


def validate_backup_configuration(data):
    if not isinstance(data, dict) or data.get('format') != 'openstick-config-v1':
        raise ValueError('不是有效的 OpenStick 配置备份')
    mobile = data.get('mobile', {})
    apn = str(mobile.get('apn', '')).strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', apn):
        raise ValueError('备份中的 APN 格式不正确')
    traffic_limit = int(mobile.get('traffic_limit_mb', 0) or 0)
    if traffic_limit < 0 or traffic_limit > 1048576:
        raise ValueError('备份中的流量上限不正确')
    clean_mobile = {
        'apn': apn,
        'roaming_allowed': mobile.get('roaming_allowed') is True,
        'traffic_limit_mb': traffic_limit,
        'disconnect_at_limit': mobile.get('disconnect_at_limit') is True,
        'auto_connect_domestic': mobile.get('auto_connect_domestic') is True,
    }
    wifi = data.get('wifi', {})
    ssid = str(wifi.get('ssid', ''))
    passphrase = str(wifi.get('passphrase', ''))
    channel = int(wifi.get('channel', 6) or 6)
    if not ssid or len(ssid.encode('utf-8')) > 32 or not 8 <= len(passphrase) <= 63 or channel not in range(1, 14):
        raise ValueError('备份中的 Wi‑Fi 配置不正确')
    clean_wifi = {'ssid': ssid, 'passphrase': passphrase, 'channel': channel, 'enabled': wifi.get('enabled') is True}

    email = data.get('email', {})
    if not isinstance(email, dict) or len(json.dumps(email)) > 8192:
        raise ValueError('备份中的邮箱配置不正确')
    if email:
        if str(email.get('host', '')) != 'smtp.qq.com' or int(email.get('port', 0) or 0) != 465:
            raise ValueError('只允许恢复当前支持的 QQ SMTP 配置')
        if not re.fullmatch(r'[A-Za-z0-9]{8,64}', str(email.get('authorization_code', ''))):
            raise ValueError('备份中的邮箱授权码格式不正确')
        username = str(email.get('username', ''))
        recipient = str(email.get('recipient', ''))
        if not re.fullmatch(r'[A-Za-z0-9._%+-]{1,64}@qq\.com', username) or not re.fullmatch(r'[A-Za-z0-9._%+-]{1,64}@qq\.com', recipient):
            raise ValueError('备份中的 QQ 邮箱地址格式不正确')
        email = {
            'host': 'smtp.qq.com',
            'port': 465,
            'username': username,
            'recipient': recipient,
            'authorization_code': str(email['authorization_code']),
            'verified': email.get('verified') is True,
        }

    contacts = data.get('contacts', {'contacts': []})
    items = contacts.get('contacts', []) if isinstance(contacts, dict) else []
    if not isinstance(items, list) or len(items) > 1000:
        raise ValueError('备份中的通讯录过大')
    clean_contacts = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('备份中的联系人格式不正确')
        name = str(item.get('name', '')).strip()
        number = normalize_number(item.get('number', ''))
        if not name or len(name) > 40 or not re.fullmatch(r'\+?[0-9]{3,24}', number):
            raise ValueError('备份中的联系人格式不正确')
        clean_contacts.append({'name': name, 'number': number})

    proxy = data.get('proxy', {})
    if not isinstance(proxy, dict):
        raise ValueError('备份中的代理配置不正确')
    raw_nodes = proxy.get('nodes', [])
    if not isinstance(raw_nodes, list) or len(raw_nodes) > 500:
        raise ValueError('备份中的代理节点过多')
    clean_nodes = [validate_proxy_node(item) for item in raw_nodes]
    raw_subscriptions = proxy.get('subscriptions', [])
    if not isinstance(raw_subscriptions, list) or len(raw_subscriptions) > 100:
        raise ValueError('备份中的代理订阅过多')
    clean_subscriptions = []
    for item in raw_subscriptions:
        if not isinstance(item, dict):
            raise ValueError('备份中的订阅格式不正确')
        parsed = urllib.parse.urlsplit(str(item.get('url', '')))
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ValueError('备份中的订阅链接格式不正确')
        clean_subscriptions.append({
            'id': clean_proxy_id(item.get('id'), 'sub'),
            'name': str(item.get('name', ''))[:80],
            'url': str(item.get('url', ''))[:2048],
            'updated_at': str(item.get('updated_at', ''))[:32],
        })
    mode = str(proxy.get('mode', 'direct'))
    if mode not in ('direct', 'rule', 'global'):
        raise ValueError('备份中的代理模式不正确')
    selected = str(proxy.get('selected_node', 'direct'))
    if selected != 'direct' and not any(item['id'] == selected for item in clean_nodes):
        selected, mode = 'direct', 'direct'
    clean_proxy = {
        'mode': mode,
        'selected_node': selected,
        'nodes': clean_nodes,
        'subscriptions': clean_subscriptions,
        'health_check': proxy.get('health_check') is True,
        'strategy': str(proxy.get('strategy', 'manual')) if str(proxy.get('strategy', 'manual')) in ('manual', 'latency', 'fallback') else 'manual',
        'strategy_candidates': [str(item) for item in proxy.get('strategy_candidates', []) if str(item) in {node['id'] for node in clean_nodes}],
    }
    raw_services = data.get('proxy_services', {})
    clean_services = {key: raw_services.get(key) is True for key in PROXY_SERVICES}
    notification = data.get('notifications', default_notify_config())
    if not isinstance(notification, dict) or len(json.dumps(notification)) > 32768:
        raise ValueError('备份中的通知配置不正确')
    rules = notification.get('rules', {})
    channels = notification.get('channels', {})
    if not isinstance(rules, dict) or not isinstance(channels, dict):
        raise ValueError('备份中的通知配置不正确')
    mode = str(rules.get('mode', 'all'))
    numbers = split_filter_values(rules.get('numbers', []), 100, 30)
    keywords = split_filter_values(rules.get('keywords', []), 100, 60)
    if mode not in ('all', 'match', 'codes'):
        raise ValueError('通知转发范围不正确')
    for number in numbers:
        if not re.fullmatch(r'\+?[0-9][0-9 -]{2,28}', number):
            raise ValueError('通知筛选号码不正确')
    bark_raw = channels.get('bark', {})
    telegram_raw = channels.get('telegram', {})
    webhook_raw = channels.get('webhook', {})
    if not all(isinstance(item, dict) for item in (bark_raw, telegram_raw, webhook_raw)):
        raise ValueError('备份中的通知渠道不正确')
    bark_key = str(bark_raw.get('device_key', ''))
    telegram_token = str(telegram_raw.get('bot_token', ''))
    telegram_chat = str(telegram_raw.get('chat_id', ''))
    webhook_url = str(webhook_raw.get('url', ''))
    if bark_key and not re.fullmatch(r'[A-Za-z0-9_-]{6,200}', bark_key):
        raise ValueError('Bark 配置不正确')
    if telegram_token and not re.fullmatch(r'[0-9]{5,20}:[A-Za-z0-9_-]{20,100}', telegram_token):
        raise ValueError('Telegram 配置不正确')
    if telegram_chat and not re.fullmatch(r'-?[0-9]{3,24}|@[A-Za-z0-9_]{5,32}', telegram_chat):
        raise ValueError('Telegram Chat ID 不正确')
    if webhook_url:
        webhook_url = validate_https_url(webhook_url, 'Webhook 地址')
    bark_server = validate_https_url(bark_raw.get('server', 'https://api.day.app'), 'Bark 服务器', 'https://api.day.app')
    validated_notification = {
        'enabled': notification.get('enabled') is True,
        'rules': {
            'mode': mode, 'numbers': numbers, 'keywords': keywords,
            'contacts_only': rules.get('contacts_only') is True,
            'verification_codes': rules.get('verification_codes') is True,
        },
        'channels': {
            'bark': {'enabled': bark_raw.get('enabled') is True and bool(bark_key), 'server': bark_server, 'device_key': bark_key},
            'telegram': {'enabled': telegram_raw.get('enabled') is True and bool(telegram_token and telegram_chat), 'bot_token': telegram_token, 'chat_id': telegram_chat},
            'webhook': {'enabled': webhook_raw.get('enabled') is True and bool(webhook_url), 'url': webhook_url},
        },
    }
    return {
        'format': 'openstick-config-v1',
        'created_at': str(data.get('created_at', ''))[:32],
        'device': 'UFI003-MSM8916',
        'mobile': clean_mobile,
        'wifi': clean_wifi,
        'email': email,
        'email_retry_enabled': data.get('email_retry_enabled') is True,
        'contacts': {'contacts': clean_contacts},
        'notifications': validated_notification,
        'proxy': clean_proxy,
        'proxy_services': clean_services,
    }


def encrypt_configuration(passphrase):
    if len(passphrase) < 10 or len(passphrase) > 128:
        raise ValueError('备份密码应为 10–128 个字符')
    plaintext = json.dumps(collect_configuration(), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(plaintext) > BACKUP_MAX_BYTES:
        raise ValueError('配置备份超过 4 MB，已停止导出')
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac('sha256', passphrase.encode('utf-8'), salt, BACKUP_ITERATIONS, dklen=64)
    encrypted = subprocess.run([
        'openssl', 'enc', '-aes-256-cbc', '-e', '-K', derived[:32].hex(),
        '-iv', iv.hex(), '-nosalt',
    ], input=plaintext, capture_output=True, timeout=30, check=False)
    if encrypted.returncode:
        raise RuntimeError('配置加密失败')
    body = BACKUP_MAGIC + salt + iv + encrypted.stdout
    return body + hmac.new(derived[32:], body, hashlib.sha256).digest()


def decrypt_configuration(payload, passphrase):
    minimum = len(BACKUP_MAGIC) + 16 + 16 + 32 + 16
    if len(payload) < minimum or len(payload) > BACKUP_MAX_BYTES + 512 or not payload.startswith(BACKUP_MAGIC):
        raise ValueError('备份文件格式不正确')
    offset = len(BACKUP_MAGIC)
    salt, iv = payload[offset:offset + 16], payload[offset + 16:offset + 32]
    ciphertext, supplied_mac = payload[offset + 32:-32], payload[-32:]
    derived = hashlib.pbkdf2_hmac('sha256', passphrase.encode('utf-8'), salt, BACKUP_ITERATIONS, dklen=64)
    if not hmac.compare_digest(hmac.new(derived[32:], payload[:-32], hashlib.sha256).digest(), supplied_mac):
        raise ValueError('备份密码错误或文件已损坏')
    decrypted = subprocess.run([
        'openssl', 'enc', '-aes-256-cbc', '-d', '-K', derived[:32].hex(),
        '-iv', iv.hex(), '-nosalt',
    ], input=ciphertext, capture_output=True, timeout=30, check=False)
    if decrypted.returncode:
        raise ValueError('备份密码错误或文件已损坏')
    try:
        return validate_backup_configuration(json.loads(decrypted.stdout.decode('utf-8')))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError('备份密码错误或文件已损坏')


def apply_configuration(data):
    data = validate_backup_configuration(data)
    mobile = data['mobile']
    save_mobile_settings(
        mobile['apn'], mobile['roaming_allowed'], mobile['traffic_limit_mb'], mobile['disconnect_at_limit']
    )
    set_auto_connect_domestic(mobile['auto_connect_domestic'])
    wifi = data['wifi']
    update_wifi(wifi['ssid'], wifi['passphrase'], wifi['channel'])
    if not wifi['enabled']:
        set_wifi_enabled(False)
    if data['email']:
        write_json(EMAIL_CONFIG, data['email'])
    else:
        EMAIL_CONFIG.unlink(missing_ok=True)
    write_json(CONTACTS_FILE, data['contacts'])
    write_json(NOTIFY_CONFIG, data['notifications'])
    if data['email_retry_enabled']:
        EMAIL_RETRY_DISABLED.unlink(missing_ok=True)
    else:
        EMAIL_RETRY_DISABLED.parent.mkdir(parents=True, exist_ok=True)
        EMAIL_RETRY_DISABLED.touch(mode=0o600, exist_ok=True)
    apply_proxy_settings(data['proxy'])
    for kind, enabled in data['proxy_services'].items():
        set_proxy_enabled(kind, enabled)
    return {'ok': True, 'restored_at': datetime.now().isoformat(timespec='seconds')}


def restore_configuration(payload, passphrase):
    incoming = decrypt_configuration(payload, passphrase)
    previous = validate_backup_configuration(collect_configuration())
    try:
        return apply_configuration(incoming)
    except Exception as exc:
        try:
            apply_configuration(previous)
        except Exception:
            raise RuntimeError(f'恢复失败：{exc}；自动回滚也未完全成功，请运行一键诊断')
        raise RuntimeError(f'恢复失败：{exc}；已自动恢复原配置')


def is_usb_uplink_gateway(address):
    try:
        candidate = ipaddress.ip_address(address)
    except ValueError:
        return False
    if not candidate.is_private:
        return False
    routes = command_json(['ip', '-j', '-4', 'route', 'show', 'default'], [])
    return any(
        item.get('dev') in ('usb0', 'usb1') and item.get('gateway') == address
        for item in routes
    )


class Handler(BaseHTTPRequestHandler):
    def allowed(self):
        ip = self.client_address[0]
        return (ip == '127.0.0.1' or ip.startswith('192.168.68.') or
                ip.startswith('192.168.69.') or ip.startswith('192.168.70.') or
                is_usb_uplink_gateway(ip))

    def reply(self, status, content_type, body, headers=None):
        data = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.allowed():
            self.reply(403, 'text/plain; charset=utf-8', 'Forbidden')
        elif self.path == '/' or self.path.startswith('/?'):
            try:
                page = UI_FILE.read_bytes()
            except OSError:
                page = PAGE.encode('utf-8')
            self.reply(200, 'text/html; charset=utf-8', page)
        elif self.path == '/manifest.webmanifest':
            self.reply(200, 'application/manifest+json; charset=utf-8', MANIFEST_FILE.read_bytes())
        elif self.path == '/icon.svg':
            self.reply(200, 'image/svg+xml', ICON_FILE.read_bytes())
        elif self.path == '/api/messages':
            self.reply(200, 'application/json; charset=utf-8', json.dumps({'messages': messages()}, ensure_ascii=False))
        elif self.path == '/api/contacts':
            self.reply(200, 'application/json; charset=utf-8', json.dumps({'contacts': contacts()}, ensure_ascii=False))
        elif self.path == '/api/status':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(device_status()))
        elif self.path == '/api/email-status':
            configured = False
            recipient = ''
            try:
                email_config = json.loads(EMAIL_CONFIG.read_text(encoding='utf-8'))
                configured = bool(email_config.get('verified'))
                recipient = str(email_config.get('recipient', ''))
            except (OSError, ValueError, json.JSONDecodeError):
                pass
            pending = sum(1 for _ in INBOX.glob('*.forward-pending'))
            route = run_command(['ip', '-4', 'route', 'show', 'default'], timeout=3)
            self.reply(200, 'application/json; charset=utf-8', json.dumps({
                'configured': configured,
                'recipient': recipient,
                'pending': pending,
                'retry_enabled': not EMAIL_RETRY_DISABLED.exists(),
                'delivery_available': route.returncode == 0 and bool(route.stdout.strip()),
            }))
        elif self.path == '/api/notify-config':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(public_notify_config(), ensure_ascii=False))
        elif self.path == '/api/notify-history':
            self.reply(200, 'application/json; charset=utf-8', json.dumps({'history': notify_history()}, ensure_ascii=False))
        elif self.path == '/api/cellular':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(cellular_details(), ensure_ascii=False))
        elif self.path == '/api/uplink':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(uplink_details(), ensure_ascii=False))
        elif self.path == '/api/mobile-settings':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(mobile_settings(), ensure_ascii=False))
        elif self.path == '/api/proxy':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(proxy_details(), ensure_ascii=False))
        elif self.path == '/api/proxy-config':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(public_proxy_settings(), ensure_ascii=False))
        elif self.path == '/api/proxy-logs':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(proxy_logs(), ensure_ascii=False))
        elif self.path == '/api/proxy-history':
            self.reply(200, 'application/json; charset=utf-8', json.dumps({'history': proxy_history()}, ensure_ascii=False))
        elif self.path == '/api/health':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(health_details(), ensure_ascii=False))
        elif self.path == '/api/build':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(build_details(), ensure_ascii=False))
        elif self.path == '/api/diagnostic-download':
            payload = json.dumps(diagnostic_details(), ensure_ascii=False, indent=2).encode('utf-8')
            filename = f"openstick-diagnostic-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            self.reply(200, 'application/json; charset=utf-8', payload, {
                'Content-Disposition': f'attachment; filename="{filename}"',
            })
        elif self.path.startswith('/api/traffic'):
            self.reply(200, 'application/json; charset=utf-8', json.dumps(
                traffic_details('archive=1' in self.path), ensure_ascii=False
            ))
        elif self.path.startswith('/api/thermal'):
            self.reply(200, 'application/json; charset=utf-8', json.dumps(
                thermal_details('archive=1' in self.path), ensure_ascii=False
            ))
        elif self.path == '/api/wifi':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(wifi_details(), ensure_ascii=False))
        elif self.path == '/api/esim':
            try:
                result = esim_details()
            except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
                result = {'detected': False, 'eid': '', 'firmware': '', 'profiles': []}
            self.reply(200, 'application/json; charset=utf-8', json.dumps(result, ensure_ascii=False))
        elif self.path == '/api/esim-network':
            self.reply(200, 'application/json; charset=utf-8', json.dumps(esim_network_path(), ensure_ascii=False))
        else:
            self.reply(404, 'text/plain; charset=utf-8', 'Not found')

    def do_POST(self):
        if not self.allowed():
            self.reply(403, 'application/json; charset=utf-8', json.dumps({'error': '禁止访问'}, ensure_ascii=False))
            return
        if self.path not in ('/api/send', '/api/message-retry', '/api/message-delete', '/api/email-config', '/api/email-retry', '/api/notify-config', '/api/notify-test', '/api/notify-retry', '/api/admin-password', '/api/cellular', '/api/wifi', '/api/wifi-toggle', '/api/mobile-settings', '/api/roaming', '/api/auto-domestic', '/api/uplink/usb', '/api/proxy', '/api/proxy-config', '/api/proxy-subscription-update', '/api/proxy-rules-update', '/api/proxy-test', '/api/proxy-exit', '/api/proxy-history-restore', '/api/backup-export', '/api/backup-restore', '/api/contacts', '/api/contact-delete', '/api/esim-action', '/api/esim-download'):
            self.reply(404, 'application/json; charset=utf-8', json.dumps({'error': 'Not found'}))
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            maximum = 6 * 1024 * 1024 if self.path == '/api/backup-restore' else 8192
            if length < 1 or length > maximum:
                raise ValueError('请求大小不正确')
            request = json.loads(self.rfile.read(length).decode('utf-8'))
            protected = self.path in (
                '/api/email-config', '/api/notify-config', '/api/admin-password',
                '/api/mobile-settings', '/api/uplink/usb', '/api/proxy-history-restore',
                '/api/backup-export', '/api/backup-restore', '/api/esim-action',
                '/api/esim-download',
            )
            protected = protected or (self.path == '/api/wifi' and request.get('passphrase') not in (None, ''))
            if protected and not check_admin(str(request.get('username', '')), str(request.get('password', ''))):
                self.reply(401, 'application/json; charset=utf-8', json.dumps({'error': '管理员密码错误'}, ensure_ascii=False))
                return
            if self.path == '/api/admin-password':
                new_password = str(request.get('new_password', ''))
                if len(new_password) < 8 or len(new_password) > 128:
                    raise ValueError('新密码应为 8–128 个字符')
                save_admin_password(new_password)
                self.reply(200, 'application/json; charset=utf-8', json.dumps({'ok': True}))
                return
            if self.path == '/api/uplink/usb':
                result = usb_uplink_action(str(request.get('action', '')))
                self.reply(202 if result.get('status') == 'accepted' else 200, 'application/json; charset=utf-8', json.dumps(result, ensure_ascii=False))
                return
            if self.path == '/api/backup-export':
                payload = encrypt_configuration(str(request.get('backup_passphrase', '')))
                filename = f"openstick-config-{datetime.now().strftime('%Y%m%d-%H%M%S')}.osbackup"
                self.reply(200, 'application/octet-stream', payload, {
                    'Content-Disposition': f'attachment; filename="{filename}"',
                })
                return
            if self.path == '/api/backup-restore':
                encoded = str(request.get('backup_data', ''))
                try:
                    payload = base64.b64decode(encoded, validate=True)
                except (ValueError, binascii.Error):
                    raise ValueError('备份文件编码不正确')
                result = restore_configuration(payload, str(request.get('backup_passphrase', '')))
                self.reply(200, 'application/json; charset=utf-8', json.dumps(result, ensure_ascii=False))
                return
            if self.path == '/api/email-retry':
                enabled = request.get('enabled') is True
                EMAIL_RETRY_DISABLED.parent.mkdir(parents=True, exist_ok=True)
                if enabled:
                    try:
                        EMAIL_RETRY_DISABLED.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    EMAIL_RETRY_DISABLED.touch(mode=0o600, exist_ok=True)
                self.reply(200, 'application/json; charset=utf-8', json.dumps({
                    'retry_enabled': enabled,
                    'pending': sum(1 for _ in INBOX.glob('*.forward-pending')),
                }))
                return
            if self.path == '/api/notify-config':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(save_notify_config(request), ensure_ascii=False))
                return
            if self.path == '/api/notify-test':
                result = run_notify('test', str(request.get('channel', '')))
                self.reply(200, 'application/json; charset=utf-8', json.dumps(result, ensure_ascii=False))
                return
            if self.path == '/api/notify-retry':
                result = run_notify('retry', str(request.get('id', '')))
                self.reply(200, 'application/json; charset=utf-8', json.dumps(result, ensure_ascii=False))
                return
            if self.path == '/api/contacts':
                result = save_contact(
                    str(request.get('name', '')),
                    str(request.get('number', '')),
                    str(request.get('note', '')),
                    str(request.get('tag', '')),
                )
                self.reply(200, 'application/json; charset=utf-8', json.dumps({'contacts': result}, ensure_ascii=False))
                return
            if self.path == '/api/contact-delete':
                result = delete_contact(str(request.get('number', '')))
                self.reply(200, 'application/json; charset=utf-8', json.dumps({'contacts': result}, ensure_ascii=False))
                return
            if self.path == '/api/message-delete':
                result = delete_sms_records(request.get('message_id', ''), request.get('number', ''))
                self.reply(200, 'application/json; charset=utf-8', json.dumps(result, ensure_ascii=False))
                return
            if self.path == '/api/message-retry':
                target, message_id, timestamp, number, text = prepare_sms_retry(request.get('message_id', ''))
                threading.Thread(
                    target=send_sms_background,
                    args=(target, message_id, timestamp, number, text),
                    daemon=True
                ).start()
                self.reply(202, 'application/json; charset=utf-8', json.dumps({
                    'ok': True, 'message_id': message_id, 'state': 'sending'
                }, ensure_ascii=False))
                return
            if self.path == '/api/esim-action':
                result = esim_profile_action(
                    str(request.get('action', '')),
                    str(request.get('profile_id', ''))
                )
                self.reply(200, 'application/json; charset=utf-8', json.dumps(result, ensure_ascii=False))
                return
            if self.path == '/api/esim-download':
                result = esim_download(
                    str(request.get('activation_code', '')).strip(),
                    str(request.get('confirmation_code', '')).strip()
                )
                self.reply(200, 'application/json; charset=utf-8', json.dumps(result, ensure_ascii=False))
                return
            if self.path == '/api/cellular':
                enabled = request.get('enabled') is True
                if enabled:
                    thermal = thermal_details()
                    if thermal.get('temperature') is not None and thermal['temperature'] >= THERMAL_THROTTLE_C:
                        raise ValueError('设备温度过高，请降到 57℃ 以下再开启蜂窝数据')
                    changed = run_command(['nmcli', 'connection', 'up', 'unicom-4g'], timeout=75)
                    if changed.returncode:
                        raise RuntimeError((changed.stderr or changed.stdout or 'cellular connection failed').strip())
                else:
                    run_command(['nmcli', 'connection', 'down', 'unicom-4g'], timeout=20)
                self.reply(200, 'application/json; charset=utf-8', json.dumps(cellular_details(), ensure_ascii=False))
                return
            if self.path == '/api/wifi-toggle':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    set_wifi_enabled(request.get('enabled') is True), ensure_ascii=False
                ))
                return
            if self.path == '/api/auto-domestic':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    set_auto_connect_domestic(request.get('enabled') is True), ensure_ascii=False
                ))
                return
            if self.path == '/api/proxy':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    set_proxy_enabled(str(request.get('kind', '')), request.get('enabled') is True),
                    ensure_ascii=False
                ))
                return
            if self.path == '/api/proxy-config':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    save_proxy_preferences(request), ensure_ascii=False
                ))
                return
            if self.path == '/api/proxy-subscription-update':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    update_proxy_subscription(str(request.get('subscription_id', ''))), ensure_ascii=False
                ))
                return
            if self.path == '/api/proxy-rules-update':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    update_proxy_rules(), ensure_ascii=False
                ))
                return
            if self.path == '/api/proxy-test':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    test_all_proxy_nodes() if request.get('all') is True else
                    test_proxy_node(str(request.get('node_id', ''))), ensure_ascii=False
                ))
                return
            if self.path == '/api/proxy-exit':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(proxy_exit_ip(), ensure_ascii=False))
                return
            if self.path == '/api/proxy-history-restore':
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    restore_proxy_snapshot(str(request.get('snapshot_id', ''))), ensure_ascii=False
                ))
                return
            if self.path == '/api/roaming':
                allowed = request.get('enabled') is True
                changed = run_command([
                    'nmcli', 'connection', 'modify', 'unicom-4g',
                    'connection.autoconnect', 'no',
                    'gsm.home-only', 'no' if allowed else 'yes'
                ], timeout=15)
                if changed.returncode:
                    raise RuntimeError((changed.stderr or changed.stdout or '漫游设置保存失败').strip())
                self.reply(200, 'application/json; charset=utf-8', json.dumps(mobile_settings(), ensure_ascii=False))
                return
            if self.path == '/api/wifi':
                ssid = str(request.get('ssid', '')).strip()
                passphrase = request.get('passphrase')
                if passphrase is not None:
                    passphrase = str(passphrase)
                try:
                    channel = int(request.get('channel', 6))
                except (TypeError, ValueError):
                    raise ValueError('Wi‑Fi 信道格式不正确')
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    update_wifi(ssid, passphrase, channel), ensure_ascii=False
                ))
                return
            if self.path == '/api/mobile-settings':
                apn = str(request.get('apn', '')).strip()
                roaming_allowed = request.get('roaming_allowed') is True
                disconnect_at_limit = request.get('disconnect_at_limit') is True
                try:
                    traffic_limit_mb = int(request.get('traffic_limit_mb', 0) or 0)
                except (TypeError, ValueError):
                    raise ValueError('流量上限格式不正确')
                self.reply(200, 'application/json; charset=utf-8', json.dumps(
                    save_mobile_settings(apn, roaming_allowed, traffic_limit_mb, disconnect_at_limit),
                    ensure_ascii=False
                ))
                return
            if self.path == '/api/email-config':
                authorization_code = str(request.get('authorization_code', '')).strip()
                recipient = str(request.get('recipient', '')).strip()
                if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', recipient):
                    raise ValueError('接收邮箱格式不正确')
                if not re.fullmatch(r'[A-Za-z0-9]{8,64}', authorization_code):
                    raise ValueError('授权码格式不正确')
                config = {
                    'host': 'smtp.qq.com',
                    'port': 465,
                    'username': recipient,
                    'recipient': recipient,
                    'authorization_code': authorization_code,
                    'verified': False,
                }
                EMAIL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
                temporary = EMAIL_CONFIG.with_suffix('.tmp')
                temporary.write_text(json.dumps(config), encoding='utf-8')
                temporary.chmod(0o600)
                temporary.replace(EMAIL_CONFIG)
                tested = subprocess.run(
                    ['/usr/local/sbin/openstick-sms-email.py', '--test'],
                    capture_output=True, text=True, timeout=45, check=False
                )
                if tested.returncode:
                    raise RuntimeError('QQ 邮箱验证失败，请确认已开启 SMTP 并使用授权码')
                config['verified'] = True
                temporary.write_text(json.dumps(config), encoding='utf-8')
                temporary.chmod(0o600)
                temporary.replace(EMAIL_CONFIG)
                self.reply(200, 'application/json; charset=utf-8', json.dumps({'ok': True}, ensure_ascii=False))
                return
            number = str(request.get('number', '')).strip()
            text = str(request.get('text', '')).strip()
            if not re.fullmatch(r'[+0-9][0-9 -]{2,24}', number):
                raise ValueError('收件号码格式不正确')
            number = number.replace(' ', '').replace('-', '')
            if not text or len(text) > 500:
                raise ValueError('短信内容应为 1–500 个字符')
            target, message_id, timestamp = save_outgoing_message(number, text)
            threading.Thread(
                target=send_sms_background,
                args=(target, message_id, timestamp, number, text),
                daemon=True
            ).start()
            self.reply(202, 'application/json; charset=utf-8', json.dumps({
                'ok': True, 'message_id': message_id, 'state': 'sending'
            }, ensure_ascii=False))
        except (ValueError, RuntimeError) as exc:
            self.reply(400, 'application/json; charset=utf-8', json.dumps({'error': str(exc)}, ensure_ascii=False))
        except (json.JSONDecodeError, UnicodeDecodeError, subprocess.TimeoutExpired):
            self.reply(400, 'application/json; charset=utf-8', json.dumps({'error': '请求或发送超时'}, ensure_ascii=False))
        except Exception as exc:
            print(f'API internal error: {type(exc).__name__}', flush=True)
            self.reply(500, 'application/json; charset=utf-8', json.dumps({'error': '内部检查失败，配置未确认应用'}, ensure_ascii=False))

    def log_message(self, fmt, *args):
        return


if __name__ == '__main__':
    INBOX.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=traffic_monitor, daemon=True).start()
    threading.Thread(target=thermal_monitor, daemon=True).start()
    threading.Thread(target=proxy_health_monitor, daemon=True).start()
    try:
        shortcut_server = ThreadingHTTPServer(('0.0.0.0', 80), Handler)
    except OSError as exc:
        print(f'port 80 shortcut unavailable: {exc}', flush=True)
    else:
        threading.Thread(target=shortcut_server.serve_forever, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
