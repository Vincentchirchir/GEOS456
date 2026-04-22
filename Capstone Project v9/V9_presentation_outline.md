# GEOS456 Capstone Project V9 Presentation Outline

## Title
**GEOS456 Capstone Project V9: Automated Alignment Sheets in ArcGIS Pro**

Suggested subtitle:
**Linear Referencing, Layout Automation, and Page-Aware PDF Export**

## Slide 1 - Title Slide
- Project title
- Course and group/member names
- Date
- Full-page visual: final alignment sheet export or ArcGIS Pro layout screenshot

Speaker focus:
- Introduce V9 as an ArcGIS Pro Python toolbox built to automate alignment sheet production from a linear feature.

## Slide 2 - Project Rationale
- Alignment sheets are used to communicate route position, stationing, crossings, overlaps, and surrounding context in a reviewable page-by-page format.
- Producing those sheets manually requires repeated GIS editing, label cleanup, and page export work.
- V9 matters because it reduces repetitive production work and improves consistency across deliverables.

Suggested visual:
- A simple before/after workflow graphic:
  - Manual process: route prep -> stationing -> intersections -> layout edits -> export cleanup
  - V9 process: one tool-driven workflow -> standardized outputs

## Slide 3 - Problem Statement
- The problem is not just making a map.
- The real problem is producing consistent, route-based alignment sheets that require:
  - measured routes
  - stationing
  - crossing and overlap analysis
  - custom station-band graphics
  - auto-filled text
  - page-aware export behavior
- Native ArcGIS Pro tools handle part of this process, but shared custom layout graphics do not automatically update correctly across map series pages.
- Without automation, repeated runs can create stale labels, duplicate text, and inconsistent sheet exports.

Suggested visual:
- Problem diagram showing where manual failure points happen.

## Slide 4 - Project-Specific Geospatial Technology
- V9 uses **linear referencing** because events need to be located by distance along a route, not only by x-y position.
- The project uses ArcGIS Pro tools and concepts directly tied to the workflow:
  - **Create Routes** to build an M-enabled route
  - **Generate Points Along Lines** to create regular stations
  - **Locate Features Along Routes** to convert crossings and overlaps into route-based event tables
  - **Spatial map series** to generate page extents
  - **Reverse geocoding** to support readable title-block labels
- These are not generic GIS ideas in this project; they are the foundation of the automation pipeline.

Suggested visual:
- Architecture diagram:
  - input route -> M-enabled route -> stations + events -> layout -> map series -> PDF

## Slide 5 - Project Scope, Objectives, and Goals
- Scope:
  - ArcGIS Pro and ArcPy only
  - one input polyline route
  - optional point, line, and polygon analysis layers
  - layout creation
  - map series generation
  - PDF export
- Objectives:
  - Create a reliable M-enabled route and stationing system.
  - Detect and locate crossings and overlaps from optional context layers.
  - Build a repeatable layout with station bands, metadata, and export-ready content.
  - Keep the main map, mini map, and exported sheets synchronized.
- Goal:
  - Turn one route and optional context layers into a repeatable, client-ready alignment sheet package.

Suggested visual:
- Four-phase project plan graphic:
  - route creation
  - event analysis
  - layout automation
  - export

## Slide 6 - Data Captured and Data Management
- Input data:
  - source polyline route
  - optional overlapping or intersecting analysis layers
  - current ArcGIS Pro maps
  - project geodatabase
- Persistent outputs:
  - `{base}_Route`
  - `{base}_Stations`
  - `{layer}_Intersections`
  - `{layer}_Overlaps`
  - `{layer}_OverlapsTable`
  - `{input}_MapIndex`
- Temporary data:
  - copied route geometry
  - dissolved route geometry
  - clipped route segments
  - in-memory event tables
  - temporary overlap features
  - page redraw graphics used during export
- Data management strategy:
  - preserve the source data
  - separate retained outputs from temporary processing layers

Suggested visuals:
- One map showing the route and context layers
- One data lifecycle graphic showing inputs, temporary products, and retained outputs

## Slide 7 - Methodology: How the Workflow Was Designed
- The methodology was determined by the needs of linear infrastructure mapping.
- The project required route events, chainage labels, crossings, and overlaps to be stored and displayed by measure.
- ArcGIS Pro documentation supported the design choices for:
  - route creation
  - station generation
  - route event location
  - map series behavior
  - reverse geocoding
- The workflow design was shaped both by formal tool capabilities and by practical problems encountered during development.

Suggested visual:
- Research-to-design table with two columns:
  - ArcGIS concept/tool
  - How V9 uses it

## Slide 8 - Brief Review of Research
- **Create Routes** supports building routes from existing lines and assigning measures along them.
- **Generate Points Along Lines** supports fixed-interval point generation for stationing.
- **Locate Features Along Routes** writes route and measure information into event tables for crossings and overlaps.
- **Map series** supports feature-driven page extents, but shared graphics remain static unless separately managed.
- **Reverse geocoding** supports converting route locations into readable place or address labels.

Suggested visual:
- Five small callouts, one per source/tool, tied to a V9 component

## Slide 9 - Methodology Part 1: Route Creation and Stationing
- Copy the selected input line so the source dataset is not modified.
- Dissolve the line if needed so route creation runs on a simplified geometry.
- Create an M-enabled route.
- Generate points at the requested station interval.
- Remove duplicate end stations when needed.
- Join formatted chainage values back to the station points.

Suggested visuals:
- Input route map
- Dissolved route map
- Station point output map with chainage labels

