from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import time
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "frontend" / "index.html").read_bytes()

MESSAGES = {
    "messages": [
        {"id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "number": "15380839075", "text": "你好，稍后联系。", "pdu_type": "submit", "state": "failed", "error": "error: couldn't send the SMS: QMI protocol error (47): UnknownError", "timestamp": "2026-08-31T10:26:12+00:00"},
        {"number": "10010", "text": "【中国联通】您本月套餐剩余流量 8.6 GB。", "pdu_type": "deliver", "state": "received", "timestamp": "2026-08-31 10:18"},
        {"number": "15380839075", "text": "好的，设备下午带过来。", "pdu_type": "deliver", "state": "received", "timestamp": "2026-08-31 09:46"},
        {"number": "15380839075", "text": "UFI003 的短信界面正在调整。", "pdu_type": "submit", "state": "sent", "timestamp": "2026-08-31 09:42"},
        {"number": "95588", "text": "您的验证码为 381927，5 分钟内有效。", "pdu_type": "deliver", "state": "received", "timestamp": "2026-08-30 22:16"},
        {"number": "10010", "text": "查询余额请回复 101。", "pdu_type": "deliver", "state": "received", "timestamp": "2026-08-30 18:30"},
    ]
}

CONTACTS = {"contacts": [{"name": "测试联系人", "number": "15380839075", "note": "设备联调", "tag": "工作"}]}

STATUS_PAYLOADS = {
    "/api/status": {"cellular": False, "rsrp": None, "temperature": 49.0, "storage_free": "2.3 GB", "storage_total": "7.2 GB", "uptime": "1 小时 16 分", "server_time": time.time()},
    "/api/cellular": {"connected": False, "operator": "", "roaming": False, "packet_status": "disconnected", "autoconnect": False},
    "/api/wifi": {"connected": False, "autoconnect": False, "ssid": "openstick-failsafe", "channel": 6},
    "/api/email-status": {"configured": True, "recipient": "demo@example.com", "pending": 0, "retry_enabled": True, "delivery_available": True},
    "/api/health": {
        "healthy": True,
        "modem": True,
        "version": "2026.09.01.2",
        "build": {
            "release": "2026.09.01.2",
            "build_date": "2026-09-01",
            "components": {
                "webui": {"version": "2026.09.01.2", "sha256": "52daad538c26416a6d8ba85ce9dc7aec244cf8abbccfdf4b363a021ca67fe5a9", "size": 210217, "available": True},
                "backend": {"version": "2026.09.01.2", "sha256": "3574f4beb26a9ce9b3276c77730f835275b22244abe8c59c7015fa733bdd8628", "size": 163949, "available": True},
                "uplink_manager": {"version": "2026.08.31.1", "sha256": "5ef3150a850fafb1a50981ea25a4b987882d07ea93ef57b2822bced9527719d5", "size": 7135, "available": True},
            },
        },
        "issues": [],
        "services": [
            {"name": "openstick-sms-web", "active": True, "required": True},
            {"name": "openstick-sms-inbox", "active": True, "required": True},
            {"name": "openstick-notify", "active": True, "required": True},
            {"name": "openstick-auto-cellular", "active": True, "required": True},
            {"name": "openstick-windows-rndis", "active": True, "required": True},
            {"name": "openstick-mdns", "active": True, "required": True},
            {"name": "openstick-firewall", "active": True, "required": True},
        ],
    },
    "/api/notify-config": {
        "enabled": False,
        "pending": 0,
        "history_count": 0,
        "rules": {"mode": "all"},
        "channels": {
            "bark": {"enabled": False, "configured": False},
            "telegram": {"enabled": False, "configured": False},
            "webhook": {"enabled": False, "configured": False},
        },
    },
    "/api/notify-history": {"history": []},
    "/api/thermal": {
        "temperature": 49.0,
        "level": "normal",
        "action": "温度正常",
        "history": [{"time": time.time() - offset, "temperature": 47.8 + (index % 7) * 0.22} for index, offset in enumerate(range(300, -1, -5))],
        "archive": [],
        "server_time": time.time(),
    },
    "/api/traffic": {
        "rx": "286.4 KB", "tx": "93.8 KB", "total": "380.2 KB",
        "rx_rate": "0 B/s", "tx_rate": "0 B/s", "limit_mb": 0, "limit_percent": 0,
        "history": [{"time": time.time() - offset, "rx_bps": (index % 9) * 145, "tx_bps": (index % 5) * 72} for index, offset in enumerate(range(300, -1, -5))],
        "archive": [],
        "server_time": time.time(),
    },
}


class PreviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        path = url.path
        if path in {"/", "/index.html"}:
            html = HTML
            scene = parse_qs(url.query).get("scene", [""])[0]
            scripts = {
                "conversation": "setTimeout(()=>document.querySelector('.conversation-item:nth-child(2)')?.click(),700)",
                "contacts": "setTimeout(()=>{},700)",
                "contact-editor": "setTimeout(()=>document.querySelector('#openContacts')?.click(),700)",
                "compose": "setTimeout(()=>document.querySelector('#openCompose')?.click(),700)",
                "compose-suggest": "setTimeout(()=>{document.querySelector('#openCompose')?.click();setTimeout(()=>{const input=document.querySelector('#smsNumber');input.value='测';input.dispatchEvent(new Event('input',{bubbles:true}))},150)},700)",
                "delete-menu": "setTimeout(()=>{document.querySelector('.conversation-item:nth-child(2)')?.click();setTimeout(()=>{document.querySelector('#threadMoreMenu').open=true;document.querySelector('.message-delete')?.focus()},150)},700)",
                "failed-message": "setTimeout(()=>document.querySelector('.conversation-item')?.click(),700)",
                "conversation-menu": "(()=>{const open=()=>{const row=document.querySelector('.conversation-item');if(row)row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:610,clientY:260}))};open();const timer=setInterval(open,120);setTimeout(()=>clearInterval(timer),2400)})()",
                "pin-conversation": "(()=>{const pin=()=>{const row=document.querySelector('.conversation-item');if(!row)return false;row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:610,clientY:260}));document.querySelector('#smsContextMenu button')?.click();return true};if(!pin()){const observer=new MutationObserver(()=>{if(pin())observer.disconnect()});observer.observe(document.body,{childList:true,subtree:true})}})()",
                "contact-menu": "(()=>{const open=()=>{const row=document.querySelector('.contact');if(!row)return false;row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:1550,clientY:250}));return true};if(!open()){const observer=new MutationObserver(()=>{if(open())observer.disconnect()});observer.observe(document.body,{childList:true,subtree:true})}})()",
                "message-menu": "setTimeout(()=>{document.querySelector('.conversation-item')?.click();setTimeout(()=>{const row=document.querySelector('.message-row');row?.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:1260,clientY:330}))},180)},700)",
                "send": "setTimeout(()=>{document.querySelector('.conversation-item')?.click();setTimeout(()=>{const box=document.querySelector('#threadMessageBody');box.value='这是一条本地交互测试短信';document.querySelector('#threadSend')?.click()},150)},700)",
                "phone-layout": "document.documentElement.style.width='390px';document.body.style.width='390px'",
                "diagnostics-services": "setTimeout(()=>document.querySelector('#diagServicesToggle')?.click(),700)",
                "diagnostics-services-phone": "document.documentElement.style.width='390px';document.body.style.width='390px';setTimeout(()=>document.querySelector('#diagServicesToggle')?.click(),700)",
                "dismiss-network": "setTimeout(()=>document.querySelector('#dismissNoSimNetwork')?.click(),700)",
            }
            if scene in scripts:
                html = html.replace(b"</body>", f"<script>{scripts[scene]}</script></body>".encode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
            return
        payload = MESSAGES if path == "/api/messages" else CONTACTS if path == "/api/contacts" else STATUS_PAYLOADS.get(path, {})
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        payload = CONTACTS if self.path == "/api/contacts" else {"ok": True}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8765), PreviewHandler).serve_forever()
