import arcpy
import os
import math


def get_base_feature_name(path_or_name):
    """
    Strips known suffixes from a feature class path or name to get a clean
    display name. Internal underscores are replaced with spaces for readability.
    For example, 'glac_landform_ln_ll_intersect_event_intersect' becomes
    'glac landform ln ll'.
    """
    name = os.path.splitext(os.path.basename(str(path_or_name)))[0]

    # Suffixes are ordered longest-first so more specific patterns match before
    # shorter ones — e.g. '_intersect_event_intersect' before '_intersect_event'
    suffixes = [
        "_intersect_event_single",
        "_intersect_event_intersect",
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

    # Replace underscores with spaces for cleaner label display on the layout
    name = name.replace("_", " ")

    return name


def build_band_records(point_event_tables, line_event_tables):
    """
    Reads point and line event tables and builds a flat list of record dicts.

    Point records contain: type, meas, chainage, source_table, source_name
    Line records contain:  type, range, fmeas, tmeas, source_table, source_name

    Parameters
    ----------
    point_event_tables : list of str
        Paths to point event tables (each has MEAS and Chainage fields).
    line_event_tables : list of str
        Paths to line event tables (each has FMEAS, TMEAS, ChainageRange fields).
    """
    records = []

    # Point event tables
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

    # Line event tables
    for table in line_event_tables:
        source_table_name = os.path.basename(table)
        source_name = get_base_feature_name(source_table_name)

        with arcpy.da.SearchCursor(
            table, ["FMEAS", "TMEAS", "ChainageRange"]
        ) as cursor:
            for fmeas, tmeas, chainage_range in cursor:
                # Normalise direction so fmeas is always the smaller value
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


def get_route_measure_range(route_fc):
    """
    Returns the minimum and maximum M values from the first and last points
    of the route geometry.

    Parameters
    ----------
    route_fc : str
        Path to the route feature class. Must have M-values enabled.

    Returns
    -------
    tuple of (float, float) — (min_measure, max_measure)
    """
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

            # Both M values must be present — routes without M are not supported
            if m1 is None or m2 is None:
                raise ValueError("Route does not have valid M-values.")

            return min(float(m1), float(m2)), max(float(m1), float(m2))

    raise ValueError("No valid route geometry found.")


def measure_to_layout_x(measure, route_start, route_end, band_left, band_width):
    """
    Converts a route measure value into an x position on the layout band.

    Parameters
    ----------
    measure : float
        The measure value to convert.
    route_start : float
        The measure at the left edge of the band.
    route_end : float
        The measure at the right edge of the band.
    band_left : float
        Left edge of the band in layout page units (inches).
    band_width : float
        Total width of the band in layout page units (inches).

    Returns
    -------
    float — x position in layout page units (inches)
    """
    total_range = route_end - route_start

    if total_range == 0:
        raise ValueError("Route start and end measures are the same.")

    # How far along the band this measure falls, expressed as a 0-1 ratio
    ratio = (measure - route_start) / total_range

    return band_left + (ratio * band_width)


def sort_band_records(band_records):
    """
    Sorts band records by measure value so they are ordered along the route.
    Points sort by meas, lines sort by fmeas (the start of the overlap).
    """

    def sort_key(rec):
        if rec["type"] == "POINT":
            return rec["meas"]
        return rec["fmeas"]

    return sorted(band_records, key=sort_key)


def build_layout_band_positions(
    band_records, route_start, route_end, band_left, band_width
):
    """
    Adds layout x positions to each band record based on its measure value.

    Points get a single x value.
    Lines get x1 (from) and x2 (to) values.

    Returns a new list of records — originals are not modified.
    """
    positioned = []

    for rec in band_records:
        if rec["type"] == "POINT":
            # Single x position from the point measure
            x = measure_to_layout_x(
                rec["meas"], route_start, route_end, band_left, band_width
            )
            rec_copy = rec.copy()
            rec_copy["x"] = x
            positioned.append(rec_copy)

        elif rec["type"] == "LINE":
            # Two x positions — one for each end of the overlap
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
    Assigns a y position to each record based on its type.

    Points and lines are placed on separate rows so they do not overlap.
    Returns a new list of records — originals are not modified.
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
    Returns a list of readable strings describing each record.
    Useful for debugging — print or log these to check band positions.
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
    band_records,
    band_left,
    band_width,
    point_row_y,
    line_row_y,
    route_start,
    route_end,
):
    """
    Full preparation pipeline for layout band logic.

    Runs sort -> position -> assign rows -> summarize in one call.

    Parameters
    ----------
    band_records : list of dict
        Raw records from build_band_records.
    band_left : float
        Left edge of the band in layout page units (inches).
    band_width : float
        Width of the band in layout page units (inches).
    point_row_y : float
        Y position for point record row (inches).
    line_row_y : float
        Y position for line record row (inches).
    route_start : float
        Measure at the start of the current page or full route.
    route_end : float
        Measure at the end of the current page or full route.

    Returns
    -------
    dict with keys:
        route_start, route_end,
        sorted_records, positioned_records, row_ready_records, debug_lines
    """
    if route_start is None or route_end is None:
        raise ValueError("route_start and route_end are required.")

    route_start = float(route_start)
    route_end = float(route_end)

    if route_end <= route_start:
        raise ValueError(f"Invalid measure range: start={route_start}, end={route_end}")

    # Step 1 — sort records by measure so they run left to right on the band
    sorted_records = sort_band_records(band_records)

    # Step 2 — compute x positions on the band for each record
    positioned_records = build_layout_band_positions(
        sorted_records,
        route_start,
        route_end,
        band_left,
        band_width,
    )

    # Step 3 — assign y positions based on record type
    row_ready_records = assign_band_rows(
        positioned_records,
        point_row_y=point_row_y,
        line_row_y=line_row_y,
    )

    # Step 4 — build debug summary strings
    debug_lines = summarize_band_records(row_ready_records)

    return {
        "route_start": route_start,
        "route_end": route_end,
        "sorted_records": sorted_records,
        "positioned_records": positioned_records,
        "row_ready_records": row_ready_records,
        "debug_lines": debug_lines,
    }


