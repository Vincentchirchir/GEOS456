import arcpy
import time


# ─────────────────────────────────────────────────────────────────────────────
# PAGE LAYOUT STRUCTURE  (Tabloid 17 x 11 inches)
#
#  11.00"  ┬ top of page
#  10.50"  ├ top of TOP stationing band        (band_top_upper)
#   9.50"  ├ bottom of TOP stationing band     (band_bottom_upper)
#           │   = top of main map frame
#   2.67"  ├ bottom of main map frame
#           │   = top of BOTTOM stationing band (band_top_lower)
#   1.67"  ├ bottom of BOTTOM stationing band  (band_bottom_lower)
#   0.00"  ┴ bottom of page
#           │   Legend, Mini Map, Project Info, Tables occupy 0 – 1.67"
#
# Both bands are 1 inch tall.
# Top band holds Bars 1-3.
# Bottom band holds Bars 4-6.  Labels alternate between Bar 5 and Bar 6 rows.
# ─────────────────────────────────────────────────────────────────────────────

# Page proportions — all positions expressed as fractions of page dimensions
# so the layout scales correctly across different page sizes.

# Top stationing band occupies the top 1" of the page
# On an 11" page:  10.50" / 11" = 0.9545,  9.50" / 11" = 0.8636
BAND_TOP_UPPER_FRAC = 10.50 / 11.0  # top edge of upper stationing band
BAND_BOTTOM_UPPER_FRAC = 9.50 / 11.0  # bottom edge of upper stationing band

# Main map frame sits between the two bands
# Top of map = bottom of upper band = 9.50" / 11" = 0.8636
# Bottom of map = top of lower band = 2.67" / 11" = 0.2427
MAP_TOP_FRAC = BAND_BOTTOM_UPPER_FRAC  # 9.50" / 11"
MAP_BOTTOM_FRAC = 2.67 / 11.0  # 2.67" / 11"

# Bottom stationing band occupies 1" just above the bottom elements
# On an 11" page:  2.67" / 11" = 0.2427,  1.67" / 11" = 0.1518
BAND_TOP_LOWER_FRAC = MAP_BOTTOM_FRAC  # 2.67" / 11"
BAND_BOTTOM_LOWER_FRAC = 1.67 / 11.0  # 1.67" / 11"

# Bottom elements (Legend, Tables, Project Info) occupy 0 to 1.67"
BOTTOM_ELEMENTS_TOP_FRAC = BAND_BOTTOM_LOWER_FRAC  # 1.67" / 11"

# ── Bar row fractions within the TOP band (9.50" to 10.50") ──────────────────
# Each bar is roughly 0.2" tall with a small gap between bars.
# Positions expressed as fractions of page height.
TOP_BAR1_TOP_FRAC = 10.30 / 11.0
TOP_BAR1_BOTTOM_FRAC = 10.10 / 11.0

TOP_BAR2_TOP_FRAC = 9.90 / 11.0
TOP_BAR2_BOTTOM_FRAC = 9.70 / 11.0

TOP_BAR3_TOP_FRAC = 9.68 / 11.0
TOP_BAR3_BOTTOM_FRAC = 9.50 / 11.0

# ── Bar row fractions within the BOTTOM band (1.67" to 2.67") ────────────────
BOT_BAR4_TOP_FRAC = 2.50 / 11.0
BOT_BAR4_BOTTOM_FRAC = 2.30 / 11.0

BOT_BAR5_TOP_FRAC = 2.28 / 11.0
BOT_BAR5_BOTTOM_FRAC = 2.08 / 11.0

BOT_BAR6_TOP_FRAC = 1.85 / 11.0
BOT_BAR6_BOTTOM_FRAC = 1.67 / 11.0


def add_north_arrow(project, layout, map_frame, width, height):
    """
    Adds a north arrow to the layout at a proportional position.
    Position is scaled to the page size so it works on any paper format.
    """
    north_arrow_location = arcpy.Point(
        width * 0.9247818181818180,
        height * 0.0404588235294118,
    )

    north_arrow_style = project.listStyleItems(
        "ArcGIS 2D", "North_Arrow", "ArcGIS North 3"
    )[0]

    north_arrow = layout.createMapSurroundElement(
        north_arrow_location, "North_Arrow", map_frame, north_arrow_style, "North Arrow"
    )
    north_arrow.locked = True

    north_arrow.elementWidth = 0.0719 * (width / 11)
    north_arrow.elementHeight = 0.1497 * (height / 8.5)

    return north_arrow


