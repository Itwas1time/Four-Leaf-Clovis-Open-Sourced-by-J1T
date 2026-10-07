from .base_scraper import BaseScraper
from .nrhp_scraper import NRHPScraper
from .tdar_scraper import TDARScraper, NADBScraper
from .dinaa_scraper import DInaaScraper
from .open_context_scraper import OpenContextScraper, OpenContextDigitalAntiquityScraper
from .pidba_scraper import PIDBAScraper
from .neotoma_scraper import NeotomaScraper
from .heritage_sw_scraper import HeritageSWScraper
from .crow_canyon_scraper import CrowCanyonScraper
from .existing_collectors import HydroScraper, GeologyScraper, LandStatusScraper
from .meta_scraper import SKOPEScraper, OpenArchDataScraper, CARDScraper, ArchSynthScraper, GitHubArchScraper
from .tribal_scraper import TIGERTribalScraper, NativeLandScraper, BIATribalScraper, EPATribalScraper
from .gbif_fossil_scraper import GBIFFossilScraper
from .neotoma_fossil_scraper import NeotomaFossilScraper
from .idigbio_fossil_scraper import IDigBioFossilScraper
from .pbdb_scraper import PBDBScraper

ALL_SCRAPERS = [
    NRHPScraper,
    TDARScraper,
    NADBScraper,
    DInaaScraper,
    OpenContextScraper,
    OpenContextDigitalAntiquityScraper,
    PIDBAScraper,
    NeotomaScraper,
    HeritageSWScraper,
    CrowCanyonScraper,
    HydroScraper,
    GeologyScraper,
    LandStatusScraper,
    SKOPEScraper,
    OpenArchDataScraper,
    CARDScraper,
    ArchSynthScraper,
    GitHubArchScraper,
    TIGERTribalScraper,
    NativeLandScraper,
    BIATribalScraper,
    EPATribalScraper,
    GBIFFossilScraper,
    NeotomaFossilScraper,
    IDigBioFossilScraper,
    PBDBScraper,
]

SCRAPER_MAP = {s.source_id: s for s in ALL_SCRAPERS}
