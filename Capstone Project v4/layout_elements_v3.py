import arcpy
import time

# Both bands are 1 inch tall.
# Top band holds 3 horizontal bar LINES.
# Bottom band holds 3 horizontal bar LINES.
# Bar lines are single horizontal lines — NOT polygons — so they cannot
# double up on reruns the way polygon top/bottom edge pairs do.
# Page proportions — all positions expressed as fractions of page height
# so the layout scales correctly across different page sizes.
# Top stationing band — top 1" of the page
BAND_TOP_UPPER_FRAC = 10.50 / 11.0  # top edge of upper stationing band
BAND_BOTTOM_UPPER_FRAC = 9.50 / 11.0  # bottom edge of upper stationing band

# Main map frame sits between the two bands
MAP_TOP_FRAC = BAND_BOTTOM_UPPER_FRAC  # 9.50" / 11"
MAP_BOTTOM_FRAC = 3.17 / 11.0  # 3.17" / 11"

# Bottom stationing band — 1" just above the bottom elements
BAND_TOP_LOWER_FRAC = MAP_BOTTOM_FRAC  # 3.17" / 11"
BAND_BOTTOM_LOWER_FRAC = 2.17 / 11.0  # 2.17" / 11"

# Bottom elements (Legend, Tables, Project Info) occupy 0 to 2.17"
BOTTOM_ELEMENTS_TOP_FRAC = BAND_BOTTOM_LOWER_FRAC

# TOP band bar line positions (single y value per bar)
# Each bar is one horizontal line — no top/bottom pair needed.
# Three lines divide the top band into readable rows.
TOP_BAR1_FRAC = 10.30 / 11.0  # top bar line
TOP_BAR2_FRAC = 9.90 / 11.0  # middle bar line
TOP_BAR3_FRAC = 9.68 / 11.0  # bottom bar line

# BOTTOM band bar line positions
# Labels alternate between the gap above Bar 5 and the gap above Bar 6.
BOT_BAR4_FRAC = 2.60 / 11.0  # top bar line
# BOT_BAR5_FRAC = 2.28 / 11.0  # middle bar line
# BOT_BAR6_FRAC = 1.85 / 11.0  # bottom bar line


def add_legend(project, layout, map_frame, map_name, width, height):
    """
    Adds a map legend to the layout inside the legend boundary box.

    The legend is set to 3 columns with dynamic patch sizes scaled to the
    page dimensions. Layer items are sorted by geometry type (Point →
    Polyline → Polygon → Raster) and only visible features are shown.
    No title, layer names, or headings are shown — keeps the legend clean.

    Parameters
    ----------
    project : arcpy.mp.ArcGISProject
    layout  : arcpy.mp.Layout
    map_frame : arcpy.mp.MapFrame
        The main map frame — legend reflects its layers.
    map_name : str
        Name of the main map — used to sort legend items by layer type.
    width, height : float
        Page dimensions in inches.
    """
    width_ratio = width / 11
    height_ratio = height / 8.5

    legend_location = arcpy.Point(
        width * 0.019090909,
        height * 0.192941176,
    )

    legend_style = project.listStyleItems("ArcGIS 2D", "LEGEND", "Legend 1")[0]

    legend = layout.createMapSurroundElement(
        legend_location, "LEGEND", map_frame, legend_style, "Legend"
    )

    # Keep legend in sync with layer visibility changes
    legend.syncLayerVisibility = True

    # Scale legend size to page dimensions
    legend.elementWidth = 3.314 * width_ratio
    legend.elementHeight = 1.5835 * height_ratio

    # Dynamic patch and font sizes — scaled to page
    dynamic_patch_width = 15 * width_ratio
    dynamic_patch_height = 10 * height_ratio
    dynamic_font_size = 6 * height_ratio

    legend_cim = legend.getDefinition("V3")

    # Hide title and headings — keep the legend compact and clean
    legend_cim.showTitle = False
    legend_cim.fittingStrategy = "AdjustColumnsAndFont"
    legend_cim.columns = 3
    legend_cim.minFontSize = dynamic_font_size
    legend_cim.defaultPatchWidth = dynamic_patch_width
    legend_cim.defaultPatchHeight = dynamic_patch_height
    legend_cim.useMapSeriesShape = True

    # Apply item settings — show only visible features, hide layer names
    for item in legend_cim.items:
        item.showVisibleFeaturesOnly = True
        item.showLayerName = False
        item.showHeading = False
        item.showGroupLayerName = False
        item.patchWidth = dynamic_patch_width
        item.patchHeight = dynamic_patch_height

        # Scale label font size
        label_sym = getattr(item, "labelSymbol", None)
        if label_sym is not None:
            label_sym.symbol.height = dynamic_font_size

    # Sort legend items: Point → Polyline → Polygon → Raster
    geometry_order = {"Point": 1, "Polyline": 2, "Polygon": 3, "RasterLayer": 4}

    try:
        targeted_map = project.listMaps(map_name)[0]

        def sort_key(item):
            try:
                layers = targeted_map.listLayers(item.name)
                if not layers:
                    return 99
                layer = layers[0]
                if layer.isFeatureLayer:
                    shape = arcpy.Describe(layer.dataSource).shapeType
                    return geometry_order.get(shape, 3)
                if layer.isRasterLayer:
                    return 4
                return 99
            except:
                return 99

        if legend_cim.items:
            legend_cim.items = sorted(legend_cim.items, key=sort_key)

    except Exception as e:
        arcpy.AddWarning(f"Could not sort legend items: {e}")

    legend.setDefinition(legend_cim)
    return legend


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