def add_scale_bar(project, layout, map_frame, width, height):
    """
    Adds a metric alternating scale bar to the layout.
    Size and label font are scaled to the page dimensions.
    """
    scale_bar_location = arcpy.Point(
        width * 0.9204636363636360,
        height * 0.0534470588235294,
    )

    scale_bar_style = project.listStyleItems(
        "ArcGIS 2D", "SCALE_BAR", "Alternating Scale Bar 1 Metric"
    )[0]

    scale_bar = layout.createMapSurroundElement(
        scale_bar_location, "SCALE_BAR", map_frame, scale_bar_style, "Scale Bar"
    )

    scale_bar.elementWidth = 0.7725 * (width / 11)
    scale_bar.elementHeight = 0.3148 * (height / 8.5)

    scale_bar_cim = scale_bar.getDefinition("V3")
    scale_bar_cim.unitLabelPosition = "Below"
    scale_bar_cim.divisions = 1
    scale_bar_cim.subdivisions = 3
    scale_bar_cim.fittingStrategy = "AdjustDivision"
    scale_bar_cim.markPosition = "BelowBar"
    scale_bar_cim.unitLabelGap = 3 * (height / 8.5)
    scale_bar_cim.labelSymbol.symbol.height = 4 * (height / 8.5)
    scale_bar_cim.unitLabelSymbol.symbol.height = 4 * (height / 8.5)
    scale_bar.setDefinition(scale_bar_cim)

    return scale_bar


def add_map_scale_text(project, layout, map_frame, width, height):
    """
    Adds a dynamic map scale text element below the scale bar.
    Uses a dynamic tag so the scale updates automatically with the map frame.
    """
    map_scale_location = arcpy.Point(
        width * 0.9489818181818180,
        height * 0.03927058823529414,
    )

    map_scale = project.createTextElement(
        layout,
        map_scale_location,
        "POINT",
        '<dyn type="mapFrame" name="Map Frame" property="scale" preStr="1:"/>',
        4,
    )
    map_scale.name = "Map Scale"
    map_scale.locked = True

    cim = map_scale.getDefinition("V3")
    cim.fontFamilyName = "Tahoma"
    cim.graphic.symbol.symbol.height = 4 * (height / 8.5)
    map_scale.setDefinition(cim)

    return map_scale


