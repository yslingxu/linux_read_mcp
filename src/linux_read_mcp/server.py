"""MCP Server for read-only access to Linux system information."""

import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import Any

import psutil
from mcp.server import MCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security constraints
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_LOG_PATHS = [
    "/var/log",
    "/var/log/syslog",
    "/var/log/messages",
    "/var/log/auth.log",
    "/var/log/kern.log",
]

# Restricted paths that cannot be read
RESTRICTED_PATHS = [
    "/etc/shadow",
    "/etc/passwd",
    "/proc/*/environ",
    "/sys",
    "/proc/sysrq-trigger",
]


def is_path_safe(path: str) -> bool:
    """Check if a path is safe to read."""
    resolved = Path(path).resolve()
    
    # Check restricted paths
    for restricted in RESTRICTED_PATHS:
        if str(resolved).startswith(restricted):
            return False
    
    # Check if file exists and is readable
    if not resolved.exists():
        return False
    
    # Prevent reading special files
    if resolved.is_char_device() or resolved.is_block_device():
        return False
    
    return True


def read_file_safe(path: str, max_lines: int = 1000) -> str:
    """Safely read a file with size and line limits."""
    if not is_path_safe(path):
        raise PermissionError(f"Cannot read path: {path}")
    
    resolved = Path(path)
    
    # Check file size
    try:
        size = resolved.stat().st_size
        if size > MAX_FILE_SIZE:
            return f"File too large ({size} bytes, max {MAX_FILE_SIZE})"
    except OSError as e:
        raise PermissionError(f"Cannot access file: {e}")
    
    # Read file
    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            if len(lines) > max_lines:
                return "".join(lines[:max_lines]) + f"\n... (truncated, total {len(lines)} lines)"
            return "".join(lines)
    except Exception as e:
        raise OSError(f"Error reading file: {e}")


def list_directory_safe(path: str) -> str:
    """Safely list directory contents."""
    if not is_path_safe(path):
        raise PermissionError(f"Cannot access path: {path}")
    
    resolved = Path(path)
    if not resolved.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    
    try:
        entries = []
        for item in sorted(resolved.iterdir())[:100]:  # Limit to 100 entries
            stat = item.stat()
            entries.append(
                f"{'D' if item.is_dir() else 'F'} "
                f"{stat.st_size:>12} {item.name}"
            )
        return "\n".join(entries)
    except Exception as e:
        raise OSError(f"Error listing directory: {e}")


# Create MCP server using MCPServer (high-level API)
mcp = MCPServer("linux-read-mcp")


def main():
    """Main entry point for the MCP server."""
    logger.info("Starting Linux Read MCP Server")
    mcp.run()


# Define tools using decorators
@mcp.tool()
def read_file(path: str, max_lines: int = 1000) -> str:
    """Read the contents of a file. Limited to 10MB per file and 1000 lines."""
    return read_file_safe(path, max_lines)


@mcp.tool()
def list_directory(path: str) -> str:
    """List contents of a directory (up to 100 entries)."""
    return list_directory_safe(path)


