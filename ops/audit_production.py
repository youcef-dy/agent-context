"""Read-only VPS inventory for planning Adam context deployment.

Prints resource limits, service names and credential *names*, never values.
Accepts no input and makes no network request or filesystem modification.
"""

import json
import os
import re
import subprocess


def command(args):
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=8, check=True)
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def env_names(path):
    try:
        with open(path, encoding="utf-8") as stream:
            text = stream.read(65536)
    except OSError:
        return []
    return sorted(set(re.findall(r"(?m)^\s*(?:export\s+)?([A-Z][A-Z0-9_]{2,80})\s*=", text)))


def container(name):
    raw = command(["docker", "inspect", name, "--format", "{{json .}}"])
    if raw is None:
        return None
    try:
        item = json.loads(raw)
        host = item.get("HostConfig") or {}
        state = item.get("State") or {}
        mounts = item.get("Mounts") or []
        return {
            "running": state.get("Running"),
            "image": item.get("Config", {}).get("Image"),
            "memory_limit_bytes": host.get("Memory"),
            "cpu_quota": host.get("CpuQuota"),
            "cpu_period": host.get("CpuPeriod"),
            "mount_destinations": [m.get("Destination") for m in mounts],
            "restart_policy": (host.get("RestartPolicy") or {}).get("Name"),
        }
    except (ValueError, TypeError):
        return None


def main():
    names = command(["docker", "ps", "--format", "{{.Names}}"])
    memory = command(["free", "-m"])
    disk = command(["df", "-h", "/"])
    config_path = "/srv/hermes/data/config.yaml"
    try:
        with open(config_path, encoding="utf-8") as stream:
            config = stream.read(2_000_000)
        # This reports only whether a provider is explicitly named.
        provider = next((name for name in ("hindsight", "holographic", "local")
                         if re.search(r"(?m)^\s*provider:\s*[\"']?" + name + r"[\"']?\s*$", config)), None)
        profile_routes = "profile_routes:" in config
        mcp_names = sorted(set(re.findall(r"(?m)^\s{2,8}(render|postgres|context):\s*$", config)))
    except OSError:
        provider, profile_routes, mcp_names = None, None, []
    print(json.dumps({
        "container_names": names.splitlines() if names else [],
        "hermes": container("hermes"),
        "render_broker": container("adam-render-broker"),
        "memory_table": memory,
        "root_disk": disk,
        "hermes_env_names": env_names("/srv/hermes/data/.env"),
        "broker_env_names": env_names("/etc/adam-render-broker.env"),
        "hermes_memory_provider_name": provider,
        "profile_routes_configured": profile_routes,
        "mcp_entry_names": mcp_names,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
