"""Collect a JavaScript-rendered public page locally with Playwright.

Only the supplied hostname is allowed. Any cross-origin navigation/resource,
loopback/private IP destination, or unsupported scheme is blocked. Respect
site usage rules and obtain permission where required.
"""
from __future__ import annotations
import argparse
import asyncio
import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright


def is_public_host(host: str) -> bool:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except OSError:
        return False
    return bool(addresses) and all(ipaddress.ip_address(addr).is_global for addr in addresses)


async def main_async(url: str, output: str):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise SystemExit("Provide a public HTTP(S) URL without embedded credentials.")
    hostname = parsed.hostname.lower()
    if not is_public_host(hostname):
        raise SystemExit("The supplied hostname does not resolve exclusively to public IP addresses.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def allow_same_public_host(route):
            target = urlparse(route.request.url)
            host = (target.hostname or "").lower()
            if target.scheme in {"http", "https"} and host == hostname:
                await route.continue_()
            else:
                await route.abort()

        await page.route("**/*", allow_same_public_host)
        response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        if response is None or response.status >= 400:
            await browser.close()
            raise RuntimeError("The public page could not be loaded successfully.")
        title = await page.title()
        text = (await page.locator("body").inner_text(timeout=5000))[:12000]
        await browser.close()

    Path(output).write_text(json.dumps({"url": url, "title": title, "text": text}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved JS-rendered page evidence to {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--output", default="playwright_research.json")
    args = parser.parse_args()
    asyncio.run(main_async(args.url, args.output))

if __name__ == "__main__":
    main()
