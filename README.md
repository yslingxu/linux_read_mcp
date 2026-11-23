# Linux Read MCP Server

Linux只读MCP服务器，用于在OpenCode中远程查询系统信息和Docker资源。适用于Linux系统故障排除、性能监控、Docker容器诊断等运维场景。

## 目录

- [功能概述](#功能概述)
- [部署指南](#部署指南)
- [使用示例](#使用示例)

---

## 功能概述

这个MCP服务器提供**19个只读工具**，用于远程查询Linux系统状态、Docker容器信息和卷配置，帮助快速诊断系统问题、监控资源使用、分析容器状态。

### 可用工具

#### 系统工具 (10个)

| 工具 | 描述 |
|------|------|
| `get_system_info` | 获取系统信息（OS、主机名、架构等） |
| `get_cpu_info` | 获取CPU信息（核心数、频率、使用率） |
| `get_memory_info` | 获取内存信息（总量、使用量、交换分区） |
| `get_disk_info` | 获取磁盘信息（所有挂载分区的容量使用情况） |
| `get_network_info` | 获取网络接口信息（IP地址、子网掩码等） |
| `get_uptime` | 获取系统运行时间（启动时间和运行时长） |
| `get_process_info` | 获取进程列表（可按名称过滤） |
| `read_file` | 读取文件内容（限制10MB、1000行） |
| `list_directory` | 列出目录内容（最多100项） |
| `get_service_logs` | 获取systemd服务日志（使用journalctl） |

#### Docker工具 (9个)

| 工具 | 描述 |
|------|------|
| `get_docker_containers` | 列出所有Docker容器及状态 |
| `get_docker_images` | 列出所有Docker镜像 |
| `get_docker_stats` | 获取Docker容器资源使用情况（CPU、内存等） |
| `get_docker_logs` | 获取Docker容器日志 |
| `get_docker_inspect` | 获取Docker容器详细信息 |
| `get_docker_volumes` | 列出所有Docker卷及挂载点 |
| `get_docker_volume_inspect` | 获取Docker卷详细配置信息 |
| `get_docker_volume_usage` | 获取Docker卷使用空间大小 |
| `get_docker_container_volumes` | 查看容器挂载的所有卷 |

### 安全特性

- ✅ 只读操作，不能修改系统
- ✅ 路径验证，防止目录遍历
- ✅ 敏感文件保护（/etc/shadow等不可读）
- ✅ 文件大小限制（10MB）
- ✅ 设备文件保护
- ✅ 容器名称验证

---

## 部署指南

### 1. Linux主机安装

#### 安装uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

#### 安装项目
```bash
cd /path/to/linux_read_mcp
uv sync
```

### 2. Windows上配置OpenCode

编辑 `~/.config/opencode/opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "linux-read": {
        "type": "local",
        "command": [
          "ssh",
          "-i",
          "C:\\Users\\[YOUR_USERNAME]\\.ssh\\id_rsa",
          "[LINUX_USER]@[LINUX_HOST]",
          "cd [PROJECT_PATH] && uv run python -m linux_read_mcp.server"
        ]
      }
    }
  }
}
```

**替换参数说明**：
- `[YOUR_USERNAME]`: 替换为您的Windows用户名
- `[LINUX_USER]`: 替换为Linux服务器的用户名
- `[LINUX_HOST]`: 替换为Linux主机IP地址或主机名
- `[PROJECT_PATH]`: 替换为项目在Linux上的绝对路径（如 `/opt/linux_read_mcp`）

### 3. SSH密钥设置（首次使用）

#### 在Linux服务器生成SSH密钥

在Linux服务器上执行：
```bash
# 生成密钥对（如果已有密钥可跳过）
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# 添加公钥到authorized_keys
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 显示私钥内容，复制保存
cat ~/.ssh/id_rsa
```

#### 在Windows上保存私钥并配置权限

在Windows PowerShell中执行：

```powershell
# 创建.ssh目录（如果不存在）
mkdir "$env:USERPROFILE\.ssh" -Force

# 将Linux服务器上的私钥内容保存到本地文件
# 手动复制私钥内容，或使用以下命令（需替换[LINUX_USER]和[LINUX_HOST]）
scp [LINUX_USER]@[LINUX_HOST]:~/.ssh/id_rsa "$env:USERPROFILE\.ssh\id_rsa"

# 设置私钥文件权限（移除继承权限，仅保留当前用户完全控制）
icacls "$env:USERPROFILE\.ssh\id_rsa" /inheritance:r
icacls "$env:USERPROFILE\.ssh\id_rsa" /grant:r "$env:USERNAME:F"
```

**说明**：命令中的 `[LINUX_USER]` 和 `[LINUX_HOST]` 需要替换为实际的Linux用户名和主机地址。

### 4. 验证连接

```bash
opencode mcp list
```

应该看到：
```
✓ linux-read       connected
```

---

## 使用示例

在OpenCode中可以直接用自然语言查询：

```
# 系统监控
查看Linux服务器的CPU和内存使用情况

# Docker容器诊断
nginx容器最近的100行日志是什么？

# Docker卷空间检查
列出所有Docker卷及使用空间

# 进程分析
显示所有python进程
```

---

## 项目结构

```
linux_read_mcp/
├── src/linux_read_mcp/
│   ├── __init__.py
│   └── server.py          # MCP服务器实现（19个工具）
├── scripts/
│   ├── start-server.sh    # 启动脚本
│   └── test_tools.py      # 测试脚本
├── pyproject.toml         # 项目配置
└── README.md              # 本文件
```

## 依赖

- **Python**: >=3.12
- **mcp**: >=1.0.0 (MCP协议SDK)
- **psutil**: >=6.0.0 (系统信息库)
- **Docker**: 可选，用于Docker工具

## 许可证

MIT
