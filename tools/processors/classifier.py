"""Step 3: Classify normalized records into target layers."""

import logging

logger = logging.getLogger("scraper")

ANOMALY_CLASSIFICATION = {
    "mound": ["mound", "tumulus", "burial mound", "platform mound", "effigy mound",
              "conical mound", "temple mound"],
    "depression": ["borrow pit", "pit house", "kiva", "sunken plaza", "quarry pit",
                   "depression"],
    "linear_raised": ["earthwork", "embankment", "causeway", "road", "wall", "linear"],
    "linear_depression": ["canal", "ditch", "trench", "moat"],
    "platform_terrace": ["terrace", "platform", "great house", "pueblo",
                         "cliff dwelling"],
    "enclosure": ["enclosure", "fort", "stockade", "palisade", "ring", "circle",
                  "geometric"],
}

SHELTER_CLASSIFICATION = {
    "cave_karst": ["cave", "cavern", "grotto", "sinkhole", "karst", "limestone cave"],
    "rockshelter_sandstone": ["rockshelter", "rock shelter", "bluff shelter",
                              "overhang", "alcove", "cliff dwelling"],
    "lava_tube": ["lava tube", "lava cave", "volcanic cave"],
    "overhang": ["overhang", "canopy", "ledge"],
}

# Shelter type short codes used by cave_shelters.py
SHELTER_SHORT = {
    "cave_karst": "K",
    "rockshelter_sandstone": "R",
    "lava_tube": "L",
    "overhang": "O",
}

SOIL_KEYWORDS = {
    "shell_midden": ["shell midden", "midden", "shell ring", "shell heap"],
    "dark_earth": ["dark earth", "terra preta", "anthropogenic soil", "black earth"],
    "fire_cracked_rock": ["fire-cracked rock", "fcr", "burned rock", "fire cracked"],
}


def _match_classification(text: str, classification: dict) -> str | None:
    """Find the first matching classification for the given text."""
    text_lower = text.lower()
    for category, keywords in classification.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return None


def classify_record(record: dict) -> dict:
    """Classify a normalized record into target layers.

    Returns the record with added 'layers' dict mapping layer names to
    layer-specific attributes.
    """
    name = record.get("name", "").lower()
    site_type = record.get("site_type", "").lower()
    description = record.get("description", "").lower()
    combined = f"{name} {site_type} {description}"

    layers = {}

    # Everything goes to known_sites
    layers["known_sites"] = True

    # Everything with a name goes to search_index
    if record.get("name"):
        layers["search_index"] = True

    # Check for terrain anomalies
    anomaly_type = _match_classification(combined, ANOMALY_CLASSIFICATION)
    if anomaly_type:
        layers["terrain_anomalies"] = {"anomaly_type": anomaly_type}

    # Check for cave/shelter
    shelter_type = _match_classification(combined, SHELTER_CLASSIFICATION)
    if shelter_type:
        layers["cave_shelters"] = {
            "shelter_type": shelter_type,
            "shelter_short": SHELTER_SHORT[shelter_type],
        }

    # Check for soil anomalies
    soil_type = _match_classification(combined, SOIL_KEYWORDS)
    if soil_type:
        layers["soil_anomalies"] = {"soil_type": soil_type}

    # Check for Paleoindian projectile points
    paleo_keywords = ["paleoindian", "clovis", "folsom", "cumberland",
                      "dalton", "eden", "scottsbluff", "hell gap",
                      "gainey", "suwannee", "simpson", "redstone"]
    if any(kw in combined for kw in paleo_keywords):
        layers["citizen_reports"] = {"artifact_class": "lithic_projectile"}

    record["layers"] = layers
    return record


def classify_records(records: list[dict]) -> list[dict]:
    """Classify all records and return with layer assignments."""
    classified = [classify_record(r) for r in records]

    # Log classification stats
    layer_counts = {}
    for rec in classified:
        for layer in rec.get("layers", {}):
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

    for layer, count in sorted(layer_counts.items()):
        logger.info(f"[classifier] {layer}: {count} records")

    return classified
