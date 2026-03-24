import arcpy
import time


def add_north_arrow(project, layout, map_frame, width, height):
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
    locked_texts = []
    unlocked_texts = []

    texts = [
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

    # Lock elements individually instead of grouping
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
    grouping_polygons = []

    boundaries = [
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
            "polygon_name": "Plan View Border",
            "x_min_poly": 0,
            "y_min_poly": height * 0.197647058823529,
            "x_max_poly": width,
            "y_max_poly": height * 0.801176470588235,
            "outline": 0.5,
        },
        {
            "polygon_name": "Stationing Border",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.80117647058823500,
            "x_max_poly": width,
            "y_max_poly": height,
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
            "polygon_name": "Stationing Bar 1",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.9796117647058820,
            "x_max_poly": width,
            "y_max_poly": height,
            "outline": 0.25,
        },
        {
            "polygon_name": "Stationing Bar 2",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.9398470588235290,
            "x_max_poly": width,
            "y_max_poly": height * 0.9597294117647060,
            "outline": 0.25,
        },
        {
            "polygon_name": "Stationing Bar 3",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.9000823529411760,
            "x_max_poly": width,
            "y_max_poly": height * 0.9199647058823530,
            "outline": 0.25,
        },
        {
            "polygon_name": "Stationing Bar 4",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.8603176470588240,
            "x_max_poly": width,
            "y_max_poly": height * 0.8802000000000000,
            "outline": 0.25,
        },
        {
            "polygon_name": "Stationing Bar 5",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.82055294117647100,
            "x_max_poly": width,
            "y_max_poly": height * 0.84043529411764700,
            "outline": 0.25,
        },
        {
            "polygon_name": "Stationing Bar Border",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.80117647058823500,
            "x_max_poly": width,
            "y_max_poly": height,
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

        poly_cim = poly.getDefinition("V3")
        poly_cim.graphic.symbol.symbol.symbolLayers[0].width = boundary["outline"]
        poly.setDefinition(poly_cim)

        grouping_polygons.append(poly)

    if grouping_polygons:
        group_polygons = project.createGroupElement(
            layout, grouping_polygons, "DO NOT TOUCH (Boundaries)"
        )
        group_cim = group_polygons.getDefinition("V3")
        group_cim.locked = True
        group_polygons.setDefinition(group_cim)
