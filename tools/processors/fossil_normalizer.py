"""Normalize fossil records from all sources into a common format."""

import logging
import math

logger = logging.getLogger("scraper")

# US bounding box
US_MIN_LAT, US_MAX_LAT = 24.0, 72.0
US_MIN_LON, US_MAX_LON = -180.0, -66.0

# Common names for notable species
COMMON_NAMES = {
    "Mammuthus columbi": "Columbian Mammoth",
    "Mammuthus primigenius": "Woolly Mammoth",
    "Mammut americanum": "American Mastodon",
    "Smilodon fatalis": "Saber-tooth Cat",
    "Smilodon populator": "Saber-tooth Cat (giant)",
    "Arctodus simus": "Short-faced Bear",
    "Canis dirus": "Dire Wolf",
    "Panthera atrox": "American Lion",
    "Megalonyx jeffersonii": "Jefferson's Ground Sloth",
    "Paramylodon harlani": "Harlan's Ground Sloth",
    "Castoroides ohioensis": "Giant Beaver",
    "Equus scotti": "Scott's Horse",
    "Camelops hesternus": "Yesterday's Camel",
    "Bison antiquus": "Ancient Bison",
    "Bison latifrons": "Long-horned Bison",
    "Glyptotherium texanum": "Texas Glyptodont",
    "Bootherium bombifrons": "Shrub-ox",
    "Cervalces scotti": "Stag-moose",
    "Tremarctos floridanus": "Florida Spectacled Bear",
    "Tyrannosaurus rex": "Tyrannosaurus Rex",
    "Triceratops horridus": "Triceratops",
    "Triceratops prorsus": "Triceratops",
    "Allosaurus fragilis": "Allosaurus",
    "Stegosaurus stenops": "Stegosaurus",
    "Diplodocus longus": "Diplodocus",
    "Diplodocus carnegii": "Diplodocus",
    "Apatosaurus ajax": "Brontosaurus",
    "Apatosaurus louisae": "Brontosaurus",
    "Deinonychus antirrhopus": "Deinonychus",
    "Hadrosaurus foulkii": "Hadrosaurus",
    "Parasaurolophus walkeri": "Parasaurolophus",
    "Pachycephalosaurus wyomingensis": "Pachycephalosaurus",
    "Brachiosaurus altithorax": "Brachiosaurus",
    "Camarasaurus supremus": "Camarasaurus",
    "Ceratosaurus nasicornis": "Ceratosaurus",
    "Coelophysis bauri": "Coelophysis",
    "Edmontosaurus annectens": "Edmontosaurus",
    "Ankylosaurus magniventris": "Ankylosaurus",
    "Maiasaura peeblesorum": "Maiasaura",
    "Torosaurus latus": "Torosaurus",
    "Chasmosaurus belli": "Chasmosaurus",
    "Centrosaurus apertus": "Centrosaurus",
    "Corythosaurus casuarius": "Corythosaurus",
    "Lambeosaurus lambei": "Lambeosaurus",
    "Styracosaurus albertensis": "Styracosaurus",
    "Protoceratops andrewsi": "Protoceratops",
    "Ornithomimus velox": "Ornithomimus",
    "Struthiomimus altus": "Struthiomimus",
    "Thescelosaurus neglectus": "Thescelosaurus",
    "Tenontosaurus tilletti": "Tenontosaurus",
    "Camptosaurus dispar": "Camptosaurus",
    "Nothrotheriops shastensis": "Shasta Ground Sloth",
    "Eremotherium laurillardi": "Giant Ground Sloth",
    "Glossotherium harlani": "Harlan's Ground Sloth",
    "Tapirus veroensis": "Vero Tapir",
    "Platygonus compressus": "Flat-headed Peccary",
    "Mylohyus nasutus": "Long-nosed Peccary",
    "Paleolama mirifica": "Stout-legged Llama",
    "Hemiauchenia macrocephala": "Large-headed Llama",
    "Cuvieronius tropicus": "Gomphothere",
    "Stegomastodon mirificus": "Stegomastodon",
    "Mosasaurus hoffmannii": "Mosasaurus",
    "Tylosaurus proriger": "Tylosaurus",
    "Pteranodon longiceps": "Pteranodon",
    "Xiphactinus audax": "Xiphactinus",
    "Elasmosaurus platyurus": "Elasmosaurus",
}