## Slide 10 - Methodology Part 2: Crossings and Overlaps
- Intersect optional analysis layers with the route.
- Separate point crossings from line or polygon overlaps.
- Split multipoint intersection outputs so each crossing keeps its own geometry and measure.
- Use route event logic to store:
  - `MEAS` for point events
  - `FMEAS` and `TMEAS` for line events
- Convert route events back into usable feature classes for display and labeling.

Suggested visuals:
- Crossing map example
- Overlap map example
- Simplified event table diagram

## Slide 11 - Methodology Part 3: Layout Automation
- Build an alignment-sheet layout with:
  - main map
  - mini map
  - stationing bands
  - legend
  - scale information
  - title block
  - editable text elements
- Auto-populate text such as:
  - route name
  - station range
  - total length
  - coordinate system
  - from/to coordinates
  - page-specific intersection table values
- Use proportional layout positioning so the design can scale across page sizes.

Suggested visual:
- Annotated screenshot of the layout with labeled components

## Slide 12 - Methodology Part 4: Map Series and PDF Export
- Create strip-map index polygons for page extents.
- Use a spatial map series for page navigation and extent control.
- Redraw page-specific layout graphics before exporting each page.
- Export one page at a time.
- Merge the individual PDFs into a final deliverable.
- Reset the layout to a neutral route-wide state after export.

Why this matters:
- Shared graphics are not inherently page-aware, so V9 had to control export as a sequence, not as a single native export click.

Suggested visual:
- Page export sequence diagram:
  - set page -> redraw graphics -> export PDF -> merge

## Slide 13 - Results
- V9 produces a complete workflow from input route to final sheet deliverables.
- Key generated outputs include:
  - measured route
  - station points
  - intersection outputs
  - overlap outputs
  - map index polygons
  - layout
  - page PDFs
  - merged PDF
- The project also solved important workflow issues:
  - duplicate end stations
  - multipoint crossings
  - mini-map clutter
  - stale page graphics during export

Suggested visuals:
- Gallery of output maps and final sheets

## Slide 14 - So What: Impact and Value
- The workflow reduces manual drafting and repeated cleanup.
- It improves consistency in station labels, event outputs, and sheet structure.
- It creates a more reliable export workflow for page-specific cartographic content.
- It is relevant to real linear infrastructure mapping problems such as roadway, utility, corridor, or pipeline documentation.
- Organizational value:
  - more repeatable deliverables
  - less manual correction
  - better quality control

Suggested visual:
- Value slide with four impact blocks:
  - time savings
  - consistency
  - export reliability
  - reusable workflow

## Slide 15 - Conclusion
- V9 met the main project objectives by automating:
  - route creation
  - stationing
  - event analysis
  - layout assembly
  - synchronized export
- The project shows how GIS can support both geospatial analysis and production cartography in one workflow.
- The strongest final outcome is a usable end-to-end process for creating alignment sheet deliverables from a selected route.

Suggested visual:
- Input-to-output recap graphic

## Slide 16 - Recommendations and Reflection
- If repeating the project, the team should:
  - strengthen validation earlier
  - formalize configuration profiles
  - improve logging and run summaries
- With more time and resources, the next version should:
  - finish the disabled intersection summary panel
  - expand metadata inputs
  - add regression tests for export and event handling
- A future student group should examine:
  - configuration management
  - edge-case testing
  - separation of export logic from layout creation

Suggested visual:
- Roadmap with short-term, medium-term, and next-team recommendations

## Slide 17 - References
Use in-text citations throughout the deck, then finish with a full APA slide.

Recommended references:

1. Esri. (n.d.). *Create Routes (Linear Referencing).* ArcGIS Pro documentation. https://pro.arcgis.com/en/pro-app/3.5/tool-reference/linear-referencing/create-routes.htm
2. Esri. (n.d.). *Generate Points Along Lines (Data Management).* ArcGIS Pro documentation. https://pro.arcgis.com/en/pro-app/3.6/tool-reference/data-management/generate-points-along-lines.htm
3. Esri. (n.d.). *Locate Features Along Routes (Linear Referencing).* ArcGIS Pro documentation. https://pro.arcgis.com/en/pro-app/3.3/tool-reference/linear-referencing/locate-features-along-routes.htm
4. Esri. (n.d.). *Map series.* ArcGIS Pro documentation. https://pro.arcgis.com/en/pro-app/latest/help/layouts/map-series.htm
5. Esri. (n.d.). *Fundamentals of reverse geocoding.* ArcGIS Pro documentation. https://pro.arcgis.com/en/pro-app/latest/help/data/geocoding/fundamentals-of-reverse-geocoding.htm
6. GEOS456 Capstone Project V9 high-level documentation. (2026, April 16). Unpublished internal project documentation.

## Suggested In-Text Citation Examples
- Linear referencing was used so events could be stored by measure along the route rather than only by map position (Esri, n.d.).
- Page extents were supported with a spatial map series, but page-specific graphics required custom redraw logic before export (Esri, n.d.).
- Reverse geocoding was used to support readable title-block location labels where a useful match was available (Esri, n.d.).

## Visual Checklist
- Use maps on the data slide, methodology slides, and results slide.
- Use one annotated layout screenshot.
- Use one workflow diagram.
- Use one export sequence diagram.
- Use one impact/value summary graphic.
- Avoid text-heavy slides; keep the detail in speaker notes.

## Best Order for a Live Talk
1. Why this matters
2. What problem we solved
3. What GIS technology made it possible
4. What data and workflow we used
5. What we built
6. What results and value came out of it
7. What should happen next

