"""Authored state-by-state fossil geology readings with claim-level sources.

These are educational summaries, not a locality inventory or a prediction of
what occurs at a town or property. Geologic ages name rock/organism context,
never a calendar date for when someone may find a specimen.
"""
from __future__ import annotations

from copy import deepcopy

from core.us_places import STATE_NAMES

REVIEWED = "2026-10-07"
NPS_STATE_FOSSILS = "https://www.nps.gov/subjects/fossils/official-state-fossils.htm"
NPS_FOSSIL_TYPES = "https://www.nps.gov/subjects/fossils/fossil-types-in-parks.htm"
NPS_MOLLUSKS = "https://www.nps.gov/articles/000/fossil-mollusks.htm"
NPS_TRACE_FOSSILS = "https://www.nps.gov/subjects/fossils/what-is-a-fossil.htm"
NPS_CHINLE = "https://www.nps.gov/zion/learn/nature/secrets-of-the-chinle-formation.htm"
NPS_STATE_MAPS = "https://www.nps.gov/subjects/geology/state-geologic-maps.htm"
USGS_NATIONAL_MAP = "https://ngmdb.usgs.gov/nationalgeology/"
USGS_MAP_COVERAGE = "https://www.usgs.gov/news/national-news-release/usgs-cooperative-national-geologic-map-now-covers-50-states-us"
NPS_PRIMARY_PARKS = "https://www.nps.gov/subjects/fossils/primary-fossil-parks.htm"


def _src(title, url):
    return {"title": title, "url": url}


_NPS = _src("NPS: Official State Fossils", NPS_STATE_FOSSILS)
_TYPES = _src("NPS: Fossil types in parks", NPS_FOSSIL_TYPES)
_MOLLUSKS = _src("NPS: Fossil mollusks", NPS_MOLLUSKS)
_TRACE = _src("NPS: What is a fossil?", NPS_TRACE_FOSSILS)
_MAPS = _src("NPS: State geologic map directory", NPS_STATE_MAPS)
_NATIONAL_MAP = _src("USGS: Cooperative National Geologic Map v2", USGS_MAP_COVERAGE)
_NPS_PARKS = _src("NPS: Primary fossil parks", NPS_PRIMARY_PARKS)


def _fact(text, *sources):
    return {"text": text, "sources": [dict(source) for source in sources]}