@mcp.tool()
def get_system_info() -> str:
    """Get basic system information (OS, hostname, architecture, etc.)."""
    info = {
        "hostname": platform.node(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    return str(info)


@mcp.tool()
def get_cpu_info() -> str:
    """Get CPU information (cores, frequency, usage)."""
    info = {
        "count_logical": psutil.cpu_count(logical=True),
        "count_physical": psutil.cpu_count(logical=False),
        "frequency": dict(psutil.cpu_freq()._asdict()) if psutil.cpu_freq() else {},
        "usage_percent": psutil.cpu_percent(interval=1),
        "usage_per_cpu": psutil.cpu_percent(interval=1, percpu=True),
    }
    return str(info)


@mcp.tool()
def get_memory_info() -> str:
    """Get memory and swap information."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    info = {
        "total": mem.total,
        "available": mem.available,
        "percent": mem.percent,
        "used": mem.used,
        "free": mem.free,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_percent": swap.percent,
    }
    return str(info)


@mcp.tool()
def get_disk_info() -> str:
    """Get disk usage information for all mounted partitions."""
    disks = {}
    try:
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks[partition.mountpoint] = {
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            except (OSError, PermissionError):
                pass
    except Exception as e:
        logger.error(f"Error getting disk info: {e}")
    
    return str(disks)


@mcp.tool()
def get_network_info() -> str:
    """Get network interface information."""
    interfaces = {}
    try:
        for name, addrs in psutil.net_if_addrs().items():
            addr_list = []
            for addr in addrs:
                addr_list.append({
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask or "N/A",
                    "broadcast": addr.broadcast or "N/A",
                })
            interfaces[name] = addr_list
    except Exception as e:
        logger.error(f"Error getting network info: {e}")
    
    return str(interfaces)


@mcp.tool()
def get_process_info(search: str = "") -> str:
    """Get running processes information, optionally filtered by name."""
    processes = []
    try:
        for proc in psutil.process_iter(["pid", "name", "status", "memory_percent", "cpu_percent"]):
            try:
                if search and search.lower() not in proc.name().lower():
                    continue
                info = proc.info
                processes.append(
                    f"{info['pid']:>8} {info['status']:>10} "
                    f"{info['memory_percent']:>6.1f}% {info['cpu_percent']:>6.1f}% {info['name']}"
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.error(f"Error getting process info: {e}")
    
    return "\n".join(processes[:200])  # Limit to 200 processes


@mcp.tool()
def get_service_logs(service: str, lines: int = 100) -> str:
    """Get systemd service logs using journalctl."""
    # Validate service name
    if not service.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid service name")
    
    # Limit lines
    lines = min(lines, 1000)
    unit = f"{service}.service"
    
    try:
        cmd = ["journalctl", "-u", unit, "-n", str(lines), "--no-pager"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout or result.stderr or "No logs found"
    except FileNotFoundError:
        return "journalctl not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        raise OSError(f"Error reading logs: {e}")


@mcp.tool()
def get_uptime() -> str:
    """Get system uptime and boot time."""
    boot_time = psutil.boot_time()
    import time
    uptime_seconds = time.time() - boot_time
    
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    info = {
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": f"{days}d {hours}h {minutes}m",
        "boot_time": boot_time,
    }
    return str(info)


# Docker tools
@mcp.tool()
def get_docker_containers() -> str:
    """Get list of all Docker containers with their status."""
    try:
        cmd = ["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if not lines or not lines[0]:
                return "No containers found"
            # Format output
            formatted = "CONTAINER_ID\t\tNAME\t\t\tSTATUS\t\t\tIMAGE\n"
            formatted += "-" * 100 + "\n"
            for line in lines:
                if line.strip():
                    formatted += line + "\n"
            return formatted
        else:
            return result.stderr or "Failed to get containers"
    except FileNotFoundError:
        return "docker command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_docker_images() -> str:
    """Get list of all Docker images."""
    try:
        cmd = ["docker", "images", "--format", "{{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if not lines or not lines[0]:
                return "No images found"
            # Format output
            formatted = "REPOSITORY\t\tTAG\t\tSIZE\t\t\tCREATED\n"
            formatted += "-" * 100 + "\n"
            for line in lines:
                if line.strip():
                    formatted += line + "\n"
            return formatted
        else:
            return result.stderr or "Failed to get images"
    except FileNotFoundError:
        return "docker command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_docker_stats(container: str = "") -> str:
    """Get Docker container resource usage statistics."""
    try:
        if container:
            # Get stats for specific container
            cmd = ["docker", "stats", "--no-stream", container]
        else:
            # Get stats for all containers
            cmd = ["docker", "stats", "--no-stream"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return "No running containers"
            # Format output with headers
            lines = output.split('\n')
            formatted = ""
            for line in lines:
                formatted += line + "\n"
            return formatted
        else:
            return result.stderr or "Failed to get stats"
    except FileNotFoundError:
        return "docker command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_docker_logs(container: str, lines: int = 100) -> str:
    """Get Docker container logs."""
    if not container:
        return "Error: container name is required"
    
    # Validate container name
    if not container.replace("-", "").replace("_", "").replace(".", "").isalnum():
        return "Error: invalid container name"
    
    # Limit lines
    lines = min(lines, 1000)
    
    try:
        cmd = ["docker", "logs", "--tail", str(lines), container]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if result.returncode == 0:
            output = result.stdout or result.stderr
            return output or "No logs available"
        else:
            return result.stderr or "Failed to get logs"
    except FileNotFoundError:
        return "docker command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_docker_inspect(container: str) -> str:
    """Get detailed Docker container information."""
    if not container:
        return "Error: container name is required"
    
    # Validate container name
    if not container.replace("-", "").replace("_", "").replace(".", "").isalnum():
        return "Error: invalid container name"
    
    try:
        cmd = ["docker", "inspect", container]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if result.returncode == 0:
            # Return formatted JSON output (limited)
            import json
            try:
                data = json.loads(result.stdout)
                # Return only key information
                if data:
                    container_info = data[0]
                    output = f"""Container: {container_info.get('Name', 'N/A').lstrip('/')}
State: {container_info.get('State', {}).get('Status', 'N/A')}
Image: {container_info.get('Config', {}).get('Image', 'N/A')}
Ports: {container_info.get('NetworkSettings', {}).get('Ports', {})}
Volumes: {container_info.get('Mounts', [])}
Environment: {container_info.get('Config', {}).get('Env', [])[:5]}"""  # First 5 env vars
                    return output
            except:
                return result.stdout[:2000]  # Return raw output if parsing fails
        else:
            return result.stderr or "Failed to inspect container"
    except FileNotFoundError:
        return "docker command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


# Docker Volume tools
@mcp.tool()
def get_docker_volumes() -> str:
    """Get list of all Docker volumes."""
    try:
        cmd = ["docker", "volume", "ls", "--format", "{{.Name}}\t{{.Driver}}\t{{.Mountpoint}}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if not lines or not lines[0]:
                return "No volumes found"
            # Format output
            formatted = "VOLUME_NAME\t\t\tDRIVER\t\tMOUNTPOINT\n"
            formatted += "-" * 120 + "\n"
            for line in lines:
                if line.strip():
                    formatted += line + "\n"
            return formatted
        else:
            return result.stderr or "Failed to get volumes"
    except FileNotFoundError:
        return "docker command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_docker_volume_inspect(volume: str) -> str:
    """Get detailed information about a Docker volume."""
    if not volume:
        return "Error: volume name is required"
    
    # Validate volume name
    if not volume.replace("-", "").replace("_", "").isalnum():
        return "Error: invalid volume name"
    
    try:
        cmd = ["docker", "volume", "inspect", volume]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if result.returncode == 0:
            import json
            try:
                data = json.loads(result.stdout)
                if data:
                    vol_info = data[0]
                    output = f"""Volume: {vol_info.get('Name', 'N/A')}
Driver: {vol_info.get('Driver', 'N/A')}
Mountpoint: {vol_info.get('Mountpoint', 'N/A')}
Labels: {vol_info.get('Labels', {})}
Scope: {vol_info.get('Scope', 'N/A')}"""
                    return output
            except:
                return result.stdout[:2000]
        else:
            return result.stderr or "Failed to inspect volume"
    except FileNotFoundError:
        return "docker command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_docker_volume_usage(volume: str) -> str:
    """Get usage information of a Docker volume."""
    if not volume:
        return "Error: volume name is required"
    
    # Validate volume name
    if not volume.replace("-", "").replace("_", "").isalnum():
        return "Error: invalid volume name"
    
    try:
        # First get volume info to get mountpoint
        cmd_inspect = ["docker", "volume", "inspect", volume]
        result_inspect = subprocess.run(
            cmd_inspect,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if result_inspect.returncode != 0:
            return "Volume not found"
        
        import json
        try:
            vol_data = json.loads(result_inspect.stdout)
            if vol_data:
                mountpoint = vol_data[0].get('Mountpoint', '')
                if mountpoint:
                    # Get disk usage of the mountpoint
                    cmd_du = ["du", "-sh", mountpoint]
                    result_du = subprocess.run(
                        cmd_du,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    
                    if result_du.returncode == 0:
                        size_info = result_du.stdout.strip()
                        output = f"""Volume: {volume}
Mountpoint: {mountpoint}
Size: {size_info}"""
                        return output
        except:
            pass
        
        return f"Could not determine usage for volume {volume}"
    except FileNotFoundError:
        return "docker or du command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_docker_container_volumes(container: str) -> str:
    """Get volumes mounted in a Docker container."""
    if not container:
        return "Error: container name is required"
    
    # Validate container name
    if not container.replace("-", "").replace("_", "").replace(".", "").isalnum():
        return "Error: invalid container name"
    
    try:
        cmd = ["docker", "inspect", container, "--format", "{{json .Mounts}}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if result.returncode == 0:
            import json
            try:
                mounts = json.loads(result.stdout)
                if not mounts:
                    return f"Container '{container}' has no mounted volumes"
                
                output = f"Volumes mounted in container '{container}':\n"
                output += "-" * 100 + "\n"
                for mount in mounts:
                    output += f"Source (Host/Volume): {mount.get('Source', 'N/A')}\n"
                    output += f"Destination (Container): {mount.get('Destination', 'N/A')}\n"
                    output += f"Driver: {mount.get('Driver', 'N/A')}\n"
                    output += f"Mode: {mount.get('Mode', 'N/A')}\n"
                    output += f"Type: {mount.get('Type', 'N/A')}\n"
                    output += "-" * 100 + "\n"
                return output
            except:
                return result.stdout[:2000]
        else:
            return result.stderr or "Failed to get container volumes"
    except FileNotFoundError:
        return "docker command not found"
    except subprocess.TimeoutExpired:
        return "Command timeout"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    main()
