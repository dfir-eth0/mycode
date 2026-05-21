#!/usr/bin/env python3
# MIT License
# 
# Copyright (c) 2025 dfir-eth0
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import asyncio
import socket
import random
import time
import sys
from scapy.all import IP, TCP, sr1

async def scapy_stealth_scan(host, port, timeout=1):
    try:
        src_port = random.randint(1024, 65535)
        ip_packet = IP(dst=host, ttl=random.randint(60, 120))
        tcp_packet = TCP(sport=src_port, dport=port, flags="S", seq=random.randint(1, 100000))
        response = sr1(ip_packet/tcp_packet, timeout=timeout, verbose=0)
        if response and response.haslayer(TCP):
            if response.getlayer(TCP).flags == 0x12:
                return True
        return False
    except:
        return False

async def socket_connect_scan(host, port, timeout=0.5):
    try:
        loop = asyncio.get_event_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = await loop.run_in_executor(None, sock.connect_ex, (host, port))
        sock.close()
        return result == 0
    except:
        return False

async def hybrid_scan_port(host, port, use_stealth=True):
    if use_stealth:
        return await scapy_stealth_scan(host, port)
    else:
        return await socket_connect_scan(host, port)

async def quick_scan(host, start_port, end_port, use_stealth=True, max_concurrent=50):
    semaphore = asyncio.Semaphore(max_concurrent)
    open_ports = []
    
    async def scan_one(port):
        async with semaphore:
            if await hybrid_scan_port(host, port, use_stealth):
                open_ports.append(port)
                print(f"[+] {host}:{port} OPEN")
    
    tasks = [scan_one(port) for port in range(start_port, end_port+1)]
    await asyncio.gather(*tasks)
    return open_ports

async def monitor_port_forever(host, port, delay=2, use_stealth=True):
    print(f"[*] Monitoring {host}:{port} every {delay}s (stealth={use_stealth})")
    last_status = None
    while True:
        is_open = await hybrid_scan_port(host, port, use_stealth)
        current_status = "OPEN" if is_open else "CLOSED"
        if current_status != last_status:
            print(f"[{time.strftime('%H:%M:%S')}] {host}:{port} -> {current_status}")
            last_status = current_status
        await asyncio.sleep(delay)

async def hybrid_monitor_mode(host, start_port=1, end_port=100, monitor_delay=5, use_stealth=True):
    print(f"[*] Quick scanning {host}:{start_port}-{end_port}")
    open_ports = await quick_scan(host, start_port, end_port, use_stealth)
    if not open_ports:
        print("[-] No open ports found")
        return
    print(f"[*] Open ports: {open_ports}")
    print(f"[*] Starting forever monitoring")
    tasks = [monitor_port_forever(host, port, monitor_delay, use_stealth) for port in open_ports]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scanner.py <IP>                # scan + monitor")
        print("  python scanner.py <IP> --monitor <port>  # monitor single port")
        print("  python scanner.py <IP> --socket       # socket only (no scapy)")
        sys.exit(1)
    
    host = sys.argv[1]
    use_stealth = "--socket" not in sys.argv
    
    if "--monitor" in sys.argv and len(sys.argv) > 3:
        port = int(sys.argv[3])
        asyncio.run(monitor_port_forever(host, port, use_stealth=use_stealth))
    else:
        asyncio.run(hybrid_monitor_mode(host, use_stealth=use_stealth))