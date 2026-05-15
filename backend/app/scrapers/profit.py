from .rss_base import RSSBaseScraper


class ProfitScraper(RSSBaseScraper):
    source_name = "Profit.ro"
    source_url = "https://www.profit.ro"
    rss_url = "https://www.profit.ro/rss"

    def _parse_entry(self, entry) -> dict | None:
        article = super()._parse_entry(entry)
        if article:
            article["category"] = "economic"
        return article
