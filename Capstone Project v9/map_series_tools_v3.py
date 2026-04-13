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
    """
    Creates a strip map index feature class and sets up a spatial map series
    on the layout. The index features drive the per-page extent and rotation.

    Parameters
    ----------
    input_line_fc : str
        Path to the input pipeline feature class.
    output_gdb : str
        Path to the output geodatabase where the index FC is saved.
    layout : arcpy.mp.Layout
    map_frame : arcpy.mp.MapFrame
    main_map : arcpy.mp.Map
    scale : int
        Map series scale.
    orientation : str
        "Horizontal" or "Vertical".
    overlap_percent : int
        Overlap percentage between pages (0-99).

    Returns
    -------
    dict with keys: index_fc, index_layer, map_series
    """
    data_input = os.path.splitext(os.path.basename(str(input_line_fc)))[0]
    index_output = os.path.join(output_gdb, f"{data_input}_index")

    if arcpy.Exists(index_output):
        arcpy.management.Delete(index_output)

    # Validate numeric inputs
    scale = int(scale)
    overlap_percent = int(overlap_percent)

    if scale <= 0:
        raise ValueError("Map series scale must be greater than zero.")

    if overlap_percent < 0 or overlap_percent > 99:
        raise ValueError("Overlap percent must be between 0 and 99.")

    # Use 90% of map frame width and 65% of height so the route fits with margin
    mf_width = f"{float(map_frame.elementWidth)  * 0.90} Inches"
    mf_height = f"{float(map_frame.elementHeight) * 0.65} Inches"

    arcpy.AddMessage(f"Map frame width used: {mf_width}")
    arcpy.AddMessage(f"Map frame height used: {mf_height}")
    arcpy.AddMessage(f"Map series scale used: {scale}")
    arcpy.AddMessage(f"Map series overlap used: {overlap_percent}")
    arcpy.AddMessage(f"Map series orientation used: {orientation}")

    # Create strip map index features — one polygon per page
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

    # Add index layer to the map — hidden from legend
    index_layer = main_map.addDataFromPath(index_output)
    index_layer.visible = False

    # Create the spatial map series driven by the index layer
    map_series = layout.createSpatialMapSeries(
        mapframe=map_frame,
        index_layer=index_layer,
        name_field="PageNumber",
        sort_field="PageNumber",
    )

    # Configure map series via CIM
    cim = map_series.getDefinition("V3")
    cim.enabled = True
    cim.mapFrameName = map_frame.name
    cim.indexLayerURI = index_layer.getDefinition("V3").uRI
    cim.sortAscending = True
    cim.extentOptions = "BestFit"
    cim.rotationField = "Angle"  # auto-rotate to follow route
    cim.startingPageNumber = 1
    map_series.setDefinition(cim)

    return {
        "index_fc": index_output,
        "index_layer": index_layer,
        "map_series": map_series,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAP SERIES PAGE UPDATER
#
# Loops through every page and for each page:
#   1. Sets the active page
#   2. Applies rotation from the index Angle field
#   3. Gets the visible measure range from the map frame extent
#   4. Filters band records to the visible range
#   5. Redraws ticks and labels for this page only
#   6. Auto-populates all text elements with page-specific values
#      — empty pages get cleared tables and updated station values
# ─────────────────────────────────────────────────────────────────────────────


def _get_page_rotation(index_fc, page_number):
    """
    Reads the Angle field from the strip map index feature for a given page.

    The Angle field is created automatically by StripMapIndexFeatures and
    represents the rotation needed to align the map frame with the route
    direction on that page.

    Returns 0.0 if the angle cannot be read.
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
    Filters band records to only those visible on the current page.

    POINT records are included if their meas falls within [page_start, page_end].
    LINE records are included if they overlap the page range at all.
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
                # Include if the overlap range intersects the page range at all
                if fmeas <= page_end and tmeas >= page_start:
                    filtered.append(rec)

    return filtered


def _get_page_shape(index_fc, page_number):
    """
    Returns the strip-map index polygon for a single map-series page.

    We use the real polygon geometry, not just its extent, so page-aware
    filtering follows the true rotated page footprint.
    """
    with arcpy.da.SearchCursor(
        index_fc,
        ["PageNumber", "SHAPE@"],
        where_clause=f"PageNumber = {page_number}",
    ) as cursor:
        for row in cursor:
            return row[1]
    return None


def _export_layout_page_pdf(layout, pdf_output_folder, layout_name, page_num):
    """
    Exports the currently drawn layout page to an individual PDF.

    The layout already contains page-specific custom graphics/text at this
    point, so exporting the layout directly preserves those custom elements.
    """
    os.makedirs(pdf_output_folder, exist_ok=True)
    page_pdf_path = os.path.join(
        pdf_output_folder, f"{layout_name}_Page_{page_num:02d}.pdf"
    )

    if os.path.exists(page_pdf_path):
        os.remove(page_pdf_path)

    layout.exportToPDF(
        out_pdf=page_pdf_path,
        resolution=300,
        image_quality="BEST",
        jpeg_compression_quality=80,
    )
    return page_pdf_path


def _merge_exported_page_pdfs(page_pdf_paths, merged_pdf_path):
    """
    Merges the individually exported page PDFs into a single deliverable.

    We intentionally merge the already-rendered page PDFs instead of calling
    map_series.exportToPDF because custom layout graphics are shared across all
    map-series pages and must be redrawn page-by-page before export.
    """
    if not page_pdf_paths:
        raise ValueError("No page PDFs were supplied for merging.")

    if os.path.exists(merged_pdf_path):
        os.remove(merged_pdf_path)

    pdf_doc = arcpy.mp.PDFDocumentCreate(merged_pdf_path)
    try:
        for pdf_path in page_pdf_paths:
            if pdf_path and os.path.exists(pdf_path):
                pdf_doc.appendPages(pdf_path)
    finally:
        pdf_doc.saveAndClose()

    return merged_pdf_path


def _resolve_preview_page_number(map_series, page_count):
    """
    Returns a safe page number to leave active in the layout after processing.

    Custom ticks/tables are shared layout elements, so after batch exporting we
    redraw one final preview page and leave the layout on that page for the user.
    """
    try:
        page_num = int(getattr(map_series, "currentPageNumber", 1) or 1)
    except Exception:
        page_num = 1

    if page_num < 1 or page_num > page_count:
        return 1
    return page_num


def _update_single_map_series_page(
    layout,
    map_frame,
    map_series,
    index_fc,
    route_fc,
    band_records,
    point_event_features,
    line_event_features,
    band_geom,
    input_line_fc,
    project,
    width,
    height,
    page_num,
    page_count,
    scale=None,
):
    """
    Redraws all custom page-specific content for a single map-series page.

    ArcGIS Pro updates map-driven content automatically for map series, but the
    stationing band ticks and the custom table/summary text are plain layout
    elements. Those elements are shared across all pages, so they must be
    cleared and rebuilt every time we switch pages.
    """
    from band_tools import (
        clear_point_ticks_and_labels,
        build_point_records_with_layout_xy,
        build_line_records_with_layout_xy,
        draw_point_ticks_and_labels,
        get_route_measures_in_extent,
    )
    from auto_populate import auto_populate_layout

    arcpy.AddMessage(f"  Processing page {page_num} of {page_count}...")

    page_band_records = []
    page_summary_records = []
    all_page_records = []

    try:
        map_series.currentPageNumber = page_num
    except Exception as e:
        arcpy.AddWarning(f"  Could not set page {page_num}: {e}")
        return None

    try:
        angle = _get_page_rotation(index_fc, page_num)
        map_frame.camera.heading = angle
        arcpy.AddMessage(f"  Page {page_num} rotation: {angle:.2f} degrees")
    except Exception as e:
        arcpy.AddWarning(f"  Could not apply rotation for page {page_num}: {e}")

    if scale is not None:
        try:
            map_frame.camera.scale = int(scale)
            arcpy.AddMessage(f"  Page {page_num} scale locked to: {int(scale)}")
        except Exception as e:
            arcpy.AddWarning(f"  Could not set scale for page {page_num}: {e}")

    page_shape = None
    page_extent = None
    page_start = None
    page_end = None

    try:
        page_shape = _get_page_shape(index_fc, page_num)
        if page_shape is None:
            arcpy.AddWarning(f"  Could not read page shape for page {page_num}.")
            return None

        page_extent = page_shape.extent
        page_start, page_end = get_route_measures_in_extent(route_fc, page_shape)
    except Exception as e:
        arcpy.AddWarning(f"  Could not get measure range for page {page_num}: {e}")
        return None

    if page_start is None or page_end is None:
        arcpy.AddWarning(f"  No route visible on page {page_num} — skipping.")
        return None

    arcpy.AddMessage(
        f"  Page {page_num} index extent: "
        f"XMin={page_extent.XMin:.1f}, XMax={page_extent.XMax:.1f}, "
        f"YMin={page_extent.YMin:.1f}, YMax={page_extent.YMax:.1f}"
    )
    arcpy.AddMessage(
        f"  Page {page_num} measure range from index extent: "
        f"{page_start:.1f} to {page_end:.1f}"
    )

    page_band_records = _filter_band_records_to_page(band_records, page_start, page_end)
    # Start with the route-table records as a fallback, then replace them with
    # page-specific event-feature records once we build those below. The event
    # features follow the same geometry/tick path the user sees on the sheet, so
    # using them for the table/summary keeps the text in sync with the drawn page.
    page_summary_records = list(page_band_records)
    arcpy.AddMessage(
        f"  Page {page_num}: {len(page_band_records)} visible band records."
    )

    try:
        # Always clear the previous page's custom graphics first so stale ticks
        # do not leak into the next page export or preview.
        clear_point_ticks_and_labels(layout)

        page_point_records = []
        if point_event_features:
            page_point_records = build_point_records_with_layout_xy(
                point_event_features=point_event_features,
                map_frame=map_frame,
                route_start=page_start,
                route_end=page_end,
                band_left=band_geom["band_left"],
                band_width=band_geom["band_width"],
            )
            page_point_records = [
                r
                for r in page_point_records
                if page_start <= r.get("meas", -1) <= page_end
            ]

        page_line_records = []
        if line_event_features:
            page_line_records = build_line_records_with_layout_xy(
                line_event_features=line_event_features,
                map_frame=map_frame,
                route_start=page_start,
                route_end=page_end,
                band_left=band_geom["band_left"],
                band_width=band_geom["band_width"],
            )
            page_line_records = [
                r
                for r in page_line_records
                if r.get("fmeas", -1) <= page_end and r.get("tmeas", -1) >= page_start
            ]

        # Keep an undeduplicated copy for the intersection table/summary. Those
        # sections should report both visible point intersections and visible line
        # overlaps on the current page.
        page_summary_records = page_point_records + page_line_records

        line_source_names = {r.get("source_name") for r in page_line_records}
        page_point_records = [
            r for r in page_point_records if r.get("source_name") not in line_source_names
        ]

        all_page_records = page_point_records + page_line_records

        if all_page_records:
            ticks = draw_point_ticks_and_labels(
                layout=layout,
                point_records=all_page_records,
                band_y_top=band_geom["top_band_bottom"],
                band_y_bottom=band_geom["bot_band_top"],
                label_top_row1_y=band_geom["top_label_row1_y"],
                label_top_row2_y=band_geom["top_label_row2_y"],
                label_top_row3_y=band_geom["top_label_row3_y"],
                label_top_row4_y=band_geom["top_label_row4_y"],
                label_bottom_row1_y=band_geom["bot_label_row1_y"],
                label_bottom_row2_y=band_geom["bot_label_row2_y"],
                label_bottom_row3_y=band_geom["bot_label_row3_y"],
                label_bottom_row4_y=band_geom["bot_label_row4_y"],
                half_tick=0.1,
                text_height=0.17,
                font_name="Tahoma",
            )
            arcpy.AddMessage(
                f"  Page {page_num}: drew {len(ticks)} ticks and labels."
            )
        else:
            arcpy.AddMessage(
                f"  Page {page_num}: no features visible — bands cleared."
            )

    except Exception as e:
        arcpy.AddWarning(f"  Could not redraw ticks for page {page_num}: {e}")

    try:
        auto_populate_layout(
            layout=layout,
            project=project,
            width=width,
            height=height,
            input_line_fc=input_line_fc,
            route_fc=route_fc,
            route_start=page_start,
            route_end=page_end,
            band_records=page_summary_records,
            is_page_update=True,
        )
    except Exception as e:
        arcpy.AddWarning(f"  Could not auto-populate text for page {page_num}: {e}")

    return {
        "page_number": page_num,
        "page_start": page_start,
        "page_end": page_end,
        "page_band_records": page_summary_records,
        "drawn_record_count": len(all_page_records),
    }


def update_map_series_pages(
    layout,
    map_frame,
    map_series,
    index_fc,
    route_fc,
    band_records,
    point_event_features,
    line_event_features,
    band_geom,
    route_start,
    route_end,
    input_line_fc,
    project,
    width,
    height,
    scale=None,
    export_pdf=False,
    pdf_output_folder=None,
    layout_name="Layout",
):
    """
    Updates custom map-series content and optionally exports a complete PDF set.

    Important ArcGIS Pro behavior:
        Native map-series elements update automatically per page, but the band
        ticks/labels and the manually written table/summary are shared layout
        elements. Because of that, the reliable workflow is:

        1. Switch to a page
        2. Redraw the custom layout elements for that page
        3. Export that page immediately
        4. Merge the exported page PDFs afterwards

    When export_pdf is False we update only the active preview page, since
    browsing to another page in the layout will not auto-refresh these custom
    layout graphics without rerunning the tool.

    Parameters
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
    line_event_features : list of str
        Paths to line event feature classes.
    band_geom : dict
        Band geometry from _get_stationing_band_geometry().
    route_start, route_end : float
        Full route measure range.
    input_line_fc : str
        Path to input line feature class — for auto-populate.
    project : arcpy.mp.ArcGISProject
        Current project — for auto-populate text element creation.
    width, height : float
        Page dimensions in inches.
    """
    page_count = map_series.pageCount
    arcpy.AddMessage(f"Updating {page_count} map series pages...")
    if page_count < 1:
        arcpy.AddWarning("No map series pages were found.")
        return

    preview_page_num = _resolve_preview_page_number(map_series, page_count)

    if export_pdf and pdf_output_folder:
        exported_page_paths = []
        arcpy.AddMessage(
            "Export PDF is enabled — drawing custom content page-by-page and "
            "merging the exported pages afterwards."
        )

        for page_num in range(1, page_count + 1):
            page_result = _update_single_map_series_page(
                layout=layout,
                map_frame=map_frame,
                map_series=map_series,
                index_fc=index_fc,
                route_fc=route_fc,
                band_records=band_records,
                point_event_features=point_event_features,
                line_event_features=line_event_features,
                band_geom=band_geom,
                input_line_fc=input_line_fc,
                project=project,
                width=width,
                height=height,
                page_num=page_num,
                page_count=page_count,
                scale=scale,
            )

            if page_result is None:
                continue

            try:
                page_pdf_path = _export_layout_page_pdf(
                    layout=layout,
                    pdf_output_folder=pdf_output_folder,
                    layout_name=layout_name,
                    page_num=page_num,
                )
                exported_page_paths.append(page_pdf_path)
                arcpy.AddMessage(f"  Page {page_num}: exported to {page_pdf_path}")
            except Exception as e:
                arcpy.AddWarning(f"  Page {page_num}: could not export PDF: {e}")

        if exported_page_paths:
            try:
                merged_pdf_path = os.path.join(
                    pdf_output_folder, f"{layout_name}_All_Pages.pdf"
                )
                _merge_exported_page_pdfs(exported_page_paths, merged_pdf_path)
                arcpy.AddMessage(f"Merged PDF exported to: {merged_pdf_path}")
            except Exception as e:
                arcpy.AddWarning(f"Could not merge exported page PDFs: {e}")
        else:
            arcpy.AddWarning("No individual page PDFs were created, so merge was skipped.")

        # Leave the layout on a sensible preview page when the tool finishes.
        _update_single_map_series_page(
            layout=layout,
            map_frame=map_frame,
            map_series=map_series,
            index_fc=index_fc,
            route_fc=route_fc,
            band_records=band_records,
            point_event_features=point_event_features,
            line_event_features=line_event_features,
            band_geom=band_geom,
            input_line_fc=input_line_fc,
            project=project,
            width=width,
            height=height,
            page_num=preview_page_num,
            page_count=page_count,
            scale=scale,
        )
    else:
        arcpy.AddMessage(
            "Export PDF is off — updating the active preview page only. "
            "Custom band graphics are redrawn for the visible page, not stored "
            "natively per map-series page."
        )

        _update_single_map_series_page(
            layout=layout,
            map_frame=map_frame,
            map_series=map_series,
            index_fc=index_fc,
            route_fc=route_fc,
            band_records=band_records,
            point_event_features=point_event_features,
            line_event_features=line_event_features,
            band_geom=band_geom,
            input_line_fc=input_line_fc,
            project=project,
            width=width,
            height=height,
            page_num=preview_page_num,
            page_count=page_count,
            scale=scale,
        )

    arcpy.AddMessage("Map series page update complete.")
    arcpy.AddMessage(
        "The active layout page has been refreshed. Use Export PDF for a fully "
        "populated multi-page deliverable built from page-by-page redraws."
    )
