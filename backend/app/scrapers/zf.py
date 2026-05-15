from .rss_base import RSSBaseScraper


class ZFScraper(RSSBaseScraper):
    source_name = "ZF - Ziarul Financiar"
    source_url = "https://www.zf.ro"
    rss_url = "https://www.zf.ro/rss"

    def _parse_entry(self, entry) -> dict | None:
        article = super()._parse_entry(entry)
        if article:
            article["category"] = "financiar"
        return article
