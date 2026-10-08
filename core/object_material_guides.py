"""Sourced, observation-first reading guides for common archaeological objects.

The guides summarize manufacturing evidence and dated examples from NPS, SHA, BLM, and U.S. Mint educational or collection sources. They do not identify an individual object, establish site age, or turn an object into a location lead.
No network requests are made. Every factual bullet carries its own citations."""

from __future__ import annotations
from copy import deepcopy
import math

PAGE_SIZE = 8
MAX_QUERY_LENGTH = 120
ALL_CATEGORIES = "all"
CATEGORIES = (
    ("glass", "Glass"),
    ("ceramics", "Ceramics"),
    ("metals", "Metals"),
    ("coins", "Coins"),
    ("buttons", "Buttons"),
    ("hardware", "Hardware"),
    ("stone", "Stone"),
)

# Source IDs are stable within this corpus and are surfaced with the URL on
# each fact, so a reader can follow the particular evidence rather than a list
# of unrelated resources.
_SOURCE_CATALOG = {
    "NPS_YOSEMITE": {
        "name": "NPS Yosemite: Pocket Guide for Identifying Artifacts",
        "url": "https://www.nps.gov/yose/learn/historyculture/facelift-pocket-guide.htm",
    },
    "SHA_BOTTLE_HOME": {
        "name": "SHA/BLM Historic Glass Bottle Identification and Information Website",
        "url": "https://sha.org/bottle/",
    },
    "SHA_BOTTLE_BASES": {
        "name": "SHA Historic Bottle Website: Bottle Bases",
        "url": "https://secure-sha.org/bottle/bases.htm",
    },
    "SHA_BOTTLE_FINISHES": {
        "name": "SHA Historic Bottle Website: Finishes and Closures",
        "url": "https://secure-sha.org/bottle/finishstyles.htm",
    },
    "SHA_BOTTLE_BODY": {
        "name": "SHA Historic Bottle Website: Body and Mold Seams",
        "url": "https://www.secure-sha.org/bottle/body.htm",
    },
    "SHA_BOTTLE_COLORS": {
        "name": "SHA Historic Bottle Website: Bottle Colors",
        "url": "https://secure-sha.org/bottle/colors.htm",
    },
    "SHA_BOTTLE_DATING": {
        "name": "SHA: Summary Guide to Dating Bottles",
        "url": "https://sha.org/bottle/pdffiles/SummaryGuidetoDatingBottles.pdf",
    },
    "SHA_OWENS_MACHINE": {
        "name": "SHA: The Owens Bottle Co., Part 1 - History",
        "url": "https://sha.org/bottle/pdffiles/OwensBottleCoPart1.pdf",
    },
    "NPS_BOTTLE_MARK": {
        "name": "NPS Fort Stanwix: Imported Ink Bottle",
        "url": "https://www.nps.gov/articles/imported-ink-bottle.htm",
    },
    "NPS_JAMESTOWN_POTTERY": {
        "name": "NPS Historic Jamestowne: Pottery at Jamestown",
        "url": "https://www.nps.gov/jame/learn/historyculture/pottery-at-jamestown.htm",
    },
    "NPS_TRANSFERWARE": {
        "name": "NPS Fort Vancouver: Transfer Print Ceramics",
        "url": "https://www.nps.gov/articles/000/transferprintfova.htm",
    },
    "NPS_CERAMIC_ASSEMBLAGE": {
        "name": "NPS National Register report: ceramic assemblage chronology (site-specific)",
        "url": "https://npgallery.nps.gov/GetAsset/8d9ff6d6-15f9-4438-84be-024c05c73168",
    },
    "NPS_CORNELISON": {
        "name": "NPS National Register: Cornelison Pottery",
        "url": "https://npgallery.nps.gov/NRHP/GetAsset/NRHP/78001380_text",
    },
    "SHA_COARSE_CERAMICS": {
        "name": "Society for Historical Archaeology: Ceramics Identification is Clear as Mud",
        "url": "https://sha.org/archaeology/ceramics-identification-clear-mud/",
    },
    "NPS_CERAMIC_GLASS_CARE": {
        "name": "NPS/AIC: Caring for Ceramic and Glass Objects",
        "url": "https://pubs.nps.gov/eTIC/MANZ-MORA/MAWA_479_131930_0001_of_0040.pdf",
    },
    "NPS_BUTTONS": {
        "name": "NPS: 50 Nifty Finds #50, Buttoning It Up",
        "url": "https://www.nps.gov/articles/000/50-nifty-finds-50-buttoning-it-up.htm",
    },
    "NPS_BONE_BUTTONS": {
        "name": "NPS Fort Stanwix: Bone Buttons and Manufacturing Tool",
        "url": "https://home.nps.gov/articles/000/bone-buttons-manufacturing-tool.htm",
    },
    "NPS_DECORATIVE_ARTIFACTS": {
        "name": "NPS Fort Pulaski: Decorative Artifacts",
        "url": "https://www.nps.gov/fopu/learn/historyculture/decoration.htm",
    },
    "NPS_CAN_TRASH": {
        "name": "NPS Big Bend: What Trash Can Tell Us",
        "url": "https://home.nps.gov/bibe/learn/historyculture/trash2.htm",
    },
    "NPS_NAILS": {
        "name": "NPS: Watch Those Thumbs!",
        "url": "https://www.nps.gov/articles/watch-those-thumbs.htm",
    },
    "NPS_METAL_HANDBOOK": {
        "name": "NPS Museum Handbook: Curatorial Care of Metal Objects",
        "url": "https://home.nps.gov/subjects/museums/upload/MHI_AppO_MetalObjects.pdf",
    },
    "NPS_HARDWARE_CONTEXT": {
        "name": "NPS Wilson's Creek: Battlefield Archaeology (hardware examples and dating cautions)",
        "url": "https://www.nps.gov/parkhistory/online_books/wicr/battlefield_archeology.pdf",
    },
    "NPS_INSULATOR": {
        "name": "NPS Pipe Spring: Insulator",
        "url": "https://www.nps.gov/pisp/learn/historyculture/insulator.htm",
    },
    "NPS_GLASS_BEADS": {
        "name": "NPS Fort Vancouver: Bead Types",
        "url": "https://www.nps.gov/articles/fovabeads.htm",
    },
    "NPS_LITHICS": {
        "name": "NPS Saugus Iron Works: Types of Native American Artifacts",
        "url": "https://www.nps.gov/articles/000/native-american-artifacts.htm",
    },
    "NPS_POINT_CONTEXT": {
        "name": "NPS: Projectile Point, Why Archeologists Value Context",
        "url": "https://www.nps.gov/articles/projectile-point.htm",
    },
    "NPS_OBSIDIAN": {
        "name": "NPS Golden Gate: Archeological Finds",
        "url": "https://home.nps.gov/goga/learn/historyculture/archeological-finds-at-golden-gate-national-recreation-area.htm",
    },
    "NPS_DATING": {
        "name": "NPS: How Do Archeologists Know How Old a Site Is?",
        "url": "https://home.nps.gov/articles/000/how-do-archeologists-know-how-old-a-site-is.htm",
    },
    "NPS_FIELD_NOTES": {
        "name": "NPS: Archaeological Field Notes (artifact descriptions)",
        "url": "https://www.nps.gov/lewi/learn/historyculture/arch-archeological-field-notes-1957.htm",
    },
    "NPS_GLOSSARY": {
        "name": "NPS Archeology Glossary",
        "url": "https://home.nps.gov/subjects/archeology/glossary.htm",
    },
    "NPS_HAWAII_REPORT": {
        "name": "NPS archaeological report: ceramic and button form descriptions",
        "url": "https://www.nps.gov/havo/learn/historyculture/upload/Paliuli_Report_508.pdf",
    },
    "SMITHSONIAN_INDIAN_HEAD_CENT": {
        "name": "Smithsonian National Museum of American History: 1 Cent, United States, 1865",
        "url": "https://www.si.edu/object/1-cent-united-states-1865%3Anmah_1082325",
    },
    "USMINT_ANATOMY": {
        "name": "U.S. Mint: Anatomy of a Coin",
        "url": "https://www.usmint.gov/content/usmint/us/en/learn/collecting-basics/anatomy-of-a-coin.html",
    },
    "USMINT_MINTMARKS": {
        "name": "U.S. Mint: Mint Marks",
        "url": "https://www.usmint.gov/learn/collecting-basics/mint-marks",
    },
    "USMINT_PENNY": {
        "name": "U.S. Mint: Penny",
        "url": "https://www.usmint.gov/content/usmint/us/en/learn/coins-and-medals/circulating-coins/penny.html",
    },
    "USMINT_NICKEL": {
        "name": "U.S. Mint: Nickel",
        "url": "https://www.usmint.gov/learn/coins-and-medals/circulating-coins/nickel",
    },
    "USMINT_COIN_HISTORY": {
        "name": "U.S. Mint: History of U.S. Circulating Coins",
        "url": "https://dispatcher.usmint.gov/learn/history/us-circulating-coins",
    },
    "USMINT_TIMELINE": {
        "name": "U.S. Mint: Timeline of the Mint",
        "url": "https://www.usmint.gov/learn/history/timeline",
    },
}

