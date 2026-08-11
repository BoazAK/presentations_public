"""
Démo 1 : Scanner de ports asynchrone
PyCon Togo 2026

Utilise asyncio pour scanner des centaines de ports en parallèle.
Le site scanme.nmap.org est AUTORISÉ pour les tests.
"""

import asyncio
import sys


async def is_port_open(host: str, port: int, timeout: float = 1.0) -> int | None:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        writer.close()
        await writer.wait_closed()
        return port
    except Exception:
        return None


async def scan_ports(host: str, ports: list[int], timeout: float = 1.0) -> list[int]:
    print(f"[*] Scanning {host} ({len(ports)} ports)...")
    tasks = [is_port_open(host, port, timeout) for port in ports]
    results = await asyncio.gather(*tasks)
    open_ports = sorted(p for p in results if p is not None)
    return open_ports


def main():
    host = "scanme.nmap.org"
    ports = list(range(1, 1025))

    if len(sys.argv) > 1:
        host = sys.argv[1]

    open_ports = asyncio.run(scan_ports(host, ports))

    if open_ports:
        print(f"\n[+] Ports ouverts sur {host}:")
        for port in open_ports:
            service = {22: "SSH", 80: "HTTP", 443: "HTTPS", 8080: "HTTP-Alt", 8443: "HTTPS-Alt"}.get(port, "?")
            print(f"    {port:5d} → {service}")
    else:
        print(f"\n[-] Aucun port ouvert trouvé sur {host}")

    print(f"\n[*] Scan terminé.")


if __name__ == "__main__":
    main()
