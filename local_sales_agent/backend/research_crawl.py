"""Small, public-page-only Scrapy crawler for preloading prospect evidence.

Use only public pages you are permitted to access. Robots.txt is obeyed,
requests are rate-limited per domain, and output is written locally as JSON.
This is a preparation tool; the main app stores the output in SQLite before
an offline acceptance run.
"""
from __future__ import annotations
import argparse
import json
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

from scrapy import Spider
from scrapy.crawler import CrawlerProcess


class PublicSiteSpider(Spider):
    name = "harvey_public_site"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 1.0,
        "DOWNLOAD_TIMEOUT": 15,
        "DOWNLOAD_MAXSIZE": 2_000_000,
        "LOG_ENABLED": False,
        "USER_AGENT": "HarveyLocalResearch/1.0 (+public website research)",
        "DEPTH_LIMIT": 1,
    }

    def __init__(self, start_url: str, page_limit: int = 8, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parsed = urlparse(start_url)
        self.allowed_domains = [parsed.hostname]
        self.start_urls = [start_url]
        self.page_limit = max(1, min(int(page_limit), 25))
        self.count = 0

    def parse(self, response):
        if self.count >= self.page_limit:
            return
        self.count += 1
        title = response.css("title::text").get(default="").strip()
        text = " ".join(t.strip() for t in response.css("body *::text").getall() if t.strip())
        yield {"url": response.url, "title": title, "text": text[:12000]}
        if self.count < self.page_limit:
            for href in response.css("a::attr(href)").getall():
                yield response.follow(href, callback=self.parse)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Public website URL")
    parser.add_argument("--pages", type=int, default=8)
    parser.add_argument("--output", default="research_pages.json")
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise SystemExit("Provide a public HTTP(S) URL without embedded credentials.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))}
    except OSError as exc:
        raise SystemExit(f"Could not resolve the supplied public hostname: {exc}")
    if not addresses or not all(ipaddress.ip_address(addr).is_global for addr in addresses):
        raise SystemExit("The supplied hostname does not resolve exclusively to public IP addresses.")
    items = []
    class CollectingSpider(PublicSiteSpider):
        def parse(self, response):
            for item in super().parse(response) or []:
                items.append(item)
                yield item
    process = CrawlerProcess()
    process.crawl(CollectingSpider, start_url=args.url, page_limit=args.pages)
    process.start()
    Path(args.output).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(items)} public pages to {args.output}")

if __name__ == "__main__":
    main()
