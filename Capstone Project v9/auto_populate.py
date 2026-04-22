import arcpy
import datetime
import os

ENABLE_INTERSECTION_SUMMARY = False


# AUTO-POPULATE LAYOUT TEXT ELEMENTS
#
# Fills layout text elements that can be derived automatically from the
# tool inputs and pipeline outputs.
#
# Supports both full-route mode (single layout) and per-page mode (map series).
# In per-page mode, pass page_start and page_end instead of route_start/end,
# and pass page_band_records filtered to the current page.
#
# Elements auto-populated:
#   - Pipe Name           from input line feature class base name
#   - Starting Station    from route_start (or page_start in map series)
#   - Ending Station      from route_end   (or page_end   in map series)
#   - Total Length        from route_end - route_start
#   - Date                from today's date
#   - Coordinate System   from route spatial reference
#   - From / To           from input line feature class extent
#   - Intersection Table  from band_records (filtered to page in map series)
#   - Intersection Summary from band_records grouped by source name
#
# Elements left blank for manual entry:
#   - Project Number, Client
#   - Notes, Disclaimer, Data Sources
#   - Diameter, Material, Type, Company, Company Logo
#   - Completed By, Reviewed By, Signed By

def _get_named_text_elements(layout, element_name):
    """
    Returns every text element on the layout that matches element_name.

    Map-series reruns can leave behind duplicate text elements when a previous
    run partially failed or when ArcGIS delays layout refreshes. Working with
    the full match list instead of only the first match prevents stale page
    content from leaking into later pages.
    """
    return [
        el
        for el in layout.listElements("TEXT_ELEMENT")
        if getattr(el, "name", None) == element_name
    ]


def _delete_text_elements(layout, element_name):
    """
    Deletes all text elements that share the same name.

    This is stricter than deleting only the first match and is important for
    map-series page redraws where duplicate stale text can otherwise stack on
    top of current-page content.
    """
    removed = 0
    for el in _get_named_text_elements(layout, element_name):
        try:
            el.delete()
            removed += 1
        except Exception:
            pass
    return removed


def _set_text_element_at(
    layout,
    project,
    element_name,
    text,
    x,
    y,
    font_size=3,
    anchor="CenterPoint",
):
    """
    Creates or updates a text element at a specific x, y position on the layout.

    Deletes any existing element with the same name first so reruns do not
    stack duplicate elements on top of each other.
    """
    _delete_text_elements(layout, element_name)

    if not text:
        return

    try:
        txt = project.createTextElement(
            layout,
            arcpy.Point(x, y),
            "POINT",
            text,
            font_size,
        )
        txt.name = element_name

        cim = txt.getDefinition("V3")
        cim.anchor = anchor
        cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
        cim.graphic.symbol.symbol.height = font_size
        txt.setDefinition(cim)
        txt.name = element_name

    except Exception as e:
        arcpy.AddWarning(f"Could not create text element '{element_name}': {e}")


def _set_text_element(layout, element_name, new_text):
    """
    Finds a text element on the layout by name and updates its text content.
    In ArcGIS Pro 3.3+, layout.listElements searches all elements including
    those inside groups.
    """
    matches = _get_named_text_elements(layout, element_name)
    if matches:
        # Keep the first matching element and remove any stale duplicates so the
        # layout cannot show both the current page's text and an older page's
        # text at the same time.
        keeper = matches[0]
        keeper.text = new_text
        for extra in matches[1:]:
            try:
                extra.delete()
            except Exception:
                pass
        return True

    arcpy.AddWarning(
        f"Auto-populate: could not find text element '{element_name}' on layout."
    )
    return False


def _clear_text_element(layout, element_name):
    """
    Clears the text content of a named element to an empty string.
    Used to blank out rows that have no data on the current page.
    """
    cleared = False
    for el in _get_named_text_elements(layout, element_name):
        try:
            el.text = ""
            cleared = True
        except Exception:
            pass
    return cleared


