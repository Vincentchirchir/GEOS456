import arcpy
import os


def get_base_feature_name(path_or_name):
    name = os.path.splitext(os.path.basename(str(path_or_name)))[0]

    suffixes = [
        "_intersect_event_single",
        "_intersect_event",
        "_overlap_event",
        "_intersect",
        "_overlap",
        "_event_single",
        "_event",
        "_single",
        "_event_intersect",
    ]

    for suffix in suffixes:
        if name.lower().endswith(suffix.lower()):
            name = name[: -len(suffix)]
            break

    return name


def build_band_records(point_event_tables, line_event_tables):
    records = []

    for table in point_event_tables:
        source_table_name = os.path.basename(table)
        source_name = get_base_feature_name(source_table_name)

        with arcpy.da.SearchCursor(table, ["MEAS", "Chainage"]) as cursor:
            for meas, chainage in cursor:
                records.append(
                    {
                        "type": "POINT",
                        "meas": meas,
                        "chainage": chainage,
                        "source_table": source_table_name,
                        "source_name": source_name,
                    }
                )

    for table in line_event_tables:
        source_table_name = os.path.basename(table)
        source_name = get_base_feature_name(source_table_name)

        with arcpy.da.SearchCursor(
            table, ["FMEAS", "TMEAS", "ChainageRange"]
        ) as cursor:
            for fmeas, tmeas, chainage_range in cursor:
                start = min(fmeas, tmeas)
                end = max(fmeas, tmeas)
                records.append(
                    {
                        "type": "LINE",
                        "range": chainage_range,
                        "fmeas": start,
                        "tmeas": end,
                        "source_table": source_table_name,
                        "source_name": source_name,
                    }
                )

    return records


# for the following function, for each page, I want page_start measure and page end measure
# This should come from the route
# this is what I am trying to see if its going to work
# I want to use the current map frame camera extent, selected route, then read the minimum and maximum M values from the visible route geometry.
# I am hoping that will give the real start/end measure for the page
# def get_route_measures_in_current_extent(route_fc, map_frame):
#     extent = map_frame.camera.getExtent()
#     sr = arcpy.Describe(route_fc).spatialReference

#     extent_polygon = arcpy.Polygon(
#         arcpy.Array(
#             [
#                 arcpy.Point(extent.XMin, extent.YMin),
#                 arcpy.Point(extent.XMin, extent.YMax),
#                 arcpy.Point(extent.XMax, extent.YMax),
#                 arcpy.Point(extent.XMax, extent.YMin),
#                 arcpy.Point(extent.XMin, extent.YMin),
#             ]
#         ),
#         sr,
#     )

#     extent_fc = r"in_memory\page_extent_poly"
#     clipped_route = r"in_memory\route_in_page"

#     if arcpy.Exists(extent_fc):
#         arcpy.management.Delete(extent_fc)
#     if arcpy.Exists(clipped_route):
#         arcpy.management.Delete(clipped_route)

#     arcpy.management.CopyFeatures([extent_polygon], extent_fc)

#     arcpy.analysis.Intersect(
#         [route_fc, extent_fc],
#         clipped_route,
#         output_type="LINE",
#     )

#     visible_measures = []

#     with arcpy.da.SearchCursor(clipped_route, ["SHAPE@"]) as cursor:
#         for (shape,) in cursor:
#             if not shape:
#                 continue

#             for part in shape:
#                 for pnt in part:
#                     if pnt and pnt.M is not None:
#                         visible_measures.append(pnt.M)

#     if not visible_measures:
#         return None, None

#     return min(visible_measures), max(visible_measures)


def get_route_measure_range(route_fc):
    import arcpy

    arcpy.AddMessage(f"get_route_measure_range received: {route_fc}")
    arcpy.AddMessage(f"Type received: {type(route_fc)}")

    if not route_fc:
        raise ValueError("route_fc is empty or None.")

    if not arcpy.Exists(route_fc):
        raise ValueError(
            f"route_fc does not exist or is not a valid feature class: {route_fc}"
        )

    with arcpy.da.SearchCursor(route_fc, ["SHAPE@"]) as cursor:
        for row in cursor:
            geom = row[0]
            if not geom:
                continue

            first_pt = geom.firstPoint
            last_pt = geom.lastPoint

            if first_pt is None or last_pt is None:
                continue

            m1 = first_pt.M
            m2 = last_pt.M

            if m1 is None or m2 is None:
                raise ValueError("Route does not have valid M-values.")

            return min(float(m1), float(m2)), max(float(m1), float(m2))

    raise ValueError("No valid route geometry found.")


