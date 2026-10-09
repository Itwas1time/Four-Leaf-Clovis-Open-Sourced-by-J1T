> **Public edition:** Census town points and reviewed reference catalogs are bundled. Optional data collections retain their publishers' original location qualifications. Private find locations and personal data are excluded from Git. See the [README](../README.md) for the data inventory.

# ARCHAEO-SCAN Data Sources

## Terrain (SRTM 30m DEM)
- **Source:** NASA / USGS Shuttle Radar Topography Mission
- **API:** OpenTopography API (`https://portal.opentopography.org/API/globaldem`)
- **License:** Public Domain (US Government)
- **Coverage:** Global, 60°N to 56°S
- **Resolution:** 30m (1 arc-second)
- **Format:** GeoTIFF, EPSG:4326
- **Update:** Static (February 2000)
- **Storage:** ~25 MB per 1°×1° tile
- **Rationale:** Foundation for settlement prediction, terrain anomaly detection

## Hydrology (NHD)
- **Source:** USGS National Hydrography Dataset Plus High Resolution
- **API:** `https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer`
- **License:** Public Domain
- **Coverage:** Continental US, Alaska, Hawaii
- **Format:** GeoPackage/Shapefile
- **Update:** Continuously updated
- **Storage:** 50-200 MB per HUC4 watershed
- **Rationale:** Water access is the strongest universal predictor of settlement

## Soils (SSURGO)
- **Source:** USDA NRCS Soil Survey Geographic Database
- **API:** Soil Data Access REST (`https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest`)
- **License:** Public Domain
- **Coverage:** ~95% of US counties
- **Update:** Annual
- **Storage:** 5-20 MB per county
- **Rationale:** Anthropogenic soil signatures (anthrosols) persist for millennia

## Geology (SGMC)
- **Source:** USGS State Geologic Map Compilation
- **API:** `https://mrdata.usgs.gov/services/sgmc`
- **License:** Public Domain
- **Coverage:** Continental US
- **Rationale:** Karst→caves, sandstone→rockshelters, basalt→lava tubes

## Land Status (BLM SMA)
- **Source:** Bureau of Land Management Surface Management Agency
- **API:** `https://gis.blm.gov/arcgis/rest/services/lands`
- **License:** Public Domain
- **Rationale:** 95% of federal land is unsurveyed for archaeology

## Known Sites (NRHP)
- **Source:** National Register of Historic Places
- **API:** `https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services`
- **License:** Public Domain
- **Rationale:** Training data for convergence scoring model

## LiDAR (3DEP)
- **Source:** USGS 3D Elevation Program
- **API:** `https://tnmaccess.nationalmap.gov/api/v1/products`
- **License:** Public Domain
- **Coverage:** ~75% of US (growing)
- **Storage:** 2+ GB per county
- **Rationale:** Penetrates canopy to reveal invisible terrain features

## Satellite Imagery (Sentinel-2)
- **Source:** ESA Copernicus Sentinel-2 L2A
- **API:** `https://dataspace.copernicus.eu/odata/v1`
- **License:** Open (Copernicus Data Policy)
- **Resolution:** 10m (visible), 20m (red-edge/SWIR)
- **Rationale:** Crop marks from buried features visible in NDVI

## Bathymetry (NOAA)
- **Source:** NOAA National Centers for Environmental Information
- **API:** `https://www.ngdc.noaa.gov/thredds`
- **License:** Public Domain
- **Rationale:** Paleo-coastline reconstruction for submerged site prediction

## Paleoclimate
- **Source:** Composite from published reconstructions
- **License:** Academic (cite source papers)
- **Rationale:** Constrains when areas became habitable after deglaciation