# The NPS page is used as a learning index. Where it does not name an example,
# the reading uses the cited state survey or a USGS publication instead. The
# label is deliberately explicit when NPS calls an item proposed or a state
# stone rather than a designated state fossil.
_DATA = {
    "AK": {
        "title": "Alaska — Pleistocene mammoth in a geologically diverse state",
        "designation": "NPS-listed state fossil",
        "groups": ["mammals", "birds", "fish", "plants", "microfossils", "marine invertebrates", "trace fossils"],
        "periods": ["Proterozoic", "Paleozoic", "Cretaceous", "Pleistocene"],
        "facts": [
            _fact("NPS lists the woolly mammoth, Mammuthus primigenius, as Alaska's Pleistocene state fossil.", _NPS),
            _fact("Yukon–Charley Rivers National Preserve records Proterozoic stromatolites and microfossils, Paleozoic marine invertebrates, Cretaceous dinosaur evidence, and Pleistocene megafauna.", _NPS_PARKS),
            _fact("Bluff sediments along the Yukon River in Yukon–Charley span about 700,000 years and preserve successive glacial episodes alongside the preserve's Ice Age fauna.", _src("NPS: Yukon–Charley Rivers geology and paleontology", "https://www.nps.gov/yuch/planyourvisit/geology-and-paleontology.htm")),
        ],
    },
    "AL": {
        "title": "Alabama — Eocene whale in the Gulf Coastal Plain record",
        "designation": "NPS-listed state fossil",
        "groups": ["marine mammals"],
        "periods": ["Eocene"],
        "facts": [
            _fact("Alabama law designates Basilosaurus cetoides as the state fossil; NPS identifies it as an Eocene whale.", _src("Alabama Code § 1-2-20: State Fossil", "https://alison.legislature.state.al.us/code-of-alabama?section=1-2-20"), _NPS),
            _fact("The late Eocene Jackson Group includes fossiliferous Yazoo Clay units such as Pachuta Marl and Shubuta Clay; Smithsonian collections also catalog Alabama Basilosaurus from Jackson Group/Ocala Limestone strata.", _src("USGS Geolex: Pachuta Marl", "https://ngmdb.usgs.gov/Geolex/UnitRefs/PachutaRefs_3153.html"), _src("Smithsonian Institution: Basilosaurus cetoides specimen", "https://www.si.edu/object/nmnhpaleobiology_3342398")),
            _fact("USGS describes Basilosaurus cetoides as a characteristic Eocene whale-like mammal of the Jackson strata and illustrates an Alabama skull restored from collected specimens; the older name Zeuglodon refers to its molar-tooth shape.", _src("USGS Professional Paper 46: Alabama Eocene vertebrates, plate XXI", "https://pubs.usgs.gov/pp/0046/report.pdf")),
        ],
    },
    "AR": {
        "title": "Arkansas — abundant invertebrate fossils and a mixed record",
        "designation": "No Arkansas example listed on the NPS state-fossils page",
        "groups": ["invertebrates", "marine reptiles", "mammals", "plants", "trace fossils"],
        "periods": ["Ordovician", "Pennsylvanian", "Cretaceous", "Pleistocene"],
        "facts": [
            _fact("Most Arkansas fossils are invertebrates. The state survey also records occasional Cretaceous vertebrate bones in the southwest and Pleistocene mammal teeth and bones in gravel, sinkhole, and cave deposits.", _src("Arkansas Geological Survey: Fossils", "https://geology.arkansas.gov/geology/fossils.html")),
            _fact("Northern Arkansas limestone ranges from Ordovician through Pennsylvanian units; Cretaceous and Tertiary deposits add shark teeth, fish and whale bones, reptiles, and land mammals.", _src("Arkansas Geological Survey: Fossils", "https://geology.arkansas.gov/geology/fossils.html")),
            _fact("The survey illustrates a fossil-like pattern in chert from the Boone Formation and describes septarian concretions in the Fayetteville Formation, both inorganic structures that can be mistaken for remains.", _src("Arkansas Geological Survey: Fossils and pseudofossils", "https://geology.arkansas.gov/geology/fossils.html")),
        ],
    },
    "AZ": {
        "title": "Arizona — Triassic forests and Colorado Plateau layers",
        "designation": "NPS-listed state fossil",
        "groups": ["plants", "reptiles", "amphibians", "dinosaurs", "marine invertebrates"],
        "periods": ["Triassic", "Paleozoic"],
        "facts": [
            _fact("NPS lists Araucarioxylon arizonicum, fossil wood from the Triassic, as Arizona's state fossil. Petrified wood is a plant fossil, distinct from a mineral pattern that only resembles a tree section.", _NPS, _TYPES),
            _fact("Petrified Forest National Park documents Chinle Formation petrified logs along with reptile, amphibian, and dinosaur body fossils; the logs were buried in river sediments and preserved as minerals replaced or filled the wood.", _src("NPS: Primary fossil parks", "https://www.nps.gov/subjects/fossils/primary-fossil-parks.htm"), _src("NPS: Petrified wood in the Chinle Formation", "https://www.nps.gov/subjects/fossils/volcanoes-and-fossils.htm")),
            _fact("Farther west in Arizona, the Redwall Limestone, Toroweap, and Kaibab formations preserve brachiopods, bivalves, corals, and bryozoans; the Hermit Formation preserves plants, while Chinle rocks preserve petrified wood.", _src("NPS: Primary fossil parks", NPS_PRIMARY_PARKS)),
        ],
    },
    "CA": {
        "title": "California — Pleistocene mammals across varied basins",
        "designation": "NPS-listed state fossil",
        "groups": ["mammals", "marine invertebrates", "microfossils", "birds", "plants", "trace fossils"],
        "periods": ["Miocene", "Pleistocene", "Quaternary"],
        "facts": [
            _fact("NPS lists Smilodon californicus, the Pleistocene sabertooth cat, as California's state fossil.", _NPS),
            _fact("Joshua Tree's Pleistocene Pinto Basin formed by downfaulting and held lakes, swamps, and grasslands; horses and camels are its most common documented mammals.", _NPS_PARKS),
            _fact("Channel Islands deposits add Quaternary pygmy mammoths, marine mollusks and microfossils, Miocene marine mammals, birds, small land mammals, and root casts formed as shallow groundwater precipitated calcium carbonate.", _NPS_PARKS),
        ],
    },
    "CO": {
        "title": "Colorado — Jurassic dinosaurs and layered western basins",
        "designation": "NPS-listed state fossil",
        "groups": ["dinosaurs", "marine invertebrates", "vertebrates", "trace fossils", "insects", "arachnids", "plants", "mammals", "fish"],
        "periods": ["Cambrian", "Paleozoic", "Triassic", "Jurassic", "Cretaceous", "Eocene"],
        "facts": [
            _fact("NPS lists Stegosaurus stenops, a Jurassic plated dinosaur, as Colorado's state fossil.", _NPS),
            _fact("At Dinosaur National Monument, the Upper Jurassic Morrison Formation contains Allosaurus, Apatosaurus, Diplodocus, Camarasaurus, and Stegosaurus; NPS also documents fossil-bearing Cambrian, Paleozoic, Triassic, and Cretaceous units in the monument.", _src("NPS: Geodiversity Atlas — Dinosaur National Monument", "https://www.nps.gov/articles/nps-geodiversity-atlas-dinosaur-national-monument-colorado-and-utah.htm")),
            _fact("At Florissant, the Eocene Florissant Formation preserves insects and spiders in paper shales, large petrified tree stumps buried by volcanic mudflows, plus flowers, fruits, leaves, fish, and small mammals.", _NPS_PARKS),
        ],
    },
    "CT": {
        "title": "Connecticut — Jurassic tracks in a rift-basin landscape",
        "designation": "NPS-listed state fossil",
        "groups": ["trace fossils", "dinosaurs"],
        "periods": ["Jurassic"],
        "facts": [
            _fact("NPS lists Eubrontes giganteus, a Jurassic dinosaur track, as Connecticut's state fossil. It is a trace fossil: evidence of activity rather than a bone or tooth.", _NPS, _TRACE),
            _fact("The Connecticut Valley's Early Jurassic sandstone preserves many kinds of dinosaur tracks; the state survey catalogs more than 165 tracks recovered during construction monitoring in Rocky Hill.", _src("Connecticut DEEP: Geological Survey collections", "https://portal.ct.gov/DEEP/Geology/Collections"), _src("Connecticut DEEP: State Fossil", "https://portal.ct.gov/About/State-Symbols/The-State-Fossil")),
            _fact("Eubrontes is a large, three-toed footprint. Connecticut has no known skeletal remains of its specific trackmaker, so the state fossil records a track type rather than a named dinosaur skeleton.", _src("Connecticut DEEP: State Fossil", "https://portal.ct.gov/About/State-Symbols/The-State-Fossil")),
        ],
    },
    "DE": {
        "title": "Delaware — Cretaceous belemnite and coastal sediments",
        "designation": "NPS-listed state fossil",
        "groups": ["cephalopods", "marine invertebrates"],
        "periods": ["Cretaceous"],
        "facts": [
            _fact("NPS lists Belemnitella americana, a Cretaceous belemnite, as Delaware's state fossil. Belemnites were squid-like marine animals; the fossilized guard is an internal hard part.", _NPS, _MOLLUSKS),
            _fact("Early Cretaceous Delaware landscapes included rivers and swamps; later in the period, the sea covered most of the state and left marine fossil-bearing deposits.", _src("Delaware Geological Survey: Cretaceous fossils overview", "https://www.dgs.udel.edu/delaware-geology/cretaceous-fossils-overview")),
            _fact("Delaware Cretaceous beds preserve belemnites, large clam and oyster shells, and vertebrates including mosasaurs, plesiosaurs, crocodilians, turtles, and bony fish.", _src("Delaware Geological Survey: Cretaceous fossils overview", "https://www.dgs.udel.edu/delaware-geology/cretaceous-fossils-overview"), _src("Delaware Geological Survey: Dinosaurs in Delaware?", "https://www.dgs.udel.edu/delaware-geology/dinosaurs-delaware")),
        ],
    },
    "DC": {
        "title": "District of Columbia — Cretaceous Potomac Group fossils",
        "designation": "NPS-listed state/district dinosaur example",
        "groups": ["dinosaurs"],
        "periods": ["Cretaceous"],
        "facts": [
            _fact("NPS lists “Capitalsaurus,” an undetermined theropod dinosaur from the Cretaceous, for Washington, D.C. The name is a public learning label; the classification is explicitly undetermined on the NPS page.", _NPS),
            _fact("The Potomac Heritage overview places the District at the Fall Line, the transition between Piedmont bedrock and Coastal Plain sediments.", _src("NPS: Potomac Heritage Trail geology", "https://home.nps.gov/pohe/learn/nature/geology.htm")),
            _fact("Lower Cretaceous Potomac Group deposits around the District are fluvial-deltaic sands, silts, clays, and gravels; NPS inventories document dinosaur-bearing strata and track evidence in the Potomac Group.", _src("USGS: Geologic map of Washington West quadrangle", "https://www.usgs.gov/publications/geologic-map-washington-west-30-60-quadrangle-maryland-virginia-and-washington-dc"), _src("NPS: Oxon Run paleontological resource inventory", "https://irmadev.nps.gov/DataStore/Reference/Profile/2287217")),
        ],
    },
    "FL": {
        "title": "Florida — shallow-marine carbonates and younger river fossils",
        "designation": "NPS-listed state stone; proposed fossil is explicitly unofficial",
        "groups": ["corals", "marine vertebrates", "mammals", "marine invertebrates"],
        "periods": ["Eocene", "Oligocene", "Miocene", "Pliocene", "Pleistocene"],
        "facts": [
            _fact("NPS identifies agatized coral as Florida's official state stone and labels the proposed fossil sea biscuit as unofficial. The coral example is Oligocene–Miocene; the sea biscuit is listed as Eocene.", _NPS),
            _fact("The Florida Museum describes the Peace River Formation as middle Miocene to earliest Pliocene nearshore deposits with shark and ray teeth, bony fish, and marine mammals.", _src("Florida Museum: Peace River Paleo Project", "https://www.floridamuseum.ufl.edu/vertpaleo/amateur-collector/pripp/")),
            _fact("The Florida Museum separates Peace River fossils into late Miocene marine fauna and late Pleistocene land-mammal fauna; the younger assemblage includes Columbian mammoth, mastodon, horse, bison, sloth, and saber-toothed cat.", _src("Florida Museum: Peace River Paleo Project", "https://www.floridamuseum.ufl.edu/vertpaleo/amateur-collector/pripp/")),
        ],
    },
    "GA": {
        "title": "Georgia — Cretaceous-to-Miocene shark teeth",
        "designation": "NPS-listed state fossil example",
        "groups": ["sharks", "marine vertebrates", "mammals", "marine invertebrates", "plants"],
        "periods": ["Cretaceous", "Miocene", "Pleistocene"],
        "facts": [
            _fact("NPS lists a shark tooth as Georgia's state fossil example and places the record broadly from the Cretaceous to the Miocene.", _NPS),
            _fact("Georgia's coastal Pleistocene deposits preserve marine and land vertebrates: the survey lists mastodon, mammoth, ground sloth, extinct horse, shark teeth, and crocodile remains.", _src("Georgia Geological Survey: Pleistocene deposits of coastal Georgia", "https://epd.georgia.gov/document/publication/ic-31-subsurface-study-pleistocene-deposits-coastal-georgia-1965/download")),
            _fact("In those coastal Pleistocene beds, shark teeth occur with molluscan shells, especially clams and snails; plant fragments and lignitic clay also occur in the sediment sequence.", _src("Georgia Geological Survey: Pleistocene deposits of coastal Georgia", "https://epd.georgia.gov/document/publication/ic-31-subsurface-study-pleistocene-deposits-coastal-georgia-1965/download")),
        ],
    },
    "HI": {
        "title": "Hawaiʻi — young volcanic islands and late fossil bird records",
        "designation": "No Hawaiʻi example listed on the NPS state-fossils page",
        "groups": ["birds"],
        "periods": ["Holocene"],
        "facts": [
            _fact("USGS documents extinct and surviving Hawaiian birds from sand dunes, limestone sinkholes, and lava tubes; most dated bones are only a few thousand years old, within the Holocene.", _src("USGS Hawaiian Volcano Observatory: Fossils reveal Hawaiʻi's past birdlife", "https://www.usgs.gov/news/volcano-watch-fossils-reveal-birdlife-hawaiis-past")),
            _fact("The USGS state map covers the eight major islands and documents basalt flows and volcanic rift zones in a young island chain.", _src("USGS: Geologic map of the State of Hawaiʻi", "https://www.usgs.gov/publications/geologic-map-state-hawaii"), _NATIONAL_MAP),
            _fact("USGS reports at least 33 newly recognized extinct and living bird species from the fossil record, including waterfowl, ibises, rails, owls, and songbirds.", _src("USGS Hawaiian Volcano Observatory: Fossils reveal Hawaiʻi's past birdlife", "https://www.usgs.gov/news/volcano-watch-fossils-reveal-birdlife-hawaiis-past")),
        ],
    },
    "ID": {
        "title": "Idaho — Pliocene Hagerman horse and other local fossils",
        "designation": "NPS-listed state fossil",
        "groups": ["mammals", "birds", "fish", "plants", "trace fossils"],
        "periods": ["Pliocene"],
        "facts": [
            _fact("NPS lists Equus simplicidens, the Pliocene Hagerman horse, as Idaho's state fossil.", _NPS),
            _fact("NPS reports more than 200 Hagerman horse individuals from the monument's Horse Quarry; the species is more closely related to zebras than to modern domestic horses.", _NPS_PARKS),
            _fact("Hagerman's Pliocene Glenns Ferry deposits preserve a varied ecosystem with wetland and riparian birds, fish, beavers, peccaries, pronghorn, ground sloths, and carnivorans; the species count approaches 200.", _src("NPS: Hagerman Fossil Beds fossils", "https://www.nps.gov/hafo/learn/nature/fossils.htm"), _src("NPS: New discoveries from old bones at Hagerman", "https://www.nps.gov/articles/park-paleo-spring-2018-prassack-hafo.htm")),
        ],
    },
    "IL": {
        "title": "Illinois — the Pennsylvanian Tully Monster and coal-swamp life",
        "designation": "NPS-listed state fossil",
        "groups": ["soft-bodied marine animals", "fish", "crustaceans", "mollusks", "arthropods"],
        "periods": ["Pennsylvanian"],
        "facts": [
            _fact("NPS lists Tullimonstrum gregarium, the Pennsylvanian Tully Monster, as Illinois's state fossil.", _NPS),
            _fact("At Mazon Creek, the Francis Creek Shale records Pennsylvanian river deltas, swamp lowlands, and shallow bays; ironstone concretions preserve both marine Essex and land-and-freshwater Braidwood faunas.", _src("Illinois State Geological Survey: Mazon Creek paleontology", "https://isgswikis.web.illinois.edu/mazon_creek/index.php/Mazon_Creek_Area_Paleontology")),
            _fact("The Illinois State Museum describes the Tully Monster as a soft-bodied animal with stalked sensory organs and a flexible snout ending in a grasping claw; Mazon Creek also preserves fish, shrimp, clams, and land arthropods.", _src("Illinois State Museum: Mazon Creek animals", "https://www.museum.state.il.us/exhibits/changes/htmls/tropical/marine_animals.html"), _src("Illinois State Museum: About Mazon Creek", "https://www.museum.state.il.us/exhibits/mazon_creek/about_mazon_creek.html")),
        ],
    },
    "IN": {
        "title": "Indiana — Pleistocene mastodons and older marine rocks",
        "designation": "NPS-listed state fossil",
        "groups": ["mammals"],
        "periods": ["Pleistocene"],
        "facts": [
            _fact("NPS lists a Pleistocene mastodon as Indiana's state fossil.", _NPS),
            _fact("Most Indiana fossils are marine and Paleozoic: the Indiana Geological and Water Survey describes shallow seas that repeatedly covered the state and preserve brachiopods, bryozoans, crinoids, bivalves, and corals.", _src("Indiana Geological and Water Survey: Common fossils of Indiana", "https://legacy.igws.indiana.edu/ReferenceDocs/Fossil_card.pdf")),
            _fact("Indiana's fossil record also includes mammoths and other Pleistocene mammals in glacial and river deposits, younger than the Paleozoic sea-floor fossils that dominate its bedrock record.", _NPS, _src("Indiana Geological and Water Survey: Common fossils of Indiana", "https://legacy.igws.indiana.edu/ReferenceDocs/Fossil_card.pdf")),
        ],
    },
    "IA": {
        "title": "Iowa — shallow-sea shells, corals, and crinoids",
        "designation": "No Iowa example listed on the NPS state-fossils page",
        "groups": ["corals", "brachiopods", "crinoids", "gastropods", "eurypterids", "mammals"],
        "periods": ["Ordovician", "Devonian", "Mississippian", "Pleistocene"],
        "facts": [
            _fact("Iowa Geological Survey records shallow-sea fossils across several intervals, including Devonian colonial corals and brachiopods, Ordovician gastropods, and Mississippian crinoids.", _src("Iowa Geological Survey: Fossils", "https://iowageologicalsurvey.uiowa.edu/iowa-geology/popular-interest/fossils")),
            _fact("The Devonian Cedar Valley Group at the Coralville fossil gorge preserves corals, stromatoporoids, brachiopods, and crinoid remains from a tropical sea.", _src("Iowa Geological Survey: Iowa geology", "https://iowageologicalsurvey.uiowa.edu/iowa-geology"), _src("Iowa Geological Survey: Fossils", "https://iowageologicalsurvey.uiowa.edu/iowa-geology/popular-interest/fossils")),
            _fact("The Middle Ordovician Winneshiek Shale preserves soft-bodied fossils and an early eurypterid from a distinct marine environment; Iowa also has widespread Pleistocene mammoth and mastodon remains.", _src("Iowa Geological Survey: Paleontology", "https://iowageologicalsurvey.uiowa.edu/research/paleontology"), _src("Iowa Geological Survey: Fossils", "https://iowageologicalsurvey.uiowa.edu/iowa-geology/popular-interest/fossils")),
        ],
    },
    "KS": {
        "title": "Kansas — Cretaceous marine reptiles and flying reptiles",
        "designation": "NPS-listed state fossil examples",
        "groups": ["marine reptiles", "pterosaurs", "marine invertebrates"],
        "periods": ["Cretaceous"],
        "facts": [
            _fact("NPS lists Cretaceous Pteranodon and Tylosaurus for Kansas: a flying pterosaur and a marine mosasaur.", _NPS),
            _fact("Western Kansas's Niobrara Chalk formed from calcareous marine sediment in the Cretaceous inland sea; the chalk consists largely of calcite from microscopic marine organisms.", _src("Kansas Geological Survey: Chalk", "https://geokansas.ku.edu/chalk")),
            _fact("Kansas chalk beds preserve mosasaurs, plesiosaurs, pterosaurs, toothed marine birds, large fish, clams, and other marine fossils.", _src("Kansas Geological Survey: Chalk", "https://geokansas.ku.edu/chalk")),
        ],
    },
    "KY": {
        "title": "Kentucky — marine invertebrates in Ordovician and Mississippian rocks",
        "designation": "NPS-listed state fossil examples",
        "groups": ["brachiopods", "marine invertebrates"],
        "periods": ["Ordovician", "Mississippian"],
        "facts": [
            _fact("NPS lists brachiopods as Kentucky's state fossil, with an Ordovician-to-Mississippian age range.", _NPS),
            _fact("Most Kentucky Ordovician through Mississippian rocks formed in shallow tropical seas; the Kentucky Geological Survey documents brachiopods, corals, trilobites, crinoids, fish, and shark remains.", _src("Kentucky Geological Survey: Fossils", "https://kgs.uky.edu/kgsweb/olops/pub/kgs/s_12/KGS12FT42005.pdf")),
            _fact("The central Bluegrass region is underlain by fossil-rich Ordovician limestone and shale; Permian, Triassic, and Jurassic strata are largely absent from the state's rock record.", _src("Kentucky Geological Survey: Ordovician strata", "https://www.uky.edu/KGS/geoky/ordovician.htm"), _src("Kentucky Geological Survey: Fossils", "https://kgs.uky.edu/kgsweb/olops/pub/kgs/s_12/KGS12FT42005.pdf")),
        ],
    },
    "LA": {
        "title": "Louisiana — Oligocene petrified palm and Gulf sediments",
        "designation": "NPS-listed state fossil",
        "groups": ["plants"],
        "periods": ["Eocene", "Oligocene"],
        "facts": [
            _fact("NPS lists Oligocene petrified palm wood as Louisiana's state fossil.", _NPS),
            _fact("The Middle Eocene Cane River Formation of the Claiborne Group is among Louisiana's best-known fossil-bearing units; a Geological Survey of Louisiana account identifies about 150 marine species there, including clams, oysters, corals, cephalopods, foraminifera, and fish.", _src("Louisiana Geological Survey: Fossils from the Cane River Site", "https://upload.lsu.edu/lgs/publications/products/Free_publications/CaneRiver-fossils.pdf")),
            _fact("Most Louisiana surface exposures are Tertiary or Quaternary river, delta, and swamp sediments; the state survey notes that marine fossil beds are less common at the surface, making the Cane River marine assemblage a notable contrast.", _src("Louisiana Geological Survey: Fossils from the Cane River Site", "https://upload.lsu.edu/lgs/publications/products/Free_publications/CaneRiver-fossils.pdf")),
        ],
    },
    "ME": {
        "title": "Maine — Devonian plant fossils and ancient forests",
        "designation": "NPS-listed state fossil",
        "groups": ["plants"],
        "periods": ["Devonian"],
        "facts": [
            _fact("Maine's Devonian state fossil Pertica quadrifaria came from the Trout Valley Formation and grew in a brackish marsh near an active volcano; plant fragments were buried in sediment before decay.", _src("Maine Geological Survey: Pertica quadrifaria", "https://www.maine.gov/dacf/mgs/explore/fossils/stfossil.htm")),
            _fact("Maine's Paleozoic bedrock record spans Cambrian through Devonian rocks and is dominated by marine invertebrates; the Trout Valley Formation is a rare terrestrial fossil setting.", _src("Maine Geological Survey: Fossils preserved in Maine bedrock", "https://www.maine.gov/dacf/mgs/explore/fossils/bedrock/fossil-bdrk.htm")),
            _fact("The NPS description of Katahdin Woods and Waters documents Paleozoic trilobites, sponges, corals, snails, bivalves, brachiopods, crinoids, and trace fossils in the region's ancient reef record.", _NPS_PARKS),
        ],
    },
    "MD": {
        "title": "Maryland — Miocene shells and Cretaceous dinosaurs",
        "designation": "NPS-listed state fossil and state dinosaur examples",
        "groups": ["marine mollusks", "dinosaurs"],
        "periods": ["Miocene", "Cretaceous"],
        "facts": [
            _fact("NPS lists the Miocene snail Ecphora gardnerae gardnerae and the Cretaceous dinosaur Astrodon johnstoni for Maryland. They represent very different settings and fossil groups.", _NPS),
            _fact("The Miocene Calvert Formation contains fossil-rich marine sand and clay; Maryland's Cretaceous Coastal Plain units preserve dinosaurs and other older fauna.", _src("Maryland Geological Survey: Generalized geologic map", "https://www.mgs.md.gov/geology/geologic_map/md_geologic_map.html"), _src("NPS: George Washington Birthplace paleontology", "https://www.nps.gov/gewa/learn/nature/paleontology.htm")),
            _fact("Maryland's Miocene deposits preserve whales, dolphins, porpoises, sea cows, sharks, fish, reptiles, and abundant mollusks; Ecphora is the state fossil shell from this marine setting.", _src("Maryland Geological Survey: Calvert Cliffs fossils", "https://www.mgs.md.gov/geology/fossils/calvert_cliffs_fs.html"), _src("Maryland Geological Survey: Miocene fossil teeth", "https://www.mgs.md.gov/geology/fossils/miocene_tooth_fossils.html")),
        ],
    },
    "MA": {
        "title": "Massachusetts — Jurassic tracks and rift-basin rocks",
        "designation": "NPS-listed state fossil example",
        "groups": ["trace fossils", "dinosaurs"],
        "periods": ["Jurassic"],
        "facts": [
            _fact("NPS lists dinosaur tracks as Massachusetts's state fossil example and identifies them as Jurassic trace fossils. A track records activity, not a dinosaur bone.", _NPS, _TRACE),
            _fact("Massachusetts and Connecticut Valley sandstone preserves Early Jurassic dinosaur tracks, including large Eubrontes and smaller Anchisauripus and Anomoepus prints.", _src("Connecticut Geological and Natural History Survey: Guidebook for Fieldtrips in Connecticut and Massachusetts", "https://portal.ct.gov/-/media/deep/geology/guidebooks/guidebookno9negsa2012pdf.pdf?hash=92166FCC53ABF31193EB14EB5B016409&rev=fa2c4bc0e0294bdb90816f28ffe9997d")),
            _fact("The Connecticut Valley trackways occur in Early Jurassic sandstone; Connecticut's official description notes a three-toed Eubrontes print and no known skeleton of its trackmaking animal.", _src("Connecticut DEEP: State Fossil", "https://portal.ct.gov/About/State-Symbols/The-State-Fossil")),
        ],
    },
    "MI": {
        "title": "Michigan — Devonian coral and Ice Age mastodons",
        "designation": "NPS-listed state fossil and state stone examples",
        "groups": ["corals", "mammals", "marine invertebrates"],
        "periods": ["Devonian", "Pliocene", "Pleistocene"],
        "facts": [
            _fact("NPS lists a Pleistocene mastodon as Michigan's fossil and Petoskey Stone as its Devonian fossiliferous state stone. One is a mammal; the other is colonial coral.", _NPS),
            _fact("Petoskey stones are Devonian colonial coral, Hexagonaria, from the Traverse Group; glacial ice later eroded and redeposited some coral-bearing rock fragments.", _src("Michigan EGLE: Michigan fossils", "https://www.michigan.gov/egle/public/learn/geology/rockhounding/fossils"), _src("Michigan EGLE: Petoskey stone", "https://www.michigan.gov/egle/public/learn/geology/rockhounding")),
            _fact("The Traverse Group formed on a shallow marine carbonate shelf and includes corals, trilobites, ostracods, bryozoans, crinoids, brachiopods, and mollusks; Hexagonaria is most abundant in the Gravel Point Formation.", _src("Michigan EGLE: Traverse Group and Petoskey stone", "https://www.michigan.gov/-/media/Project/Websites/egle/Documents/Programs/GRMD/Catalog/05/GIMDL-GSA87J.PDF?rev=15c99901f0f743e48830691b98f83527")),
        ],
    },
    "MN": {
        "title": "Minnesota — fossil seas, ancient stromatolites, and Ice Age mammals",
        "designation": "No Minnesota example listed on the NPS state-fossils page",
        "groups": ["stromatolites", "marine invertebrates", "ammonites", "sharks", "mammals", "plants"],
        "periods": ["Precambrian", "Cambrian", "Ordovician", "Devonian", "Cretaceous", "Pleistocene"],
        "facts": [
            _fact("The Minnesota Geological Survey identifies stromatolites in the Precambrian iron-rich rocks of the Mesabi Iron Range and mammoth, mastodon, bison, and giant beaver remains in Pleistocene glacial deposits.", _src("Minnesota Geological Survey: Fossils", "https://cse.umn.edu/mgs/fossils")),
            _fact("In southeastern Minnesota, Cambrian–Devonian sedimentary layers record ancient marine deposition; the survey describes shale, sandstone, limestone, and dolostone, with shelled organisms and local reefs.", _src("Minnesota Geological Survey: Paleozoic geology", "https://cse.umn.edu/mgs/paleozoic-geology")),
            _fact("Western Minnesota's Cretaceous deposits preserve ammonites from the Western Interior Seaway; Cretaceous bedrock also contains shark teeth, including Squalicorax, fish scales, fossil leaves, petrified wood, and pollen.", _src("Minnesota Geological Survey: Fossils", "https://cse.umn.edu/mgs/fossils")),
        ],
    },
    "MS": {
        "title": "Mississippi — Eocene whales and younger petrified wood",
        "designation": "NPS-listed state fossil examples",
        "groups": ["marine mammals", "plants"],
        "periods": ["Eocene", "Oligocene"],
        "facts": [
            _fact("NPS lists Eocene Basilosaurus and Zygorhiza whales and Oligocene petrified wood among Mississippi's state fossil examples.", _NPS),
            _fact("Late Eocene Mississippi was under deep marine water; state Geological Survey material describes archaeocete whales and a diverse marine fauna, with Basilosaurus among the largest whales.", _src("Mississippi Department of Environmental Quality: Fossil Friday", "https://www.mdeq.ms.gov/geology/fossil-friday/")),
            _fact("The same state survey describes fossil wood buried in reducing sediment as lignitized wood and later silica replacement as petrified wood; fossil plant leaves and pollen also help interpret Mississippi's sedimentary record.", _src("Mississippi Department of Environmental Quality: Fossil Friday", "https://www.mdeq.ms.gov/geology/fossil-friday/")),
        ],
    },
    "MO": {
        "title": "Missouri — Mississippian crinoids and a Cretaceous dinosaur",
        "designation": "Missouri-designated state fossil and dinosaur",
        "groups": ["crinoids", "dinosaurs", "marine invertebrates"],
        "periods": ["Mississippian", "Cretaceous"],
        "facts": [
            _fact("Missouri designates Delocrinus missouriensis, a crinoid from the Mississippian Burlington Limestone, as its state fossil; Parrosaurus missouriensis is the state dinosaur.", _src("Missouri Geological Survey: Crinoid, official state fossil", "https://dnr.mo.gov/document-search/crinoid-missouris-official-state-fossil-pub0660/pub0660"), _src("Missouri Secretary of State: State dinosaur", "https://www.sos.mo.gov/symbol/dinosaur")),
            _fact("Mississippian crinoids anchored to the seafloor with a stalk and holdfast; fossil stalk segments can weather from Burlington Limestone as small round disks with a central hole.", _src("Missouri Geological Survey: Crinoid, official state fossil", "https://dnr.mo.gov/document-search/crinoid-missouris-official-state-fossil-pub0660/pub0660")),
            _fact("Parrosaurus missouriensis is a Cretaceous hadrosaur known from rare skeletal material; Missouri's Secretary of State records the preferred genus name and the dinosaur's 2004 state designation.", _src("Missouri Secretary of State: State dinosaur", "https://www.sos.mo.gov/symbol/dinosaur")),
        ],
    },
    "MT": {
        "title": "Montana — Cretaceous dinosaurs and Western Interior Seaway fossils",
        "designation": "NPS-listed state fossil",
        "groups": ["dinosaurs", "marine invertebrates"],
        "periods": ["Cretaceous"],
        "facts": [
            _fact("NPS lists Maiasaura peeblesorum, a Cretaceous duck-billed dinosaur, as Montana's state fossil.", _NPS),
            _fact("Montana's Maiasaura is associated with the Upper Cretaceous Two Medicine Formation, where fossil eggs and nesting grounds provide evidence of colonial nesting.", _src("NPS: Egg Mountain and the Two Medicine Formation", "https://home.nps.gov/articles/mesozoic-egg-mountain-dawson-2014.htm"), _src("Montana Code: State fossil", "https://mca.legmt.gov/bills/mca/title_0010/chapter_0010/part_0050/section_0090/0010-0010-0050-0090.html")),
            _fact("The Cretaceous Bearpaw Shale preserves marine ammonites including Baculites, Hoploscaphites, and Placenticeras, as well as bivalves and a plesiosaur fossil record.", _src("NPS: Paleontological resources of Glacier National Park", "https://irma.nps.gov/DataStore/DownloadFile/444636")),
        ],
    },
    "NE": {
        "title": "Nebraska — Ice Age mammoths and younger fossil-rich basins",
        "designation": "NPS-listed state fossil examples",
        "groups": ["mammals", "trace fossils"],
        "periods": ["Pleistocene", "Miocene", "Oligocene"],
        "facts": [
            _fact("NPS lists Pleistocene mammoths as Nebraska's state fossil example.", _NPS),
            _fact("Oligocene–Miocene units in the Niobrara River valley preserve horses, rhinoceroses, oreodonts, and other land mammals.", _src("NPS: Geologic formations — Niobrara National Scenic River", "https://www.nps.gov/niob/learn/nature/geologicformations.htm")),
            _fact("At Agate Fossil Beds, Miocene bone beds preserve Menoceras, Daeodon, bear dogs, Moropus, and small camel Stenomylus; ancient beaver burrows form spiral structures nicknamed Devil's Corkscrews.", _NPS_PARKS),
        ],
    },
    "NV": {
        "title": "Nevada — Triassic ichthyosaurs and Pleistocene mammals",
        "designation": "NPS-listed state fossil",
        "groups": ["marine reptiles", "mammals"],
        "periods": ["Triassic", "Pleistocene"],
        "facts": [
            _fact("NPS lists Shonisaurus popularis, a Triassic ichthyosaur, as Nevada's state fossil.", _NPS),
            _fact("Late Pleistocene Tule Springs was a spring-fed wetland with marshes, streams, meadows, and pools; its fauna included mammoths, camels, horses, bison, sloths, and large predators.", _NPS_PARKS),
            _fact("Berlin-Ichthyosaur State Park preserves a dense concentration of large Triassic ichthyosaurs, including Shonisaurus remains from a warm marine setting.", _src("Nevada State Parks: Berlin-Ichthyosaur State Park", "https://parks.nv.gov/parks/berlin-ichthyosaur")),
        ],
    },
    "NH": {
        "title": "New Hampshire — rare fossils in metamorphosed Paleozoic rocks",
        "designation": "No New Hampshire example listed on the NPS state-fossils page",
        "groups": ["brachiopods", "bivalves", "gastropods", "trace fossils"],
        "periods": ["Silurian", "Devonian"],
        "facts": [
            _fact("The Lower Devonian Littleton Formation preserves brachiopods, including Rhipidomelloides musculosa and Euryspirifer, among fossils reported from the metamorphosed strata.", _src("USGS: Fossils of the Littleton Formation", "https://www.usgs.gov/publications/fossils-littleton-formation-lower-devonian-new-hampshire"), _src("USGS Professional Paper 334-B: Fossils of the Littleton Formation", "https://pubs.usgs.gov/pp/0334b/report.pdf")),
            _fact("USGS documents fossils in Silurian Fitch Formation and Early Devonian Littleton Formation rocks near Littleton, including brachiopods and other marine invertebrates.", _src("USGS: Fossils of the Littleton Formation", "https://www.usgs.gov/publications/fossils-littleton-formation-lower-devonian-new-hampshire"), _src("USGS: Littleton-area stratigraphy field guide", "https://pubs.usgs.gov/of/2014/1026/pdf/ofr2014-1026.pdf")),
            _fact("The Littleton fossils occur in metamorphosed sedimentary rocks, so original marine shells and outlines can be flattened or distorted by later heat and pressure.", _src("USGS: Fossils of the Littleton Formation", "https://www.usgs.gov/publications/fossils-littleton-formation-lower-devonian-new-hampshire")),
        ],
    },
    "NJ": {
        "title": "New Jersey — Cretaceous dinosaur and Coastal Plain sediments",
        "designation": "NPS-listed state fossil",
        "groups": ["dinosaurs", "marine invertebrates"],
        "periods": ["Cretaceous"],
        "facts": [
            _fact("NPS lists Hadrosaurus foulkii, a Cretaceous duck-billed dinosaur, as New Jersey's state fossil. This is one example in a state with both Coastal Plain sedimentary units and older rift-basin rocks.", _NPS, _src("New Jersey Geological Survey: Bedrock geologic map", "https://www.state.nj.us/dep/njgs/enviroed/freedwn/psnjmap.pdf")),
            _fact("The Cretaceous Coastal Plain also preserves marine fossils in units such as the Woodbury and Navesink formations, including mollusks, cephalopods, crustaceans, and vertebrate remains.", _src("New Jersey Geological Survey: Cretaceous fossils", "https://www.nj.gov/dep/njgs/enviroed/oldpubs/CretaceousPaleontology.pdf")),
            _fact("Hadrosaurus foulkii was described from a partial skeleton discovered in New Jersey in 1858; its remains occurred with marine shells, showing how a land animal can enter a coastal marine deposit.", _src("New Jersey Geological Survey: Hadrosaurus foulkii", "https://dep.nj.gov/njgws/educational/educational-publications-and-information/hadrosaurus-foulkii/")),
        ],
    },
    "NM": {
        "title": "New Mexico — Triassic Coelophysis and varied continental basins",
        "designation": "NPS-listed state fossil",
        "groups": ["dinosaurs"],
        "periods": ["Triassic"],
        "facts": [
            _fact("NPS lists Coelophysis bauri, a Triassic theropod dinosaur, as New Mexico's state fossil.", _NPS),
            _fact("White Sands preserves Late Pleistocene tracks of humans, camels, mammoths, and ground sloths along an ancient lake shoreline, where soft playa sediment recorded footprints.", _NPS_PARKS),
            _fact("Ghost Ranch preserves abundant Coelophysis skeletons in exposures of the Upper Triassic Chinle Formation, a named unit for the state's dinosaur fossil.", _src("NPS: Ghost Ranch National Natural Landmark", "https://www.nps.gov/media/photo/gallery-item.htm?gid=6C88AF9D-7FCE-4F4D-80AC-EC8F04F82889&id=e06a9df5-0d16-4d3b-8ee4-632407a9014e&pg=0")),
        ],
    },
    "NY": {
        "title": "New York — Silurian sea scorpions and Paleozoic marine beds",
        "designation": "NPS-listed state fossil",
        "groups": ["eurypterids", "marine invertebrates"],
        "periods": ["Silurian"],
        "facts": [
            _fact("NPS lists Eurypterus remipes, a Silurian eurypterid, as New York's state fossil.", _NPS),
            _fact("The New York State Museum says Eurypterus remipes was selected as the state fossil because these rare eurypterids occur in great numbers in Silurian rocks near Buffalo.", _src("New York State Museum: Eurypterid", "https://nysm.nysed.gov/exhibitions/windows/eurypterid")),
            _fact("Western New York's Silurian Bertie waterlimes preserve eurypterids and related arthropod fossils in a marine setting.", _src("New York State Museum: Silurian waterlimes research", "https://nysm.nysed.gov/sites/default/files/a_hemiaspidan_crustacean_from_the_new_york_silurian_waterlimes_a.pdf")),
        ],
    },
    "NC": {
        "title": "North Carolina — Cenozoic shark teeth across Coastal Plain deposits",
        "designation": "NPS-listed state fossil example",
        "groups": ["sharks", "marine invertebrates", "mammals", "plants"],
        "periods": ["Oligocene", "Miocene", "Pliocene", "Pleistocene"],
        "facts": [
            _fact("NPS lists fossil teeth of the Megalodon shark as North Carolina's state fossil example and gives a broad late Oligocene-to-early Pleistocene range. That interval spans multiple formations.", _NPS),
            _fact("The North Carolina Geological Survey links Megalodon fossils to nutrient-rich ancient coastal waters and phosphate-bearing sedimentary deposits in the Coastal Plain.", _src("North Carolina Geological Survey: Why geology matters", "https://www.deq.nc.gov/about/divisions/energy-mineral-and-land-resources/nc-geological-survey/geoscience-education/why-geology-matters")),
            _fact("Megalodon teeth from North Carolina can reach seven inches long; the state designated the fossilized teeth as its official fossil in 2013.", _src("North Carolina Geological Survey: Geology FAQs", "https://www.deq.nc.gov/about/divisions/energy-mineral-and-land-resources/nc-geological-survey/nc-geology-frequently-asked-questions")),
        ],
    },
    "ND": {
        "title": "North Dakota — Paleocene bored wood and Cretaceous seaway fossils",
        "designation": "NPS-listed state fossil",
        "groups": ["plants", "marine invertebrates", "marine reptiles"],
        "periods": ["Paleocene", "Cretaceous"],
        "facts": [
            _fact("NPS lists Teredo-bored petrified wood from the Paleocene for North Dakota. The boring pattern records a shipworm's activity in wood before the material was fossilized.", _NPS, _TRACE),
            _fact("North Dakota's Paleocene Cannonball Sea deposits preserve the state fossil: driftwood bored by shipworms before mineral replacement fossilized the wood.", _src("North Dakota Geological Survey: Prehistoric life", "https://www.library.nd.gov/statedocs/GeologicalSurvey2/MM-3720140212.pdf")),
            _fact("As the Cannonball Sea retreated, a western North Dakota delta supported dinosaurs, freshwater snails and clams, mammals, and plants preserved in the Hell Creek Formation; the Cannonball Formation holds marine sharks, fish, shells, and crustaceans.", _src("North Dakota Geological Survey: Prehistoric life", "https://www.library.nd.gov/statedocs/GeologicalSurvey2/MM-3720140212.pdf")),
        ],
    },
    "OH": {
        "title": "Ohio — Ordovician trilobites and Devonian armored fish",
        "designation": "NPS-listed state invertebrate fossil and fossil fish",
        "groups": ["trilobites", "armored fish", "marine invertebrates"],
        "periods": ["Ordovician", "Devonian"],
        "facts": [
            _fact("NPS lists the Ordovician trilobite Isotelus as Ohio's state invertebrate fossil and Dunkleosteus terrelli as its fossil fish. The two examples are from different periods and animal groups.", _NPS),
            _fact("The Ohio Geological Survey places Dunkleosteus terrelli in the Cleveland Shale Member of the Ohio Shale; fossils are mostly armored plates from the head and forward trunk.", _src("Ohio Geological Survey: Dunkleosteus terrelli", "https://dam.assets.ohio.gov/image/upload/ohiodnr.gov/documents/geology/GF35_Peter_2021.pdf")),
            _fact("Ohio's Ordovician Isotelus was a large seafloor trilobite in a warm shallow sea; it grew by molting its segmented exoskeleton, which helps explain why complete specimens are less common than fragments.", _src("Ohio Geological Survey: Hands-on Earth Science, Isotelus", "https://dam.assets.ohio.gov/image/upload/odnr/geological-survey/publications-maps/educational-publications/Hands-On-Earth-Science_full-series-2020.pdf")),
        ],
    },
    "OK": {
        "title": "Oklahoma — Jurassic theropod and Ordovician sea fossils",
        "designation": "NPS-listed state fossil example",
        "groups": ["dinosaurs", "brachiopods", "gastropods", "trilobites", "cephalopods", "sponges", "graptolites"],
        "periods": ["Jurassic", "Ordovician"],
        "facts": [
            _fact("NPS lists Saurophaganax maximus, a Jurassic theropod dinosaur, for Oklahoma.", _NPS),
            _fact("The Morrison Formation's Jurassic terrestrial deposits preserve Oklahoma's state theropod alongside dinosaurs and plants across the western interior basin.", _src("NPS: The Morrison Formation", "https://www.nps.gov/subjects/fossils/the-morrison-formation.htm")),
            _fact("Lower Ordovician Arbuckle Group carbonates in south-central Oklahoma contain brachiopods, gastropods, trilobites, cephalopods, sponges, and graptolites; brachiopods are especially abundant in Ordovician rocks.", _src("Oklahoma Geological Survey: Oklahoma's Brachiopods", "https://ogs.ou.edu/docs/educationalpublications/EP10.pdf"), _src("Oklahoma Geological Survey: Fossiliferous Arbuckle Group formations", "https://ogs.ou.edu/docs/geologynotes/GN-V21N8.pdf")),
        ],
    },
    "OR": {
        "title": "Oregon — Miocene forests and evolving Cenozoic mammals",
        "designation": "NPS-listed state fossil",
        "groups": ["plants", "mammals"],
        "periods": ["Miocene", "Oligocene", "Eocene"],
        "facts": [
            _fact("NPS lists Metasequoia, a Miocene conifer leaf, as Oregon's state fossil.", _NPS, _TYPES),
            _fact("John Day Fossil Beds National Monument preserves a long Cenozoic record in Clarno and John Day formations, with fossil plants and mammals across changing environments. The region's sedimentary rocks include volcanic ash-derived material.", _src("NPS: Geologic formations — John Day Fossil Beds", "https://www.nps.gov/joda/learn/nature/geologicformations.htm"), _src("NPS: Fossil type specimens in parks", "https://www.nps.gov/subjects/fossils/fossil-type-specimens-in-parks.htm")),
            _fact("The Clarno Nut Beds preserve a diverse Eocene fossil flora with more than 175 described fruit and seed species; the nearby Hancock Mammal Quarry includes the three-toed leaf-eating horse Haplohippus.", _NPS_PARKS),
        ],
    },
    "PA": {
        "title": "Pennsylvania — Devonian trilobites and Appalachian strata",
        "designation": "NPS-listed state fossil",
        "groups": ["trilobites", "marine invertebrates"],
        "periods": ["Devonian"],
        "facts": [
            _fact("NPS lists Phacops rana, a Devonian trilobite, as Pennsylvania's state fossil.", _NPS),
            _fact("Pennsylvania's Devonian rocks preserve Phacops rana and many other trilobites; fossil plates from the state survey illustrate Ordovician and Devonian groups as well as younger Pennsylvanian–Permian plants.", _src("Pennsylvania DCNR: Identifying fossils", "https://www.pa.gov/agencies/dcnr/education/geology-education/identifying-and-collecting")),
            _fact("Complete trilobites are uncommon because their rigid exoskeletons separated after death and they shed the outer skeleton during growth; Phacops is a Devonian-age fossil in the state record.", _src("Pennsylvania DCNR: Identifying fossils", "https://www.pa.gov/agencies/dcnr/education/geology-education/identifying-and-collecting")),
        ],
    },
    "PR": {
        "title": "Puerto Rico — Oligocene–Pliocene limestones and marine fossils",
        "designation": "No Puerto Rico example listed on the NPS state-fossils page",
        "groups": ["corals", "mollusks", "foraminifera", "marine invertebrates"],
        "periods": ["Cretaceous", "Oligocene", "Miocene", "Pliocene"],
        "facts": [
            _fact("USGS describes a north-coast belt of Oligocene-to-Pliocene limestone overlying volcaniclastic rocks in Puerto Rico. The map context is a coastal sedimentary sequence alongside volcanic units.", _src("USGS: Puerto Rico and U.S. Virgin Islands regional summary", "https://pubs.usgs.gov/ha/ha730/ch_n/N-PR_VItext1.html")),
            _fact("The USGS summary describes the Ponce Limestone as fossiliferous and mostly shallow-marine; the original USGS study records pelecypod and gastropod molds, coral heads, and large foraminifers.", _src("USGS: Puerto Rico regional summary", "https://pubs.usgs.gov/ha/ha730/ch_n/N-PR_VItext1.html"), _src("USGS Professional Paper 953: Middle Tertiary formations of Puerto Rico", "https://pubs.usgs.gov/pp/0953/report.pdf")),
            _fact("Puerto Rico's older island-arc core is Cretaceous volcanic and plutonic rock; younger late Oligocene–early Miocene limestones and clastic rocks flank it, with still younger limestone along parts of the coast.", _src("USGS: Geology and ground-water resources of Puerto Rico", "https://www.usgs.gov/publications/geology-and-ground-water-resources-puerto-rico")),
        ],
    },
    "RI": {
        "title": "Rhode Island — proposed trilobite and Pennsylvanian plant fossils",
        "designation": "NPS labels trilobite as a proposed state fossil",
        "groups": ["trilobites", "plants", "invertebrates"],
        "periods": ["Pennsylvanian"],
        "facts": [
            _fact("NPS labels a trilobite as Rhode Island's proposed state fossil; Rhode Island has not designated it as an official state fossil.", _NPS),
            _fact("Plant megafossils date the Narragansett Basin's sedimentary rocks to the Early through Late Pennsylvanian; the basin also contains layers of fossiliferous rock and anthracite-bearing strata.", _src("USGS Professional Paper 1110-A-L: Mississippian and Pennsylvanian systems in New England", "https://pubs.usgs.gov/pp/1110a-l/report.pdf")),
            _fact("The Narragansett Basin plant record includes fossil leaves such as Pecopteris feminaeformis in metasedimentary rocks; the fossils preserve evidence of coal-swamp vegetation later affected by metamorphism.", _src("USGS Open-File Report 78-683: Annotated bibliography of the coal flora of Massachusetts and Rhode Island", "https://pubs.usgs.gov/of/1978/0683/report.pdf"), _src("USGS Professional Paper 1110-A-L", "https://pubs.usgs.gov/pp/1110a-l/report.pdf")),
        ],
    },
    "SC": {
        "title": "South Carolina — Pleistocene mammoths and Coastal Plain deposits",
        "designation": "NPS-listed state fossil example",
        "groups": ["mammals", "marine invertebrates", "marine vertebrates", "plants"],
        "periods": ["Oligocene", "Pleistocene"],
        "facts": [
            _fact("NPS lists Columbian mammoth as South Carolina's state fossil example and places it in the Pleistocene.", _NPS),
            _fact("South Carolina's Geological Survey places most fossil localities in coastal and adjoining counties on the Atlantic Coastal Plain; many occur in coastal sedimentary deposits and limestone.", _src("South Carolina DNR: Geology FAQs", "https://www.dnr.sc.gov/admin/geofaqs.html")),
            _fact("Fossils from Charleston-area phosphate deposits include reworked Oligocene Cooper Marl fossils mixed with marine species of definite Pleistocene age in the Ladson Formation.", _src("South Carolina DNR: Oligocene fossils from the Old Bolton phosphate mine near Charleston", "https://www.dnr.sc.gov/geology/pdfs/Publications/SC_Geology/Vol_4/Vol.%204%20No.%203.pdf")),
        ],
    },
    "SD": {
        "title": "South Dakota — Cretaceous sea fossils and White River mammals",
        "designation": "NPS-listed state fossil",
        "groups": ["dinosaurs", "marine reptiles", "ammonites", "mammals"],
        "periods": ["Cretaceous", "Oligocene"],
        "facts": [
            _fact("NPS lists Triceratops, a Cretaceous horned dinosaur, as South Dakota's state fossil; the Pierre Shale exposed in Badlands National Park preserves marine fossils from the Western Interior Seaway.", _NPS, _src("NPS: Badlands geologic formations", "https://home.nps.gov/articles/000/badl-geologic-formations.htm")),
            _fact("The Pierre Shale record includes ammonites, baculites, and mosasaurs from the Western Interior Seaway; younger White River Group beds preserve land mammals.", _src("NPS: Badlands geologic formations", "https://home.nps.gov/articles/000/badl-geologic-formations.htm"), _src("NPS: Fossil mollusks", NPS_MOLLUSKS)),
            _fact("Within the White River sequence, Chadron Formation deposits record a warm, wet floodplain fauna that included brontotheres and alligators; younger Brule Formation sediments preserve a drier open-country mammal fauna such as oreodonts and nimravids.", _src("NPS: Badlands geologic formations", "https://home.nps.gov/articles/000/badl-geologic-formations.htm")),
        ],
    },
    "TN": {
        "title": "Tennessee — Cretaceous Coon Creek bivalves",
        "designation": "Tennessee-designated state fossil",
        "groups": ["bivalves", "marine invertebrates"],
        "periods": ["Cretaceous"],
        "facts": [
            _fact("Tennessee designates Pterotrigonia (Scabrotrigonia) thoracica as its state fossil; it is a Cretaceous bivalve from the Coon Creek Formation of West Tennessee.", _src("Tennessee Geological Survey: State symbols", "https://www.tn.gov/environment/program-areas/geology/geology-of-tn/state-symbols.html")),
            _fact("Pterotrigonia was a wedge-shaped shallow burrower that fed by filtering suspended food from the marine clayey-sand seafloor represented by Coon Creek deposits.", _src("Tennessee Geological Survey: State symbols", "https://www.tn.gov/environment/program-areas/geology/geology-of-tn/state-symbols.html")),
            _fact("Coon Creek shells of Pterotrigonia are preserved unaltered and abundant; the formation's marine fauna also included bivalves, snails, squid-like animals, worms, sponges, corals, crustaceans, sharks, fish, turtles, and marine reptiles.", _src("Tennessee Geological Survey: State symbols", "https://www.tn.gov/environment/program-areas/geology/geology-of-tn/state-symbols.html")),
        ],
    },
    "TX": {
        "title": "Texas — Cretaceous dinosaurs, palm wood, and marine fossils",
        "designation": "NPS-listed state fossil examples",
        "groups": ["dinosaurs", "plants", "ammonites", "mammals", "marine invertebrates"],
        "periods": ["Cretaceous", "Oligocene", "Pleistocene"],
        "facts": [
            _fact("NPS lists a Cretaceous sauropod, Pleurocoelus, and Oligocene petrified palm wood among Texas's state fossil examples. Their ages and fossil groups are different.", _NPS),
            _fact("Waco Mammoth National Monument preserves a Pleistocene nursery herd of Columbian mammoths; NPS interprets the deaths as likely resulting from a catastrophic flood.", _NPS_PARKS),
            _fact("Cretaceous clays, shales, and limestones in north Texas preserve ammonites and other marine fossils from an ancient ocean; Texas Parks and Wildlife identifies ammonites as predatory squid-like mollusks.", _src("Texas Parks and Wildlife: Eisenhower State Park interpretive guide", "https://tpwd.texas.gov/publications/pwdpubs/media/pwd_br_p4503_0032k.pdf")),
        ],
    },
    "UT": {
        "title": "Utah — Jurassic and Cretaceous dinosaurs in the Colorado Plateau record",
        "designation": "NPS-listed state fossil and state dinosaur examples",
        "groups": ["dinosaurs", "plants", "marine invertebrates", "tracks"],
        "periods": ["Jurassic", "Cretaceous", "Triassic", "Paleozoic"],
        "facts": [
            _fact("NPS lists Allosaurus as Utah's Jurassic state fossil and Utahraptor as its Early Cretaceous state dinosaur. The two emblems show separate dinosaur-age intervals.", _NPS),
            _fact("Dinosaur National Monument's NPS geology summary lists fossil-bearing formations from Cambrian through Cretaceous time and records marine invertebrates, fish, plants, vertebrates, and tracks alongside dinosaurs.", _src("NPS: Geodiversity Atlas — Dinosaur National Monument", "https://www.nps.gov/articles/nps-geodiversity-atlas-dinosaur-national-monument-colorado-and-utah.htm")),
            _fact("Zion's Triassic Moenkopi preserves marine invertebrates and reptile and synapsid tracks; its Chinle has petrified wood and phytosaurs, while Kayenta and Navajo units contain dinosaur trackways.", _NPS_PARKS),
        ],
    },
    "VT": {
        "title": "Vermont — Pleistocene beluga and ancient marine rocks",
        "designation": "NPS-listed state fossil",
        "groups": ["marine mammals"],
        "periods": ["Pleistocene"],
        "facts": [
            _fact("NPS lists Delphinapterus leucas, the Pleistocene beluga whale, as Vermont's state fossil.", _NPS),
            _fact("The Champlain Valley's marine brown clay contains the fossil beluga and shells of clams and mussels; the clay overlies glacial drift and older Silurian rock in places.", _src("Vermont Geological Survey: Fossil whale", "https://anrweb.vt.gov/PubDocs/DEC/GEO/ReportOnGeologyOfVT/Hitchcock1861V_1.pdf")),
            _fact("Vermont's state whale is Delphinapterus leucas, a Pleistocene beluga; the surrounding Champlain Sea deposits also preserve seals, fish, sponges, and marine shells.", _NPS, _src("Vermont Geological Survey: Fossil whale", "https://anrweb.vt.gov/PubDocs/DEC/GEO/ReportOnGeologyOfVT/Hitchcock1861V_1.pdf")),
        ],
    },
    "VA": {
        "title": "Virginia — Miocene–Pliocene scallop and Atlantic Coastal Plain fossils",
        "designation": "NPS-listed state fossil",
        "groups": ["bivalves", "marine invertebrates", "plants", "dinosaurs", "trace fossils"],
        "periods": ["Triassic", "Miocene", "Pliocene"],
        "facts": [
            _fact("NPS lists Chesapecten jeffersonius, a Miocene–Pliocene bivalve, as Virginia's state fossil. The shell is a marine record from the Coastal Plain.", _NPS),
            _fact("The USGS Geolex record describes Virginia's Yorktown Formation as fossiliferous marine sand and clay with abundant shell remains.", _src("USGS Geolex: Yorktown Formation publications", "https://ngmdb.usgs.gov/Geolex/UnitRefs/YorktownRefs_4487.html")),
            _fact("Virginia's Triassic basins preserve fragmentary plant remains and dinosaur tracks in sandstone and shale; body fossils of the trackmakers are not known from these cited deposits.", _src("Virginia Division of Mineral Resources: Geology of the Warrenton Quadrangle", "https://energy.virginia.gov/commercedocs/BUL_54.pdf")),
        ],
    },
    "WA": {
        "title": "Washington — Ice Age mammoths and Miocene wood",
        "designation": "NPS-listed state fossil examples",
        "groups": ["mammals", "plants"],
        "periods": ["Pleistocene", "Miocene"],
        "facts": [
            _fact("NPS lists Pleistocene Columbian mammoth and Miocene petrified wood among Washington's state fossil examples.", _NPS),
            _fact("Ginkgo Petrified Forest in central Washington lies beside Columbia River basalt flows and preserves a diverse Miocene fossil tree assemblage, including rare ginkgo wood.", _src("Washington State Parks: Ginkgo Petrified Forest history", "https://parks.wa.gov/about/news-center/field-guide-blog/ginkgo-petrified-forest-state-park-history")),
            _fact("Miocene lake-bed deposits interlayered with Columbia River basalt preserve Washington plant fossils, including the Grand Coulee flora's oak, tupelo, and Ptelea-like seeds.", _src("Washington Geological Survey: Washington Geology, vol. 29, nos. 1–2", "https://www.dnr.wa.gov/Publications/ger_washington_geology_2001_v29_no1-2.pdf")),
        ],
    },
    "WV": {
        "title": "West Virginia — Pleistocene ground sloth and older fossil coral",
        "designation": "NPS-listed state fossil and state gemstone examples",
        "groups": ["mammals", "corals"],
        "periods": ["Pleistocene", "Mississippian"],
        "facts": [
            _fact("NPS lists Megalonyx jeffersoni, a Pleistocene ground sloth, as West Virginia's state fossil; fossil coral is separately identified as the state gem and is Mississippian in age.", _NPS),
            _fact("The West Virginia Geological and Economic Survey describes the western two-thirds of the state as Appalachian Plateau sedimentary rocks, with Mississippian, Pennsylvanian, and Permian units exposed.", _src("West Virginia Geological and Economic Survey: FAQs", "https://www.wvgs.wvnet.edu/www/faq/faq.htm")),
            _fact("Megalonyx arm and hand bones found in a Monroe County cave in the 1790s were described by Thomas Jefferson in 1797; one bone was radiocarbon dated to about 35,960 years.", _src("West Virginia Geological and Economic Survey: FAQs", "https://www.wvgs.wvnet.edu/www/faq/faq.htm")),
        ],
    },
    "WI": {
        "title": "Wisconsin — Ordovician–Silurian trilobites and carbonate rocks",
        "designation": "NPS-listed state fossil",
        "groups": ["trilobites", "marine invertebrates", "corals"],
        "periods": ["Ordovician", "Silurian"],
        "facts": [
            _fact("NPS lists Calymene celebra, an Ordovician–Silurian trilobite, as Wisconsin's state fossil.", _NPS),
            _fact("Silurian trilobites in Wisconsin may be associated with reef-like habitats; the Racine Dolomite is a Silurian reef-bearing unit with abundant Niagaran fossils.", _src("Wisconsin Geological and Natural History Survey: Common Paleozoic fossils", "https://data.wgnhs.wisc.edu/pubshare/ES045.pdf"), _src("USGS Geolex: Racine Dolomite publications", "https://ngmdb.usgs.gov/Geolex/UnitRefs/RacineRefs_3469.html")),
            _fact("Trilobites are uncommon in Wisconsin: Ordovician rocks commonly yield fragments, while the Silurian record includes reef-associated forms such as the state fossil Calymene celebra.", _src("Wisconsin Geological and Natural History Survey: Common Paleozoic fossils", "https://data.wgnhs.wisc.edu/pubshare/ES045.pdf")),
        ],
    },
    "WY": {
        "title": "Wyoming — Eocene lake fish and Cretaceous dinosaurs",
        "designation": "NPS-listed state fossil and state dinosaur examples",
        "groups": ["fish", "dinosaurs", "mammals", "birds", "reptiles", "amphibians", "plants", "invertebrates"],
        "periods": ["Eocene", "Cretaceous"],
        "facts": [
            _fact("NPS lists Eocene fish genus Knightia and Cretaceous Triceratops among Wyoming's state fossil and dinosaur examples.", _NPS),
            _fact("In southwest Wyoming, the Eocene Fossil Butte Member of the Green River Formation accumulated in Fossil Lake and preserves fish, leaves, insects, birds, reptiles, bats, and mammals.", _src("NPS: Fossils at Fossil Butte", "https://home.nps.gov/fobu/learn/nature/fossils.htm"), _src("USGS Geolex: Fossil Butte Member", "https://ngmdb.usgs.gov/Geolex/UnitRefs/FossilButteRefs_8177.html")),
            _fact("NPS counts 27 fish species, 10 mammal species, 15 reptile species, and two amphibian species from the Fossil Butte Member, alongside plant and invertebrate fossils.", _src("NPS: Fossils at Fossil Butte", "https://home.nps.gov/fobu/learn/nature/fossils.htm")),
        ],
    },
}

