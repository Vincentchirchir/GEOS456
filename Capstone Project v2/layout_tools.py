import arcpy
import os
import time

arcpy.env.overwriteOutput = True

PAGE_SIZES = {
    "Letter (11x8.5)": [11, 8.5],
    "Legal (14x8.5)": [14, 8.5],
    "Tabloid (17x11)": [17, 11],
    "ANSI C (22x17)": [22, 17],
    "ANSI D (34x22)": [34, 22],
    "ANSI E (44x34)": [44, 34],
}


def get_unique_layout_name(project, desired_name):
    existing_names = [lyt.name for lyt in project.listLayouts()]
    if desired_name not in existing_names:
        return desired_name

    counter = 1
    while f"{desired_name}_{counter}" in existing_names:
        counter += 1
    return f"{desired_name}_{counter}"


def get_map_by_name(project, map_name):
    maps = project.listMaps(map_name)
    if not maps:
        raise ValueError(
            f"Map '{map_name}' was not found in the current ArcGIS Pro project."
        )
    return maps[0]


def create_layout_shell(
    project,
    layout_name,
    layout_size_name,
    main_map_name,
    mini_map_name,
):
    layout_size = PAGE_SIZES.get(layout_size_name, PAGE_SIZES["Letter (11x8.5)"])
    width, height = layout_size

    layout_name = get_unique_layout_name(project, layout_name)
    layout = project.createLayout(width, height, "INCH", layout_name)

    main_map = get_map_by_name(project, main_map_name)
    mini_map = get_map_by_name(project, mini_map_name)

    # Main map frame extent
    x_min = width * 0.011818181818182
    y_min = height * 0.197647058823529
    x_max = width
    y_max = height * 0.801176470588235

    main_extent = arcpy.Extent(x_min, y_min, x_max, y_max)
    main_frame = layout.createMapFrame(main_extent, main_map, "Map Frame")

    main_frame_cim = main_frame.getDefinition("V3")
    main_frame_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
    main_frame.setDefinition(main_frame_cim)
    main_frame.locked = True

    # Mini map frame extent
    x_min_mini = width * 0.32545454545
    y_min_mini = 0
    x_max_mini = width * 0.55
    y_max_mini = height * 0.18470588235

    mini_extent = arcpy.Extent(x_min_mini, y_min_mini, x_max_mini, y_max_mini)
    mini_frame = layout.createMapFrame(mini_extent, mini_map, "Mini Map Frame")

    mini_frame_cim = mini_frame.getDefinition("V3")
    mini_frame_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
    mini_frame.setDefinition(mini_frame_cim)
    mini_frame.locked = True

    return layout, main_frame, mini_frame, width, height


def add_map_surrounds(project, layout, main_frame, main_map, width, height):
    width_ratio = width / 11
    height_ratio = height / 8.5

    # Legend
    legend_x = width * 0.019090909
    legend_y = height * 0.192941176
    legend_location = arcpy.Point(legend_x, legend_y)

    legend_style = project.listStyleItems("ArcGIS 2D", "LEGEND", "Legend 1")[0]
    legend = layout.createMapSurroundElement(
        legend_location,
        "LEGEND",
        main_frame,
        legend_style,
        "Legend",
    )

    legend.syncLayerVisibility = True
    for lyr in main_map.listLayers():
        legend.addItem(lyr)

    legend.elementWidth = 3.314 * width_ratio
    legend.elementHeight = 1.5835 * height_ratio

    legend_cim = legend.getDefinition("V3")
    legend_cim.patchWidth = 10
    legend_cim.patchHeight = 10
    legend_cim.useMapSeriesShape = True
    legend_cim.showTitle = False

    for item in legend_cim.items:
        item.showLayerName = False
        item.showHeading = False
        item.showGroupLayerName = False

    legend_cim.fittingStrategy = "AdjustColumnsAndFont"
    legend.setDefinition(legend_cim)

    # North arrow
    north_arrow_x = width * 0.9247818181818180
    north_arrow_y = height * 0.0404588235294118
    north_arrow_location = arcpy.Point(north_arrow_x, north_arrow_y)

    north_arrow_style = project.listStyleItems(
        "ArcGIS 2D", "North_Arrow", "ArcGIS North 3"
    )[0]

    north_arrow = layout.createMapSurroundElement(
        north_arrow_location,
        "North_Arrow",
        main_frame,
        north_arrow_style,
        "North Arrow",
    )
    north_arrow.elementWidth = 0.0948 * width_ratio
    north_arrow.elementHeight = 0.1972 * height_ratio
    north_arrow.locked = True

    # Scale bar
    scale_bar_x = width * 0.9204636363636360
    scale_bar_y = height * 0.0534470588235294
    scale_bar_location = arcpy.Point(scale_bar_x, scale_bar_y)

    scale_bar_style = project.listStyleItems(
        "ArcGIS 2D", "SCALE_BAR", "Alternating Scale Bar 1 Metric"
    )[0]

    scale_bar = layout.createMapSurroundElement(
        scale_bar_location,
        "SCALE_BAR",
        main_frame,
        scale_bar_style,
        "Scale Bar",
    )

    scale_bar.elementWidth = 0.7725 * width_ratio
    scale_bar.elementHeight = 0.3148 * height_ratio

    scale_bar_cim = scale_bar.getDefinition("V3")
    scale_bar_cim.unitLabelPosition = "Below"
    scale_bar_cim.divisions = 1
    scale_bar_cim.subdivisions = 3
    scale_bar_cim.fittingStrategy = "AdjustDivision"
    scale_bar_cim.markPosition = "BelowBar"
    scale_bar_cim.unitLabelGap = 3
    scale_bar_cim.labelSymbol.symbol.height = 4
    scale_bar_cim.unitLabelSymbol.symbol.height = 4
    scale_bar.setDefinition(scale_bar_cim)