def _guide(identifier, title, summary, category, facts, questions, record):
    """Build immutable-at-rest content; citation IDs are expanded on return."""
    return {
        "id": identifier,
        "title": title,
        "summary": summary,
        "category": category,
        "facts": tuple(
            {"text": fact[0], "source_ids": tuple(fact[1])}
            for fact in facts
        ),
        "questions": tuple(questions),
        "record": (record,) if isinstance(record,str) else tuple(record),
    }

_GUIDES = (
    _guide(
        "glass-bottle-pontil",
        "Pontil scars on bottle bases",
        "A base scar can preserve evidence of how a mouth-blown bottle was held while its neck was finished.",
        "glass",
        (
            ("A pontil rod was attached to a hot vessel so a glassworker could shape its neck; separation can leave a scar on the base.", ("SHA_BOTTLE_BASES",)),
            ("NPS describes a circular base scar without molded embossing as a possible sign of a mouth-blown bottle, often before about 1860; it is a clue, not a stand-alone date.", ("NPS_YOSEMITE",)),
            ("Machine-made bottles can have suction scars that resemble pontil marks, so check whether side seams continue through the finish before interpreting a base mark.", ("SHA_BOTTLE_BASES", "SHA_BOTTLE_DATING")),
        ),
        ("Is the base mark a rough or glassy scar, a mold seam, or an embossed mark?", "Do body seams stop below the lip, end within it, or continue to the rim?"),
        ("Photograph the full base and the scar close-up with a scale; note whether embossing and mold seams are present."),
    ),
    _guide(
        "glass-bottle-applied-finish",
        "Applied bottle finish",
        "An applied lip was added to a bottle neck after the body was blown.",
        "glass",
        (
            ("An applied finish was formed by adding a separate gather of glass at the mouth and shaping it with a tool; a junction or ridge may remain inside the finish.", ("SHA_BOTTLE_FINISHES", "SHA_BOTTLE_DATING")),
            ("NPS gives an approximate 1840–1885 range for many applied finishes, while the SHA dating guide stresses that adoption varied by bottle class.", ("NPS_YOSEMITE", "SHA_BOTTLE_DATING")),
            ("A seam that ends on the neck and an irregular lip can support a mouth-blown interpretation, but neither feature alone proves a date.", ("NPS_YOSEMITE", "SHA_BOTTLE_DATING")),
        ),
        ("Can you see a separate glass ring or ridge at the finish-to-neck junction?", "Where does the body mold seam terminate relative to the finish?"),
        ("Record finish profile, inner ridge, seam endpoint, lip damage, bottle color, and the side of the bottle photographed."),
    ),
    _guide(
        "glass-bottle-tooled-finish",
        "Tooled bottle finish",
        "A tooled finish was shaped from the bottle's own neck glass, rather than added as a separate ring.",
        "glass",
        (
            ("A tooled finish can show concentric horizontal tool marks and a body seam fading out on the neck or within the finish.", ("SHA_BOTTLE_DATING", "SHA_BOTTLE_FINISHES")),
            ("The inside of a tooled finish lacks the distinct applied-glass ridge at the finish-to-neck junction.", ("SHA_BOTTLE_DATING",)),
            ("SHA describes a broad U.S. shift toward tooled finishes in the later 19th century, with small drug bottles changing earlier than large bottles; bottle type matters.", ("SHA_BOTTLE_DATING",)),
        ),
        ("Are there concentric tool marks or only mold lines?", "Does the bore show a junction ridge where added glass would meet the neck?"),
        ("Photograph the lip from above and from the side; record the seam endpoint and any internal ridge without scraping the glass."),
    ),
    _guide(
        "glass-bottle-machine-seams",
        "Bottle mold seams and machine manufacture",
        "Seam paths reveal how a container was formed, but seam evidence should be read as a set.",
        "glass",
        (
            ("A thin vertical seam continuing over the finish rim is strong evidence of machine manufacture; mouth-blown seams usually end on the neck or within the finish.", ("NPS_YOSEMITE", "SHA_BOTTLE_DATING")),
            ("The SHA chronology recognizes machine-made bottles from the late 1880s onward; the Owens machine was patented in 1903, but serious commercial bottle production began about 1905 after earlier semi-automatic machinery.", ("SHA_BOTTLE_DATING", "SHA_OWENS_MACHINE")),
            ("Some machine-made bottles retain faint 'ghost' seams from an earlier forming stage, and a base suction scar can accompany machine manufacture.", ("SHA_BOTTLE_BODY", "SHA_BOTTLE_BASES")),
        ),
        ("Does the seam reach the top edge of the finish?", "Are there faint extra seams on the body or a suction mark on the base?"),
        ("Record each seam's start and end, finish type, base mark, bottle form, and whether the seam is clear or faint."),
    ),
    _guide(
        "glass-bottle-aqua",
        "Aqua bottle glass",
        "Aqua is a common blue-green tint in historic container glass.",
        "glass",
        (
            ("Iron in common glassmaking sand can produce a blue-green or aqua tint; color is therefore related to ingredients, not a unique bottle type.", ("SHA_BOTTLE_COLORS",)),
            ("NPS describes aqua bottle glass in a broad 1800–1920 range in its Yosemite teaching guide; that park-specific field guide offers an orientation, not a universal manufacturing interval.", ("NPS_YOSEMITE",)),
            ("Bottle color should be considered together with shape, seams, finish, base, embossing, and closure evidence.", ("SHA_BOTTLE_HOME", "NPS_YOSEMITE")),
        ),
        ("Is the tint uniform through thick and thin glass, or stronger at thicker edges?", "Is the fragment definitely container glass rather than window or table glass?"),
        ("Describe the observed color in daylight, fragment thickness, curvature, and the manufacturing features visible."),
    ),
    _guide(
        "glass-bottle-solarized-purple",
        "Solarized purple glass",
        "Some formerly colorless manganese-decolorized glass turns purple after ultraviolet exposure.",
        "glass",
        (
            ("Manganese used as a decolorizer can produce purple or amethyst solarization after exposure to ultraviolet light.", ("SHA_BOTTLE_COLORS", "NPS_YOSEMITE")),
            ("The common U.S. bottle interval is described differently across sources: NPS gives 1880–1917, while the SHA discussion notes research extending likely bottle use to about 1890–1920.", ("NPS_YOSEMITE", "SHA_BOTTLE_COLORS")),
            ("Purple color can be affected by the glass recipe and exposure history, so it does not by itself identify maker, contents, or an exact year.", ("SHA_BOTTLE_COLORS",)),
        ),
        ("Is the purple tint in the glass body rather than a surface coating or patina?", "Do seams, finish, or a maker's mark give a separate manufacturing clue?"),
        ("Note tint intensity and location, glass thickness, exposure-side differences if visible, seams, base, and marks."),
    ),
    _guide(
        "glass-bottle-maker-marks",
        "Bottle maker's marks",
        "Molded base and body marks can identify manufacturers, plants, dates, or mold numbers, but require comparison.",
        "glass",
        (
            ("Glassmaker marks commonly appear on bottle bases; customer or product embossing can also appear on the body, heel, or base.", ("SHA_BOTTLE_BASES", "SHA_BOTTLE_HOME")),
            ("A mark can narrow a manufacturing interval when read with other features, but identical-looking letters and symbols may have more than one interpretation.", ("SHA_BOTTLE_HOME", "SHA_BOTTLE_BASES")),
            ("NPS notes that a ceramic or bottle maker's mark can help researchers investigate where, when, and by whom an object was made.", ("NPS_BOTTLE_MARK",)),
        ),
        ("Which characters, punctuation, symbols, and numbers are actually legible?", "Is the mark raised, impressed, or printed, and where on the vessel is it?"),
        ("Take a straight-on, raking-light image; transcribe uncertain characters with brackets or question marks and preserve line breaks."),
    ),
    _guide(
        "glass-bottle-base",
        "Bottle base features",
        "The base can preserve mold, pontil, and feeding marks even when the rest of a bottle is missing.",
        "glass",
        (
            ("Bottle base features can be formed by the mold, a pontil rod, or automatic machinery; one base mark may overlap another.", ("SHA_BOTTLE_BASES",)),
            ("A post-bottom base has an inner circular seam joined by body seams, while cup-bottom bases commonly have a heel seam above the resting surface.", ("SHA_BOTTLE_BASES", "SHA_BOTTLE_HOME")),
            ("Base shape and push-up alone are not reliable date indicators; use the whole bottle's manufacturing details and bottle class.", ("SHA_BOTTLE_BASES", "SHA_BOTTLE_DATING")),
        ),
        ("Is there a center seam, heel seam, scar, stippling, or embossed mark?", "Do the side seams join a central base seam or a seam above the resting edge?"),
        ("Record base diameter and profile, resting point, push-up depth, seam layout, scars, embossing, and any numbers."),
    ),
    _guide(
        "glass-bottle-closures",
        "Bottle finishes and closures",
        "The lip and its closure were designed to work together; the lip can help identify the container's use class.",
        "glass",
        (
            ("Bottle closures seal the contents and are closely linked to the finish, so a finish is best recorded as a closure interface rather than just a rim shape.", ("SHA_BOTTLE_FINISHES",)),
            ("Crown finishes were developed for crown-cap closures in the late 19th century; bottle class and transition timing affect the useful date range.", ("SHA_BOTTLE_FINISHES", "SHA_BOTTLE_DATING")),
            ("Threaded finishes, crown finishes, cork finishes, and specialized mineral or patent-medicine finishes are different forms; a loose fragment may not preserve enough evidence to name the closure.", ("SHA_BOTTLE_FINISHES",)),
        ),
        ("Is the lip threaded, grooved for a crown cap, or shaped for a cork or other stopper?", "Does the mouth remain attached to enough neck or body to compare with reference examples?"),
        ("Record bore diameter, outer diameter, finish profile, thread or groove pattern, and any closure fragment found in the same documented context."),
    ),
    _guide(
        "glass-window-pane",
        "Window glass fragments",
        "Flat glass from a building can differ from curved container fragments in form and edge evidence.",
        "glass",
        (
            ("NPS field notes list clear windowpane fragments separately from curved bottle and vessel pieces, illustrating why flatness and curvature should be recorded.", ("NPS_FIELD_NOTES",)),
            ("A single thickness or color does not establish a window pane's date; a building context and other architectural evidence can be more useful.", ("NPS_DATING",)),
            ("The thickness, manufacturing surface, curvature, color, and edge finish are useful descriptive observations even when a fragment cannot be dated.", ("NPS_YOSEMITE", "SHA_BOTTLE_HOME")),
        ),
        ("Is the fragment flat or curved when viewed from the edge?", "Are there putty, paint, or frame-contact traces on an edge?"),
        ("Measure thickness at several undamaged points, describe color and surface texture, and photograph both faces and the edge."),
    ),
    _guide(
        "glass-telegraph-insulator",
        "Glass line insulators",
        "A glass insulator separated a conductive wire from a pole or other support.",
        "glass",
        (
            ("NPS explains that glass insulators isolated telegraph wire from wet wooden poles because glass is a poor electrical conductor.", ("NPS_INSULATOR",)),
            ("A wire groove or channel is a functional clue: wire wrapped around the insulator at the groove.", ("NPS_INSULATOR",)),
            ("Color or thickness alone is not an identification; shape, groove, threaded pin interface, and any embossed mark should be recorded together.", ("NPS_INSULATOR", "NPS_YOSEMITE")),
        ),
        ("Is there a wire groove and a threaded or pin-style attachment area?", "Are letters, numbers, or maker symbols molded into the glass?"),
        ("Record overall profile, groove count and position, base attachment, color, embossing, and whether the object is complete or fragmentary."),
    ),
    _guide(
        "glass-bead-manufacture",
        "Glass bead manufacture",
        "Hole shape, facets, and seams can preserve clues to how a bead was made.",
        "glass",
        (
            ("NPS describes drawn beads made by stretching a hollow glass tube, which is then cut into bead lengths.", ("NPS_GLASS_BEADS",)),
            ("Mandrel-pressed beads were made in a two-part mold; pins formed the perforation, which might retain a partly filled remnant that was punched through.", ("NPS_GLASS_BEADS",)),
            ("Facets can be produced by grinding flat surfaces after forming; NPS notes faceting on some mandrel-pressed examples.", ("NPS_GLASS_BEADS",)),
        ),
        ("Is the perforation round, seam-marked, or partly obstructed?", "Are the sides rounded, drawn, molded, or ground into facets?"),
        ("Record bead length and diameter, hole diameter, color layers, facets, seams, and whether the bead is translucent or opaque."),
    ),
    _guide(
        "ceramic-body-classes",
        "Ceramic body classes",
        "Body texture, porosity, and firing can distinguish broad ware families, but not identify a specific pottery by eye alone.",
        "ceramics",
        (
            ("Earthenware is generally more porous and fired at lower temperatures than stoneware; porcelain has a fine body and a vitrified, glass-like body.", ("NPS_CERAMIC_GLASS_CARE",)),
            ("Stoneware's fired body can be dense enough to hold liquid; surface glaze and body are separate attributes to record.", ("NPS_BOTTLE_MARK", "NPS_CERAMIC_GLASS_CARE")),
            ("Specialists recommend using a constellation of attributes such as firing cores and glaze patterns because coarse earthenwares and stonewares overlap in appearance.", ("SHA_COARSE_CERAMICS",)),
        ),
        ("Can the broken edge show a dense, fine, or visibly porous body?", "Does the glaze cover the body consistently or collect on some surfaces?"),
        ("Describe body color on fresh break and surface separately; note wall thickness, temper visible to the eye, glaze, and firing core."),
    ),
    _guide(
        "ceramic-coarse-earthenware",
        "Coarse earthenware",
        "Coarse earthenware varies widely in clay, temper, glaze, and local production practice.",
        "ceramics",
        (
            ("At Jamestown, NPS describes locally made coarse earthenware with red clay bodies; imported and locally made wares occurred together.", ("NPS_JAMESTOWN_POTTERY",)),
            ("A lighter slip can cover a darker clay body, and designs may expose the underlying clay by scratching through the slip before firing.", ("NPS_JAMESTOWN_POTTERY",)),
            ("Because coarse earthenwares are variable and can resemble stonewares, SHA ceramic specialists advise comparing multiple body and glaze attributes instead of relying on one visual feature.", ("SHA_COARSE_CERAMICS",)),
        ),
        ("Does the core differ in color from the slipped or glazed surfaces?", "Are inclusions visible on the broken edge?"),
        ("Photograph the exterior, interior, and fresh break; note slip, glaze, inclusions, firing core, thickness, and rim or base shape."),
    ),
    _guide(
        "ceramic-stoneware-salt-glaze",
        "Salt-glazed stoneware",
        "Salt glazing can leave a distinctive pebbled surface on fired stoneware.",
        "ceramics",
        (
            ("Salt introduced into a kiln vaporizes and deposits a glaze on vessels; NPS describes a characteristic orange-peel or pitted surface on a 19th-century pottery example.", ("NPS_CORNELISON",)),
            ("A Fort Stanwix NPS example identifies salt-glazed stoneware and explains that this vitrified ware could safely store liquids.", ("NPS_BOTTLE_MARK",)),
            ("Salt-glazed stoneware can be brown, gray, or other colors; appearance, maker's marks, and vessel form need to be read together.", ("NPS_BOTTLE_MARK", "NPS_CORNELISON")),
        ),
        ("Does the glaze have a pebbled or orange-peel texture?", "Is the body dense and the glaze different inside and outside?"),
        ("Record surface texture, body color at a break, glaze color and coverage, vessel form, and impressed or stamped marks."),
    ),
    _guide(
        "ceramic-stoneware-bottle",
        "Stoneware bottles and ink containers",
        "Ceramic bottles served as liquid containers where glass supply or cost made stoneware useful.",
        "ceramics",
        (
            ("NPS reports stoneware bottles for ink, medicine, mineral water, and beer in archaeological collections.", ("NPS_BOTTLE_MARK",)),
            ("Some stoneware containers carry impressed maker or pottery marks that can be researched for place and manufacturing period.", ("NPS_BOTTLE_MARK",)),
            ("The phrase 'warranted not to absorb' on one NPS example describes a vitreous bottle; that maker's wording belongs to that example, not every stoneware bottle.", ("NPS_BOTTLE_MARK",)),
        ),
        ("Does the fragment include a shoulder, neck, mouth, or base that distinguishes a bottle from a crock?", "Can any impressed lettering be read without cleaning or wetting?"),
        ("Record vessel profile, body and glaze, mouth or closure evidence, mark transcription, and the exact portion represented by the sherd."),
    ),
    _guide(
        "ceramic-transfer-print",
        "Transfer-printed earthenware",
        "Transfer printing applied a repeatable engraved design to a ceramic vessel.",
        "ceramics",
        (
            ("The process transfers a design from an engraved copper plate to ceramic, producing a detailed repeatable image.", ("NPS_TRANSFERWARE",)),
            ("NPS traces the invention to about 1750 in England and describes transfer printing as a dominant decoration method in Staffordshire during the 19th century.", ("NPS_TRANSFERWARE",)),
            ("Blue was common in the Fort Vancouver collection, but transfer prints also appeared in brown, red, pink, purple, green, black, and flow blue.", ("NPS_TRANSFERWARE",)),
        ),
        ("Does the design show fine repeated lines that appear printed rather than individually painted?", "Is the print under or over the glaze, and what color is it?"),
        ("Record print color, motif fragments, print location on the vessel, glaze, body, and any maker or pattern mark."),
    ),
    _guide(
        "ceramic-flow-blue",
        "Flow-blue transferware",
        "Flow blue is a transfer-printed decoration in which blue pigment appears blurred or diffused.",
        "ceramics",
        (
            ("NPS describes a Fort Vancouver plate in flow blue and distinguishes it from the site's medium-to-dark cobalt blue prints.", ("NPS_TRANSFERWARE",)),
            ("An NPS archaeological report describes flow-blue pearlwares as particularly popular in a mid-19th-century interval for the report's studied assemblage, not as a universal date for every sherd.", ("NPS_CERAMIC_ASSEMBLAGE",)),
            ("Pattern, vessel form, body type, and maker's mark help refine an identification beyond the blue color alone.", ("NPS_TRANSFERWARE", "NPS_CERAMIC_ASSEMBLAGE")),
        ),
        ("Are printed outlines sharp or visibly blurred into a blue halo?", "Does the fragment retain a pattern repeat or edge that can be compared?"),
        ("Record print color and diffusion, pattern fragment, body class, glaze, and rim or foot profile."),
    ),
    _guide(
        "ceramic-tin-glazed-earthenware",
        "Tin-glazed earthenware",
        "A white tin glaze can create a bright ground for painted decoration.",
        "ceramics",
        (
            ("NPS describes Jamestown delftware as a buff clay body covered by a white tin glaze.", ("NPS_JAMESTOWN_POTTERY",)),
            ("Painted colors on the NPS example include blue, orange, green, yellow, and purple; a white ground alone is not sufficient to name the ware.", ("NPS_JAMESTOWN_POTTERY",)),
            ("The term delftware has a complex production history across England and continental Europe, so origin should not be inferred from the name alone.", ("NPS_JAMESTOWN_POTTERY",)),
        ),
        ("Is there a buff or pale body beneath an opaque white glaze?", "Is painted decoration applied on the white surface?"),
        ("Note body color, glaze opacity and loss, paint colors, vessel form, and any evidence of a maker's mark."),
    ),
    _guide(
        "ceramic-slip-sgraffito",
        "Slip and sgraffito decoration",
        "Scratched designs can reveal a contrast between a slip layer and the underlying clay body.",
        "ceramics",
        (
            ("A slip is a clay coating; at Jamestown, a lighter slip was placed over a red clay body before decoration.", ("NPS_JAMESTOWN_POTTERY",)),
            ("In sgraffito, the potter scratches through the slip to expose the body beneath, creating a two-color design.", ("NPS_JAMESTOWN_POTTERY",)),
            ("NPS documents floral and geometric sgraffito patterns at Jamestown; the pattern and ware must be interpreted in the relevant regional and chronological context.", ("NPS_JAMESTOWN_POTTERY",)),
        ),
        ("Does a line cut through a lighter surface layer to expose a darker body?", "Are the marks incised, scratched through slip, or molded into the vessel?"),
        ("Photograph decoration under even and raking light; describe layer colors, line depth, pattern, and sherd orientation."),
    ),
    _guide(
        "ceramic-creamware-pearlware",
        "Creamware and pearlware",
        "Creamware and pearlware are refined earthenwares that can help date assemblages when the ware identification is secure.",
        "ceramics",
        (
            ("An NPS National Register report identifies creamware as the forerunner of pearlware and gives mean production dates of 1790 and 1810 respectively for one site's assemblage analysis.", ("NPS_CERAMIC_ASSEMBLAGE",)),
            ("Those are assemblage mean dates from a particular study, not universal start and end dates for an individual fragment.", ("NPS_CERAMIC_ASSEMBLAGE", "NPS_DATING")),
            ("Decoration and glaze tone can vary; compare body, glaze, decoration, vessel form, and marks rather than assigning a ware from color alone.", ("NPS_CERAMIC_ASSEMBLAGE", "SHA_COARSE_CERAMICS")),
        ),
        ("Does the fragment's body and glaze fit a refined earthenware rather than a coarse local ware?", "Is the date estimate based on a securely identified ware or only a color impression?"),
        ("Record body, glaze, decoration, rim or foot form, maker's mark, and whether the identification is tentative."),
    ),
    _guide(
        "ceramic-porcelain",
        "Porcelain fragments",
        "A fine, vitrified body can suggest porcelain, but porcelain sherds may span many periods and sources.",
        "ceramics",
        (
            ("NPS conservation guidance describes porcelain as a very fine-bodied ceramic fired to a vitrified, glass-like body.", ("NPS_CERAMIC_GLASS_CARE",)),
            ("An NPS archaeological report found porcelain sherds difficult to date by body alone; its assemblage included examples considered possibly 18th century or earlier and a marked 20th-century cup.", ("NPS_CERAMIC_ASSEMBLAGE",)),
            ("Paint, glaze, foot ring, body translucency, and maker's marks can provide evidence beyond the broad ware label.", ("NPS_CERAMIC_ASSEMBLAGE", "NPS_YOSEMITE")),
        ),
        ("Is the body fine and vitrified on a break, or merely white on the surface?", "Does the sherd include a foot ring, painted decoration, or a readable mark?"),
        ("Record body texture, translucency if naturally visible, decoration, glaze, foot or rim profile, and exact mark wording."),
    ),
    _guide(
        "ceramic-ironstone",
        "Ironstone and vitrified whitewares",
        "Ironstone is a refined, vitrified ceramic ware often recognized by pale body and molded or decorated surfaces.",
        "ceramics",
        (
            ("NPS describes British vitreous or vitrified ironstone with molded relief patterns as a comparatively inexpensive ware marketed in California during 1850–1890.", ("NPS_YOSEMITE",)),
            ("NPS archaeological field notes record ironstone sherds with transcribed pottery marks, showing how maker marks can supplement a broad ware identification.", ("NPS_FIELD_NOTES",)),
            ("A white body is not enough to identify ironstone: porcelain and other refined earthenwares can also be white.", ("NPS_CERAMIC_GLASS_CARE", "NPS_YOSEMITE")),
        ),
        ("Is relief molded into the body, or is the pattern painted or printed?", "Does the body appear dense and vitrified on a naturally broken edge?"),
        ("Record relief, body texture, glaze, pattern, rim profile, and every fragment of a maker's mark."),
    ),
    _guide(
        "ceramic-maker-marks",
        "Ceramic maker's marks",
        "Marks on a base can identify a pottery, brand, country, or pattern, but the mark's exact use history must be checked.",
        "ceramics",
        (
            ("NPS identifies maker's marks as a way to investigate where, when, and by whom a vessel was made.", ("NPS_BOTTLE_MARK",)),
            ("Marks may be impressed, printed, painted, or stamped; record the technique and exact visible wording before trying an attribution.", ("NPS_BOTTLE_MARK", "NPS_YOSEMITE")),
            ("Marks can be reused, copied, or partially obscured; they should be read alongside the body, decoration, form, and archaeological context.", ("NPS_BOTTLE_MARK", "NPS_DATING")),
        ),
        ("Is the mark on the base, foot, or body, and is it impressed, printed, or painted?", "Which letters are certain and which are only possible?"),
        ("Photograph the full base and mark close-up; transcribe uncertain text explicitly and preserve symbols and layout."),
    ),
    _guide(
        "ceramic-sherd-form",
        "Reading a ceramic sherd's vessel form",
        "A fragment's position on a vessel determines which form and use clues it can preserve.",
        "ceramics",
        (
            ("Rim, base, handle, and body fragments preserve different parts of a vessel profile; NPS ceramic collections document these parts separately.", ("NPS_CERAMIC_ASSEMBLAGE", "NPS_JAMESTOWN_POTTERY")),
            ("Transfer-printed ceramics occurred in tableware, teaware, and toiletry forms, so a printed fragment does not necessarily come from a plate or cup.", ("NPS_TRANSFERWARE",)),
            ("NPS defines a sherd as a ceramic fragment; describing the portion represented is safer than assigning a whole vessel from a small piece.", ("NPS_GLOSSARY",)),
        ),
        ("Does the fragment retain a rim, foot, handle attachment, base, or only body wall?", "Can curvature and wall thickness distinguish a flat plate from a rounded vessel?"),
        ("Record fragment dimensions, curvature, wall thickness, rim/foot/handle features, interior versus exterior, and whether edges are fresh or worn."),
    ),
    _guide(
        "metals-surface-colors",
        "Metal appearance and surface color",
        "Metal color and corrosion are observations, not reliable chemical identifications by themselves.",
        "metals",
        (
            ("NPS metal-care guidance lists iron and iron alloys with gray, silver, blue-black, or red-brown appearances; the visible surface may be corrosion rather than original metal.", ("NPS_METAL_HANDBOOK",)),
            ("Copper and copper alloys can appear yellow, brown, red, black, blue, or green as surfaces patinate.", ("NPS_METAL_HANDBOOK",)),
            ("NPS advises against chemical spot tests and spark tests for identifying metal because they can damage or destroy an object.", ("NPS_METAL_HANDBOOK",)),
        ),
        ("Which colors are visible, and do they occur on the whole surface or in patches?", "Are deposits powdery, flaky, or stable-looking without touching them?"),
        ("Describe color, luster, corrosion texture, and visible layers; avoid scraping, polishing, magnets, acids, or spark tests."),
    ),
    _guide(
        "metals-iron-steel",
        "Iron, wrought iron, and steel",
        "Iron-bearing objects can share colors and corrosion even when their production and uses differ.",
        "metals",
        (
            ("NPS museum guidance lists wrought iron in railings, nails, and wagon hardware; cast iron in kettles and stoves; and steel in knives, tools, and structural materials.", ("NPS_METAL_HANDBOOK",)),
            ("Some, but not all, iron alloys are magnetic, so a magnet response cannot establish a specific alloy.", ("NPS_METAL_HANDBOOK",)),
            ("Rust or red-brown surface color is evidence of corrosion, not an object date or a complete identification.", ("NPS_METAL_HANDBOOK",)),
        ),
        ("Is the object a thin plate, forged rod, cast mass, or fastener?", "Are seams, tool marks, threaded sections, or a working edge visible?"),
        ("Record dimensions, cross-section, shape, surviving edge or hole pattern, corrosion, and any stamp without cleaning the surface."),
    ),
    _guide(
        "metals-copper-alloys",
        "Copper alloys and patina",
        "Brass, bronze, and copper can develop varied surface colors over time.",
        "metals",
        (
            ("NPS museum guidance describes copper and copper-alloy objects as yellow to brown, with patinas ranging through red, brown, black, blue, and green.", ("NPS_METAL_HANDBOOK",)),
            ("Brass is a copper-zinc alloy and bronze is a copper-tin alloy; appearance alone does not separate these compositions.", ("NPS_METAL_HANDBOOK",)),
            ("NPS identifies brass among historical lighting, jewelry, scientific, marine, and cookware objects, illustrating that material alone does not establish function.", ("NPS_METAL_HANDBOOK",)),
        ),
        ("Is the visible surface metallic, patinated, plated, or a mixture?", "Does the shape retain a functional clue such as a hinge, loop, socket, or fastener?"),
        ("Describe base color and corrosion colors separately; record shape, thickness, seams, attachment points, and stamped marks."),
    ),
    _guide(
        "metals-cast-objects",
        "Cast metal fragments",
        "Casting can leave seams and thick sections, but corrosion and breakage can obscure them.",
        "metals",
        (
            ("NPS lists cast iron among materials used for kettles, door hardware, firebacks, and stoves.", ("NPS_METAL_HANDBOOK",)),
            ("A cast fragment can be difficult to identify if only a generic curved or flat section survives; catalog examples include cooking-pot and Dutch-oven fragments.", ("NPS_HARDWARE_CONTEXT",)),
            ("Function should be based on preserved features such as a rim, leg, handle attachment, hinge, or repeated shape rather than on metal color alone.", ("NPS_HARDWARE_CONTEXT", "NPS_METAL_HANDBOOK")),
        ),
        ("Is there a casting seam, repeated molded surface, rim, foot, or attachment point?", "Can the fragment be oriented as part of a vessel, tool, stove, or fitting?"),
        ("Record thickness at edges and center, surface texture, curvature, attachment scars, seams, and scale photographs."),
    ),
    _guide(
        "metals-hand-soldered-cans",
        "Hand-soldered can seams",
        "Thick, uneven solder joints can be manufacturing evidence on early tin cans.",
        "metals",
        (
            ("NPS describes late-1880s cans as hand-made, with seams soldered by hand and a thick, uneven solder joint.", ("NPS_CAN_TRASH",)),
            ("NPS's Yosemite guide says lead-soldered side seams probably predate the 1890s, while crimped or double-locked unsoldered seams reflect machine manufacture after the 1890s.", ("NPS_YOSEMITE",)),
            ("The date ranges are broad and overlapping guides; a can fragment's seam must be considered with the end construction and opening.", ("NPS_YOSEMITE", "NPS_CAN_TRASH")),
        ),
        ("Is the seam a thick solder bead, a folded lock seam, or an indistinct corroded edge?", "Does the can retain one end, both ends, or only the body panel?"),
        ("Photograph the seam from both sides; record solder thickness, fold direction, panel shape, end construction, and corrosion."),
    ),
    _guide(
        "metals-can-openings",
        "Can lids and opening features",
        "The can's opening method often offers a stronger chronological clue than metal color.",
        "metals",
        (
            ("NPS documents hole-in-cap cans with a soldered vent hole and cap, and one-piece machine-made can lids after 1904.", ("NPS_YOSEMITE",)),
            ("Church-key opened beer and soda cans are broadly dated by NPS to the 1930s–1960s; pull tabs appeared in 1962.", ("NPS_YOSEMITE",)),
            ("NPS reports aluminum beverage cans in the 1950s and modern pop-top cans in the 1980s.", ("NPS_YOSEMITE",)),
        ),
        ("Is the opening a punched hole, a church-key opening, a pull tab, or a stay-on tab?", "Is there an end fragment that shows the original closure?"),
        ("Record opening shape, tab presence, end seams, label remnants, and any embossing or printed brand text."),
    ),
    _guide(
        "metals-beverage-can-forms",
        "Beverage can forms",
        "Cone-top and flat-top cans reflect changes in beverage packaging.",
        "metals",
        (
            ("NPS Big Bend describes the first successful canned soda in 1953 as sold in cone-top cans.", ("NPS_CAN_TRASH",)),
            ("The same NPS account reports that most soft-drink companies shifted from cone tops to flat tops by the end of 1954.", ("NPS_CAN_TRASH",)),
            ("All-aluminum soft-drink cans first appeared in the early 1970s in the NPS account; can alloy is not safely established by color alone.", ("NPS_CAN_TRASH", "NPS_METAL_HANDBOOK")),
        ),
        ("Does the surviving sidewall profile taper to a cone top or meet a flat end?", "Are any seams, labels, or maker codes readable?"),
        ("Record end profile, can diameter and height if complete, seam style, printed wording, and whether the fragment is body or end."),
    ),
    _guide(
        "coin-anatomy",
        "Coin anatomy",
        "A consistent coin description starts with faces, inscriptions, rim, relief, field, and edge.",
        "coins",
        (
            ("The U.S. Mint calls the heads side the obverse and the tails side the reverse.", ("USMINT_ANATOMY",)),
            ("The Mint distinguishes the raised rim, inscription, relief, flat field, and edge; edges may be plain, reeded, lettered, or decorated.", ("USMINT_ANATOMY",)),
            ("A date, mint mark, and denomination are separate observations and should each be recorded when visible.", ("USMINT_ANATOMY", "USMINT_MINTMARKS")),
        ),
        ("Which side shows the date and which side shows the denomination?", "Is the edge plain, reeded, lettered, or otherwise decorated?"),
        ("Photograph obverse, reverse, and edge; record date, legend, denomination, mint mark, diameter, and visible wear."),
    ),
    _guide(
        "coin-mint-marks",
        "Reading a U.S. coin mint mark",
        "A mint mark identifies a production facility, but its position and presence changed over time.",
        "coins",
        (
            ("The U.S. Mint defines mint marks as letters that identify where a coin was made.", ("USMINT_MINTMARKS",)),
            ("Mint marks first appeared on U.S. coins when branch mints opened in 1838; Philadelphia often remained unmarked.", ("USMINT_MINTMARKS",)),
            ("No mint marks appeared on circulating coins from 1965 through 1967; when marks returned in 1968 they were placed on obverses.", ("USMINT_MINTMARKS",)),
        ),
        ("Is a small P, D, S, W, O, CC, C, or other letter present?", "Does its position match the denomination and period being considered?"),
        ("Record the mark exactly and note its position relative to the date, portrait, or reverse design."),
    ),
    _guide(
        "coin-cent-sequence",
        "U.S. one-cent design sequence",
        "Cent designs and metal changed over time and can provide broad manufacturing clues.",
        "coins",
        (
            ("U.S. Mint design intervals include Flying Eagle cents in 1857–1858, Indian Head cents in 1859–1909, and Lincoln cents beginning in 1909.", ("USMINT_PENNY",)),
            ("The first small cents in 1857 used an 88% copper and 12% nickel alloy; earlier cents were larger and copper.", ("USMINT_PENNY",)),
            ("A penny's visible copper color does not imply a solid-copper body: modern cents have a copper surface over a zinc core.", ("USMINT_PENNY", "USMINT_ANATOMY")),
        ),
        ("Which portrait and reverse design are present?", "Does the date, diameter, edge, and apparent metal agree with that design period?"),
        ("Record design, date, mint mark, diameter, edge, and whether a core is visible at an existing damaged edge."),
    ),
    _guide(
        "coin-indian-head-cent",
        "Indian Head cent",
        "The familiar 'Indian Head' cent design depicts Liberty wearing a headdress.",
        "coins",
        (
            ("The U.S. Mint dates the Indian Head cent design to 1859–1909.", ("USMINT_PENNY",)),
            ("The Smithsonian identifies the portrait as the goddess Liberty in a Plains-style feathered warbonnet, despite the common 'Indian Head' name.", ("SMITHSONIAN_INDIAN_HEAD_CENT",)),
            ("Early Indian Head cents were copper-nickel; design name, date, and composition should be recorded separately.", ("USMINT_PENNY",)),
        ),
        ("Can the date or part of the headdress, shield, or reverse wreath still be seen?", "Is the coin complete enough to distinguish this design from an earlier Flying Eagle cent?"),
        ("Photograph both faces and edge; transcribe partial dates with uncertain digits marked rather than guessed."),
    ),
    _guide(
        "coin-lincoln-cent",
        "Lincoln cent reverses",
        "The reverse design narrows the Lincoln cent's production period.",
        "coins",
        (
            ("The Lincoln cent began in 1909; wheat ears occupied the reverse from 1909 through 1958.", ("USMINT_PENNY",)),
            ("The Lincoln Memorial reverse was used from 1959 through 2008, followed by four special reverse designs in 2009.", ("USMINT_PENNY",)),
            ("Dates establish when the Mint struck a coin, not when it entered a particular deposit or was lost.", ("USMINT_PENNY", "NPS_DATING")),
        ),
        ("Does the reverse show wheat ears, the Lincoln Memorial, a 2009 scene, or the Union Shield?", "Can you read all four date digits and any mint mark?"),
        ("Record reverse type, date, mint mark, composition clues, and whether the date is legible or estimated."),
    ),
    _guide(
        "coin-1943-steel-cent",
        "1943 steel cent",
        "A 1943 U.S. cent may be zinc-coated steel rather than copper.",
        "coins",
        (
            ("The Mint says cents in 1943 were made of zinc-coated steel because copper was needed during World War II.", ("USMINT_PENNY", "USMINT_TIMELINE")),
            ("The Mint notes a limited number of copper cents were struck in error early in 1943; a copper-colored surface alone does not verify a rare variety.", ("USMINT_PENNY",)),
            ("Corrosion or plating loss can change a coin's appearance, so record observable color and date without treating color as a composition test.", ("USMINT_PENNY", "NPS_METAL_HANDBOOK")),
        ),
        ("Is the date clearly 1943, and is any zinc coating or steel-colored edge visible?", "Has corrosion or coating loss altered the original surface?"),
        ("Record date, mint mark, weight if measured with permission, edge appearance, and condition; do not scratch or chemically test it."),
    ),
    _guide(
        "coin-nickel-sequence",
        "U.S. five-cent coin sequence",
        "The five-cent denomination includes silver half dimes, Liberty designs, Buffalo nickels, and Jefferson nickels.",
        "coins",
        (
            ("The Mint's first five-cent coins were small silver half dimes; copper-nickel five-cent coins followed in 1866.", ("USMINT_NICKEL",)),
            ("The Buffalo nickel ran from 1913 to 1938; Jefferson appeared in 1938 and Monticello remained on the reverse through 2003.", ("USMINT_NICKEL",)),
            ("During World War II, nickel was removed from the five-cent coin alloy and Philadelphia's P mark appeared above Monticello on those coins.", ("USMINT_NICKEL", "USMINT_MINTMARKS")),
        ),
        ("Does the reverse show a bison, Monticello, or an earlier eagle or wreath?", "Is a wartime P mark present above Monticello?"),
        ("Record date, reverse design, mint mark and location, edge, and any visible composition change."),
    ),
    _guide(
        "coin-silver-to-clad",
        "Silver-to-clad coin transition",
        "The 1965 Coinage Act changed circulating dime, quarter, and half-dollar materials.",
        "coins",
        (
            ("The Mint dates the removal of silver from circulating dimes and quarters to the Coinage Act of 1965.", ("USMINT_TIMELINE", "USMINT_COIN_HISTORY")),
            ("Clad coins have a metal core surrounded by a different outer layer; a copper-colored stripe may show on an existing edge view.", ("USMINT_ANATOMY",)),
            ("Earlier silver coins continued to circulate alongside clad coins, so a coin's use date may be later than its manufacture date.", ("USMINT_COIN_HISTORY", "NPS_DATING")),
        ),
        ("Does an existing edge show a single metal or a layered outer metal and copper core?", "What denomination, date, and mint mark are present?"),
        ("Record denomination, date, edge layering visible without altering the coin, and whether the design is silver-era or clad-era."),
    ),
    _guide(
        "coin-date-context",
        "What a coin date can and cannot date",
        "A coin's mint year is a manufacturing date; archaeological context determines what it can say about a deposit.",
        "coins",
        (
            ("NPS describes a dated coin in an intact deposit as evidence that the deposit could not have been placed earlier than the coin's manufacture, a terminus post quem.", ("NPS_DATING",)),
            ("The coin may have circulated or been kept for years before deposition, so the mint date is not automatically the date of loss or discard.", ("NPS_DATING",)),
            ("NPS dates sites by combining artifacts, stratigraphy, and multiple methods; one object rarely supplies a complete occupation date.", ("NPS_DATING",)),
        ),
        ("Was the coin documented in a sealed layer or simply observed loose on the surface?", "Are there other dated objects or stratigraphic observations to compare?"),
        ("Record the exact date and mint mark, the recovery context as observed, and whether that context is secure, mixed, or unknown."),
    ),
    _guide(
        "button-material-and-form",
        "Button materials and forms",
        "Buttons were made in multiple materials and could be clothing fasteners or decorative objects.",
        "buttons",
        (
            ("NPS archaeologists document bone, shell, metal, and ceramic buttons in historical assemblages.", ("NPS_DECORATIVE_ARTIFACTS",)),
            ("Buttons may be sew-through with holes or have a shank on the back; record the actual attachment form before assigning a class.", ("NPS_DECORATIVE_ARTIFACTS", "NPS_BUTTONS")),
            ("A button can be plain or decorative and may have been used on clothing or household textiles, so function should not be inferred from material alone.", ("NPS_DECORATIVE_ARTIFACTS",)),
        ),
        ("What material is visible on the face, back, edge, and attachment?", "Does it have sewing holes, a loop shank, or a missing attachment?"),
        ("Record diameter, thickness, material appearance, face design, hole or shank count, and condition."),
    ),
    _guide(
        "button-size-and-use",
        "Button size and likely placement",
        "Button dimensions and attachment type can help distinguish clothing roles, but are not a precise garment label.",
        "buttons",
        (
            ("NPS Fort Pulaski notes that button size can help identify likely use; its collection included sizes consistent with undergarments, waistcoats, trousers, shirts, and outerwear.", ("NPS_DECORATIVE_ARTIFACTS",)),
            ("NPS cautions through its examples that buttons could be replaced and mixed over time, so associated clothing or use history can be complicated.", ("NPS_BUTTONS",)),
            ("A single button's size is a clue rather than proof of who wore it or which exact garment it came from.", ("NPS_DECORATIVE_ARTIFACTS", "NPS_BUTTONS")),
        ),
        ("What is the diameter and thickness, and is the shank proportionate to the face?", "Are wear, thread, or fabric traces preserved?"),
        ("Measure face diameter and total thickness separately; record material, attachment, holes, and any surviving textile or thread."),
    ),
    _guide(
        "button-sew-through",
        "Sew-through buttons",
        "A sew-through button has holes through its face or body for direct stitching.",
        "buttons",
        (
            ("NPS archaeological descriptions distinguish single-element four-hole sew-through buttons from shanked buttons.", ("NPS_HAWAII_REPORT",)),
            ("NPS examples include iron or steel and white porcelain four-hole buttons; multiple materials can share the same broad attachment form.", ("NPS_HAWAII_REPORT",)),
            ("Hole number, arrangement, concavity, and back profile are useful classification details when identifying a fragment.", ("NPS_HAWAII_REPORT",)),
        ),
        ("How many holes are present, and are they countersunk or plain?", "Is the front flat, domed, or concave?"),
        ("Record hole count and spacing, diameter, front/back curvature, material, and whether any holes are broken."),
    ),
    _guide(
        "button-shanks-and-backmarks",
        "Button shanks and backmarks",
        "The way a shank is attached and the wording on the back can be informative but may give only a broad date.",
        "buttons",
        (
            ("For NPS uniform buttons, external solder was used primarily until the mid-1920s, while internal soldering was used from the mid-1920s to about 1973; exceptions and stockpiling complicate those ranges.", ("NPS_BUTTONS",)),
            ("NPS reports that identical front designs may persist for decades, making shank construction and backmarks more useful than the face alone.", ("NPS_BUTTONS",)),
            ("Backmarks can name either a button manufacturer or uniform supplier; they do not always name the actual maker.", ("NPS_BUTTONS",)),
        ),
        ("Is the shank soldered externally, internally, or missing?", "Does the back carry a maker, supplier, quality, or place mark?"),
        ("Photograph face and back separately; transcribe the entire backmark and describe solder placement without attempting to clean it."),
    ),
    _guide(
        "button-bone-production",
        "Bone button blanks and manufacture",
        "Bone blanks can preserve evidence of button manufacture even when no finished button survives.",
        "buttons",
        (
            ("NPS Fort Stanwix identifies distinctive bone disks as blanks left from the button-making process.", ("NPS_BONE_BUTTONS",)),
            ("A hand tool called a bit could be pressed into bone and rotated like a drill to cut a button blank.", ("NPS_BONE_BUTTONS",)),
            ("A blank is production evidence, not necessarily a finished button or proof of where the bone originated.", ("NPS_BONE_BUTTONS",)),
        ),
        ("Is the piece a finished button with holes or a rough disk without finished attachment features?", "Are concentric cut marks or unfinished edges visible?"),
        ("Record diameter, thickness, edge profile, hole status, and tool marks; use a scale and photograph both faces."),
    ),
    _guide(
        "hardware-wrought-nails",
        "Hand-wrought nails",
        "A forged nail can preserve hand-working features in its shank and head.",
        "hardware",
        (
            ("NPS describes wrought nails as iron rods reheated and hammered to taper to a point, with a head formed by hand.", ("NPS_NAILS",)),
            ("Hand-forged heads can include rosehead, butterfly, and L-head forms; L-heads were used in finish work, trim, and flooring.", ("NPS_NAILS",)),
            ("Nail types overlap through time and old nails can be reused, so a wrought form is not an exact construction date by itself.", ("NPS_NAILS", "NPS_DATING")),
        ),
        ("Is the shank square or irregular, and does it taper on multiple sides?", "Is the head hand-formed, rose-shaped, butterfly-like, or L-shaped?"),
        ("Record length without head, shank cross-section, head form, point, bends, and corrosion; photograph head and side profile."),
    ),
    _guide(
        "hardware-cut-nails",
        "Early cut nails",
        "Cut nails were sheared from iron bar and can retain burrs that reveal the cutting method.",
        "hardware",
        (
            ("U.S. nail-making machines appeared in the 1790s and early 1800s; early Type A cut nails were sheared from bar stock and headed separately.", ("NPS_NAILS",)),
            ("Type A nails were made into the 1820s according to the NPS summary of Thomas Visser's nail chronology.", ("NPS_NAILS",)),
            ("Type A cutting can leave burrs on diagonally opposite edges; check both sides of the shank if the artifact is stable enough to inspect visually.", ("NPS_NAILS",)),
        ),
        ("Does the shank look cut from flat stock rather than drawn as round wire?", "Are edge burrs visible on diagonal sides?"),
        ("Record shank width and thickness, burr sides, head formation, and whether the point is intact."),
    ),
    _guide(
        "hardware-type-b-cut-nails",
        "Type B cut nails",
        "A later cut-nail machine flipped the bar to make repeated shearing more efficient.",
        "hardware",
        (
            ("The Type B method, developed by the 1810s, flipped the iron bar after each stroke and mechanically headed the nails.", ("NPS_NAILS",)),
            ("Type B cut nails tend to have burrs on the same side of the shank because the bar was flipped for each cut.", ("NPS_NAILS",)),
            ("NPS describes Type B nails as common through much of the 19th century, with wire nails gaining the majority by the late 19th to early 20th century.", ("NPS_NAILS",)),
        ),
        ("Are burrs on the same edge of both sides of the shank?", "Does the nail look cut, with a rectangular section, or drawn round?"),
        ("Record section shape, burr orientation, length, head, and any distortion; compare several nails together if context permits."),
    ),
    _guide(
        "hardware-wire-nails",
        "Wire nails",
        "Wire nails are generally round-shanked nails produced from drawn wire.",
        "hardware",
        (
            ("NPS documents soft-steel wire nails appearing in U.S. production in the 1880s and outproducing iron cut nails within several years.", ("NPS_NAILS",)),
            ("By 1913, NPS reports that 90 percent of U.S.-produced nails were wire nails; specialty cut nails continued to be made.", ("NPS_NAILS",)),
            ("A round shank supports a wire-nail identification, while a square or rectangular cut section points to another nail type; corrosion can obscure the section.", ("NPS_NAILS",)),
        ),
        ("Is the shank round in cross-section along a protected portion?", "Is the head machine-formed and regular, or hand-formed?"),
        ("Record shank cross-section, length, head shape, point, and whether the section is observed on an uncorroded area."),
    ),
    _guide(
        "hardware-nail-measurement",
        "Recording nails and spikes",
        "Consistent measurements make nail comparisons more useful than a guessed type name.",
        "hardware",
        (
            ("NPS distinguishes nail length from head size and notes that U.S. nail trade sizes use penny designations such as 10d.", ("NPS_NAILS",)),
            ("Nail form has been used to estimate building construction or alteration periods, but NPS describes this as approximate evidence.", ("NPS_NAILS",)),
            ("A nail or spike can be reused; the object is best dated with construction context and associated fasteners rather than as a loose isolated item.", ("NPS_NAILS", "NPS_DATING")),
        ),
        ("Is it a small nail, brad, spike, or an unclassified fastener?", "What are the head-to-point length and shank cross-section?"),
        ("Measure length without the head, width and thickness at the shank, head dimensions, and point type; note any bend or break."),
    ),
    _guide(
        "hardware-screws",
        "Hand-made and machine-made screws",
        "Screw production details can help distinguish an old hand-made component from later replacements.",
        "hardware",
        (
            ("An NPS preservation report compares a hand-made screw with a machine-made screw in historic door hardware.", ("NPS_HARDWARE_CONTEXT",)),
            ("The report shows why a machine-made screw in old architectural fabric may be a replacement, while a hand-made screw may have been reused.", ("NPS_HARDWARE_CONTEXT",)),
            ("Screw evidence alone did not conclusively verify the age of the doors in that NPS case study.", ("NPS_HARDWARE_CONTEXT",)),
        ),
        ("Are the threads regular and uniform or visibly hand-formed?", "Does the screw appear to belong to a hinge or lock, or to be a later repair?"),
        ("Record head shape and slot, thread spacing, shank form, corrosion, and the hardware element it was attached to."),
    ),
    _guide(
        "hardware-hinges-locks",
        "Hinges, locks, and keys",
        "Architectural hardware fragments can have long use lives and may be repaired or reused.",
        "hardware",
        (
            ("NPS archaeological reports record hinge straps, riveted hinge fragments, lock plates, padlock parts, and keys as distinct forms of hardware.", ("NPS_HARDWARE_CONTEXT",)),
            ("A single lock or key may have a long manufacturing period and uncertain association with a nearby event or building phase.", ("NPS_HARDWARE_CONTEXT",)),
            ("Rivet holes, hinge knuckles, shackle openings, key wards, and screw patterns are functional observations that can narrow the object class.", ("NPS_HARDWARE_CONTEXT",)),
        ),
        ("Does the fragment preserve a hinge knuckle, rivet line, lock case, shackle, or key bit?", "Are there multiple wear or repair features that suggest reuse?"),
        ("Record surviving dimensions, hole spacing, hinge orientation, key bit shape, lock opening, and associated wood or masonry context."),
    ),
    _guide(
        "hardware-glass-insulators",
        "Insulators as hardware",
        "Insulators are glass or ceramic components used to keep electrical or telegraph wire apart from a support.",
        "hardware",
        (
            ("NPS describes glass telegraph insulators as a non-conductive layer between the wire and a pole, preventing electrical shorting through wet wood.", ("NPS_INSULATOR",)),
            ("The wire groove shows where the conductor was wrapped; attachment shape shows how the insulator met a pole or bracket.", ("NPS_INSULATOR",)),
            ("Insulators may be glass or ceramic, so record both material and shape rather than assuming every pale fragment is porcelain.", ("NPS_INSULATOR", "NPS_YOSEMITE")),
        ),
        ("Is a wire groove or threaded attachment preserved?", "Does the fragment show molded lettering or a distinctive profile?"),
        ("Record material appearance, profile, groove, base attachment, marks, and fragment dimensions."),
    ),
    _guide(
        "stone-flakes-debitage",
        "Chipped-stone flakes and debitage",
        "Small stone flakes can be byproducts of tool manufacture or maintenance, not finished tools.",
        "stone",
        (
            ("NPS groups chipped stone tools with byproducts of their manufacture, or debitage, as lithic artifacts.", ("NPS_LITHICS",)),
            ("Large quantities of lithic debitage in an NPS archaeological example were interpreted as evidence of tool production and maintenance.", ("NPS_POINT_CONTEXT",)),
            ("A single sharp-looking stone fragment cannot be identified as a tool from sharpness alone; shape, removals, platform, and context matter.", ("NPS_LITHICS", "NPS_POINT_CONTEXT")),
        ),
        ("Does the fragment show repeated flake scars or a striking platform?", "Are the edges consistent with an intentionally detached flake or natural break?"),
        ("Record raw material appearance, flake length and width, striking platform, dorsal scars, edge damage, and both faces."),
    ),
    _guide(
        "stone-projectile-points",
        "Projectile-point form",
        "Point shape, base, shoulders, notches, and flake scars help describe a stone point.",
        "stone",
        (
            ("NPS describes lanceolate points as lance-shaped and distinguishes contracting bases that narrow from the shoulder toward the base.", ("NPS_POINT_CONTEXT",)),
            ("A projectile point is a hafted object; the term does not by itself determine whether it was shot by bow or thrown from an atlatl.", ("NPS_OBSIDIAN", "NPS_POINT_CONTEXT")),
            ("NPS notes that point shape can support comparisons to artifact assemblages, but a surface find without archaeological context may not have a secure date or cultural attribution.", ("NPS_POINT_CONTEXT",)),
        ),
        ("Is the outline lanceolate, triangular, stemmed, notched, or too incomplete to classify?", "Is the base contracting, straight, concave, or missing?"),
        ("Photograph both faces and the edge; record length, width, thickness, base, notches, shoulders, and breakage."),
    ),
    _guide(
        "stone-hafting-evidence",
        "Hafting clues on stone tools",
        "A hafted tool was attached to a shaft or handle; wear and edge pattern may preserve clues.",
        "stone",
        (
            ("NPS describes projectile points attached below the shoulder to a shaft or handle with sinew or plant fiber.", ("NPS_POINT_CONTEXT",)),
            ("In one NPS example, less sharp edges below a point's shoulder supported an interpretation that this part had been hafted.", ("NPS_POINT_CONTEXT",)),
            ("Hafting interpretations depend on preserved edge condition and comparison, and are stronger when supported by context than by silhouette alone.", ("NPS_POINT_CONTEXT",)),
        ),
        ("Are edges below a shoulder more worn or less sharp than the working tip?", "Does the base have a stem, notches, or other attachment features?"),
        ("Record edge condition by segment, shoulder position, stem or notch dimensions, and any surviving residue without touching it."),
    ),
    _guide(
        "stone-ground-tools",
        "Ground-stone tools",
        "Ground-stone objects were shaped by grinding rather than only by flake removal.",
        "stone",
        (
            ("NPS describes ground-stone tools as made by grinding stones together and gradually removing material to form a desired shape.", ("NPS_LITHICS",)),
            ("Examples documented by NPS include axes, celts, hammerstones, plummets, and sinkers.", ("NPS_LITHICS",)),
            ("Polished or ground surfaces, pecking, grooves, and overall form should be recorded separately because different tools can share one surface treatment.", ("NPS_LITHICS",)),
        ),
        ("Are there polished, ground, pecked, or battered surfaces?", "Is a groove, bit, perforation, or deliberately shaped edge preserved?"),
        ("Record material, weight only if appropriate, dimensions, surface texture, edge form, and any groove or perforation."),
    ),
    _guide(
        "stone-grooved-axe",
        "Grooved stone axes",
        "A groove can preserve evidence for attaching a wooden handle to a stone tool.",
        "stone",
        (
            ("NPS describes a full-grooved axe with a wooden handle attached in the groove.", ("NPS_LITHICS",)),
            ("The cited NPS example was ground by removing material gradually through stone-on-stone grinding.", ("NPS_LITHICS",)),
            ("NPS gives a broad Middle to Transitional Archaic range for its particular example; a similar-looking loose object should not inherit that date.", ("NPS_LITHICS", "NPS_DATING")),
        ),
        ("Does the groove encircle the body fully or partially?", "Are the groove edges and working bit ground, pecked, or damaged?"),
        ("Record groove position and width, bit profile, cross-section, raw material, and photographs from multiple orientations."),
    ),
    _guide(
        "stone-raw-material",
        "Stone raw material",
        "Stone type can inform a comparison, but material names and color alone do not prove a source or date.",
        "stone",
        (
            ("NPS notes that Indigenous toolstone choices varied by region and were often related to locally available stone resources.", ("NPS_LITHICS",)),
            ("A stone's color can mislead: NPS describes a fine-grained rhyolite called Saugus 'Jasper' that is not true jasper.", ("NPS_LITHICS",)),
            ("NPS explains that obsidian sources can be distinguished by chemical composition using X-ray fluorescence; visual resemblance is not source analysis.", ("NPS_OBSIDIAN",)),
        ),
        ("What color, grain size, translucency, and inclusions are visible on the surface?", "Is the identification a visual description or a laboratory-supported material/source identification?"),
        ("Describe observed texture and color without forcing a mineral name; record any source attribution and how it was established."),
    ),
    _guide(
        "stone-obsidian",
        "Obsidian and chipped volcanic glass",
        "Obsidian is natural volcanic glass that can be shaped into sharp-edged tools.",
        "stone",
        (
            ("NPS describes obsidian as volcanic glass formed when lava cools rapidly and notes its ability to hold a cutting edge.", ("NPS_OBSIDIAN",)),
            ("Dark shiny obsidian can be mistaken for modern glass; NPS advises reading shape, flake scars, and archaeological context.", ("NPS_YOSEMITE", "NPS_OBSIDIAN")),
            ("Obsidian source attribution requires chemical comparison such as X-ray fluorescence; color alone does not locate the source.", ("NPS_OBSIDIAN",)),
        ),
        ("Does the piece show conchoidal flake scars, a core, or a deliberately shaped edge?", "Could it be modern glass, natural fracture, or an archaeological object?"),
        ("Describe luster, translucency, cortex, flake scars, and edge forms; photograph without moving an object from its setting."),
    ),
    _guide(
        "stone-natural-breaks-and-context",
        "Stone object and context",
        "A shaped outline alone is not enough to establish that a stone is an artifact.",
        "stone",
        (
            ("NPS field notes distinguish a piece of black obsidian without removals from an artifact, showing that dark glassy appearance alone is not enough.", ("NPS_FIELD_NOTES",)),
            ("A surface projectile point can retain useful form information while lacking stratigraphic context to establish when it was deposited.", ("NPS_POINT_CONTEXT",)),
            ("Moving an artifact can destroy spatial associations that help archaeologists interpret it; NPS asks observers to document and report rather than relocate finds in park settings.", ("NPS_YOSEMITE", "NPS_POINT_CONTEXT")),
        ),
        ("Are flake scars patterned and overlapping, or is the surface naturally fractured?", "Is the object still in place with associated material or a visible layer?"),
        ("Photograph in place with scale if permitted; note orientation, nearby materials, surface/stratigraphic context, and uncertainty."),
    ),)