def get_route_measures_in_current_extent(route_fc, map_frame):
    """
    Returns the minimum and maximum M values of the portion of the route
    that is visible inside the current map frame extent.

    Used for map series / pagination — each page gets its own measure range
    based on what part of the route is actually visible on that page.

    Parameters
    ----------
    route_fc : str
        Path to the route feature class.
    map_frame : arcpy.mp.MapFrame
        The map frame whose camera extent defines the visible area.

    Returns
    -------
    tuple of (float, float) — (min_measure, max_measure)
    Returns (None, None) if no route geometry is visible in the extent.
    """
    if not route_fc:
        raise ValueError("route_fc is required.")
    if not arcpy.Exists(route_fc):
        raise ValueError(f"route_fc does not exist: {route_fc}")
    if map_frame is None:
        raise ValueError("map_frame is required.")

    # Get the visible extent of the map frame in map coordinates
    extent = map_frame.camera.getExtent()
    sr = arcpy.Describe(route_fc).spatialReference

    # Build a polygon from the extent corners so we can clip the route to it
    extent_polygon = arcpy.Polygon(
        arcpy.Array(
            [
                arcpy.Point(extent.XMin, extent.YMin),
                arcpy.Point(extent.XMin, extent.YMax),
                arcpy.Point(extent.XMax, extent.YMax),
                arcpy.Point(extent.XMax, extent.YMin),
                arcpy.Point(extent.XMin, extent.YMin),  # close the ring
            ]
        ),
        sr,
    )

    # Temporary in-memory feature classes — cleaned up after use
    extent_fc = r"in_memory\page_extent_poly"
    clipped_route = r"in_memory\route_in_page"

    # Delete any leftovers from a previous run to avoid conflicts
    for temp_fc in [extent_fc, clipped_route]:
        if arcpy.Exists(temp_fc):
            arcpy.management.Delete(temp_fc)

    # Write the extent polygon so Intersect can use it as an input
    arcpy.management.CopyFeatures([extent_polygon], extent_fc)

    # Clip the route to the visible extent — result keeps M values
    arcpy.analysis.Intersect(
        [route_fc, extent_fc],
        clipped_route,
        output_type="LINE",
    )

    # Walk every vertex of the clipped route and collect M values
    visible_measures = []

    with arcpy.da.SearchCursor(clipped_route, ["SHAPE@"]) as cursor:
        for (shape,) in cursor:
            if not shape:
                continue

            for part in shape:
                for pnt in part:
                    if pnt and pnt.M is not None:
                        visible_measures.append(float(pnt.M))

    # Clean up temporary feature classes
    if arcpy.Exists(extent_fc):
        arcpy.management.Delete(extent_fc)
    if arcpy.Exists(clipped_route):
        arcpy.management.Delete(clipped_route)

    # If nothing was found, return None so the caller can handle it
    if not visible_measures:
        return None, None

    return min(visible_measures), max(visible_measures)


