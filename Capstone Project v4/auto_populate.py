import arcpy
import datetime
import os


# ─────────────────────────────────────────────────────────────────────────────
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
#   - Project Name, Project Number, Client, Location Address
#   - Notes, Disclaimer, Data Sources
#   - Diameter, Material, Type, Company, Company Logo
#   - Completed By, Reviewed By, Signed By
# ─────────────────────────────────────────────────────────────────────────────


def _set_text_element_at(layout, project, element_name, text, x, y, font_size=3):
    """
    Creates or updates a text element at a specific x, y position on the layout.

    Deletes any existing element with the same name first so reruns do not
    stack duplicate elements on top of each other.
    """
    # Delete existing element with this name to avoid duplicates on rerun
    for el in layout.listElements("TEXT_ELEMENT"):
        if el.name == element_name:
            el.delete()
            break

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
        cim.anchor = "CenterPoint"
        cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
        cim.graphic.symbol.symbol.height = font_size
        txt.setDefinition(cim)

    except Exception as e:
        arcpy.AddWarning(f"Could not create text element '{element_name}': {e}")


def _set_text_element(layout, element_name, new_text):
    """
    Finds a text element on the layout by name and updates its text content.
    In ArcGIS Pro 3.3+, layout.listElements searches all elements including
    those inside groups.
    """
    for el in layout.listElements("TEXT_ELEMENT"):
        if el.name == element_name:
            el.text = new_text
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
    for el in layout.listElements("TEXT_ELEMENT"):
        if el.name == element_name:
            el.text = ""
            return True
    return False


def _format_chainage(value):
    """
    Formats a raw measure value into chainage string e.g. 1230 -> '1+230'.
    Matches the chainage_code_block() logic in events_tools_v3.py.
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

    #  Total Length — updates per page in map series
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

    #  Date — only on first population
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
        all_records = point_records + line_records

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

        # Intersection Summary always updates per page
        summary = {}

        for rec in band_records:
            name = rec.get("source_name", "Unknown")
            if name not in summary:
                summary[name] = {"intersections": 0, "overlaps": 0}

            if rec["type"] == "POINT":
                summary[name]["intersections"] += 1
            elif rec["type"] == "LINE":
                summary[name]["overlaps"] += 1

        # Clear all summary rows first
        for idx in range(1, 5):
            _clear_text_element(layout, f"Intersection Summary Row {idx}")

        for idx, (name, counts) in enumerate(summary.items(), start=1):
            if idx > 4:
                arcpy.AddWarning(
                    f"  Intersection Summary: {len(summary)} features found "
                    f"but only 4 rows available."
                )
                break

            parts = []
            if counts["intersections"] > 0:
                n = counts["intersections"]
                parts.append(f"{n} intersection{'s' if n > 1 else ''}")
            if counts["overlaps"] > 0:
                n = counts["overlaps"]
                parts.append(f"{n} overlap{'s' if n > 1 else ''}")

            row_text = f"{name}:  {', '.join(parts)}"
            _set_text_element(layout, f"Intersection Summary Row {idx}", row_text)

        if summary:
            arcpy.AddMessage(
                f"  Intersection Summary: populated {min(len(summary), 4)} rows."
            )
        else:
            arcpy.AddMessage(
                "  Intersection Summary: no records on this page — cleared."
            )

    except Exception as e:
        arcpy.AddWarning(f"  Could not populate Intersection Summary: {e}")

    arcpy.AddMessage("  Auto-population complete.")
