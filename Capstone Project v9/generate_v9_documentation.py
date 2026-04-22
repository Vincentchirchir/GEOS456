from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape


OUT_PATH = Path(
    r"c:\GIS SCRIPTS\GEOS456\Capstone Project v9\V9_High_Level_Documentation.docx"
)


DATA_PRODUCTS_TABLE = {
    "headers": ["Name", "Storage", "Purpose", "Where Produced"],
    "rows": [
        [
            "{base_name}_copy",
            "output_gdb (temporary, deleted)",
            "Working copy of the input line so the original feature class is never modified during route creation.",
            "route_tools.py line 48",
        ],
        [
            "{base_name}_dissolve",
            "output_gdb (temporary, deleted)",
            "Dissolved single-feature line used to prepare FromM and ToM fields before Create Routes runs.",
            "route_tools.py line 64",
        ],
        [
            "{base_name}_Route",
            "output_gdb (retained)",
            "Final M-enabled route used by all downstream stationing, event, layout, and map-series workflows.",
            "route_tools.py line 90",
        ],
        [
            "{base_name}_segment_event",
            "output_gdb (temporary, deleted)",
            "Temporary route-event table used only when a start and end measure are supplied to clip the route segment for station generation.",
            "route_tools.py line 150",
        ],
        [
            "{base_name}_segment_fc",
            "output_gdb (temporary, deleted after station generation)",
            "Clipped route segment copied from the event layer and used as the stationing source when the workflow runs on a measure subset.",
            "route_tools.py line 183",
        ],
        [
            "{base_name}_Stations",
            "output_gdb (retained)",
            "Final station point feature class generated at the requested interval along the route.",
            "stationing_tools.py line 154",
        ],
        [
            "{base_name}_station_events",
            "in_memory (temporary)",
            "Station event table storing MEAS, DISTANCE, and Chainage values for the generated station points.",
            "stationing_tools.py line 180",
        ],
        [
            "{layer_name}_intersect",
            "in_memory (temporary)",
            "Raw point intersection geometry between the route and an analysis layer before event-location processing.",
            "events_tools.py line 123",
        ],
        [
            "{layer_name}_intersect_singlepart",
            "in_memory (temporary, deleted)",
            "Short-lived singlepart version of multipoint intersection output used only to explode multipoint crossings before copying them back.",
            "events_tools.py line 29",
        ],
        [
            "{layer_name}_Overlaps",
            "output_gdb (retained if non-empty)",
            "Raw line overlap geometry showing where the route overlaps a polyline or polygon-derived feature.",
            "events_tools.py line 134",
        ],
        [
            "{layer_name}_intersect_event",
            "in_memory (temporary)",
            "Point event table created from raw point intersections and located along the route with MEAS values.",
            "events_tools.py line 196",
        ],
        [
            "{layer_name}_OverlapsTable",
            "output_gdb (retained if non-empty)",
            "Line event table storing FMEAS, TMEAS, and chainage ranges for overlap segments.",
            "events_tools.py line 226",
        ],
        [
            "{clean_name}_Intersections",
            "output_gdb (retained)",
            "Final point intersection feature class used for map display, labeling, and layout annotation.",
            "events_tools.py line 375",
        ],
        [
            "{clean_name}_single",
            "output_gdb (conditional, retained when created)",
            "Singlepart version of the final intersections output when the copied intersection features still contain multipoint geometry.",
            "events_tools.py line 400",
        ],
        [
            "{base_name}_overlap",
            "in_memory (temporary)",
            "Route-located overlap feature geometry rebuilt from overlap event tables for layout drawing and band labeling.",
            "events_tools.py line 416",
        ],
        [
            "{input_name}_MapIndex",
            "output_gdb (retained)",
            "Strip-map index polygon feature class that drives map-series page extent, numbering, and rotation.",
            "map_series_tools.py lines 40 and 66",
        ],
        [
            "{layout_name}_Page_##.pdf",
            "PDF output folder (retained)",
            "Individual page PDF exported immediately after page-specific redraw so custom graphics stay synchronized with each page.",
            "map_series_tools.py line 195",
        ],
        [
            "{layout_name}_All_Pages.pdf",
            "PDF output folder (retained)",
            "Final merged PDF deliverable assembled from the individually exported page PDFs.",
            "map_series_tools.py lines 624 and 225",
        ],
    ],
}