# Map geological time periods from age in Ma
def _age_to_period(age_ma: float | None) -> str:
    """Convert age in millions of years to geological period name."""
    if age_ma is None:
        return ""
    try:
        age = float(age_ma)
    except (ValueError, TypeError):
        return ""
    if age < 0.0117:
        return "Holocene"
    if age < 2.58:
        return "Pleistocene"
    if age < 5.33:
        return "Pliocene"
    if age < 23.03:
        return "Miocene"
    if age < 33.9:
        return "Oligocene"
    if age < 56.0:
        return "Eocene"
    if age < 66.0:
        return "Paleocene"
    if age < 145.0:
        return "Cretaceous"
    if age < 201.3:
        return "Jurassic"
    if age < 251.9:
        return "Triassic"
    if age < 298.9:
        return "Permian"
    if age < 358.9:
        return "Carboniferous"
    if age < 419.2:
        return "Devonian"
    if age < 443.8:
        return "Silurian"
    if age < 485.4:
        return "Ordovician"
    return "Cambrian"


def _lookup_common_name(scientific_name: str, genus: str) -> str:
    """Look up common name for a species or genus."""
    if scientific_name in COMMON_NAMES:
        return COMMON_NAMES[scientific_name]
    # Try genus-level match
    for key, name in COMMON_NAMES.items():
        if key.startswith(genus + " "):
            return name
    return ""


def normalize_fossil_record(record: dict, source: str) -> dict | None:
    """Normalize a single fossil record to common format."""
    lat = record.get("lat")
    lon = record.get("lon")
    if lat is None or lon is None:
        return None

    try:
        lat, lon = float(lat), float(lon)
    except (ValueError, TypeError):
        return None

    if math.isnan(lat) or math.isnan(lon):
        return None
    if not (US_MIN_LAT <= lat <= US_MAX_LAT):
        return None
    if not (US_MIN_LON <= lon <= US_MAX_LON):
        return None

    name = str(record.get("name") or "").strip()
    genus = str(record.get("genus") or "").strip()
    species = str(record.get("species") or "").strip()
    kingdom = str(record.get("kingdom") or "").strip()
    phylum = str(record.get("phylum") or "").strip()
    cls = str(record.get("class") or "").strip()
    order = str(record.get("order") or "").strip()
    family = str(record.get("family") or "").strip()
    state = str(record.get("state") or "").strip()
    institution = str(record.get("institution") or "").strip()
    source_id = str(record.get("source_id") or "").strip()

    # Derive time period
    time_period = str(record.get("time_period") or "").strip()
    age_mya = None

    if not time_period:
        # Try age fields from different sources
        age_max = record.get("age_max_ma") or record.get("age_old")
        age_min = record.get("age_min_ma") or record.get("age_young")

        if age_max is not None:
            try:
                age_mya = float(age_max)
                time_period = _age_to_period(age_mya)
            except (ValueError, TypeError):
                pass

    common_name = _lookup_common_name(name, genus)

    # Dataset type for Neotoma records
    dataset_type = str(record.get("dataset_type") or "").strip()

    return {
        "name": name,
        "common_name": common_name,
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "state": state,
        "kingdom": kingdom,
        "phylum": phylum,
        "class": cls,
        "order": order,
        "family": family,
        "genus": genus,
        "species": species,
        "time_period": time_period,
        "age_mya": round(age_mya, 2) if age_mya is not None else None,
        "source": source,
        "source_id": source_id,
        "institution": institution,
        "dataset_type": dataset_type,
    }


def normalize_fossil_records(raw_records: list[dict], source: str) -> list[dict]:
    """Normalize a list of fossil records."""
    normalized = []
    discarded = 0
    for rec in raw_records:
        norm = normalize_fossil_record(rec, source)
        if norm:
            normalized.append(norm)
        else:
            discarded += 1

    logger.info(
        f"[fossil_normalizer] {source}: {len(normalized)} normalized, "
        f"{discarded} discarded from {len(raw_records)} raw"
    )
    return normalized
