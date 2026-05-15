from .rss_base import RSSBaseScraper


class CursDeGuvernareScraper(RSSBaseScraper):
    source_name = "Curs de Guvernare"
    source_url = "https://cursdeguvernare.ro"
    rss_url = "https://cursdeguvernare.ro/feed"

    def _parse_entry(self, entry) -> dict | None:
        article = super()._parse_entry(entry)
        if article:
            article["category"] = "politic-economic"
        return article
