"""System diagnostics and telemetry for J.A.R.V.I.S. (Stark Industries Protocol)."""
import os
import platform
import socket
import time
from datetime import datetime, timedelta
import psutil


def get_system_diagnostics() -> dict:
    """
    Return comprehensive real-time system metrics:
    CPU, RAM, Battery, Disk, Network, and Uptime.
    """
    try:
        # CPU Telemetry
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_freq = psutil.cpu_freq()
        freq_ghz = round(cpu_freq.current / 1000, 2) if cpu_freq else None

        # Memory Telemetry
        vm = psutil.virtual_memory()
        ram_total_gb = round(vm.total / (1024 ** 3), 1)
        ram_used_gb = round(vm.used / (1024 ** 3), 1)
        ram_percent = vm.percent

        # Battery Telemetry
        battery = psutil.sensors_battery()
        if battery:
            battery_percent = battery.percent
            power_plugged = battery.power_plugged
            secsleft = battery.secsleft
            if secsleft > 0:
                mins_left = secsleft // 60
                hours = mins_left // 60
                mins = mins_left % 60
                time_remaining = f"{hours}h {mins}m"
            else:
                time_remaining = "Charging / Calculating" if power_plugged else "Unknown"
            battery_info = {
                "available": True,
                "percent": battery_percent,
                "power_plugged": power_plugged,
                "status": "Plugged in (Charging)" if power_plugged else "Discharging (Battery)",
                "time_remaining": time_remaining,
            }
        else:
            battery_info = {
                "available": False,
                "status": "Desktop / AC Power (No battery sensor)",
            }

        # Storage Telemetry (Primary Drive)
        try:
            primary_drive = os.getenv("SystemDrive", "C:") + "\\"
            disk = psutil.disk_usage(primary_drive)
            disk_info = {
                "drive": primary_drive,
                "total_gb": round(disk.total / (1024 ** 3), 1),
                "free_gb": round(disk.free / (1024 ** 3), 1),
                "used_percent": disk.percent,
            }
        except Exception:
            disk_info = {"status": "Drive information unavailable"}

        # System Uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_delta = datetime.now() - boot_time
        uptime_str = f"{uptime_delta.days}d {uptime_delta.seconds // 3600}h {(uptime_delta.seconds % 3600) // 60}m"

        # Network / Host
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "127.0.0.1"

        return {
            "success": True,
            "status": "All systems nominal",
            "cpu": {
                "load_percent": cpu_percent,
                "physical_cores": cpu_count_physical,
                "logical_cores": cpu_count_logical,
                "frequency_ghz": freq_ghz,
            },
            "memory": {
                "used_gb": ram_used_gb,
                "total_gb": ram_total_gb,
                "used_percent": ram_percent,
            },
            "battery": battery_info,
            "storage": disk_info,
            "system": {
                "os": f"{platform.system()} {platform.release()} (Build {platform.version()})",
                "hostname": hostname,
                "local_ip": local_ip,
                "uptime": uptime_str,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to retrieve telemetry: {str(exc)}",
        }