def get_text_definitions(width, height):
    return [
        {
            "text": "Legend",
            "text_x": width * 0.0100636363636364,
            "text_y": height * 0.0809058823529412,
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
            "text_y": height * 0.4750941176470590,
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
            "text_y": height * 0.8750235294117650,
            "rotation": 90,
            "name": "Stationing",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True,
        },
    ]


def create_text_element(project, layout, text_info, height):
    location = arcpy.Point(text_info["text_x"], text_info["text_y"])

    text_element = project.createTextElement(
        layout,
        location,
        "POINT",
        text_info["text"],
        text_info["font_size"],
    )

    text_element.elementRotation = text_info["rotation"]
    text_element.name = text_info["name"]

    dynamic_size = text_info["font_size"] * (height / 8.5)

    text_cim = None
    for _ in range(2):
        try:
            text_cim = text_element.getDefinition("V3")
            if text_cim:
                break
        except:
            time.sleep(0.1)

    if text_cim:
        text_cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
        text_cim.graphic.symbol.symbol.fontStyleName = text_info["font_style"]
        text_cim.graphic.symbol.symbol.underline = text_info["underline"]
        text_cim.graphic.symbol.symbol.height = dynamic_size
        text_cim.locked = text_info["locked"]
        text_element.setDefinition(text_cim)

    return text_element


def add_standard_texts(project, layout, width, height):
    texts = get_text_definitions(width, height)
    for text_info in texts:
        create_text_element(project, layout, text_info, height)


def get_boundary_definitions(width, height):
    return [
        {
            "polygon_name": "Legend",
            "x_min_poly": width * 0.011818181818182,
            "y_min_poly": 0,
            "x_max_poly": width * 0.325454545454545,
            "y_max_poly": height * 0.197647058823529,
            "outline": 0.5,
        },
        {
            "polygon_name": "Legend Title",
            "x_min_poly": 0,
            "y_min_poly": 0,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * 0.197647058823529,
            "outline": 0.5,
        },
    ]


def create_boundary_element(project, layout, boundary):
    poly_blc = arcpy.Point(boundary["x_min_poly"], boundary["y_min_poly"])
    poly_tlc = arcpy.Point(boundary["x_min_poly"], boundary["y_max_poly"])
    poly_trc = arcpy.Point(boundary["x_max_poly"], boundary["y_max_poly"])
    poly_brc = arcpy.Point(boundary["x_max_poly"], boundary["y_min_poly"])

    poly_array = arcpy.Array([poly_blc, poly_tlc, poly_trc, poly_brc, poly_blc])
    poly_extent = arcpy.Polygon(poly_array)

    poly_style = project.listStyleItems(
        "ArcGIS 2D",
        "Polygon",
        "Black Outline (1pt)",
    )[0]

    poly = project.createGraphicElement(
        layout,
        poly_extent,
        poly_style,
        boundary["polygon_name"],
    )

    poly_cim = poly.getDefinition("V3")
    poly_cim.locked = True
    poly_cim.graphic.symbol.symbol.symbolLayers[0].width = boundary["outline"]
    poly.setDefinition(poly_cim)

    return poly


def add_boundary_graphics(project, layout, width, height):
    boundaries = get_boundary_definitions(width, height)
    for boundary in boundaries:
        create_boundary_element(project, layout, boundary)


def create_map_series(layout, main_frame, index_feature, scale, output_gdb):
    strip_output = os.path.join(output_gdb, "strip_map_index")

    if arcpy.Exists(strip_output):
        arcpy.management.Delete(strip_output)

    arcpy.cartography.StripMapIndexFeatures(
        index_feature,
        strip_output,
        "USEPAGEUNIT",
        scale,
    )

    layout.createSpatialMapSeries(main_frame, strip_output, "PageNumber")


def generate_alignment_layout(
    layout_name,
    layout_size,
    main_map_name,
    mini_map_name,
    map_series=False,
    map_series_data=None,
    map_series_scale=None,
):
    project = arcpy.mp.ArcGISProject("CURRENT")

    layout, main_frame, mini_frame, width, height = create_layout_shell(
        project=project,
        layout_name=layout_name,
        layout_size_name=layout_size,
        main_map_name=main_map_name,
        mini_map_name=mini_map_name,
    )

    main_map = get_map_by_name(project, main_map_name)

    add_map_surrounds(
        project=project,
        layout=layout,
        main_frame=main_frame,
        main_map=main_map,
        width=width,
        height=height,
    )

    add_standard_texts(
        project=project,
        layout=layout,
        width=width,
        height=height,
    )

    add_boundary_graphics(
        project=project,
        layout=layout,
        width=width,
        height=height,
    )

    if map_series and map_series_data and map_series_scale:
        create_map_series(
            layout=layout,
            main_frame=main_frame,
            index_feature=map_series_data,
            scale=map_series_scale,
            output_gdb=project.defaultGeodatabase,
        )

    project.save()

    return {
        "layout_name": layout.name,
        "width": width,
        "height": height,
    }