def _upsert_text_element_at(
    layout,
    project,
    element_name,
    text,
    x,
    y,
    font_size=3,
    anchor="CenterPoint",
):
    """
    Updates an existing named text element in place, or creates it if missing.

    This is safer than delete-and-recreate for layouts that may already contain
    grouped or stale elements, and it also repairs older layouts that were
    created before certain placeholder rows existed.
    """
    def _create_named_text_element(content):
        txt = project.createTextElement(
            layout,
            arcpy.Point(x, y),
            "POINT",
            content if content else " ",
            font_size,
        )
        txt.name = element_name

        cim = txt.getDefinition("V3")
        cim.anchor = anchor
        cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
        cim.graphic.symbol.symbol.height = font_size
        txt.setDefinition(cim)
        txt.name = element_name  # re-assert: setDefinition can reset the name to ""
        return txt

    matches = _get_named_text_elements(layout, element_name)
    if matches:
        keeper = matches[0]
        updated = False
        try:
            keeper.text = text
            keeper.elementPositionX = x
            keeper.elementPositionY = y
            updated = True
        except Exception:
            updated = False

        for extra in matches[1:]:
            try:
                extra.delete()
            except Exception:
                pass

        if not updated:
            try:
                keeper.delete()
            except Exception:
                pass
            try:
                _create_named_text_element(text)
                return True
            except Exception as e:
                arcpy.AddWarning(f"Could not create text element '{element_name}': {e}")
                return False

        try:
            cim = keeper.getDefinition("V3")
            cim.anchor = anchor
            cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
            cim.graphic.symbol.symbol.height = font_size
            keeper.setDefinition(cim)
            keeper.name = element_name  # re-assert: setDefinition can reset the name to ""
        except Exception:
            pass
        return True

    try:
        _create_named_text_element(text)
        return True

    except Exception as e:
        arcpy.AddWarning(f"Could not create text element '{element_name}': {e}")
        return False


def _format_chainage(value):
    """
    Formats a raw measure value into chainage string e.g. 1230 -> '1+230'.
    Matches the chainage_code_block() logic in events_tools.py.
    """
    val = int(round(float(value)))
    km = val // 1000
    remainder = val % 1000
    return f"{km}+{remainder:03d}"


def _format_coordinate(value, decimal_places=2):
    """
    Formats a coordinate value to a readable string.
    Rounds to the given number of decimal places.
    """
    return f"{round(value, decimal_places)}"


def _clear_intersection_table(layout, project, width, height, row_count=8):
    """
    Clears all intersection table row text elements.
    Called before repopulating so stale data from previous pages is removed.
    """
    col_id_x = width * 0.6330
    col_stationing_x = width * 0.6890
    col_type_x = width * 0.7440

    row_y_positions = [
        height * ((0.1411 + 0.1613) / 2),
        height * ((0.1209 + 0.1411) / 2),
        height * ((0.1007 + 0.1209) / 2),
        height * ((0.0805 + 0.1007) / 2),
        height * ((0.0603 + 0.0805) / 2),
        height * ((0.0401 + 0.0603) / 2),
        height * ((0.0199 + 0.0401) / 2),
        height * ((0.0000 + 0.0199) / 2),
    ]

    for idx in range(1, row_count + 1):
        # Delete and recreate as empty so the cell is visually blank
        _set_text_element_at(
            layout,
            project,
            f"Intersection Row {idx} ID",
            "",
            col_id_x,
            row_y_positions[idx - 1],
            6,
        )
        _set_text_element_at(
            layout,
            project,
            f"Intersection Row {idx} Stationing",
            "",
            col_stationing_x,
            row_y_positions[idx - 1],
            6,
        )
        _set_text_element_at(
            layout,
            project,
            f"Intersection Row {idx} Type",
            "",
            col_type_x,
            row_y_positions[idx - 1],
            4,
        )

    # Clear summary rows
    for idx in range(1, 5):
        _clear_text_element(layout, f"Intersection Summary Row {idx}")


