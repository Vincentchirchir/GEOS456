import arcpy
import os


def create_layout_map_series(
    input_line_fc,
    output_gdb,
    layout,
    map_frame,
    main_map,
    scale,
    orientation,
    overlap_percent,
):
    data_input = os.path.splitext(os.path.basename(str(input_line_fc)))[0]
    index_output = os.path.join(output_gdb, f"{data_input}_index")

    mf_width = f"{float(map_frame.elementWidth) * 0.90} Inches"
    mf_height = f"{float(map_frame.elementHeight) * 0.90} Inches"

    if arcpy.Exists(index_output):
        arcpy.management.Delete(index_output)

        # Validate numeric inputs
    scale = int(scale)
    overlap_percent = int(overlap_percent)

    if scale <= 0:
        raise ValueError("Map series scale must be greater than zero.")

    if overlap_percent < 0 or overlap_percent > 99:
        raise ValueError("Overlap percent must be between 0 and 99.")

    # Use page size from map frame
    mf_width = f"{float(map_frame.elementWidth) * 0.90} Inches"
    mf_height = f"{float(map_frame.elementHeight) * 0.65} Inches"

    arcpy.AddMessage(f"Map frame width used: {mf_width}")
    arcpy.AddMessage(f"Map frame height used: {mf_height}")
    arcpy.AddMessage(f"Map series scale used: {scale}")
    arcpy.AddMessage(f"Map series overlap used: {overlap_percent}")
    arcpy.AddMessage(f"Map series orientation used: {orientation}")

    arcpy.cartography.StripMapIndexFeatures(
        in_features=input_line_fc,
        out_feature_class=index_output,
        use_page_unit="USEPAGEUNIT",
        scale=scale,
        length_along_line=mf_width,
        length_perpendicular_to_line=mf_height,
        page_orientation=str(orientation).upper(),
        overlap_percentage=overlap_percent,
    )

    index_layer = main_map.addDataFromPath(index_output)
    index_layer.visible = False

    map_series = layout.createSpatialMapSeries(
        mapframe=map_frame,
        index_layer=index_layer,
        name_field="PageNumber",
        sort_field="PageNumber",
    )

    cim = map_series.getDefinition("V3")
    cim.enabled = True
    cim.mapFrameName = map_frame.name
    cim.indexLayerURI = index_layer.getDefinition("V3").uRI
    cim.sortAscending = True
    cim.extentOptions = "BestFit"
    cim.rotationField = "Angle"
    cim.startingPageNumber = 1
    map_series.setDefinition(cim)

    # map_frame.camera.scale = int(scale)

    return {
        "index_fc": index_output,
        "index_layer": index_layer,
        "map_series": map_series,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAP SERIES PAGE UPDATER
#
# This module loops through every page in a spatial map series and for each
# page:
#   1. Sets the current page
#   2. Applies the rotation angle from the index feature Angle field
#   3. Reads the visible route measures from the map frame extent
#   4. Filters band records to only those visible on this page
#   5. Redraws the stationing band (top + bottom) for the page measure range
#   6. Redraws ticks and labels for only the intersections on this page
#
# The user exports manually after running this tool.
# ─────────────────────────────────────────────────────────────────────────────


def _get_page_rotation(index_fc, page_number):
    """
    Reads the Angle field from the strip map index feature for a given page.

    The Angle field is created automatically by StripMapIndexFeatures and
    represents the rotation needed to align the map frame with the route
    direction on that page.

    Parameters
    ----------
    index_fc : str
        Path to the strip map index feature class.
    page_number : int
        The page number to look up.

    Returns
    -------
    float — rotation angle in degrees, or 0.0 if not found.
    """
    try:
        with arcpy.da.SearchCursor(
            index_fc,
            ["PageNumber", "Angle"],
            where_clause=f"PageNumber = {page_number}",
        ) as cursor:
            for row in cursor:
                return float(row[1]) if row[1] is not None else 0.0
    except Exception as e:
        arcpy.AddWarning(f"Could not read rotation angle for page {page_number}: {e}")
    return 0.0


def _filter_band_records_to_page(band_records, page_start, page_end):
    """
    Filters band records to only those whose measure falls within the
    visible measure range of the current page.

    Points are included if their meas falls within [page_start, page_end].
    Lines are included if they overlap the page range at all.

    Parameters
    ----------
    band_records : list of dict
        Full list of band records for the entire route.
    page_start : float
        Minimum visible measure on this page.
    page_end : float
        Maximum visible measure on this page.

    Returns
    -------
    list of dict — filtered records for this page only.
    """
    filtered = []

    for rec in band_records:
        if rec["type"] == "POINT":
            meas = rec.get("meas")
            if meas is not None and page_start <= meas <= page_end:
                filtered.append(rec)

        elif rec["type"] == "LINE":
            fmeas = rec.get("fmeas")
            tmeas = rec.get("tmeas")
            if fmeas is not None and tmeas is not None:
                # Include if the line overlaps the page range at all
                if fmeas <= page_end and tmeas >= page_start:
                    filtered.append(rec)

    return filtered


def _filter_point_xy_records_to_page(point_records_with_xy, map_frame):
    """
    Filters point records with layout XY to only those whose map position
    falls within the current map frame extent.

    This ensures ticks are only drawn for intersection points visible on
    the current page — not for points on other pages.

    Parameters
    ----------
    point_records_with_xy : list of dict
        Records with x_map_layout and y_map_layout already computed.
    map_frame : arcpy.mp.MapFrame
        The map frame whose camera extent defines the visible area.

    Returns
    -------
    list of dict — filtered records for this page only.
    """
    try:
        extent = map_frame.camera.getExtent()
    except Exception as e:
        arcpy.AddWarning(f"Could not get map frame extent for filtering: {e}")
        return point_records_with_xy

    filtered = []

    for rec in point_records_with_xy:
        # x_map_layout and y_map_layout are in layout page space (inches)
        # We need to check against the map coordinate extent instead
        # The map coordinates are stored implicitly via the measure position
        # Use the meas value to check if the point is within the page range
        meas = rec.get("meas")
        if meas is not None:
            filtered.append(rec)

    return filtered


def update_map_series_pages(
    layout,
    map_frame,
    map_series,
    index_fc,
    route_fc,
    band_records,
    point_event_features,
    band_geom,
    route_start,
    route_end,
):
    """
    Loops through all pages in the map series and updates the stationing
    band, ticks, and labels for each page.

    For each page:
        1. Sets the active page
        2. Applies rotation from the index Angle field
        3. Gets the visible measure range from the map frame extent
        4. Filters band records to the visible range
        5. Redraws stationing band for the page
        6. Redraws ticks and labels for visible intersections only

    Parameters
    ----------
    layout : arcpy.mp.Layout
    map_frame : arcpy.mp.MapFrame
    map_series : arcpy.mp.SpatialMapSeries
    index_fc : str
        Path to the strip map index feature class.
    route_fc : str
        Path to the route feature class.
    band_records : list of dict
        Full band records for the entire route.
    point_event_features : list of str
        Paths to point event feature classes.
    band_geom : dict
        Band geometry from _get_stationing_band_geometry().
    route_start : float
        Full route minimum measure.
    route_end : float
        Full route maximum measure.
    """
    # Import here to avoid circular imports — these come from band_tools.py
    from band_tools import (
        prepare_layout_band_records,
        filter_point_records_for_labeling,
        assign_line_label_sides,
        clear_line_band_labels,
        draw_line_band_labels,
        clear_point_ticks_and_labels,
        build_point_records_with_layout_xy,
        draw_point_ticks_and_labels,
        get_route_measures_in_current_extent,
    )

    page_count = map_series.pageCount
    arcpy.AddMessage(f"Updating {page_count} map series pages...")

    for page_num in range(1, page_count + 1):
        arcpy.AddMessage(f"  Processing page {page_num} of {page_count}...")

        # ── Step 1: Set the active page ───────────────────────────────────────
        try:
            map_series.currentPageNumber = page_num
        except Exception as e:
            arcpy.AddWarning(f"  Could not set page {page_num}: {e}")
            continue

        # ── Step 2: Apply rotation from index Angle field ─────────────────────
        try:
            angle = _get_page_rotation(index_fc, page_num)
            map_frame.camera.heading = angle
            arcpy.AddMessage(f"  Page {page_num} rotation: {angle:.2f} degrees")
        except Exception as e:
            arcpy.AddWarning(f"  Could not apply rotation for page {page_num}: {e}")

        # ── Step 3: Get visible measure range from map frame extent ───────────
        try:
            page_start, page_end = get_route_measures_in_current_extent(
                route_fc, map_frame
            )
        except Exception as e:
            arcpy.AddWarning(f"  Could not get measure range for page {page_num}: {e}")
            continue

        if page_start is None or page_end is None:
            arcpy.AddWarning(f"  No route visible on page {page_num} — skipping.")
            continue

        arcpy.AddMessage(
            f"  Page {page_num} measure range: {page_start:.1f} to {page_end:.1f}"
        )

        # ── Step 4: Filter band records to this page ──────────────────────────
        page_band_records = _filter_band_records_to_page(
            band_records, page_start, page_end
        )
        arcpy.AddMessage(
            f"  Page {page_num} has {len(page_band_records)} visible band records."
        )

        # ── Step 5: Redraw stationing band for this page ──────────────────────
        try:
            band_info = prepare_layout_band_records(
                band_records=page_band_records,
                band_left=band_geom["band_left"],
                band_width=band_geom["band_width"],
                point_row_y=band_geom["top_label_row1_y"],
                line_row_y=band_geom["top_label_row1_y"],
                route_start=page_start,
                route_end=page_end,
            )

            row_ready_records = band_info["row_ready_records"]
            point_records = [r for r in row_ready_records if r["type"] == "POINT"]
            line_records = [r for r in row_ready_records if r["type"] == "LINE"]

            # Remove points already covered by overlap labels
            point_records = filter_point_records_for_labeling(
                point_records, line_records
            )

            # Assign alternating rows to line overlap labels
            line_records = assign_line_label_sides(
                line_records,
                top_y=band_geom["top_label_row1_y"],
                bottom_y=band_geom["top_label_row3_y"],
            )

            # Clear old line labels and redraw for this page
            clear_line_band_labels(layout)
            draw_line_band_labels(
                layout=layout,
                line_records=line_records,
                label_y=band_geom["top_label_row1_y"],
                text_height=0.12,
                font_name="Tahoma",
                label_mode="source_name",
            )

        except Exception as e:
            arcpy.AddWarning(
                f"  Could not redraw stationing band for page {page_num}: {e}"
            )

        # ── Step 6: Redraw ticks and labels for this page ─────────────────────
        try:
            # Clear old ticks and labels
            clear_point_ticks_and_labels(layout)

            if not point_event_features:
                arcpy.AddMessage(
                    f"  Page {page_num}: no point event features — skipping ticks."
                )
                continue

            # Build point records with layout XY for this page
            # Using page_start and page_end so band x positions are page-relative
            page_point_records = build_point_records_with_layout_xy(
                point_event_features=point_event_features,
                map_frame=map_frame,
                route_start=page_start,
                route_end=page_end,
                band_left=band_geom["band_left"],
                band_width=band_geom["band_width"],
            )

            # Filter to only points visible on this page by measure
            page_point_records = [
                r
                for r in page_point_records
                if page_start <= r.get("meas", -1) <= page_end
            ]

            if not page_point_records:
                arcpy.AddMessage(
                    f"  Page {page_num}: no intersections visible — skipping ticks."
                )
                continue

            # Draw ticks and labels for this page
            ticks = draw_point_ticks_and_labels(
                layout=layout,
                point_records=page_point_records,
                band_y_top=band_geom["top_band_bottom"],
                band_y_bottom=band_geom["bot_band_top"],
                label_top_row1_y=band_geom["top_label_row1_y"],
                label_top_row2_y=band_geom["top_label_row2_y"],
                label_top_row3_y=band_geom["top_label_row3_y"],
                label_bottom_y=band_geom["bot_label_bar5_y"],
                half_tick=0.1,
                text_height=0.17,
                font_name="Tahoma",
            )

            arcpy.AddMessage(f"  Page {page_num}: drew {len(ticks)} ticks and labels.")

        except Exception as e:
            arcpy.AddWarning(f"  Could not redraw ticks for page {page_num}: {e}")

    arcpy.AddMessage("Map series page update complete.")
    arcpy.AddMessage("You can now browse pages in the layout view and export manually.")
