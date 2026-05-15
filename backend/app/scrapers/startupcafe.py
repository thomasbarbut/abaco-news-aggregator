from .rss_base import RSSBaseScraper


class StartupCafeScraper(RSSBaseScraper):
    source_name = "StartupCafe.ro"
    source_url = "https://startupcafe.ro"
    rss_url = "https://startupcafe.ro/feed"

    def _parse_entry(self, entry) -> dict | None:
        article = super()._parse_entry(entry)
        if article:
            article["category"] = "startup"
        return article