def _record_sort_value(rec):
    """
    Returns the measure value used to sort table rows left-to-right.

    Point records sort by their single measure and line records sort by the
    start of the overlap so the intersection table follows the route order.
    """
    if rec.get("type") == "POINT":
        return rec.get("meas", float("inf"))
    return rec.get("fmeas", float("inf"))


def _build_intersection_summary(band_records):
    """
    Groups band records by source name and counts intersections/overlaps.

    Keeping the summary build separate makes it easier to reuse and prevents
    control-flow bugs from hiding the summary when the table succeeds.
    """
    summary = {}

    for rec in band_records:
        # Use `or` so that None and "" both fall back to "Unknown", not just
        # a missing key — otherwise sorted() crashes on NoneType comparisons.
        name = rec.get("source_name") or "Unknown"
        if name not in summary:
            summary[name] = {"intersections": 0, "overlaps": 0}

        if rec.get("type") == "POINT":
            summary[name]["intersections"] += 1
        elif rec.get("type") == "LINE":
            summary[name]["overlaps"] += 1

    return summary


def _delete_text_elements_in_box(layout, x_min, x_max, y_min, y_max):
    """
    Deletes text elements whose anchor point falls inside a layout box.

    This clears stale summary text from previous buggy runs, including unnamed
    leftovers that exact-name cleanup cannot catch.
    """
    removed = 0
    for el in layout.listElements("TEXT_ELEMENT"):
        try:
            x = el.elementPositionX
            y = el.elementPositionY
        except Exception:
            continue

        if x_min <= x <= x_max and y_min <= y <= y_max:
            try:
                el.delete()
                removed += 1
            except Exception:
                pass
    return removed


def _clean_summary_source_name(name):
    """
    Shortens band-record source names for the narrow summary panel.
    """
    text = (name or "Unknown").strip()
    lower = text.lower()
    for suffix in (" intersect", " intersection"):
        if lower.endswith(suffix):
            return text[: -len(suffix)].strip()
    return text


def _populate_intersection_summary(layout, project, width, height, band_records):
    """
    Updates the four summary rows using page-filtered band records.

    Uses in-place text updates (same pattern as all other auto-populate fields)
    rather than delete-and-recreate. Delete-and-recreate fails silently when
    the template element is inside a layout group — the delete is swallowed,
    the old element persists, a new one is created on top, and the row renders
    doubled/garbled text.
    """
    try:
        if not ENABLE_INTERSECTION_SUMMARY:
            summary_box_left = width * 0.77154545454545500
            summary_box_right = width * 0.84103636363636400
            summary_box_bottom = height * 0.0809058823529412
            summary_box_top = height * 0.1714941176470590

            # Temporary disable: clear any stale summary text from the row area
            # so exported PDFs stay clean while the summary feature is revisited.
            _delete_text_elements_in_box(
                layout,
                summary_box_left,
                summary_box_right,
                summary_box_bottom,
                summary_box_top,
            )
            for idx in range(1, 5):
                _clear_text_element(layout, f"Intersection Summary Row {idx}")

            arcpy.AddMessage("  Intersection Summary: disabled.")
            return

        summary = _build_intersection_summary(band_records)

        summary_box_left = width * 0.77154545454545500
        summary_box_right = width * 0.84103636363636400
        summary_box_bottom = height * 0.0809058823529412
        summary_box_top = height * 0.1714941176470590
        summary_text_x = summary_box_left + (width * 0.0045)
        summary_row_y_positions = [
            height * ((0.1585529411764710 + 0.1714941176470590) / 2),
            height * ((0.1326352941176470 + 0.1455764705882350) / 2),
            height * ((0.1068117647058820 + 0.1197647058823530) / 2),
            height * ((0.0809058823529412 + 0.0944000000000000) / 2),
        ]

        # Remove any dynamic text in the summary panel before drawing the
        # current page. This clears stale leftovers from previous reruns.
        _delete_text_elements_in_box(
            layout,
            summary_box_left,
            summary_box_right,
            summary_box_bottom,
            summary_box_top,
        )

        row_idx = 0
        for name, counts in sorted(summary.items()):
            parts = []
            if counts["intersections"] > 0:
                n = counts["intersections"]
                parts.append(f"{n} int.")
            if counts["overlaps"] > 0:
                n = counts["overlaps"]
                parts.append(f"{n} ovl.")

            if not parts:
                continue

            row_idx += 1
            if row_idx > 4:
                arcpy.AddWarning(
                    f"  Intersection Summary: {len(summary)} features found "
                    f"but only 4 rows available."
                )
                break

            display_name = _clean_summary_source_name(name)
            row_text = f"{display_name}: {', '.join(parts)}"
            _set_text_element_at(
                layout,
                project,
                f"Auto Intersection Summary Row {row_idx}",
                row_text,
                summary_text_x,
                summary_row_y_positions[row_idx - 1],
                2.5,
                anchor="LeftPoint",
            )

        if row_idx > 0:
            arcpy.AddMessage(
                f"  Intersection Summary: populated {row_idx} row{'s' if row_idx > 1 else ''}."
            )
        else:
            arcpy.AddMessage(
                "  Intersection Summary: no records on this page — cleared."
            )

    except Exception as e:
        arcpy.AddWarning(f"  Could not populate Intersection Summary: {e}")