BLOCKS = [
    ("title", "GEOS456 Capstone Project V9"),
    ("subtitle", "High-Level Documentation"),
    (
        "p",
        "Scope: Final documentation for the toolbox and support modules in "
        "GEOS456/Capstone Project v9. Date: April 16, 2026.",
    ),
    ("h1", "Project Overview"),
    (
        "p",
        "V9 is an ArcGIS Pro Python toolbox that automates the production of "
        "alignment sheets from a selected linear feature. The workflow creates "
        "a measured route, generates stationing, detects intersections and "
        "overlaps against optional analysis layers, builds a presentation-ready "
        "layout, and can export a page-based PDF deliverable.",
    ),
    (
        "p",
        "The final V9 design emphasizes repeatability inside the current "
        "ArcGIS Pro project. It reduces manual sheet preparation, keeps the "
        "main map and mini map synchronized, and rebuilds page-specific "
        "graphics when map series pages are exported.",
    ),
    ("h1", "Primary Purpose"),
    (
        "p",
        "The toolbox turns one input route and a set of optional context "
        "layers into a consistent alignment-sheet package. At a high level, "
        "it supports route linear referencing, regular station generation, "
        "chainage formatting, crossing and overlap analysis, layout assembly, "
        "and final sheet export.",
    ),
    ("h1", "End-to-End Workflow"),
    (
        "bullet",
        "The user runs Generate Alignment Sheets from LinearReferencing.pyt.",
    ),
    (
        "bullet",
        "The tool reads the selected polyline, output geodatabase, station "
        "interval, and optional start and end measures.",
    ),
    (
        "bullet",
        "A measured route is created from the input line so all downstream "
        "outputs can be referenced by route measure.",
    ),
    (
        "bullet",
        "Station points are generated at the requested interval and are joined "
        "back to chainage text values.",
    ),
    (
        "bullet",
        "Optional analysis layers are intersected against the route to find "
        "point crossings and line or polygon overlaps.",
    ),
    (
        "bullet",
        "Those crossings and overlaps are located along the route and "
        "converted into event tables and feature classes.",
    ),
    (
        "bullet",
        "If layout creation is enabled, the tool builds an alignment-sheet "
        "layout with a main map, mini map, title block, legend, scale "
        "information, stationing bands, and editable text areas.",
    ),
    (
        "bullet",
        "If map series is enabled, strip-map index polygons drive page extent "
        "and rotation.",
    ),
    (
        "bullet",
        "If PDF export is enabled, each page is redrawn with page-specific "
        "labels and table content, exported one page at a time, and then "
        "merged into a single PDF.",
    ),
    ("h1", "Main User Inputs"),
    (
        "bullet",
        "Input Linear Feature: required polyline layer that represents the "
        "route or corridor to document.",
    ),
    (
        "bullet",
        "Output Geodatabase: required workspace that stores route, station, "
        "overlap, intersection, and index outputs.",
    ),
    (
        "bullet",
        "Station Interval: required spacing between generated station points.",
    ),
    (
        "bullet",
        "Start Measure and End Measure: optional controls for the route "
        "measure system and for limiting the processed segment.",
    ),
    (
        "bullet",
        "Search Tolerance: optional tolerance used when locating features "
        "along the route.",
    ),
    (
        "bullet",
        "Overlapping or Intersecting Features: optional analysis layers used "
        "to populate crossing and overlap outputs.",
    ),
    (
        "bullet",
        "Layout settings: optional controls for layout name, page size, main "
        "map, and mini map.",
    ),
    (
        "bullet",
        "Map series settings: optional controls for scale, page orientation, "
        "and overlap percentage.",
    ),
    (
        "bullet",
        "PDF output folder: optional folder used when page exports are "
        "requested.",
    ),
    ("h1", "Key Outputs"),
    ("h2", "Persistent Geodatabase Outputs"),
    (
        "bullet",
        "A measured route feature class named from the input base name, for "
        "example {base}_Route.",
    ),
    (
        "bullet",
        "A station point feature class, for example {base}_Stations.",
    ),
    (
        "bullet",
        "Optional overlap feature classes for line and polygon layers, for "
        "example {layer}_Overlaps.",
    ),
    (
        "bullet",
        "Optional overlap event tables, for example {layer}_OverlapsTable.",
    ),
    (
        "bullet",
        "Optional point intersection feature classes, for example "
        "{layer}_Intersections.",
    ),
    (
        "bullet",
        "Optional strip-map index features for map series, for example "
        "{input}_MapIndex.",
    ),
    ("h2", "Temporary or In-Memory Working Data"),
    (
        "bullet",
        "Station event tables used to hold MEAS and Chainage values during "
        "the ArcGIS Pro session.",
    ),
    (
        "bullet",
        "Intermediate point and line event tables created from Locate "
        "Features Along Routes.",
    ),
    (
        "bullet",
        "In-memory overlap feature layers and page-export working graphics.",
    ),
    ("h2", "Project and Deliverable Outputs"),
    (
        "bullet",
        "A finished ArcGIS Pro layout with standard sheet elements and "
        "auto-populated text.",
    ),
    (
        "bullet",
        "An optional spatial map series based on strip-map index polygons.",
    ),
    (
        "bullet",
        "Optional single-page PDFs plus a merged final PDF named "
        "{layout_name}_All_Pages.pdf.",
    ),
    ("h1", "Module Responsibilities"),
    (
        "bullet",
        "LinearReferencing.pyt: toolbox entry point, parameter definitions, "
        "validation, and orchestration of the full workflow.",
    ),
    (
        "bullet",
        "route_tools.py: creates the M-enabled route and optionally clips the "
        "route to a measure range for station generation.",
    ),
    (
        "bullet",
        "stationing_tools.py: generates station points, locates them along the "
        "route, formats chainage, removes duplicate end stations, and joins "
        "chainage back to the points.",
    ),
    (
        "bullet",
        "events_tools.py: builds raw intersections and overlaps, creates "
        "event tables, adds chainage fields, and converts route events back "
        "into feature classes.",
    ),
    (
        "bullet",
        "band_tools.py: converts event data into station-band records and "
        "layout coordinates for ticks, labels, and overlap graphics.",
    ),
    (
        "bullet",
        "map_tools.py: adds outputs to the correct maps, snapshots existing "
        "site layers, and manages clutter control for the mini map.",
    ),
    (
        "bullet",
        "layout_tools.py: creates the alignment layout, positions the map "
        "frames, sets extent buffers, and optionally creates the spatial map "
        "series.",
    ),
    (
        "bullet",
        "layout_elements.py: builds the legend, north arrow, scale bar, map "
        "scale text, title block, boundary graphics, and standard editable "
        "text elements.",
    ),
    (
        "bullet",
        "geocoding_tools.py: derives the sheet title and subtitle from the "
        "input feature name and from reverse geocoding or coordinate fallback "
        "logic.",
    ),
    (
        "bullet",
        "auto_populate.py: fills standard text fields such as pipe name, "
        "date, stations, total length, coordinate system, from and to "
        "coordinates, and the intersection table.",
    ),
    (
        "bullet",
        "map_series_tools.py: handles page-by-page redraw, page rotation, "
        "page-specific auto-population, page export, PDF merge, and "
        "route-wide reset after export.",
    ),
    ("h1", "Layout and Cartography Strategy"),
    (
        "p",
        "The alignment sheet is built around a main map frame, a mini "
        "overview map, upper and lower stationing bands, and a bottom "
        "information area for legend and project text. Layout positions are "
        "expressed proportionally so the design can scale across different "
        "paper sizes.",
    ),
    (
        "p",
        "V9 also improves mini map behavior. When the same ArcGIS Pro map is "
        "used for both the main and mini frames, the toolbox can create a "
        "dedicated mini-map copy so generated outputs do not clutter the "
        "overview frame. When separate maps are already being used, the tool "
        "applies a frame-level visibility whitelist to preserve site context.",
    ),
    ("h1", "Map Series and PDF Export Behavior"),
    (
        "p",
        "A major design point in V9 is the handling of custom page graphics. "
        "ArcGIS Pro updates map-driven content automatically in a spatial map "
        "series, but the custom station-band ticks, labels, and manual table "
        "text are shared layout elements. Because those elements are not "
        "page-aware by default, V9 does not rely on a single native map-series "
        "PDF export call.",
    ),
    (
        "p",
        "Instead, V9 switches to each page, redraws the page-specific content, "
        "exports that page immediately, and then merges all exported pages into "
        "one PDF. After export, the layout is restored to a neutral route-wide "
        "state so stale page graphics do not remain visible while the user "
        "browses the project interactively.",
    ),
    ("h1", "Auto-Populated Content"),
    ("bullet", "Pipe name from the input dataset name."),
    (
        "bullet",
        "Starting station, ending station, and total length from the current "
        "route or page measure range.",
    ),
    (
        "bullet",
        "Date and coordinate system from the active run and route spatial "
        "reference.",
    ),
    ("bullet", "From and To coordinate text from the input extent."),
    (
        "bullet",
        "Project title and subtitle derived from cleaned input naming plus "
        "reverse-geocoded location where possible.",
    ),
    (
        "bullet",
        "Intersection table entries based on visible point crossings and "
        "overlap records.",
    ),
    ("h1", "Glossary of Key Terms"),
    (
        "bullet",
        "Alignment Sheet: The final layout output showing the route, "
        "stationing, crossings, overlaps, and map information.",
    ),
    (
        "bullet",
        "Linear Referencing: The ArcGIS workflow used to locate features by "
        "distance along a route instead of only by x and y position.",
    ),
    (
        "bullet",
        "Route: The main input line converted into a measured feature so all "
        "downstream outputs can be referenced by distance.",
    ),
    (
        "bullet",
        "M-enabled Route: A route whose geometry stores M values, which the "
        "project uses as route measures.",
    ),
    (
        "bullet",
        "Measure: A numeric distance value along the route.",
    ),
    (
        "bullet",
        "Start Measure and End Measure: Optional values that define where "
        "processing begins and ends along the route.",
    ),
    (
        "bullet",
        "MEAS: The measure value for a point event.",
    ),
    (
        "bullet",
        "FMEAS and TMEAS: The from-measure and to-measure values for a line "
        "event or overlap segment.",
    ),
    (
        "bullet",
        "Station: A generated point placed at a regular interval along the route.",
    ),
    (
        "bullet",
        "Stationing: The overall process of creating and labeling those "
        "regular route points.",
    ),
    (
        "bullet",
        "Station Interval: The spacing between generated station points, such "
        "as 100 meters.",
    ),
    (
        "bullet",
        "Chainage: The formatted station label used in the project, such as "
        "1+250.",
    ),
    (
        "bullet",
        "Search Tolerance: The distance tolerance used when locating features "
        "along the route.",
    ),
    (
        "bullet",
        "Analysis Layers: Optional point, line, or polygon layers checked for "
        "crossings or overlaps with the route.",
    ),
    (
        "bullet",
        "Intersection: A point where the route crosses another feature.",
    ),
    (
        "bullet",
        "Overlap: A segment where the route shares space with another line or "
        "polygon-derived feature.",
    ),
    (
        "bullet",
        "Event Table: A table storing route-referenced results such as MEAS, "
        "FMEAS, and TMEAS.",
    ),
    (
        "bullet",
        "Route Event Layer: A layer created from an event table and the "
        "measured route.",
    ),
    (
        "bullet",
        "Point Event Feature: A route-located output representing point crossings.",
    ),
    (
        "bullet",
        "Line Event Feature: A route-located output representing overlap segments.",
    ),
    (
        "bullet",
        "Band Records: The flattened data structure used to draw station-band "
        "ticks, labels, and table entries on the layout.",
    ),
    (
        "bullet",
        "Stationing Bands: The upper and lower layout bands that display "
        "route-related ticks and labels.",
    ),
    (
        "bullet",
        "Main Map Frame: The primary map on the sheet that shows the route in detail.",
    ),
    (
        "bullet",
        "Mini Map: The overview map that gives wider geographic context.",
    ),
    (
        "bullet",
        "Layout: The ArcGIS Pro page composition containing map frames, text, "
        "legend, scale bar, and graphics.",
    ),
    (
        "bullet",
        "Auto-Populate: The logic that fills layout text such as pipe name, "
        "station range, length, coordinates, and table rows.",
    ),
    (
        "bullet",
        "Spatial Map Series: The page-based layout workflow where each page "
        "follows a portion of the route.",
    ),
    (
        "bullet",
        "Strip Map Index: The polygon index feature class used to define "
        "map-series pages.",
    ),
    (
        "bullet",
        "Page Rotation: The angle applied so each map-series page follows the "
        "route direction.",
    ),
    (
        "bullet",
        "Page-Specific Content: Graphics and text that must be rebuilt for "
        "each map-series page.",
    ),
    (
        "bullet",
        "Output GDB: The output geodatabase where the project stores route, "
        "stations, intersections, overlaps, and index features.",
    ),
    (
        "bullet",
        "Merged PDF: The final combined alignment-sheet export created from "
        "individually exported pages.",
    ),
    ("h1", "Challenges Encountered During Development"),
    (
        "bullet",
        "ArcGIS Pro map series did not automatically handle custom station-band "
        "ticks, labels, and manual table text because those items are shared "
        "layout elements rather than true page-aware content.",
    ),
    (
        "bullet",
        "Repeated tool runs could leave duplicate text, stale labels, and old "
        "boundary graphics in the layout, so V9 had to add explicit cleanup "
        "logic before redrawing page content.",
    ),
    (
        "bullet",
        "Using the same ArcGIS Pro map for both the main map and mini map "
        "caused clutter in the overview frame because generated outputs "
        "appeared in both places unless visibility was controlled carefully.",
    ),
    (
        "bullet",
        "Relying on aprx.activeMap was not reliable once layouts were involved, "
        "because the active view could switch away from the intended main map "
        "and break where outputs were added.",
    ),
    (
        "bullet",
        "GeneratePointsAlongLines can create duplicate end stations when the "
        "line length and interval combination lands on the endpoint more than "
        "once, so duplicate station measures had to be detected and removed.",
    ),
    (
        "bullet",
        "Intersect operations could return multipoint results, but locating "
        "those features along routes only stores one measure per input feature, "
        "so the intersections had to be split to preserve distinct crossings.",
    ),
    (
        "bullet",
        "Point intersections needed to retain their real crossing geometry for "
        "leader placement, so V9 preserved leader anchor IDs and joined chainage "
        "fields back onto copied raw geometries instead of relying only on "
        "route-event output layers.",
    ),
    (
        "bullet",
        "Reverse geocoding for the title block was useful but not guaranteed, "
        "so the workflow needed fallbacks for unhelpful results, address-like "
        "tokens, or missing portal geocoder responses.",
    ),
    (
        "bullet",
        "Because page-specific exports depend on redrawing first and exporting "
        "immediately afterward, the export path had to be treated as a controlled "
        "sequence rather than a simple one-click ArcGIS Pro map series export.",
    ),
    (
        "bullet",
        "The intersection summary area was not reliable enough to leave fully "
        "enabled in the final state, so it was temporarily disabled to keep "
        "exported sheets clean and predictable.",
    ),
    ("h1", "Recommendations for Future Work"),
    (
        "bullet",
        "Revisit and complete the disabled intersection summary panel so it can "
        "be safely included in final sheets without leftover or duplicated text.",
    ),
    (
        "bullet",
        "Add a lightweight configuration file or parameter profile system so "
        "common project settings such as page size, station interval, maps, and "
        "export folder can be reused without re-entry.",
    ),
    (
        "bullet",
        "Improve logging and run reporting by writing a summary file after each "
        "run that records created outputs, skipped layers, warnings, and export "
        "results for QA purposes.",
    ),
    (
        "bullet",
        "Add more formal validation around required fields, coordinate systems, "
        "and unsupported geometry cases before processing begins so failures are "
        "caught earlier.",
    ),
    (
        "bullet",
        "Consider separating export logic from layout creation logic even "
        "further so the page-redraw and PDF workflow can be tested and reused "
        "more independently.",
    ),
    (
        "bullet",
        "Expand the title and metadata system so client name, project number, "
        "review status, and other corporate fields can be fed from structured "
        "inputs instead of being filled manually.",
    ),
    (
        "bullet",
        "Investigate whether some band and label drawing can be converted into "
        "more structured layout groups or reusable templates to reduce custom "
        "cleanup logic on reruns.",
    ),
    (
        "bullet",
        "Add targeted regression tests for station duplication, multipoint "
        "intersection handling, mini map filtering, and page export behavior so "
        "future edits do not reintroduce solved issues.",
    ),
    (
        "bullet",
        "Document a recommended operating checklist for end users inside ArcGIS "
        "Pro so project setup, layer selection, export expectations, and rerun "
        "behavior are consistently understood.",
    ),
    ("h1", "Current Final-State Notes"),
    (
        "bullet",
        "The toolbox is designed to run inside the current ArcGIS Pro project "
        "and depends on ArcPy and ArcGIS Pro layout and map APIs.",
    ),
    (
        "bullet",
        "Input data is expected to be a polyline feature layer. Optional "
        "analysis layers can be point, line, or polygon data.",
    ),
    (
        "bullet",
        "If no analysis layers are supplied, the route and stationing workflow "
        "still runs and the layout can still be created, but no crossing or "
        "overlap band content is added.",
    ),
    (
        "bullet",
        "The title block attempts reverse geocoding for a better location label "
        "and falls back to coordinates if a usable geocoder response is not "
        "available.",
    ),
    (
        "bullet",
        "The intersection summary panel exists in code but is intentionally "
        "disabled in the final configuration so exported layouts remain clean "
        "while that feature is revisited.",
    ),
    (
        "bullet",
        "When map series is enabled but PDF export is turned off, V9 resets the "
        "layout to a route-wide base state instead of leaving one page preview "
        "on the sheet.",
    ),
    ("h1", "Final Folder Contents"),
    (
        "bullet",
        "Core final code files: LinearReferencing.pyt, route_tools.py, "
        "stationing_tools.py, events_tools.py, band_tools.py, map_tools.py, "
        "layout_tools.py, layout_elements.py, geocoding_tools.py, "
        "auto_populate.py, and map_series_tools.py.",
    ),
    (
        "bullet",
        "Toolbox metadata files with .pyt.xml extensions are also present in "
        "the folder and support ArcGIS Pro toolbox metadata and help behavior.",
    ),
    ("h1", "Recommended Use for Final Deliverables"),
    (
        "bullet",
        "Use Generate Alignment Sheets as the single entry point for the workflow.",
    ),
    (
        "bullet",
        "Provide the final route layer, output geodatabase, and desired station "
        "interval first.",
    ),
    (
        "bullet",
        "Add intersecting and overlapping layers only when they are required "
        "for sheet annotation.",
    ),
    (
        "bullet",
        "For a final deliverable package, enable Create Layout, Create Map "
        "Series, and Export Alignment Sheets in PDF.",
    ),
    (
        "bullet",
        "Keep the generated layout and merged PDF as the primary presentation "
        "outputs, with the geodatabase outputs serving as traceable analytical "
        "support data.",
    ),
    ("h1", "Appendix"),
    ("h2", "Appendix A: Final V9 File Inventory"),
    (
        "bullet",
        "LinearReferencing.pyt: main ArcGIS Pro toolbox and orchestration entry point.",
    ),
    (
        "bullet",
        "route_tools.py: route creation and optional measure-range clipping logic.",
    ),
    (
        "bullet",
        "stationing_tools.py: station generation, chainage calculation, and station joins.",
    ),
    (
        "bullet",
        "events_tools.py: intersections, overlaps, event tables, and event features.",
    ),
    (
        "bullet",
        "band_tools.py: band-record preparation, layout positioning, ticks, and labels.",
    ),
    (
        "bullet",
        "map_tools.py: map targeting, mini map filtering, and output layer management.",
    ),
    (
        "bullet",
        "layout_tools.py: layout creation, map frames, extent buffering, and map series setup.",
    ),
    (
        "bullet",
        "layout_elements.py: legend, title block, north arrow, scale bar, and sheet graphics.",
    ),
    (
        "bullet",
        "geocoding_tools.py: title naming support, reverse geocoding, and coordinate fallback.",
    ),
    (
        "bullet",
        "auto_populate.py: automatic text, table, and page-value population.",
    ),
    (
        "bullet",
        "map_series_tools.py: per-page redraw, export, PDF merge, and layout reset behavior.",
    ),
    (
        "bullet",
        "generate_v9_documentation.py: documentation generator for the final Word deliverable.",
    ),
    ("h2", "Appendix B: High-Level Execution Sequence"),
    (
        "bullet",
        "Input route is validated and written into a measured route feature class.",
    ),
    (
        "bullet",
        "Station points are generated and assigned MEAS and Chainage values.",
    ),
    (
        "bullet",
        "Optional analysis layers are intersected with the route to derive crossings and overlaps.",
    ),
    (
        "bullet",
        "Crossings and overlaps are located along the route and converted into event outputs.",
    ),
    (
        "bullet",
        "Band records are built for use in ticks, labels, and intersection table content.",
    ),
    (
        "bullet",
        "Outputs are added to the correct ArcGIS Pro maps used by the layout.",
    ),
    (
        "bullet",
        "If requested, the alignment-sheet layout and map series are created.",
    ),
    (
        "bullet",
        "Auto-populated values and page graphics are drawn onto the layout.",
    ),
    (
        "bullet",
        "If PDF export is enabled, each page is rebuilt, exported, and merged into the final deliverable.",
    ),
    ("h2", "Appendix C: Common Output Naming Patterns"),
    (
        "bullet",
        "{base}_Route: measured route feature class derived from the input line.",
    ),
    (
        "bullet",
        "{base}_Stations: station point feature class generated at the selected interval.",
    ),
    (
        "bullet",
        "{layer}_Intersections: output feature class for point crossings.",
    ),
    (
        "bullet",
        "{layer}_Overlaps: output feature class for overlap segments.",
    ),
    (
        "bullet",
        "{layer}_OverlapsTable: route event table for overlap ranges.",
    ),
    (
        "bullet",
        "{input}_MapIndex: strip-map index feature class for map series pages.",
    ),
    (
        "bullet",
        "{layout_name}_All_Pages.pdf: merged PDF deliverable created from exported pages.",
    ),
    ("h2", "Appendix D: Data Products Generated by V9"),
    (
        "p",
        "The table below summarizes the named datasets and output files created "
        "by the V9 workflow, including retained deliverables and temporary "
        "scratch products created in in_memory or the output geodatabase.",
    ),
    ("table", DATA_PRODUCTS_TABLE),
    ("h1", "Summary"),
    (
        "p",
        "The V9 folder represents a complete ArcGIS Pro automation package for "
        "alignment-sheet production. Its strength is not only in generating "
        "route and stationing outputs, but in carrying those outputs all the "
        "way through layout assembly, page management, and final PDF export "
        "with page-aware graphics. At a high level, V9 is organized, modular, "
        "and ready to be described as the final implementation for the "
        "capstone deliverable.",
    ),
]


