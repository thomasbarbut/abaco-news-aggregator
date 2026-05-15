from .rss_base import RSSBaseScraper


class JuridiceScraper(RSSBaseScraper):
    source_name = "Juridice.ro"
    source_url = "https://juridice.ro"
    rss_url = "https://juridice.ro/feed"

    def _parse_entry(self, entry) -> dict | None:
        article = super()._parse_entry(entry)
        if article:
            article["category"] = "juridic"
        return article
