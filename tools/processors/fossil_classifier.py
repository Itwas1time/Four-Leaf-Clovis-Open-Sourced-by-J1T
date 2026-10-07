"""Classify normalized fossil records into dinosaur, megafauna, and plant layers."""

import logging

logger = logging.getLogger("scraper")

# Megafauna genera (Pleistocene large animals)
MEGAFAUNA_GENERA = {
    "Mammuthus", "Mammut", "Megalonyx", "Smilodon", "Arctodus",
    "Bison", "Equus", "Camelops", "Glyptodon", "Nothrotheriops",
    "Paramylodon", "Eremotherium", "Castoroides", "Cervalces",
    "Bootherium", "Tapirus", "Platygonus", "Mylohyus",
    "Paleolama", "Hemiauchenia", "Cuvieronius", "Stegomastodon",
    "Megatherium", "Glossotherium", "Panthera", "Miracinonyx",
    "Tremarctos", "Glyptotherium", "Ursus", "Canis",
    "Nothrotheriops", "Holmesina", "Dasypus",
}

# Orders/families that indicate dinosaurs
DINOSAUR_ORDERS = {
    "saurischia", "ornithischia", "theropoda", "sauropodomorpha",
    "ornithopoda", "thyreophora", "marginocephalia", "ceratopsia",
}

DINOSAUR_FAMILIES = {
    "tyrannosauridae", "triceratopsidae", "ceratopsidae", "hadrosauridae",
    "stegosauridae", "ankylosauridae", "diplodocidae", "brachiosauridae",
    "dromaeosauridae", "ornithomimidae", "pachycephalosauridae",
    "allosauridae", "camarasauridae", "coelophysidae", "abelisauridae",
    "spinosauridae", "therizinosauridae", "oviraptoridae",
    "titanosauridae", "neoceratopsia", "iguanodontidae",
}

# Marine reptile orders/families
MARINE_REPTILE_KEYWORDS = {
    "plesiosauria", "ichthyosauria", "mosasauridae", "mosasaurus",
    "tylosaurus", "elasmosaurus", "plesiosaurus", "ichthyosaurus",
    "pliosauridae",
}

# Pterosaur keywords
PTEROSAUR_KEYWORDS = {
    "pterosauria", "pteranodon", "pterodactyl", "azhdarchidae",
    "pteranodontidae",
}

# Mesozoic time periods
MESOZOIC_PERIODS = {"triassic", "jurassic", "cretaceous"}

# Pleistocene time periods
PLEISTOCENE_PERIODS = {"pleistocene", "holocene", "quaternary"}


def classify_fossil(record: dict) -> str:
    """Classify a fossil record into a taxon group.

    Returns one of: "dinosaur", "megafauna", "marine_reptile", "pterosaur",
    "ancient_plant", "invertebrate", or "other_vertebrate".
    """
    cls = (record.get("class") or "").lower()
    order = (record.get("order") or "").lower()
    family = (record.get("family") or "").lower()
    genus = (record.get("genus") or "").strip()
    name = (record.get("name") or "").lower()
    kingdom = (record.get("kingdom") or "").lower()
    phylum = (record.get("phylum") or "").lower()
    time_period = (record.get("time_period") or "").lower()
    dataset_type = (record.get("dataset_type") or "").lower()

    # Plants (kingdom Plantae or plant-related dataset types)
    if kingdom == "plantae" or dataset_type in ("pollen", "plant macrofossil", "charcoal"):
        return "ancient_plant"

    # Dinosaurs
    if order in DINOSAUR_ORDERS:
        return "dinosaur"
    if family in DINOSAUR_FAMILIES:
        return "dinosaur"
    # Check name for dinosaur-specific keywords
    dino_keywords = ["saurus", "ceratops", "raptor", "tyranno", "stego",
                     "ankylo", "hadro", "brachio", "diplo", "apato",
                     "iguanodon", "deinonychus", "coelophysis", "maiasaur"]
    if cls == "reptilia" and time_period in MESOZOIC_PERIODS:
        if any(kw in name for kw in dino_keywords):
            return "dinosaur"

    # Marine reptiles
    combined = f"{order} {family} {name}"
    if any(kw in combined for kw in MARINE_REPTILE_KEYWORDS):
        return "marine_reptile"

    # Pterosaurs (group with dinosaurs for display)
    if any(kw in combined for kw in PTEROSAUR_KEYWORDS):
        return "dinosaur"

    # Megafauna (check genus)
    if genus in MEGAFAUNA_GENERA:
        return "megafauna"

    # Large Pleistocene mammals are megafauna candidates
    if cls == "mammalia" and time_period in PLEISTOCENE_PERIODS:
        # Known megafauna families
        megafauna_families = {
            "elephantidae", "mammutidae", "megatheriidae", "mylodontidae",
            "megalonychidae", "glyptodontidae", "felidae", "ursidae",
            "camelidae", "equidae",
        }
        if family in megafauna_families:
            return "megafauna"

    # Vertebrate fauna dataset type from Neotoma
    if dataset_type == "vertebrate fauna":
        if time_period in PLEISTOCENE_PERIODS or not time_period:
            return "megafauna"

    # Mesozoic-era reptilian classes → dinosaur layer
    # GBIF classifies many fossil reptiles under specific classes, not "Reptilia"
    mesozoic_classes = {
        "testudines", "squamata", "crocodylia", "elasmobranchii",
        "amphibia", "actinopterygii", "chondrichthyes",
    }
    if cls in mesozoic_classes:
        return "dinosaur"

    # Remaining reptilia in any form → dinosaur
    if cls == "reptilia":
        return "dinosaur"

    # Mammalia without time period info → likely megafauna from fossil collections
    if cls == "mammalia":
        return "megafauna"

    # Invertebrate fossils
    if phylum in ("mollusca", "arthropoda", "brachiopoda", "echinodermata"):
        return "invertebrate"

    # Default: other vertebrate
    return "other_vertebrate"


def classify_fossil_records(records: list[dict]) -> list[dict]:
    """Classify all fossil records and add taxon_group field."""
    counts = {}
    for rec in records:
        group = classify_fossil(rec)
        rec["taxon_group"] = group
        counts[group] = counts.get(group, 0) + 1

    for group, count in sorted(counts.items()):
        logger.info(f"[fossil_classifier] {group}: {count}")

    return records