def auto_populate_layout(
    layout,
    project,
    width,
    height,
    input_line_fc,
    route_fc,
    route_start,
    route_end,
    band_records,
    is_page_update=False,
):
    """
    Fills all auto-populatable text elements on the layout.

    Can be called in two modes:
        Full route mode  (is_page_update=False) — populates with full route values
        Per-page mode    (is_page_update=True)  — populates with page-specific values
                                                   route_start/end are the page range
                                                   band_records are filtered to the page

    Parameters
    ----------
    layout : arcpy.mp.Layout
    project : arcpy.mp.ArcGISProject
    width, height : float
        Page dimensions in inches.
    input_line_fc : str
        Path to input line feature class.
    route_fc : str
        Path to route feature class.
    route_start : float
        Start measure — full route start or page start in map series.
    route_end : float
        End measure — full route end or page end in map series.
    band_records : list of dict
        Full route records or page-filtered records in map series.
    is_page_update : bool
        If True, suppresses Pipe Name, Date, Coordinate System, From/To
        since those do not change per page.
    """
    if not is_page_update:
        arcpy.AddMessage("Auto-populating layout text elements...")
    else:
        arcpy.AddMessage("  Auto-populating page text elements...")

    # Pipe Name — only on first population, not per page
    if not is_page_update:
        try:
            pipe_name = os.path.splitext(os.path.basename(input_line_fc))[0]
            _set_text_element(layout, "Pipe Name", pipe_name)
            arcpy.AddMessage(f"  Pipe Name: {pipe_name}")
        except Exception as e:
            arcpy.AddWarning(f"  Could not set Pipe Name: {e}")

    # Starting and Ending Station — updates per page in map series
    try:
        start_ch = _format_chainage(route_start)
        end_ch = _format_chainage(route_end)
        _set_text_element(layout, "Starting Station", f"Starting Station: {start_ch}")
        _set_text_element(layout, "Ending Station", f"Ending Station:   {end_ch}")
        arcpy.AddMessage(f"  Starting Station: {start_ch}")
        arcpy.AddMessage(f"  Ending Station:   {end_ch}")
    except Exception as e:
        arcpy.AddWarning(f"  Could not set station fields: {e}")

    # Total Length — updates per page in map series
    try:
        total_length = route_end - route_start
        if total_length >= 1000:
            length_str = f"{total_length / 1000:.3f} km"
        else:
            length_str = f"{total_length:.1f} m"
        _set_text_element(layout, "Total Length", f"Total Length: {length_str}")
        arcpy.AddMessage(f"  Total Length: {length_str}")
    except Exception as e:
        arcpy.AddWarning(f"  Could not set Total Length: {e}")

    # Date — only on first population
    if not is_page_update:
        try:
            today = datetime.date.today().strftime("%d/%m/%Y")
            _set_text_element(layout, "Date", today)
            arcpy.AddMessage(f"  Date: {today}")
        except Exception as e:
            arcpy.AddWarning(f"  Could not set Date: {e}")

    # Coordinate System — only on first population
    if not is_page_update:
        try:
            sr_name = arcpy.Describe(route_fc).spatialReference.name
            _set_text_element(layout, "Coordinate System", sr_name)
            arcpy.AddMessage(f"  Coordinate System: {sr_name}")
        except Exception as e:
            arcpy.AddWarning(f"  Could not set Coordinate System: {e}")

    # From / To — only on first population
    if not is_page_update:
        try:
            desc = arcpy.Describe(input_line_fc)
            extent = desc.extent

            from_str = (
                f"From: X {_format_coordinate(extent.XMin)}, "
                f"Y {_format_coordinate(extent.YMin)}"
            )
            to_str = (
                f"To:   X {_format_coordinate(extent.XMax)}, "
                f"Y {_format_coordinate(extent.YMax)}"
            )

            _set_text_element(layout, "From", from_str)
            _set_text_element(layout, "To", to_str)
            arcpy.AddMessage(f"  {from_str}")
            arcpy.AddMessage(f"  {to_str}")

        except Exception as e:
            arcpy.AddWarning(f"  Could not set From/To: {e}")

    # Intersection Table — always updates per page
    # Clear all rows first so stale data from previous page is removed
    try:
        _clear_intersection_table(layout, project, width, height)

        point_records = [r for r in band_records if r.get("type") == "POINT"]
        line_records = [r for r in band_records if r.get("type") == "LINE"]
        all_records = sorted(point_records + line_records, key=_record_sort_value)

        row_y_positions = [
            height * ((0.1411 + 0.1613) / 2),
            height * ((0.1209 + 0.1411) / 2),
            height * ((0.1007 + 0.1209) / 2),
            height * ((0.0805 + 0.1007) / 2),
            height * ((0.0603 + 0.0805) / 2),
            height * ((0.0401 + 0.0603) / 2),
            height * ((0.0199 + 0.0401) / 2),
            height * ((0.0000 + 0.0199) / 2),
        ]

        col_id_x = width * 0.6330
        col_stationing_x = width * 0.6890
        col_type_x = width * 0.7440

        for idx, rec in enumerate(all_records, start=1):
            if idx > 8:
                arcpy.AddWarning(
                    f"  Intersection Table: {len(all_records)} records found "
                    f"but only 8 rows available."
                )
                break

            row_y = row_y_positions[idx - 1]

            if rec["type"] == "POINT":
                chainage = rec.get("chainage", "")
                source_name = rec.get("source_name", "")
                rec_type = "Intersection"
            else:
                chainage = rec.get("range", "")
                source_name = rec.get("source_name", "")
                rec_type = "Overlap"

            _set_text_element_at(
                layout,
                project,
                f"Intersection Row {idx} ID",
                str(idx),
                col_id_x,
                row_y,
                6,
            )

            _set_text_element_at(
                layout,
                project,
                f"Intersection Row {idx} Stationing",
                chainage,
                col_stationing_x,
                row_y,
                6,
            )

            _set_text_element_at(
                layout,
                project,
                f"Intersection Row {idx} Type",
                f"{source_name} ({rec_type})",
                col_type_x,
                row_y,
                4,
            )

        if all_records:
            arcpy.AddMessage(
                f"  Intersection Table: populated {min(len(all_records), 8)} rows."
            )
        else:
            arcpy.AddMessage("  Intersection Table: no records on this page — cleared.")

    except Exception as e:
        arcpy.AddWarning(f"  Could not populate Intersection Table: {e}")

    _populate_intersection_summary(layout, project, width, height, band_records)

    arcpy.AddMessage("  Auto-population complete.")