def add_standard_texts(project, layout, width, height):
    """
    Adds all standard text labels to the layout — titles, page numbers,
    project info labels, and section headings.

    Locked elements cannot be accidentally moved in the layout view.
    Unlocked elements (Date, Pages) are left editable by the user.

    NOTE: The Stationing label now reads 'Stationing' for both bands —
    it sits on the left margin beside the top stationing band as before.
    """
    locked_texts = []
    unlocked_texts = []

    texts = [
        {
            "text": "Legend",
            "text_x": width * 0.0100636363636364,
            # Adjusted y — bottom elements now end at BOTTOM_ELEMENTS_TOP_FRAC
            "text_y": height * (BOTTOM_ELEMENTS_TOP_FRAC * 0.41),
            "rotation": 90,
            "name": "Legend Text",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Plan View",
            "text_x": width * 0.0100636363636364,
            # Centre of the map frame vertically
            "text_y": height * ((MAP_TOP_FRAC + MAP_BOTTOM_FRAC) / 2),
            "rotation": 90,
            "name": "Plan View",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Stationing",
            "text_x": width * 0.0100636363636364,
            # Centre of the top stationing band
            "text_y": height * ((BAND_TOP_UPPER_FRAC + BAND_BOTTOM_UPPER_FRAC) / 2),
            "rotation": 90,
            "name": "Stationing Top",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Stationing",
            "text_x": width * 0.0100636363636364,
            # Centre of the bottom stationing band
            "text_y": height * ((BAND_TOP_LOWER_FRAC + BAND_BOTTOM_LOWER_FRAC) / 2),
            "rotation": 90,
            "name": "Stationing Bottom",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Project Name",
            "text_x": width * 0.860909090909091,
            "text_y": height * 0.187058823529412,
            "rotation": 0,
            "name": "Project Name",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Project Number",
            "text_x": width * 0.85814545454545500,
            "text_y": height * 0.16167058823529400,
            "rotation": 0,
            "name": "Project Number",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Client",
            "text_x": width * 0.87070909090909100,
            "text_y": height * 0.10138823529411800,
            "rotation": 0,
            "name": "Client",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Date",
            "text_x": width * 0.92413636363636400,
            "text_y": height * 0.00757647058823529,
            "rotation": 0,
            "name": "Date",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Page <dyn type='page' property='index'/> of <dyn type='page' property='count'/>",
            "text_x": width * 0.9640090909090910,
            "text_y": height * 0.007576470588235290,
            "rotation": 0,
            "name": "Pages",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Site Area",
            "text_x": width * 0.39314545454545500,
            "text_y": height * 0.18712941176470600,
            "rotation": 0,
            "name": "Site Area",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Summary Table",
            "text_x": width * 0.52360909090909100,
            "text_y": height * 0.18716470588235300,
            "rotation": 0,
            "name": "Summary Table",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Intersection Table Title",
            "text_x": width * 0.665454545454546,
            "text_y": height * 0.187058823529412,
            "rotation": 0,
            "name": "Intersection Table",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
    ]

    for title in texts:
        location = arcpy.Point(title["text_x"], title["text_y"])

        text_element = project.createTextElement(
            layout,
            location,
            "POINT",
            title["text"],
            title["font_size"],
        )

        text_element.elementRotation = title["rotation"]
        text_element.name = title["name"]

        cim = None
        for _ in range(2):
            try:
                cim = text_element.getDefinition("V3")
                if cim:
                    break
            except:
                time.sleep(0.1)

        if cim:
            cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
            cim.graphic.symbol.symbol.fontStyleName = title["font_style"]
            cim.graphic.symbol.symbol.underline = title["underline"]
            cim.graphic.symbol.symbol.height = title["font_size"] * (height / 8.5)
            cim.locked = title["locked"]
            text_element.setDefinition(cim)

        if title["locked"]:
            locked_texts.append(text_element)
        else:
            unlocked_texts.append(text_element)

    # Lock and unlock elements individually
    for text_element in locked_texts:
        try:
            text_element.locked = True
        except:
            pass

    for text_element in unlocked_texts:
        try:
            text_element.locked = False
        except:
            pass


def add_boundary_graphics(project, layout, width, height):
    """
    Draws all boundary box polygons on the layout.

    Structure after update:
        - Top stationing band  : 9.50" to 10.50"  (3 bars)
        - Plan View            : 2.67" to 9.50"
        - Bottom stationing band: 1.67" to 2.67"  (3 bars, labels between bars 5 and 6)
        - Bottom elements      : 0" to 1.67"  (Legend, Tables, Project Info — unchanged)

    All x positions are unchanged — only y positions for the stationing
    and plan view borders have been adjusted.
    """
    grouping_polygons = []

    boundaries = [
        # ── Bottom element boxes — UNCHANGED ────────────────────────────────
        {
            "polygon_name": "Intersection Table",
            "x_min_poly": width * 0.60580000000000000,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.77154545454545500,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5,
        },
        {
            "polygon_name": "Summary Table Title",
            "x_min_poly": width * 0.48090909090909100,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.60580000000000000,
            "y_max_poly": height * 0.19767058823529400,
            "outline": 0.5,
        },
        {
            "polygon_name": "Legend",
            "x_min_poly": width * 0.011818181818182,
            "y_min_poly": 0,
            "x_max_poly": width * 0.325454545454545,
            "y_max_poly": height * 0.197647058823529,
            "outline": 0.5,
        },
        {
            "polygon_name": "Mini Map Border",
            "x_min_poly": width * 0.32545454545454500,
            "y_min_poly": 0,
            "x_max_poly": width * 0.48090909090909100,
            "y_max_poly": height * 0.18443529411764700,
            "outline": 0.5,
        },
        {
            "polygon_name": "Project Info Border",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": 0,
            "x_max_poly": width,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5,
        },
        {
            "polygon_name": "Site Area Title",
            "x_min_poly": width * 0.32545454545454500,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.48090909090909100,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5,
        },
        {
            "polygon_name": "Project Name Box",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.1714941176470590,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1976470588235290,
            "outline": 0.5,
        },
        {
            "polygon_name": "Project Number Box",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.1452235294117650,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1715058823529410,
            "outline": 0.5,
        },
        {
            "polygon_name": "Location Address Box",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.1133294117647060,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1452235294117650,
            "outline": 0.5,
        },
        {
            "polygon_name": "Client Box",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1133294117647060,
            "outline": 0.5,
        },
        {
            "polygon_name": "Notes Box",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": 0,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.0809058823529412,
            "outline": 0.5,
        },
        {
            "polygon_name": "Names Box",
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.0943058823529412,
            "x_max_poly": width,
            "y_max_poly": height * 0.1452235294117650,
            "outline": 0.5,
        },
        {
            "polygon_name": "Coordinate System Box",
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.0230588235294118,
            "x_max_poly": width,
            "y_max_poly": height * 0.0943058823529412,
            "outline": 0.5,
        },
        {
            "polygon_name": "Date Box",
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": 0,
            "x_max_poly": width * 0.9589090909090910,
            "y_max_poly": height * 0.0230470588235294,
            "outline": 0.5,
        },
        {
            "polygon_name": "Page Box",
            "x_min_poly": width * 0.9589090909090910,
            "y_min_poly": 0,
            "x_max_poly": width,
            "y_max_poly": height * 0.0230470588235294,
            "outline": 0.5,
        },
        # ── Plan View border — y adjusted to sit between the two bands ───────
        {
            "polygon_name": "Plan View Border",
            "x_min_poly": 0,
            # Bottom of plan view = top of bottom stationing band
            "y_min_poly": height * BAND_TOP_LOWER_FRAC,
            "x_max_poly": width,
            # Top of plan view = bottom of top stationing band
            "y_max_poly": height * BAND_BOTTOM_UPPER_FRAC,
            "outline": 0.5,
        },
        # ── TOP stationing band border ────────────────────────────────────────
        {
            "polygon_name": "Top Stationing Border",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * BAND_BOTTOM_UPPER_FRAC,  # 9.50" / 11"
            "x_max_poly": width,
            "y_max_poly": height * BAND_TOP_UPPER_FRAC,  # 10.50" / 11"
            "outline": 0.5,
        },
        # ── TOP band — 3 bar rows ─────────────────────────────────────────────
        {
            "polygon_name": "Top Stationing Bar 1",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * TOP_BAR1_BOTTOM_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * TOP_BAR1_TOP_FRAC,
            "outline": 0.25,
        },
        {
            "polygon_name": "Top Stationing Bar 2",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * TOP_BAR2_BOTTOM_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * TOP_BAR2_TOP_FRAC,
            "outline": 0.25,
        },
        {
            "polygon_name": "Top Stationing Bar 3",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * TOP_BAR3_BOTTOM_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * TOP_BAR3_TOP_FRAC,
            "outline": 0.25,
        },
        # ── BOTTOM stationing band border ─────────────────────────────────────
        {
            "polygon_name": "Bottom Stationing Border",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * BAND_BOTTOM_LOWER_FRAC,  # 1.67" / 11"
            "x_max_poly": width,
            "y_max_poly": height * BAND_TOP_LOWER_FRAC,  # 2.67" / 11"
            "outline": 0.5,
        },
        # ── BOTTOM band — 3 bar rows ──────────────────────────────────────────
        {
            "polygon_name": "Bottom Stationing Bar 4",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * BOT_BAR4_BOTTOM_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * BOT_BAR4_TOP_FRAC,
            "outline": 0.25,
        },
        {
            "polygon_name": "Bottom Stationing Bar 5",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * BOT_BAR5_BOTTOM_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * BOT_BAR5_TOP_FRAC,
            "outline": 0.25,
        },
        {
            "polygon_name": "Bottom Stationing Bar 6",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * BOT_BAR6_BOTTOM_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * BOT_BAR6_TOP_FRAC,
            "outline": 0.25,
        },
    ]

    for boundary in boundaries:
        poly_blc = arcpy.Point(boundary["x_min_poly"], boundary["y_min_poly"])
        poly_tlc = arcpy.Point(boundary["x_min_poly"], boundary["y_max_poly"])
        poly_trc = arcpy.Point(boundary["x_max_poly"], boundary["y_max_poly"])
        poly_brc = arcpy.Point(boundary["x_max_poly"], boundary["y_min_poly"])

        poly_array = arcpy.Array([poly_blc, poly_tlc, poly_trc, poly_brc, poly_blc])
        poly_extent = arcpy.Polygon(poly_array)

        poly_style = project.listStyleItems(
            "ArcGIS 2D", "Polygon", "Black Outline (1pt)"
        )[0]

        poly = project.createGraphicElement(
            layout, poly_extent, poly_style, name=boundary["polygon_name"]
        )

        # Apply the outline weight defined per boundary
        poly_cim = poly.getDefinition("V3")
        poly_cim.graphic.symbol.symbol.symbolLayers[0].width = boundary["outline"]
        poly.setDefinition(poly_cim)

        grouping_polygons.append(poly)

    # Group all boundary polygons and lock them so they cannot be
    # accidentally moved or deleted in the layout view
    if grouping_polygons:
        group_polygons = project.createGroupElement(
            layout, grouping_polygons, "DO NOT TOUCH (Boundaries)"
        )
        group_cim = group_polygons.getDefinition("V3")
        group_cim.locked = True
        group_polygons.setDefinition(group_cim)