def measure_to_layout_x(measure, route_start, route_end, band_left, band_width):

    # Converts a route measure into an x position on the layout band.

    total_range = route_end - route_start
    if total_range == 0:
        raise ValueError("Route start and end measures are the same.")

    ratio = (measure - route_start) / total_range
    return band_left + (ratio * band_width)


def sort_band_records(band_records):
    def sort_key(rec):
        if rec["type"] == "POINT":
            return rec["meas"]
        return rec["fmeas"]

    return sorted(band_records, key=sort_key)


def build_layout_band_positions(
    band_records, route_start, route_end, band_left, band_width
):
    """
    Returns the same records with layout x positions added.
    """
    positioned = []

    for rec in band_records:
        if rec["type"] == "POINT":
            x = measure_to_layout_x(
                rec["meas"], route_start, route_end, band_left, band_width
            )
            rec_copy = rec.copy()
            rec_copy["x"] = x
            positioned.append(rec_copy)

        elif rec["type"] == "LINE":
            x1 = measure_to_layout_x(
                rec["fmeas"], route_start, route_end, band_left, band_width
            )
            x2 = measure_to_layout_x(
                rec["tmeas"], route_start, route_end, band_left, band_width
            )
            rec_copy = rec.copy()
            rec_copy["x1"] = x1
            rec_copy["x2"] = x2
            positioned.append(rec_copy)

    return positioned


def assign_band_rows(positioned_records, point_row_y, line_row_y):
    """
    Adds a y position for simple band layout.

    This keeps POINT and LINE records on separate rows for now.
    """
    row_ready = []

    for rec in positioned_records:
        rec_copy = rec.copy()

        if rec["type"] == "POINT":
            rec_copy["y"] = point_row_y
        elif rec["type"] == "LINE":
            rec_copy["y"] = line_row_y

        row_ready.append(rec_copy)

    return row_ready


def summarize_band_records(positioned_records):
    """
    Returns a list of readable strings for debugging.
    """
    lines = []

    for rec in positioned_records:
        if rec["type"] == "POINT":
            lines.append(
                f"POINT {rec['chainage']} -> meas {rec['meas']} -> x {rec['x']}"
            )
        elif rec["type"] == "LINE":
            lines.append(
                f"LINE {rec['range']} -> {rec['fmeas']} to {rec['tmeas']} -> x1 {rec['x1']}, x2 {rec['x2']}"
            )

    return lines


def prepare_layout_band_records(
    route_fc,
    band_records,
    band_left,
    band_width,
    point_row_y,
    line_row_y,
):
    """
    Full preparation pipeline for layout band logic.

    Returns
    -------
    dict with:
        route_start
        route_end
        sorted_records
        positioned_records
        row_ready_records
        debug_lines
    """
    route_start, route_end = get_route_measure_range(route_fc)

    sorted_records = sort_band_records(band_records)

    positioned_records = build_layout_band_positions(
        sorted_records,
        route_start,
        route_end,
        band_left,
        band_width,
    )

    row_ready_records = assign_band_rows(
        positioned_records,
        point_row_y=point_row_y,
        line_row_y=line_row_y,
    )

    debug_lines = summarize_band_records(row_ready_records)

    return {
        "route_start": route_start,
        "route_end": route_end,
        "sorted_records": sorted_records,
        "positioned_records": positioned_records,
        "row_ready_records": row_ready_records,
        "debug_lines": debug_lines,
    }