def draw_line_band_labels(
    layout,
    line_records,
    label_y,
    text_height=0.12,
    font_name="Arial",
    prefix="BandLineLabel",
    label_mode="source_name",
):
    """
    Draws text labels for line (overlap) records on the layout band.

    Labels are placed at the midpoint between x1 and x2 so they sit
    centred over the overlap extent.

    Parameters
    ----------
    layout : arcpy.mp.Layout
        The layout to draw on.
    line_records : list of dict
        Records with type="LINE", x1, and x2 already computed.
    label_y : float
        Default y position for labels (inches).
    text_height : float
        Text height in inches — converted to points internally.
    font_name : str
        Font family name.
    prefix : str
        Name prefix for created elements — used for cleanup.
    label_mode : str
        "source_name" — show feature name only
        "chainage"    — show chainage range only
        "both"        — show "feature name (chainage range)"
    """
    created_elements = []
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    # Convert inches to points (1 inch = 72 points)
    text_size_points = text_height * 72

    for i, rec in enumerate(line_records, start=1):

        # Only process line records
        if rec.get("type") != "LINE":
            continue

        x1 = rec.get("x1")
        x2 = rec.get("x2")

        # Allow per-record label_y override, fall back to function parameter
        record_label_y = rec.get("label_y", label_y)
        source_name = rec.get("source_name", "")
        range_text = rec.get("range", "")

        # Build label text based on the requested mode
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

        # Place the label at the midpoint of the overlap extent
        x_mid = (x1 + x2) / 2.0

        # Build a safe element name — special characters cause issues in ArcPy
        safe_text = (
            label_text.replace("+", "_")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
        )
        element_name = f"{prefix}_{i}_{safe_text}"
        point_geom = arcpy.Point(x_mid, record_label_y)

        try:
            txt = aprx.createTextElement(
                layout,
                point_geom,
                "POINT",
                label_text,
                text_size_points,
            )
            txt.name = element_name

            # Set font and anchor via CIM — not directly settable on the element
            cim = txt.getDefinition("V3")
            cim.anchor = "CenterPoint"  # centre horizontally over the overlap
            cim.graphic.symbol.symbol.fontFamilyName = font_name
            cim.graphic.symbol.symbol.height = text_size_points
            txt.setDefinition(cim)

        except Exception as e:
            arcpy.AddWarning(f"Could not create band line label '{label_text}': {e}")
            continue

        created_elements.append(txt)

    return created_elements


