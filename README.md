# Linux Read MCP Server

Linux只读MCP服务器，用于在OpenCode中远程查询系统信息。

## 功能概述

这个MCP服务器提供10个只读工具，用于查询Linux系统状态和信息。

### 可用工具

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

### 安全特性

- ✅ 只读操作，不能修改系统
- ✅ 路径验证，防止目录遍历
- ✅ 敏感文件保护（/etc/shadow等不可读）
- ✅ 文件大小限制（10MB）
- ✅ 设备文件保护

## 部署指南

### 1. Linux主机安装

#### 安装uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
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

**替换以下参数**：
- `[YOUR_USERNAME]`: 你的Windows用户名
- `[LINUX_USER]`: Linux用户名
- `[LINUX_HOST]`: Linux主机IP或主机名
- `[PROJECT_PATH]`: Linux上项目的绝对路径（如 `/opt/linux_read_mcp`）

**示例**：
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
          "C:\\Users\\admin\\.ssh\\id_rsa",
          "ubuntu@192.168.1.100",
          "cd /opt/linux_read_mcp && uv run python -m linux_read_mcp.server"
        ]
      }
    }
  }
}
```

### 3. 验证连接

```bash
opencode mcp list
```

应该看到：
```
✓ linux-read       connected
```

## 使用示例

在OpenCode中尝试以下命令：

### 查看系统信息
```
显示Linux服务器的系统版本和CPU信息
```

### 检查资源使用
```
查看内存和磁盘使用情况
```

### 检查进程
```
列出所有nginx进程
```

### 读取文件
```
读取/etc/hostname文件
```

### 查看日志
```
显示SSH服务最近100行日志
```

### 完整示例对话

**用户**: "我想了解这个Linux服务器的状态"

**OpenCode会**:
1. 调用 `get_system_info()` - 获取系统基本信息
2. 调用 `get_cpu_info()` - 显示CPU状态
3. 调用 `get_memory_info()` - 显示内存使用
4. 调用 `get_disk_info()` - 显示磁盘使用
5. 返回完整的系统概览

## SSH设置（首次使用）

### 生成SSH密钥

在Windows PowerShell中：
```powershell
mkdir "$env:USERPROFILE\.ssh" -Force
ssh-keygen -t rsa -b 4096 -f "$env:USERPROFILE\.ssh\id_rsa"
```

### 添加公钥到Linux

```powershell
cat "$env:USERPROFILE\.ssh\id_rsa.pub" | ssh user@linux-host "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

## 项目结构

```
linux_read_mcp/
├── src/linux_read_mcp/
│   ├── __init__.py
│   └── server.py          # MCP服务器实现
├── scripts/
│   ├── start-server.sh    # 启动脚本
│   └── test_tools.py      # 测试脚本
├── pyproject.toml
└── README.md              # 本文件
```

## 依赖

- mcp>=1.0.0
- psutil>=6.0.0
- Python>=3.12

## 许可证

MIT