def make_paragraph(text, style=None, bold=False):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return (
        "<w:p>"
        f"{ppr}"
        "<w:r>"
        f"{rpr}"
        f'<w:t xml:space="preserve">{escape(text)}</w:t>'
        "</w:r>"
        "</w:p>"
    )


def make_table(table_data):
    col_widths = [1800, 1800, 3240, 2520]
    headers = table_data["headers"]
    rows = table_data["rows"]

    grid = "".join(f'<w:gridCol w:w="{width}"/>' for width in col_widths)

    def make_cell(text, width, *, bold=False, shaded=False):
        shading = (
            '<w:shd w:val="clear" w:color="auto" w:fill="D9E2F3"/>'
            if shaded
            else ""
        )
        return (
            "<w:tc>"
            "<w:tcPr>"
            f'<w:tcW w:w="{width}" w:type="dxa"/>'
            '<w:vAlign w:val="top"/>'
            f"{shading}"
            "</w:tcPr>"
            f"{make_paragraph(text, 'Normal', bold=bold)}"
            "</w:tc>"
        )

    header_row = (
        "<w:tr>"
        + "".join(
            make_cell(header, width, bold=True, shaded=True)
            for header, width in zip(headers, col_widths)
        )
        + "</w:tr>"
    )

    body_rows = []
    for row in rows:
        body_rows.append(
            "<w:tr>"
            + "".join(make_cell(value, width) for value, width in zip(row, col_widths))
            + "</w:tr>"
        )

    return (
        "<w:tbl>"
        "<w:tblPr>"
        '<w:tblW w:w="0" w:type="auto"/>'
        '<w:tblLayout w:type="fixed"/>'
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="8" w:space="0" w:color="808080"/>'
        '<w:left w:val="single" w:sz="8" w:space="0" w:color="808080"/>'
        '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="808080"/>'
        '<w:right w:val="single" w:sz="8" w:space="0" w:color="808080"/>'
        '<w:insideH w:val="single" w:sz="6" w:space="0" w:color="BFBFBF"/>'
        '<w:insideV w:val="single" w:sz="6" w:space="0" w:color="BFBFBF"/>'
        "</w:tblBorders>"
        "</w:tblPr>"
        f"<w:tblGrid>{grid}</w:tblGrid>"
        f"{header_row}"
        + "".join(body_rows)
        + "</w:tbl>"
    )