def clear_line_band_labels(layout, prefix="BandLineLabel"):
    """
    Deletes all line band labels previously created with draw_line_band_labels.
    Call this before redrawing to avoid duplicate elements.

    Returns the number of elements removed.
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


def assign_line_label_sides(line_records, top_y, bottom_y):
    """
    Assigns each line record a label position — alternating top and bottom
    to reduce overlap when overlaps are close together.

    Returns a new list of records with label_side and label_y added.
    """
    updated = []

    for i, rec in enumerate(line_records):
        new_rec = rec.copy()

        # Even index = top, odd index = bottom
        if i % 2 == 0:
            new_rec["label_side"] = "TOP"
            new_rec["label_y"] = top_y
        else:
            new_rec["label_side"] = "BOTTOM"
            new_rec["label_y"] = bottom_y

        updated.append(new_rec)

    return updated


def filter_point_records_for_labeling(point_records, line_records):
    """
    Removes point records whose feature already appears as a line overlap.

    When a feature overlaps the route (LINE record exists), its entry and
    exit intersection points (POINT records) are redundant — the overlap
    label covers them. This function removes those boundary points so the
    band is not cluttered with duplicate labels.
    """
    # Collect all feature names that have an overlap (LINE) record
    line_source_names = {
        rec.get("source_name") for rec in line_records if rec.get("type") == "LINE"
    }

    filtered = []

    for rec in point_records:
        source_name = rec.get("source_name")

        # Skip this point if its feature is already shown as a line overlap
        if source_name in line_source_names:
            continue

        filtered.append(rec)

    return filtered


def _map_point_to_layout_xy(map_x, map_y, map_frame):
    """
    Converts a map coordinate (in the map's CRS) into a layout page coordinate
    (in inches) using the map frame's current extent and its position on the page.

    ArcPy MapFrame does not have a built-in coordinate conversion method, so
    this is computed manually using proportional scaling:
        - Find where the map point sits within the map extent (0-1 ratio)
        - Apply that ratio to the map frame's position and size on the layout page

    Parameters
    ----------
    map_x : float
        X coordinate in the map's coordinate system.
    map_y : float
        Y coordinate in the map's coordinate system.
    map_frame : arcpy.mp.MapFrame
        The map frame element on the layout.

    Returns
    -------
    tuple of (float, float) — (layout_x, layout_y) in page units (inches)
    """
    # Get the current visible extent of the map frame in map coordinates
    extent = map_frame.camera.getExtent()

    # Get the map frame's position and size on the layout page in inches
    frame_x = map_frame.elementPositionX  # left edge of map frame on page
    frame_y = map_frame.elementPositionY  # bottom edge of map frame on page
    frame_w = map_frame.elementWidth  # width of map frame in inches
    frame_h = map_frame.elementHeight  # height of map frame in inches

    # Compute how far across the map extent the point falls, as a 0-1 ratio
    ratio_x = (map_x - extent.XMin) / (extent.XMax - extent.XMin)
    ratio_y = (map_y - extent.YMin) / (extent.YMax - extent.YMin)

    # Apply that ratio to the map frame size to get layout page coordinates
    layout_x = frame_x + ratio_x * frame_w
    layout_y = frame_y + ratio_y * frame_h

    return layout_x, layout_y


def build_point_records_with_layout_xy(
    point_event_features,
    map_frame,
    route_start,
    route_end,
    band_left,
    band_width,
):
    """
    Reads each point feature's real map geometry, converts it to layout page
    coordinates, and builds a record dict ready for tick drawing.

    This is the bridge between the map coordinate system and the layout page.
    Each intersection point has a real location on the map — this function
    finds that location and translates it into inches on the layout page so
    that ticks can be drawn directly above the correct map position.

    Parameters
    ----------
    point_event_features : list of str
        Paths to point feature classes (output of make_event_layers_from_tables).
    map_frame : arcpy.mp.MapFrame
        The map frame on the layout — used to convert map coords to page coords.
    route_start : float
        The minimum measure value of the route (or current page range start).
    route_end : float
        The maximum measure value of the route (or current page range end).
    band_left : float
        Left edge of the stationing band in layout page units (inches).
    band_width : float
        Total width of the stationing band in layout page units (inches).

    Returns
    -------
    list of dict, each containing:
        type            -- always "POINT"
        meas            -- route measure value
        chainage        -- formatted chainage string e.g. "1+230"
        source_name     -- feature class base name (used as label)
        x               -- x position on the band (computed from measure)
        x_map_layout    -- layout page x of the real map intersection point
        y_map_layout    -- layout page y of the real map intersection point
    """
    records = []

    # Total measure span — used to compute proportional position along the band
    total_range = route_end - route_start

    for fc in point_event_features:
        # Strip suffixes and replace underscores to get a clean display name
        source_name = get_base_feature_name(fc)

        with arcpy.da.SearchCursor(
            fc, ["SHAPE@X", "SHAPE@Y", "MEAS", "Chainage"]
        ) as cursor:
            for map_x, map_y, meas, chainage in cursor:

                # Skip records with missing geometry or measure — cannot place them
                if meas is None or map_x is None or map_y is None:
                    continue

                # Compute how far along the band this measure falls as a 0-1 ratio
                ratio = (meas - route_start) / total_range

                # Translate that ratio into an x position on the layout band
                x_band = band_left + ratio * band_width

                # Convert the real map coordinate to layout page coordinate in inches
                layout_x, layout_y = _map_point_to_layout_xy(map_x, map_y, map_frame)

                records.append(
                    {
                        "type": "POINT",
                        "meas": meas,
                        "chainage": chainage or "",
                        "source_name": source_name,
                        "x": x_band,  # position on the band from measure
                        "x_map_layout": layout_x,  # real page x of the map point
                        "y_map_layout": layout_y,  # real page y of the map point
                    }
                )

    return records


def wrap_label_text(text, max_chars=12):
    """
    Wraps a label string by inserting newlines at word boundaries.

    Words are split on spaces. A new line is started whenever adding
    the next word would exceed max_chars on the current line.

    Parameters
    ----------
    text : str
        The label text to wrap.
    max_chars : int
        Maximum number of characters per line before wrapping.

    Returns
    -------
    str — the wrapped text with newline characters inserted
    """
    words = text.split(" ")
    lines = []
    current_line = ""

    for word in words:
        # Check if adding this word would exceed the line length limit
        if current_line and len(current_line) + 1 + len(word) > max_chars:
            # Current line is full — save it and start a new one
            lines.append(current_line)
            current_line = word
        else:
            # Word fits on the current line — append it
            current_line = f"{current_line} {word}".strip()

    # Save the last line
    if current_line:
        lines.append(current_line)

    return "\n".join(lines)


def draw_point_ticks_and_labels(
    layout,
    point_records,
    band_y_top,  # y of the bottom edge of the TOP stationing band
    band_y_bottom,  # y of the top edge of the BOTTOM stationing band
    label_bottom_y,  # y where labels sit inside the bottom band
    label_top_row1_y,  # gap above Bar 1
    label_top_row2_y,  # gap between Bar 1 and Bar 2
    label_top_row3_y,  # gap between Bar 2 and Bar 3
    half_tick=0.1,
    text_height=0.17,
    font_name="Arial",
    prefix="PointTick",
    max_label_chars=12,
):
    """
    Draws a vertical tick and label for each point record on the layout.

    Records alternate between the top and bottom stationing bands:
        Odd  index (1, 3, 5...) → tick at top band bottom edge,
                                   label inside top band at label_top_y
        Even index (2, 4, 6...) → tick at bottom band top edge,
                                   label inside bottom band at label_bottom_y
    Parameters
    ----------
    layout : arcpy.mp.Layout
        The layout object to draw elements on.
    point_records : list of dict
        Records produced by build_point_records_with_layout_xy.
    band_y_top : float
        Y of the bottom edge of the top stationing band (inches).
        Odd-index ticks straddle this line.
    band_y_bottom : float
        Y of the top edge of the bottom stationing band (inches).
        Even-index ticks straddle this line.
    label_top_y : float
        Y position for labels in the top band (inches).
    label_bottom_y : float
        Y position for labels in the bottom band (inches).
    half_tick : float
        How far the tick extends above and below the band edge (inches).
        Total tick height = half_tick * 2.
    text_height : float
        Label text height in inches — converted to points internally.
    font_name : str
        Font to use for labels.
    prefix : str
        Name prefix for all created elements — used for cleanup later.
    max_label_chars : int
        Maximum characters per line before the label text wraps.
    """
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    created = []

    # Convert text height from inches to points (1 inch = 72 points)
    text_size_pts = text_height * 72

    for i, rec in enumerate(point_records, start=1):

        # Only process point records — skip anything else in the list
        if rec.get("type") != "POINT":
            continue

        # Use map layout x so the tick sits directly above the real map feature
        # This value was computed by _map_point_to_layout_xy earlier
        x = rec.get("x_map_layout")

        # Use source name as the primary label — fall back to chainage if missing
        label_text = (
            rec.get("label") or rec.get("source_name") or rec.get("chainage") or ""
        )

        # Skip if position or label text is missing
        if x is None or not label_text:
            continue

        # Wrap long labels so they do not run into neighbouring labels
        label_text = wrap_label_text(label_text, max_chars=max_label_chars)

        # Alternate between top band and bottom band
        # Odd index  → top band tick + label
        # Even index → bottom band tick + label
        # --- Alternate between top band and bottom band ----------------------
        # Odd index  (1, 3, 5...) → top band tick + label
        # Even index (2, 4, 6...) → bottom band tick + label
        if i % 2 == 1:
            # Odd record — tick at the bottom edge of the top band
            tick_band_y = band_y_top

            # Cycle through 3 label rows within the top band
            # i=1 → row1, i=3 → row2, i=5 → row3, i=7 → row1 again etc.
            # We use (i // 2) % 3 to step through rows only on odd records
            row_index = (i // 2) % 3
            if row_index == 0:
                current_label_y = label_top_row1_y  # gap above Bar 1
            elif row_index == 1:
                current_label_y = label_top_row2_y  # gap between Bar 1 and Bar 2
            else:
                current_label_y = label_top_row3_y  # gap between Bar 2 and Bar 3

            # Label is centred in the gap between bar lines
            anchor = "CenterPoint"

        else:
            # Even record — tick at the top edge of the bottom band
            tick_band_y = band_y_bottom
            current_label_y = label_bottom_y
            anchor = "CenterPoint"

        # Draw vertical tick straddling the band edge
        try:
            tick_geom = arcpy.Polyline(
                arcpy.Array(
                    [
                        # Slightly below the band edge
                        arcpy.Point(x, tick_band_y - half_tick),
                        # Slightly above the band edge
                        arcpy.Point(x, tick_band_y + half_tick),
                    ]
                )
            )

            tick_el = aprx.createGraphicElement(layout, tick_geom)
            tick_el.name = f"{prefix}_Tick_{i}"  # named for cleanup later
            created.append(tick_el)

        except Exception as e:
            arcpy.AddWarning(
                f"Could not create tick for '{label_text}': {type(e).__name__}: {e}"
            )

        #  Draw label at the alternating band position
        try:
            txt = aprx.createTextElement(
                layout,
                arcpy.Point(x, current_label_y),
                "POINT",
                label_text,
                text_size_pts,
            )
            txt.name = f"{prefix}_Label_{i}"  # named for cleanup later

            # Apply font, size, and anchor position via CIM
            cim = txt.getDefinition("V3")
            # BottomCenterPoint = text grows up (top band labels)
            # TopCenterPoint    = text grows down (bottom band labels)
            cim.anchor = anchor
            cim.graphic.symbol.symbol.fontFamilyName = font_name
            cim.graphic.symbol.symbol.height = text_size_pts
            txt.setDefinition(cim)

            created.append(txt)

        except Exception as e:
            arcpy.AddWarning(f"Could not create label '{label_text}': {e}")

    return created


def clear_point_ticks_and_labels(layout, prefix="PointTick"):
    """
    Deletes all tick and label elements previously created by
    draw_point_ticks_and_labels. Call this before redrawing to avoid duplicates.

    Returns the number of elements removed.
    """
    removed = 0

    for el in layout.listElements():
        # Match any element whose name starts with the given prefix
        if el.name.startswith(prefix):
            el.delete()
            removed += 1

    return removed  # return count so the caller can log how many were removed