_CATEGORY_NAMES = dict(CATEGORIES)
_GUIDE_BY_ID = {guide["id"]: guide for guide in _GUIDES}

def _expand_guide(guide):
    used_ids = []
    for fact in guide["facts"]:
        for source_id in fact["source_ids"]:
            if source_id not in used_ids:
                used_ids.append(source_id)
    expanded_facts = [
        {
            "text": fact["text"],
            "sources": [dict(_SOURCE_CATALOG[source_id]) | {"id": source_id}
                        for source_id in fact["source_ids"]],
        }
        for fact in guide["facts"]
    ]
    return {
        "id": guide["id"],
        "title": guide["title"],
        "summary": guide["summary"],
        "category": guide["category"],
        "facts": expanded_facts,
        "questions": list(guide["questions"]),
        "record": list(guide["record"]),
        "sources": [dict(_SOURCE_CATALOG[source_id]) | {"id": source_id}
                    for source_id in used_ids],
    }

def _safe_query(value):
    if not isinstance(value, str) or len(value) > MAX_QUERY_LENGTH:
        return None
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        return None
    if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
        return None
    return " ".join(value.casefold().split())

def guide_stats():
    """Return corpus totals and stable per-category counts."""
    by_category = [
        {"id": category, "name": name,
         "count": sum(guide["category"] == category for guide in _GUIDES)}
        for category, name in CATEGORIES
    ]
    return {
        "total_guides": len(_GUIDES),
        "total_facts": sum(len(guide["facts"]) for guide in _GUIDES),
        "source_count": len(_SOURCE_CATALOG),
        "categories": by_category,
    }

