from .rss_base import RSSBaseScraper


class ManagerScraper(RSSBaseScraper):
    source_name = "Manager.ro"
    source_url = "https://www.manager.ro"
    rss_url = "https://www.manager.ro/rss.php"

    def _parse_entry(self, entry) -> dict | None:
        article = super()._parse_entry(entry)
        if article:
            article["category"] = "management"
        return article
