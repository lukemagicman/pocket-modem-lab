import argparse
import json
import urllib.request


def get_json(base_url, endpoint):
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{endpoint}",
        headers={"Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description="OpenStick 设备只读回归检查")
    parser.add_argument("device_url")
    parser.add_argument("--expected-version", default="")
    args = parser.parse_args()

    health = get_json(args.device_url, "/api/health")
    uplink = get_json(args.device_url, "/api/uplink")
    wifi = get_json(args.device_url, "/api/wifi")

    required = [item for item in health.get("services", []) if item.get("required")]
    inactive = [item.get("name", "unknown") for item in required if not item.get("active")]
    if inactive:
        raise SystemExit(f"必要服务未运行：{', '.join(inactive)}")
    if wifi.get("autoconnect") is not False:
        raise SystemExit("Wi-Fi autoconnect 未保持关闭")
    if args.expected_version and health.get("version") != args.expected_version:
        raise SystemExit(
            f"版本不一致：设备 {health.get('version')}，预期 {args.expected_version}"
        )
    for key in ("mode", "active", "uplinks", "capabilities", "management"):
        if key not in uplink:
            raise SystemExit(f"/api/uplink 缺少字段：{key}")

    components = health.get("build", {}).get("components", {})
    if args.expected_version:
        for name in ("webui", "backend", "uplink_manager"):
            info = components.get(name, {})
            if not info.get("available") or len(info.get("sha256", "")) != 64:
                raise SystemExit(f"构建信息不完整：{name}")

    print(
        "Live read-only check OK: "
        f"version={health.get('version')}, "
        f"required={len(required)}/{len(required)}, "
        f"temperature={health.get('temperature')} C, "
        f"wifi_autoconnect={wifi.get('autoconnect')}, "
        f"uplink={uplink.get('active') or 'management-only'}"
    )


if __name__ == "__main__":
    main()