def build_document_xml():
    body_parts = []
    for kind, text in BLOCKS:
        if kind == "title":
            body_parts.append(make_paragraph(text, "Title"))
        elif kind == "subtitle":
            body_parts.append(make_paragraph(text, "Subtitle"))
        elif kind == "h1":
            body_parts.append(make_paragraph(text, "Heading1"))
        elif kind == "h2":
            body_parts.append(make_paragraph(text, "Heading2"))
        elif kind == "bullet":
            body_parts.append(make_paragraph("- " + text, "Normal"))
        elif kind == "table":
            body_parts.append(make_table(text))
        else:
            body_parts.append(make_paragraph(text, "Normal"))

    sect_pr = (
        "<w:sectPr>"
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/>'
        "</w:sectPr>"
    )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document '
        'xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:w10="urn:schemas-microsoft-com:office:word" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
        'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
        'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
        'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
        'mc:Ignorable="w14 wp14">'
        "<w:body>"
        + "".join(body_parts)
        + sect_pr
        + "</w:body></w:document>"
    )


STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
        <w:sz w:val="22"/>
        <w:szCs w:val="22"/>
        <w:lang w:val="en-US"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:after="120"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
      <w:sz w:val="22"/>
      <w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:before="120" w:after="120"/>
    </w:pPr>
    <w:rPr>
      <w:b/>
      <w:sz w:val="34"/>
      <w:szCs w:val="34"/>
      <w:color w:val="1F1F1F"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:i/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:color w:val="5A5A5A"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:before="240" w:after="60"/>
    </w:pPr>
    <w:rPr>
      <w:b/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
      <w:color w:val="2F5496"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:before="120" w:after="20"/>
    </w:pPr>
    <w:rPr>
      <w:b/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:color w:val="404040"/>
    </w:rPr>
  </w:style>
</w:styles>
"""


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


DOC_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""


CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>GEOS456 Capstone Project V9 High-Level Documentation</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">2026-04-16T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-04-16T00:00:00Z</dcterms:modified>
</cp:coreProperties>
"""


APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Office Word</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Title</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>1</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="1" baseType="lpstr">
      <vt:lpstr>Document</vt:lpstr>
    </vt:vector>
  </TitlesOfParts>
  <Company></Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""


def build_docx():
    document_xml = build_document_xml()

    output_path = resolve_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output_path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", RELS_XML)
        zf.writestr("docProps/core.xml", CORE_XML)
        zf.writestr("docProps/app.xml", APP_XML)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/styles.xml", STYLES_XML)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS_XML)

    return output_path


def resolve_output_path():
    if not OUT_PATH.exists():
        return OUT_PATH

    try:
        OUT_PATH.unlink()
        return OUT_PATH
    except PermissionError:
        return OUT_PATH.with_name(
            f"{OUT_PATH.stem}_UPDATED{OUT_PATH.suffix}"
        )


if __name__ == "__main__":
    final_path = build_docx()
    print(final_path)
    print(f"Size: {final_path.stat().st_size} bytes")
