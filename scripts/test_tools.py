#!/usr/bin/env python3
"""
测试脚本 - 验证MCP服务器的所有功能

运行此脚本来测试所有可用的工具。
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from linux_read_mcp.server import (
        get_system_info,
        get_cpu_info,
        get_memory_info,
        get_disk_info,
        get_network_info,
        get_process_info,
        get_service_logs,
        get_uptime,
        read_file_safe,
        list_directory_safe,
    )
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已运行: uv sync")
    sys.exit(1)


def print_section(title):
    """打印分隔符和标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_system_info():
    """测试系统信息"""
    print_section("系统信息")
    info = get_system_info()
    print(info)


def test_cpu_info():
    """测试CPU信息"""
    print_section("CPU信息")
    info = get_cpu_info()
    print(info)


def test_memory_info():
    """测试内存信息"""
    print_section("内存信息")
    info = get_memory_info()
    print(info)


def test_disk_info():
    """测试磁盘信息"""
    print_section("磁盘信息")
    info = get_disk_info()
    print(info)


def test_network_info():
    """测试网络信息"""
    print_section("网络信息")
    info = get_network_info()
    print(info)


def test_process_info():
    """测试进程信息"""
    print_section("进程信息 (所有进程)")
    result = get_process_info()
    lines = result.split("\n")[:10]  # 只显示前10行
    print("\n".join(lines))
    if len(result.split("\n")) > 10:
        print(f"  ... 还有更多进程")
    
    print_section("进程信息 (搜索 'python')")
    result = get_process_info(search="python")
    if result.strip():
        print(result)
    else:
        print("  未找到Python进程")


def test_uptime():
    """测试系统运行时间"""
    print_section("系统运行时间")
    info = get_uptime()
    print(info)


def test_read_file():
    """测试读取文件"""
    print_section("读取文件")
    
    # 尝试读取一些常见的文件
    test_files = [
        "/etc/hostname",
        "/proc/cpuinfo",
        "/etc/os-release",
    ]
    
    for filepath in test_files:
        try:
            content = read_file_safe(filepath, max_lines=5)
            print(f"\n  文件: {filepath}")
            print(f"  {'─'*50}")
            for line in content.split("\n")[:5]:
                print(f"  {line}")
            if len(content.split("\n")) > 5:
                print(f"  ...")
        except Exception as e:
            print(f"\n  文件: {filepath}")
            print(f"  错误: {e}")


def test_list_directory():
    """测试列出目录"""
    print_section("列出目录")
    
    test_dirs = [
        "/",
        "/etc",
        "/tmp",
        "/var/log",
    ]
    
    for dirpath in test_dirs:
        try:
            content = list_directory_safe(dirpath)
            print(f"\n  目录: {dirpath}")
            print(f"  {'─'*50}")
            for line in content.split("\n")[:8]:
                print(f"  {line}")
            if len(content.split("\n")) > 8:
                print(f"  ...")
        except Exception as e:
            print(f"\n  目录: {dirpath}")
            print(f"  错误: {e}")


def test_service_logs():
    """测试服务日志"""
    print_section("服务日志")
    
    # 尝试读取一些常见服务的日志
    test_services = [
        "ssh",
        "systemd",
        "kernel",
    ]
    
    for service in test_services:
        try:
            logs = get_service_logs(service, lines=5)
            print(f"\n  服务: {service}")
            print(f"  {'─'*50}")
            for line in logs.split("\n")[:5]:
                print(f"  {line}")
            if len(logs.split("\n")) > 5:
                print(f"  ...")
        except Exception as e:
            print(f"\n  服务: {service}")
            print(f"  错误: {e}")


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "═"*58 + "╗")
    print("║" + " "*15 + "Linux Read MCP 服务器测试" + " "*17 + "║")
    print("╚" + "═"*58 + "╝")
    
    try:
        test_system_info()
        test_cpu_info()
        test_memory_info()
        test_disk_info()
        test_network_info()
        test_uptime()
        test_process_info()
        test_read_file()
        test_list_directory()
        test_service_logs()
        
        print_section("测试完成")
        print("✓ 所有测试执行完毕")
        
    except KeyboardInterrupt:
        print("\n\n✗ 测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