# Text Elements


def add_standard_texts(project, layout, width, height):
    """
    Adds all standard text labels to the layout.

    Texts are split into two groups:
      - Locked   → grouped as "DO NOT TOUCH (Text)" — cannot be moved accidentally
      - Unlocked → grouped as "Editable Text" — user fills these in

    Includes section headings, project info labels, table column headers,
    summary table data fields, company info, and page/date elements.
    Two Stationing labels are created — one for the top band, one for the bottom.
    """
    locked_texts = []
    unlocked_texts = []

    texts = [
        #  Section headings (rotated, left margin)
        {
            "text": "Legend",
            "text_x": width * 0.0100636363636364,
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
            "text_y": height * ((BAND_TOP_LOWER_FRAC + BAND_BOTTOM_LOWER_FRAC) / 2),
            "rotation": 90,
            "name": "Stationing Bottom",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        # Table section titles
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
            "text": "Intersection Table",
            "text_x": width * 0.665454545454546,
            "text_y": height * 0.187058823529412,
            "rotation": 0,
            "name": "Intersection Table",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Intersection Summary",
            "text_x": width * 0.778181818181818,
            "text_y": height * 0.187058823529412,
            "rotation": 0,
            "name": "Intersection Summary",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        # Intersection table column headers
        {
            "text": "ID",
            "text_x": width * 0.63047272727272700,
            "text_y": height * 0.1728,
            "rotation": 0,
            "name": "Point ID",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Stationing",
            "text_x": width * 0.67589090909090900,
            "text_y": height * 0.1728,
            "rotation": 0,
            "name": "Stationing Info",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Type",
            "text_x": width * 0.73805454545454600,
            "text_y": height * 0.1728,
            "rotation": 0,
            "name": "Intersection Type",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
        # Project info labels (underlined headers)
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
            "text": "Location Address",
            "text_x": width * 0.85640909090909100,
            "text_y": height * 0.13356470588235300,
            "rotation": 0,
            "name": "Location Address",
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
            "text": "Notes",
            "text_x": width * 0.87080909090909100,
            "text_y": height * 0.06797647058823530,
            "rotation": 0,
            "name": "Notes",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Data Sources",
            "text_x": width * 0.78954545454545500,
            "text_y": height * 0.06797647058823530,
            "rotation": 0,
            "name": "Data Sources",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True,
        },
        {
            "text": "Disclaimer",
            "text_x": width * 0.52998181818181800,
            "text_y": height * 0.04317647058823530,
            "rotation": 0,
            "name": "Disclaimer",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True,
        },
        # Summary table data fields (editable)
        {
            "text": "Pipe Name",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1740235294117650,
            "rotation": 0,
            "name": "Pipe Name",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Starting Station: <>",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1610941176470590,
            "rotation": 0,
            "name": "Starting Station",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Ending Station: <>",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1481647058823530,
            "rotation": 0,
            "name": "Ending Station",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Total Length: <>",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1352235294117650,
            "rotation": 0,
            "name": "Total Length",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "From:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1222941176470590,
            "rotation": 0,
            "name": "From",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "To:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1093529411764710,
            "rotation": 0,
            "name": "To",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Diameter:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.0964235294117647,
            "rotation": 0,
            "name": "Diameter",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Material:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.0834352941176471,
            "rotation": 0,
            "name": "Material",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Type:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.0704941176470588,
            "rotation": 0,
            "name": "Type",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Company:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.0575647058823529,
            "rotation": 0,
            "name": "Company",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        # Company / names box (editable)
        {
            "text": "Company Logo",
            "text_x": width * 0.9258000000000000,
            "text_y": height * 0.1644117647058820,
            "rotation": 0,
            "name": "Company Logo",
            "font_size": 8,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Completed By:",
            "text_x": width * 0.92046363636363600,
            "text_y": height * 0.13342352941176500,
            "rotation": 0,
            "name": "Completed By",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Reviewed By:",
            "text_x": width * 0.92046363636363600,
            "text_y": height * 0.11680000000000000,
            "rotation": 0,
            "name": "Reviewed By",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Signed By:",
            "text_x": width * 0.92046363636363600,
            "text_y": height * 0.10018823529411800,
            "rotation": 0,
            "name": "Signed By",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "Coordinate System",
            "text_x": width * 0.94052727272727300,
            "text_y": height * 0.02751764705882350,
            "rotation": 0,
            "name": "Coordinate System",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        # Intersection Table row text elements (auto-populated)
        # Sit inside each intersection table row box.
        # Named "Intersection Row 1" through "Intersection Row 8".
        # Filled automatically by auto_populate_layout().
        {
            "text": "",
            "text_x": width * 0.6100,
            "text_y": height * 0.1660,
            "rotation": 0,
            "name": "Intersection Row 1",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "",
            "text_x": width * 0.6100,
            "text_y": height * 0.1414,
            "rotation": 0,
            "name": "Intersection Row 2",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "",
            "text_x": width * 0.6100,
            "text_y": height * 0.1168,
            "rotation": 0,
            "name": "Intersection Row 3",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "",
            "text_x": width * 0.6100,
            "text_y": height * 0.1045,
            "rotation": 0,
            "name": "Intersection Row 4",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "",
            "text_x": width * 0.6100,
            "text_y": height * 0.0799,
            "rotation": 0,
            "name": "Intersection Row 5",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "",
            "text_x": width * 0.6100,
            "text_y": height * 0.0553,
            "rotation": 0,
            "name": "Intersection Row 6",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "",
            "text_x": width * 0.6100,
            "text_y": height * 0.0307,
            "rotation": 0,
            "name": "Intersection Row 7",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        {
            "text": "",
            "text_x": width * 0.6100,
            "text_y": height * 0.0184,
            "rotation": 0,
            "name": "Intersection Row 8",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False,
        },
        # Date and page (editable)
        {
            "text": "CURRENT DATE",
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

        # Retry CIM access — occasionally needed on first creation
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

    # Apply lock state individually — grouping is not used for text elements
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

    # Intersection Summary row text elements — created outside the locked/unlocked
    # groups so that layout.listElements() can find them directly by name.
    # Initialized with " " (space) so ArcPy registers the element.
    # Filled automatically by auto_populate_layout().
    summary_row_texts = [
        {
            "text": " ",
            "text_x": width * 0.7730,
            "text_y": height * 0.1650,
            "name": "Intersection Summary Row 1",
            "font_size": 3,
        },
        {
            "text": " ",
            "text_x": width * 0.7730,
            "text_y": height * 0.1380,
            "name": "Intersection Summary Row 2",
            "font_size": 3,
        },
        {
            "text": " ",
            "text_x": width * 0.7730,
            "text_y": height * 0.1110,
            "name": "Intersection Summary Row 3",
            "font_size": 3,
        },
        {
            "text": " ",
            "text_x": width * 0.7730,
            "text_y": height * 0.0850,
            "name": "Intersection Summary Row 4",
            "font_size": 3,
        },
    ]

    for row in summary_row_texts:
        location = arcpy.Point(row["text_x"], row["text_y"])
        text_element = project.createTextElement(
            layout,
            location,
            "POINT",
            row["text"],
            row["font_size"],
        )
        text_element.name = row["name"]

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
            cim.graphic.symbol.symbol.fontStyleName = "Regular"
            cim.graphic.symbol.symbol.underline = False
            cim.graphic.symbol.symbol.height = row["font_size"] * (height / 8.5)
            cim.locked = False
            text_element.setDefinition(cim)


def add_boundary_graphics(project, layout, width, height):
    """
    Draws all boundary boxes and stationing bar lines on the layout.

    CLEANUP ON RERUN:
        The boundary group is deleted at the start so reruns do not stack
        duplicate elements. The group is named "DO NOT TOUCH (Boundaries)".

    Layout structure:
        Top stationing band   (9.50" to 10.50") — outer border + 3 bar LINES
        Plan View border      (2.67" to 9.50")
        Bottom stationing band (1.67" to 2.67") — outer border + 3 bar LINES
        Bottom elements       (0" to 1.67")     — all polygon boxes unchanged

    Stationing bars are LINES not polygons — one element per bar means
    nothing doubles up when the tool reruns.
    """

    # Delete existing boundary group before redrawing
    for el in layout.listElements():
        if el.name == "DO NOT TOUCH (Boundaries)":
            el.delete()
            break

    grouping_elements = []

    # Polygon boundary boxes
    boundaries = [
        # Intersection Table row divider column
        {
            "polygon_name": "Intersection Table Row Divider",
            "x_min_poly": width * 0.6612818181818180,
            "y_min_poly": 0,
            "x_max_poly": width * 0.7167363636363640,
            "y_max_poly": height * 0.1844352941176470,
            "outline": 0.25,
        },
        # ─Left margin section label boxes
        {
            "polygon_name": "Legend Title Box",
            "x_min_poly": 0,
            "y_min_poly": 0,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * 0.197647058823529,
            "outline": 0.5,
        },
        {
            "polygon_name": "Plan View Label Box",
            "x_min_poly": 0,
            "y_min_poly": height * BAND_TOP_LOWER_FRAC,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * BAND_BOTTOM_UPPER_FRAC,
            "outline": 0.5,
        },
        {
            "polygon_name": "Top Stationing Label Box",
            "x_min_poly": 0,
            "y_min_poly": height * BAND_BOTTOM_UPPER_FRAC,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * BAND_TOP_UPPER_FRAC,
            "outline": 0.5,
        },
        {
            "polygon_name": "Bottom Stationing Label Box",
            "x_min_poly": 0,
            "y_min_poly": height * BAND_BOTTOM_LOWER_FRAC,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * BAND_TOP_LOWER_FRAC,
            "outline": 0.5,
        },
        #  Legend and Mini Map
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
        # Summary Table
        {
            "polygon_name": "Site Area Title",
            "x_min_poly": width * 0.32545454545454500,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.48090909090909100,
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
            "polygon_name": "Summary Table Row 1",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1585647058823530,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1714941176470590,
            "outline": 0.25,
        },
        {
            "polygon_name": "Summary Table Row 2",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1327058823529410,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1456352941176470,
            "outline": 0.25,
        },
        {
            "polygon_name": "Summary Table Row 3",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1068352941176470,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1197647058823530,
            "outline": 0.25,
        },
        {
            "polygon_name": "Summary Table Row 4",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0939058823529412,
            "outline": 0.25,
        },
        {
            "polygon_name": "Summary Table Row 5",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.0550470588235294,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0679764705882353,
            "outline": 0.25,
        },
        {
            "polygon_name": "Summary Table Features",
            "x_min_poly": width * 0.4912909090909090,
            "y_min_poly": height * 0.0553058823529412,
            "x_max_poly": width * 0.5913545454545450,
            "y_max_poly": height * 0.1823176470588240,
            "outline": 0,
        },
        {
            "polygon_name": "Disclaimer Boundary",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": 0,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0550470588235294,
            "outline": 0.5,
        },
        # Intersection Table
        # Title bar at the very top
        {
            "polygon_name": "Intersection Table Title",
            "x_min_poly": width * 0.6058,
            "y_min_poly": height * 0.1844,
            "x_max_poly": width * 0.7715,
            "y_max_poly": height * 0.1976,
            "outline": 0.5,
        },
        # Column header row — contains ID, Stationing, Type labels
        {
            "polygon_name": "Intersection Table Header Row",
            "x_min_poly": width * 0.6058,
            "y_min_poly": height * 0.1613,
            "x_max_poly": width * 0.7715,
            "y_max_poly": height * 0.1844,
            "outline": 0.5,  # heavier border separates header from data rows
        },
        # Vertical column dividers — span from bottom to top of header row
        {
            "polygon_name": "Intersection Table Col Divider 1",
            "x_min_poly": width * 0.6613,
            "y_min_poly": 0,
            "x_max_poly": width * 0.6613,
            "y_max_poly": height * 0.1844,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Table Col Divider 2",
            "x_min_poly": width * 0.7167,
            "y_min_poly": 0,
            "x_max_poly": width * 0.7167,
            "y_max_poly": height * 0.1844,
            "outline": 0.25,
        },
        # 8 data rows evenly spaced from 0 to 0.1613
        {
            "polygon_name": "Intersection Table Row 1",
            "x_min_poly": width * 0.6058,
            "x_max_poly": width * 0.7715,
            "y_min_poly": height * 0.1411,
            "y_max_poly": height * 0.1613,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Table Row 2",
            "x_min_poly": width * 0.6058,
            "x_max_poly": width * 0.7715,
            "y_min_poly": height * 0.1209,
            "y_max_poly": height * 0.1411,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Table Row 3",
            "x_min_poly": width * 0.6058,
            "x_max_poly": width * 0.7715,
            "y_min_poly": height * 0.1007,
            "y_max_poly": height * 0.1209,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Table Row 4",
            "x_min_poly": width * 0.6058,
            "x_max_poly": width * 0.7715,
            "y_min_poly": height * 0.0805,
            "y_max_poly": height * 0.1007,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Table Row 5",
            "x_min_poly": width * 0.6058,
            "x_max_poly": width * 0.7715,
            "y_min_poly": height * 0.0603,
            "y_max_poly": height * 0.0805,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Table Row 6",
            "x_min_poly": width * 0.6058,
            "x_max_poly": width * 0.7715,
            "y_min_poly": height * 0.0401,
            "y_max_poly": height * 0.0603,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Table Row 7",
            "x_min_poly": width * 0.6058,
            "x_max_poly": width * 0.7715,
            "y_min_poly": height * 0.0199,
            "y_max_poly": height * 0.0401,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Table Row 8",
            "x_min_poly": width * 0.6058,
            "x_max_poly": width * 0.7715,
            "y_min_poly": height * 0.0000,
            "y_max_poly": height * 0.0199,
            "outline": 0.25,
        },
        # Outer border around the entire data area
        {
            "polygon_name": "Intersection Table Border",
            "x_min_poly": width * 0.6058,
            "y_min_poly": 0,
            "x_max_poly": width * 0.7715,
            "y_max_poly": height * 0.1844,
            "outline": 0.5,
        },
        #  Intersection Summary
        {
            "polygon_name": "Intersection Summary Title",
            "x_min_poly": width * 0.77154545454545500,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.84103636363636400,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5,
        },
        {
            "polygon_name": "Intersection Summary Row 1",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1585529411764710,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1714941176470590,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Summary Row 2",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1326352941176470,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1455764705882350,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Summary Row 3",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1068117647058820,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1197647058823530,
            "outline": 0.25,
        },
        {
            "polygon_name": "Intersection Summary Row 4",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.0944000000000000,
            "outline": 0.25,
        },
        {
            "polygon_name": "Data Sources Box",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": 0,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.0809058823529412,
            "outline": 0.5,
        },
        # Project Info
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
        # Company / Names / Logo
        {
            "polygon_name": "Insert Logo Box",
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.1452235294117650,
            "x_max_poly": width,
            "y_max_poly": height * 0.19764705882352900,
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
        # Main borders
        {
            "polygon_name": "Plan View Border",
            "x_min_poly": 0,
            "y_min_poly": height * BAND_TOP_LOWER_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * BAND_BOTTOM_UPPER_FRAC,
            "outline": 0.5,
        },
        {
            "polygon_name": "Top Stationing Border",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * BAND_BOTTOM_UPPER_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * BAND_TOP_UPPER_FRAC,
            "outline": 0.5,
        },
        {
            "polygon_name": "Bottom Stationing Border",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * BAND_BOTTOM_LOWER_FRAC,
            "x_max_poly": width,
            "y_max_poly": height * BAND_TOP_LOWER_FRAC,
            "outline": 0.5,
        },
    ]

    # Draw all polygon boundaries
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

        poly_cim = poly.getDefinition("V3")
        poly_cim.graphic.symbol.symbol.symbolLayers[0].width = boundary["outline"]
        poly.setDefinition(poly_cim)

        grouping_elements.append(poly)

    # Stationing bar lines — 3 top, 3 bottom
    # Each bar is a SINGLE horizontal line spanning the full band width.
    # One element per bar — no top and bottom edge pair — so they cannot
    # double up when the tool reruns.
    bar_lines = [
        # Top band — 3 lines dividing the top stationing band into rows
        {"name": "Top Bar 1", "y_frac": TOP_BAR1_FRAC},
        {"name": "Top Bar 2", "y_frac": TOP_BAR2_FRAC},
        # {"name": "Top Bar 3", "y_frac": TOP_BAR3_FRAC},
        # Bottom band — 3 lines dividing the bottom stationing band into rows
        {"name": "Bottom Bar 4", "y_frac": BOT_BAR4_FRAC},
        # {"name": "Bottom Bar 5", "y_frac": BOT_BAR5_FRAC},
        # {"name": "Bottom Bar 6", "y_frac": BOT_BAR6_FRAC},
    ]

    # Left edge matches the stationing border left edge
    bar_x_left = width * 0.01176363636363640
    bar_x_right = width  # bars span the full page width

    for bar in bar_lines:
        # Compute the y position of this bar line in page inches
        y = height * bar["y_frac"]

        # Build a horizontal polyline at this y position
        bar_geom = arcpy.Polyline(
            arcpy.Array(
                [
                    arcpy.Point(bar_x_left, y),  # left end of the bar line
                    arcpy.Point(bar_x_right, y),  # right end of the bar line
                ]
            )
        )

        # Draw the line element on the layout
        bar_el = project.createGraphicElement(layout, bar_geom, name=bar["name"])

        grouping_elements.append(bar_el)

    # --- Group all elements and lock so nothing can be accidentally moved ----
    # Polygons and bar lines are grouped together under one locked group.
    if grouping_elements:
        group = project.createGroupElement(
            layout, grouping_elements, "DO NOT TOUCH (Boundaries)"
        )
        group_cim = group.getDefinition("V3")
        group_cim.locked = True
        group.setDefinition(group_cim)