def search_guides(query="", category=ALL_CATEGORIES, page=1):
    """Search reviewed guide text and return stable, paged summary rows.

    Query matching is case-insensitive literal substring matching, not regex.
    Invalid or oversized text and unknown categories return an empty result.
    Invalid page values use page 1; out-of-range positive pages clamp to the
    last available page.
    """
    normalized = _safe_query(query)
    if normalized is None:
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    if not isinstance(category, str) or category not in (ALL_CATEGORIES, *_CATEGORY_NAMES):
        return {"rows": [], "total": 0, "page": 1, "pages": 1}
    if type(page) is not int or page < 1:
        page = 1
    selected = []
    for guide in _GUIDES:
        if category != ALL_CATEGORIES and guide["category"] != category:
            continue
        searchable = " ".join((
            guide["title"], guide["summary"],
            *(fact["text"] for fact in guide["facts"]),
            *guide["questions"],
        )).casefold()
        if normalized and normalized not in searchable:
            continue
        selected.append(guide)
    total = len(selected)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, pages)
    start = (page - 1) * PAGE_SIZE
    rows = [
        {
            "id": guide["id"],
            "title": guide["title"],
            "summary": guide["summary"],
            "category": guide["category"],
            "fact_count": len(guide["facts"]),
            "question_count": len(guide["questions"]),
        }
        for guide in selected[start:start + PAGE_SIZE]
    ]
    return {"rows": rows, "total": total, "page": page, "pages": pages}

def get_guide(identifier):
    """Return a defensive copy of a reviewed guide, or None for an unknown ID."""
    if not isinstance(identifier, str):
        return None
    return _expand_guide(_GUIDE_BY_ID[identifier]) if identifier in _GUIDE_BY_ID else None
