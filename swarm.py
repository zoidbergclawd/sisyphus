#!/usr/bin/env python3
"""
Ralph Swarm Harness

Simple orchestration script to run Ralph with The Companion (Claude Code Controller).
Automatically starts the Companion server and configures Ralph to talk to it.

Usage:
    ./swarm.py [ralph_args]
    
Example:
    ./swarm.py start feature-prd.json
"""

import os
import sys
import time
import subprocess
import socket
import signal
import uuid
from pathlib import Path

COMPANION_PORT = 3456
COMPANION_CMD = ["bunx", "the-companion", "serve"]

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_companion():
    """Start the Companion server in the background."""
    print("🤖 Starting The Companion (Claude Code Controller)...")
    try:
        # Redirect output to null to keep terminal clean, or log file
        process = subprocess.Popen(
            COMPANION_CMD,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return process
    except FileNotFoundError:
        print("❌ Error: 'bun' not found. Please install bun.")
        sys.exit(1)

def main():
    companion_process = None
    
    # Check if companion is running
    if not is_port_open(COMPANION_PORT):
        companion_process = start_companion()
        # Wait for it to start
        print("⏳ Waiting for Companion to be ready...")
        for _ in range(10):
            if is_port_open(COMPANION_PORT):
                break
            time.sleep(1)
        else:
            print("❌ Companion failed to start.")
            if companion_process:
                companion_process.kill()
            sys.exit(1)
        print(f"✅ Companion running on http://localhost:{COMPANION_PORT}")
    else:
        print(f"✅ Companion already running on http://localhost:{COMPANION_PORT}")

    # Generate session ID for this run
    session_id = f"ralph-{uuid.uuid4().hex[:8]}"
    companion_url = f"ws://localhost:{COMPANION_PORT}/ws/cli/{session_id}"
    
    print(f"🔗 Session ID: {session_id}")
    print(f"👉 Open http://localhost:{COMPANION_PORT} to watch Ralph work.")

    # Set up environment for Ralph
    env = os.environ.copy()
    env["RALPH_COMPANION_URL"] = companion_url
    
    # Construct Ralph command
    # Use uv to run ralph
    ralph_cmd = ["uv", "run", "ralph"] + sys.argv[1:]
    if not any(arg.startswith("start") for arg in sys.argv[1:]):
        # Default to showing help if no args provided
        if len(sys.argv) == 1:
            ralph_cmd = ["ralph", "--help"]

    print(f"🚀 Launching Ralph: {' '.join(ralph_cmd)}")
    
    try:
        # Run Ralph
        subprocess.run(ralph_cmd, env=env, check=False)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")
    finally:
        # Cleanup if we started the companion? 
        # Usually better to leave it running for inspection, 
        # but for a harness, maybe we kill it if we started it?
        # Jon asked for a "simple harness". Keeping it running is usually more useful.
        if companion_process:
            print("ℹ️  Companion server left running.")
            # companion_process.kill() 

if __name__ == "__main__":
    main()
