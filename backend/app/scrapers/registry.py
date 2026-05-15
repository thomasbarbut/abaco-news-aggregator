from .zf import ZFScraper
from .profit import ProfitScraper
from .cursdeguvernare import CursDeGuvernareScraper
from .manager import ManagerScraper
from .startupcafe import StartupCafeScraper
from .juridice import JuridiceScraper
from .economedia import EconomiediaScraper
from .wall_street import WallStreetScraper
from .forbes import ForbesScraper
from .avocatnet import AvocatnetScraper

SCRAPER_REGISTRY = {
    "ZF - Ziarul Financiar": ZFScraper,
    "Profit.ro": ProfitScraper,
    "Curs de Guvernare": CursDeGuvernareScraper,
    "Manager.ro": ManagerScraper,
    "StartupCafe.ro": StartupCafeScraper,
    "Juridice.ro": JuridiceScraper,
    "Economedia": EconomiediaScraper,
    "Wall-Street.ro": WallStreetScraper,
    "Forbes România": ForbesScraper,
    "Avocatnet.ro": AvocatnetScraper,
}


def get_scraper(source_name: str):
    cls = SCRAPER_REGISTRY.get(source_name)
    if cls is None:
        raise ValueError(f"No scraper registered for: {source_name}")
    return cls()  # type: ignore[abstract]