def draw_point_band_labels(
    layout,
    point_records,
    label_y,
    text_height=0.12,
    font_name="Tahoma",
    prefix="BandPointLabel",
    label_mode="source_name",  # "source_name", "chainage", or "both"
):

    # Draw point labels in the layout using precomputed x positions.

    created_elements = []
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    text_size_points = (
        text_height * 72 if text_height and text_height < 1 else text_height
    )

    for i, rec in enumerate(point_records, start=1):
        if rec.get("type") != "POINT":
            continue

        x = rec.get("x")
        record_label_y = rec.get("label_y", label_y)
        source_name = rec.get("source_name", "")
        chainage = rec.get("chainage", "")

        if label_mode == "source_name":
            label_text = source_name
        elif label_mode == "both":
            if source_name and chainage:
                label_text = f"{source_name} ({chainage})"
            else:
                label_text = source_name or chainage
        else:
            label_text = chainage

        if x is None or not label_text:
            continue

        safe_text = (
            label_text.replace("+", "_")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
        )
        element_name = f"{prefix}_{i}_{safe_text}"
        point_geom = arcpy.Point(x, record_label_y)

        try:
            txt = aprx.createTextElement(
                layout,
                point_geom,
                "POINT",
                label_text,
                text_size_points,
            )
            txt.name = element_name

            cim = txt.getDefinition("V3")
            cim.anchor = "CenterPoint"
            cim.graphic.symbol.symbol.fontFamilyName = font_name
            cim.graphic.symbol.symbol.height = text_size_points
            txt.setDefinition(cim)

        except Exception as e:
            arcpy.AddWarning(f"Could not create band point label '{label_text}': {e}")
            continue

        created_elements.append(txt)

    return created_elements


def draw_line_band_labels(
    layout,
    line_records,
    label_y,
    text_height=0.12,
    font_name="Arial",
    prefix="BandLineLabel",
    label_mode="source_name",
):
    # here we are going to draw lines on layout using the midpoint of to and from measures
    created_elements = []
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    text_size_points = (
        text_height * 72 if text_height and text_height < 1 else text_height
    )

    for i, rec in enumerate(line_records, start=1):
        if rec.get("type") != "LINE":
            continue

        x1 = rec.get("x1")
        x2 = rec.get("x2")
        source_name = rec.get("source_name", "")
        range_text = rec.get("range", "")

        if label_mode == "source_name":
            label_text = source_name
        elif label_mode == "both":
            if source_name and range_text:
                label_text = f"{source_name} ({range_text})"
            else:
                label_text = source_name or range_text
        else:
            label_text = range_text

        if x1 is None or x2 is None or not label_text:
            continue

        x_mid = (x1 + x2) / 2.0

        safe_text = (
            label_text.replace("+", "_")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
        )
        element_name = f"{prefix}_{i}_{safe_text}"
        point_geom = arcpy.Point(x_mid, label_y)

        try:
            txt = aprx.createTextElement(
                layout,
                point_geom,
                "POINT",
                label_text,
                text_size_points,
            )
            txt.name = element_name

            cim = txt.getDefinition("V3")
            cim.anchor = "CenterPoint"
            cim.graphic.symbol.symbol.fontFamilyName = font_name
            cim.graphic.symbol.symbol.height = text_size_points
            txt.setDefinition(cim)

        except Exception as e:
            arcpy.AddWarning(f"Could not create band line label '{label_text}': {e}")
            continue

        created_elements.append(txt)

    return created_elements


def clear_point_band_labels(layout, prefix="BandPointLabel"):
    """
    Deletes previously created point band labels from the layout.
    """
    if not layout:
        raise ValueError("Layout is required.")

    to_delete = []
    for elm in layout.listElements("TEXT_ELEMENT"):
        if elm.name.startswith(prefix):
            to_delete.append(elm)

    for elm in to_delete:
        elm.delete()

    return len(to_delete)


def clear_line_band_labels(layout, prefix="BandLineLabel"):
    """
    Deletes previously created line band labels from the layout.
    """
    if not layout:
        raise ValueError("Layout is required.")

    to_delete = []
    for elm in layout.listElements("TEXT_ELEMENT"):
        if elm.name.startswith(prefix):
            to_delete.append(elm)

    for elm in to_delete:
        elm.delete()

    return len(to_delete)


def assign_point_label_sides(
    point_records,
    top_y,
    bottom_y,
):
    # Assign each point record a label side and y-position.

    # For now:
    # - alternate labels top/bottom
    # - preserves x position already computed

    updated = []

    for i, rec in enumerate(point_records):
        new_rec = rec.copy()

        if i % 2 == 0:
            new_rec["label_side"] = "TOP"
            new_rec["label_y"] = top_y
        else:
            new_rec["label_side"] = "BOTTOM"
            new_rec["label_y"] = bottom_y

        updated.append(new_rec)

    return updated
