#!/usr/bin/env python3
"""
Healthcheck script for scheduler service.
Verifies that the scheduler_worker.py process is running.
"""
import sys
import psutil

try:
    # Check if any process is running scheduler_worker.py
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            if cmdline and any("scheduler_worker.py" in str(arg) for arg in cmdline):
                # Process found and running
                sys.exit(0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Process not found
    sys.exit(1)
except Exception as e:
    # Error occurred
    print(f"Healthcheck error: {e}")
    sys.exit(1)
