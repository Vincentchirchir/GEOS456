import arcpy
import datetime


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-POPULATE LAYOUT TEXT ELEMENTS
#
# This  fills in layout text elements that can be derived automatically
# from the tool inputs and pipeline outputs. It targets elements by their
# name as set in add_standard_texts() in layout_elements_v3.py.
#
# Elements auto-populated:
#   - Pipe Name           from input line feature class base name
#   - Starting Station    from route_start measure
#   - Ending Station      from route_end measure
#   - Total Length        from route_end - route_start
#   - Date                from today's date
#   - Coordinate System   from route spatial reference
#   - From / To           from input line feature class extent
#   - Intersection Table  from band_records point intersections
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

    If an element with this name already exists it is deleted first so
    reruns do not stack duplicate text elements on top of each other.

    Parameters
    ----------
    layout : arcpy.mp.Layout
    project : arcpy.mp.ArcGISProject
    element_name : str
    text : str
    x, y : float
        Position in layout page units (inches).
    font_size : float
        Font size in points.
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

    Parameters
    ----------
    layout : arcpy.mp.Layout
    element_name : str
        Must match the name set on the element in add_standard_texts().
    new_text : str
        The text to write into the element.

    Returns
    -------
    bool — True if the element was found and updated, False if not found.
    """
    for el in layout.listElements("TEXT_ELEMENT"):
        if el.name == element_name:
            el.text = new_text
            return True

    # Warn if the element was not found — helps diagnose name mismatches
    arcpy.AddWarning(
        f"Auto-populate: could not find text element '{element_name}' on layout."
    )
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
    Formats a coordinate value to a readable string with units.
    Rounds to the given number of decimal places.
    """
    return f"{round(value, decimal_places)}"


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
):
    """
    Fills all auto-populatable text elements on the layout.

    Call this after the layout has been created and all text elements
    have been added by add_standard_texts() in layout_elements_v3.py.

    Parameters
    ----------
    layout : arcpy.mp.Layout
        The layout object containing the text elements to populate.
    input_line_fc : str
        Path to the input line feature class — used for pipe name and extent.
    route_fc : str
        Path to the route feature class — used for coordinate system.
    route_start : float
        Minimum measure value of the route (from get_route_measure_range).
    route_end : float
        Maximum measure value of the route (from get_route_measure_range).
    band_records : list of dict
        Records from build_band_records — used for intersection table and summary.
    """

    arcpy.AddMessage("Auto-populating layout text elements...")

    # Pipe Name
    # Use the base name of the input feature class — strips path and extension
    try:
        import os

        pipe_name = os.path.splitext(os.path.basename(input_line_fc))[0]
        _set_text_element(layout, "Pipe Name", pipe_name)
        arcpy.AddMessage(f"  Pipe Name: {pipe_name}")
    except Exception as e:
        arcpy.AddWarning(f"  Could not set Pipe Name: {e}")

    # Starting and Ending Station
    # Formatted as chainage strings e.g. 0+000 and 3+803
    try:
        start_ch = _format_chainage(route_start)
        end_ch = _format_chainage(route_end)
        _set_text_element(layout, "Starting Station", f"Starting Station: {start_ch}")
        _set_text_element(layout, "Ending Station", f"Ending Station:   {end_ch}")
        arcpy.AddMessage(f"  Starting Station: {start_ch}")
        arcpy.AddMessage(f"  Ending Station:   {end_ch}")
    except Exception as e:
        arcpy.AddWarning(f"  Could not set station fields: {e}")

    # Total Length
    # route_end - route_start gives the total measured length in route units
    try:
        total_length = route_end - route_start
        # Format as km if over 1000, otherwise in metres
        if total_length >= 1000:
            length_str = f"{total_length / 1000:.3f} km"
        else:
            length_str = f"{total_length:.1f} m"
        _set_text_element(layout, "Total Length", f"Total Length: {length_str}")
        arcpy.AddMessage(f"  Total Length: {length_str}")
    except Exception as e:
        arcpy.AddWarning(f"  Could not set Total Length: {e}")

    #  Date
    # Today's date formatted as DD/MM/YYYY
    try:
        today = datetime.date.today().strftime("%d/%m/%Y")
        _set_text_element(layout, "Date", today)
        arcpy.AddMessage(f"  Date: {today}")
    except Exception as e:
        arcpy.AddWarning(f"  Could not set Date: {e}")

    # Coordinate System
    # Read from the route feature class spatial reference
    try:
        sr_name = arcpy.Describe(route_fc).spatialReference.name
        _set_text_element(layout, "Coordinate System", sr_name)
        arcpy.AddMessage(f"  Coordinate System: {sr_name}")
    except Exception as e:
        arcpy.AddWarning(f"  Could not set Coordinate System: {e}")

    #  From / To
    # Read from the bounding extent of the input line feature class
    # Expressed as X/Y coordinates of the SW and NE corners
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

    # Intersection Table rows
    # Each column has its own text element positioned within its column box.
    # Column x positions match the boundary boxes in layout_elements_v3.py:
    #   ID column        → left of table to row divider 1  (~0.6058 to 0.6613)
    #   Stationing column → row divider 1 to row divider 2  (~0.6613 to 0.7167)
    #   Type column       → row divider 2 to table right    (~0.7167 to 0.7715)
    try:
        point_records = [r for r in band_records if r.get("type") == "POINT"]
        line_records = [r for r in band_records if r.get("type") == "LINE"]
        all_records = point_records + line_records

        # Y centre positions matching the actual Intersection Table Row boxes
        # Each centre = (y_max + y_min) / 2 for each row polygon

        row_y_positions = [
            height * ((0.1411 + 0.1613) / 2),  # Row 1 centre
            height * ((0.1209 + 0.1411) / 2),  # Row 2 centre
            height * ((0.1007 + 0.1209) / 2),  # Row 3 centre
            height * ((0.0805 + 0.1007) / 2),  # Row 4 centre
            height * ((0.0603 + 0.0805) / 2),  # Row 5 centre
            height * ((0.0401 + 0.0603) / 2),  # Row 6 centre
            height * ((0.0199 + 0.0401) / 2),  # Row 7 centre
            height * ((0.0000 + 0.0199) / 2),  # Row 8 centre
        ]

        # X centre positions for each column
        col_id_x = width * 0.6330  # centre of ID column
        col_stationing_x = width * 0.6890  # centre of Stationing column
        col_type_x = width * 0.7440  # centre of Type column

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

            # ID column — row number
            _set_text_element_at(
                layout,
                project,
                f"Intersection Row {idx} ID",
                str(idx),
                col_id_x,
                row_y,
                6,
            )

            #  Stationing column — chainage value
            _set_text_element_at(
                layout,
                project,
                f"Intersection Row {idx} Stationing",
                chainage,
                col_stationing_x,
                row_y,
                6,
            )

            #  Type column — feature name and type
            _set_text_element_at(
                layout,
                project,
                f"Intersection Row {idx} Type",
                f"{source_name} ({rec_type})",
                col_type_x,
                row_y,
                4,
            )

        arcpy.AddMessage(
            f"  Intersection Table: populated {min(len(all_records), 8)} rows."
        )

    except Exception as e:
        arcpy.AddWarning(f"  Could not populate Intersection Table: {e}")

    # Intersection Summary
    # Groups records by source_name and counts intersections and overlaps.
    # Layout has 4 summary row boxes.
    try:
        summary = {}  # { source_name: {"intersections": n, "overlaps": n} }

        for rec in band_records:
            name = rec.get("source_name", "Unknown")
            if name not in summary:
                summary[name] = {"intersections": 0, "overlaps": 0}

            if rec["type"] == "POINT":
                summary[name]["intersections"] += 1
            elif rec["type"] == "LINE":
                summary[name]["overlaps"] += 1

        for idx, (name, counts) in enumerate(summary.items(), start=1):
            if idx > 4:
                arcpy.AddWarning(
                    f"  Intersection Summary: {len(summary)} features found "
                    f"but only 4 rows available."
                )
                break

            intersections = counts["intersections"]
            overlaps = counts["overlaps"]

            # Build summary row text
            parts = []
            if intersections > 0:
                parts.append(
                    f"{intersections} intersection{'s' if intersections > 1 else ''}"
                )
            if overlaps > 0:
                parts.append(f"{overlaps} overlap{'s' if overlaps > 1 else ''}")

            row_text = f"{name}:  {', '.join(parts)}"

            element_name = f"Intersection Summary Row {idx}"
            _set_text_element(layout, element_name, row_text)

        arcpy.AddMessage(
            f"  Intersection Summary: populated {min(len(summary), 4)} rows."
        )

    except Exception as e:
        arcpy.AddWarning(f"  Could not populate Intersection Summary: {e}")

    arcpy.AddMessage("Auto-population complete.")
