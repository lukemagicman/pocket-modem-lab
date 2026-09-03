# Security Policy

## Scope

本项目会接触蜂窝网络、短信、SIM/eSIM、设备管理权限和本地代理配置。诊断资料可能包含高度敏感信息。

## Reporting

请使用 GitHub 仓库的 **Security → Report a vulnerability** 私下报告安全问题。不要在公开 Issue 中粘贴电话号码、短信、IMEI/IMSI/ICCID/EID、激活码、Token、密码、订阅 URL 或完整诊断包。

## Safe operation

- 优先执行只读命令。
- 任何 boot、GPT、PDC/MCFG、NV/QCN/EFS、SIM/eUICC 写入都应先建立并校验备份。
- 不要在生产号码或不可承担资费的 SIM 上运行自动短信、漫游或下载测试。
- Web 控制台对局域网开放前，应修改默认凭据并增加合适的访问控制。