def _validate_data():
    """Fail loudly if a shipped reading is incomplete or loses provenance."""
    if set(_DATA) != set(STATE_NAMES):
        raise RuntimeError("State fossil readings must cover all states, DC, and PR exactly once")
    for code, record in _DATA.items():
        for field in ("title", "designation"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise RuntimeError(f"{code} must have a non-empty {field}")
        for field in ("groups", "periods"):
            values = record.get(field)
            if (not isinstance(values, list) or not values
                    or not all(isinstance(value, str) and value.strip() for value in values)
                    or len(values) != len(set(values))):
                raise RuntimeError(f"{code} must have a non-empty, unique {field} list")
        facts = record.get("facts")
        if not isinstance(facts, list) or not 3 <= len(facts) <= 5:
            raise RuntimeError(f"{code} must have three to five authored facts")
        if not all(isinstance(fact.get("text"), str) and fact.get("text")
                   and fact.get("sources") for fact in facts):
            raise RuntimeError(f"{code} facts must have text and claim-level sources")
        if not all(isinstance(source.get("title"), str) and source["title"].strip()
                   and isinstance(source.get("url"), str) and source["url"].startswith("https://")
                   for fact in facts for source in fact["sources"]):
            raise RuntimeError(f"{code} has an incomplete or non-HTTPS citation")


_validate_data()


def state_reading(state: str) -> dict | None:
    """Return a detached, source-cited reading for a state or territory code.

    Returns ``None`` for unknown codes so callers cannot accidentally display
    a made-up state reading or imply fossil coverage where none was reviewed.
    """
    if not isinstance(state, str):
        return None
    code = state.strip().upper()
    record = _DATA.get(code)
    if record is None:
        return None
    return {
        "name": STATE_NAMES.get(code, code),
        "title": record["title"],
        "facts": deepcopy(record["facts"]),
        "fossil_groups": list(record["groups"]),
        "periods": list(record["periods"]),
        "reviewed": REVIEWED,
        "designation": record["designation"],
    }


def state_codes():
    """Return codes for all 50 states, the District of Columbia, and Puerto Rico."""
    return sorted(_DATA)
