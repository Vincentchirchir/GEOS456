import arcpy

from geocoding_tools import _build_sheet_title, _get_input_extent

# Page proportions — all positions expressed as fractions of page height
# so the layout scales correctly across different page sizes.

# Top stationing band — top 1" of the page
BAND_TOP_UPPER_FRAC = 10.50 / 11.0   # top edge of the upper stationing band
BAND_BOTTOM_UPPER_FRAC = 9.50 / 11.0  # bottom edge of the upper stationing band

# Main map frame sits between the two bands
MAP_TOP_FRAC = BAND_BOTTOM_UPPER_FRAC  # 9.50" / 11"
MAP_BOTTOM_FRAC = 4.5 / 11.0           # 4.50" / 11"

# Bottom stationing band — 1" just above the bottom elements
BAND_TOP_LOWER_FRAC = MAP_BOTTOM_FRAC   # 4.50" / 11"
BAND_BOTTOM_LOWER_FRAC = 2.17 / 11.0   # 2.17" / 11"

# Bottom elements (Legend, Tables, Project Info) occupy 0 to 2.17"
BOTTOM_ELEMENTS_TOP_FRAC = BAND_BOTTOM_LOWER_FRAC

# Top band bar line y-positions
TOP_BAR5_FRAC = 10.5 / 11.0   # top of band
TOP_BAR1_FRAC = 10.0 / 11.0
TOP_BAR2_FRAC = 9.5 / 11.0
TOP_BAR3_FRAC = 9.0 / 11.0
TOP_BAR4_FRAC = 8.5 / 11.0   # bottom of band

# Bottom band bar line y-positions
BOT_BAR4_FRAC = 4.0 / 11.0   # top of band
BOT_BAR5_FRAC = 3.5 / 11.0
BOT_BAR6_FRAC = 3.0 / 11.0
BOT_BAR7_FRAC = 2.5 / 11.0   # bottom of band


def get_layout_dimensions(layout_size):
    """
    Returns (width, height) in inches for a named layout size.
    Defaults to Letter (11x8.5) if the size is not recognised.
    """
    sizes = {
        "Letter (11x8.5)": (11, 8.5),
        "Legal (14x8.5)": (14, 8.5),
        "Tabloid (17x11)": (17, 11),
        "ANSI C (22x17)": (22, 17),
        "ANSI D (34x22)": (34, 22),
        "ANSI E (44x34)": (44, 34),
    }
    return sizes.get(layout_size, (11, 8.5))


def generate_alignment_layout(
    layout_name,
    layout_size,
    main_map_name,
    mini_map_name,
    input_line_fc,
    output_gdb,
    create_map_series=False,
    map_series_scale=None,
    map_series_orientation=None,
    map_series_overlap=None,
):
    """
    Builds a complete alignment sheet layout in the current ArcGIS Pro project.

    Creates the layout, positions the main and mini map frames, zooms both to
    the input line extent, adds all standard elements (north arrow, scale bar,
    legend, title, boundary graphics), and optionally sets up a spatial map series.

    Parameters
    ----------
    layout_name : str
        Name for the new layout.
    layout_size : str
        Page size string e.g. "Tabloid (17x11)". See get_layout_dimensions().
    main_map_name : str
        Name of the ArcGIS Pro map to use as the main map frame.
    mini_map_name : str
        Name of the ArcGIS Pro map to use as the mini overview frame.
    input_line_fc : str
        Path to the input line feature class — used to set extents and title.
    output_gdb : str
        Path to the output geodatabase — used for map series index features.
    create_map_series : bool, optional
        If True, creates a strip-map spatial map series on the layout.
    map_series_scale : int, optional
        Scale for the map series (required when create_map_series is True).
    map_series_orientation : str, optional
        "Horizontal" or "Vertical" (required when create_map_series is True).
    map_series_overlap : int, optional
        Overlap percentage between pages 0-99 (required when create_map_series is True).

    Returns
    -------
    dict
        layout, layout_name, main_map_frame, mini_map_frame,
        width, height, map_series_info
    """
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    width, height = get_layout_dimensions(layout_size)
    arcpy.AddMessage(f"Creating layout '{layout_name}' with size {layout_size}.")

    main_map = aprx.listMaps(main_map_name)[0]
    mini_map = aprx.listMaps(mini_map_name)[0]
    arcpy.AddMessage(
        f"Using main map '{main_map_name}' and mini map '{mini_map_name}'."
    )

    layout = aprx.createLayout(width, height, "INCH", layout_name)

    # Main map frame bounds (as fractions of page size)
    x_min = width *  0.011818181818182  # left edge
    y_min = height * 0.4090941176470590  # bottom edge
    x_max = width                        # right edge
    y_max = height * 0.7272705882352940  # top edge

    main_extent = arcpy.Extent(x_min,
                               y_min,
                               x_max,
                               y_max)
    
    main_map_frame = layout.createMapFrame(main_extent,
                                           main_map, 
                                           "Map Frame")

    main_cim = main_map_frame.getDefinition("V3")
    main_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
    main_map_frame.setDefinition(main_cim)
    main_map_frame.locked = True

    #  Zoom map frame to the input line extent
    # This ensures the layout always shows the current study area, not a
    # hardcoded extent from a previous run.  _get_input_extent respects any
    # active selection so "Use the selected records" is honoured automatically.

    try:
        input_extent = _get_input_extent(input_line_fc)

        # Add a small buffer around the extent so the route is not clipped
        # to the very edge of the map frame
        x_buffer = (input_extent.XMax - input_extent.XMin) * 0.05
        y_buffer = (input_extent.YMax - input_extent.YMin) * 0.05

        buffered_extent = arcpy.Extent(
            input_extent.XMin - x_buffer,
            input_extent.YMin - y_buffer,
            input_extent.XMax + x_buffer,
            input_extent.YMax + y_buffer,
            spatial_reference=input_extent.spatialReference,
        )

        main_map_frame.camera.setExtent(buffered_extent)

        arcpy.AddMessage(f"Map frame zoomed to input line extent with 5% buffer.")

    except Exception as e:
        arcpy.AddWarning(
            f"Could not zoom map frame to input extent: {e}. "
            "You may need to set the extent manually."
        )

    # Mini map frame bounds
    x_min_mini = width * 0.32545454545454500
    y_min_mini = 0
    x_max_mini = width * 0.48090909090909100
    y_max_mini = height * 0.18443529411764700

    mini_extent = arcpy.Extent(x_min_mini,
                               y_min_mini,
                               x_max_mini,
                               y_max_mini)
    
    mini_map_frame = layout.createMapFrame(mini_extent, mini_map, "Mini Map Frame")

    mini_cim = mini_map_frame.getDefinition("V3")
    mini_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
    mini_map_frame.setDefinition(mini_cim)
    mini_map_frame.locked = True

    #  Zoom mini map frame to the input line extent
    # Same logic as the main map frame — respects any active selection.
    # A larger buffer is used so the mini map shows more surrounding context.
    
    try:
        input_extent = _get_input_extent(input_line_fc)

        # Use a 15% buffer for the mini map so it shows more context
        # around the route than the main map frame
        x_buffer = (input_extent.XMax - input_extent.XMin) * 0.15
        y_buffer = (input_extent.YMax - input_extent.YMin) * 0.15

        buffered_extent = arcpy.Extent(
            input_extent.XMin - x_buffer,
            input_extent.YMin - y_buffer,
            input_extent.XMax + x_buffer,
            input_extent.YMax + y_buffer,
            spatial_reference=input_extent.spatialReference,
        )

        mini_map_frame.camera.setExtent(buffered_extent)

        arcpy.AddMessage(f"Mini map frame zoomed to input line extent with 15% buffer.")

    except Exception as e:
        arcpy.AddWarning(
            f"Could not zoom mini map frame to input extent: {e}. "
            "You may need to set the extent manually."
        )

    map_series_info = None

    if create_map_series:
        arcpy.AddMessage("Creating layout map series...")
        from map_series_tools import create_layout_map_series

        map_series_info = create_layout_map_series(
            input_line_fc=input_line_fc,
            output_gdb=output_gdb,
            layout=layout,
            map_frame=main_map_frame,
            main_map=main_map,
            scale=map_series_scale,
            orientation=map_series_orientation,
            overlap_percent=map_series_overlap,
        )

    # layout_elements is imported here rather than at module level to avoid a
    # circular import: layout_elements imports the constants defined above.
    from layout_elements import (
        add_north_arrow,
        add_scale_bar,
        add_map_scale_text,
        add_standard_texts,
        add_boundary_graphics,
        add_legend,
        add_auto_title,
    )

    arcpy.AddMessage("Adding layout elements...")
    add_boundary_graphics(aprx, layout, width, height, main_map_frame)
    add_north_arrow(aprx, layout, main_map_frame, width, height)
    add_legend(aprx, layout, main_map_frame, main_map_name, width, height)
    add_scale_bar(aprx, layout, main_map_frame, width, height)
    add_map_scale_text(aprx, layout, main_map_frame, width, height)
    add_standard_texts(aprx, layout, width, height)

    # ── Auto-generate the sheet title ────────────────────────────────────────
    # Derives title from the input FC name, reverse geocoded city, and year.
    # Requires an active ArcGIS Online portal sign-in (~0.04 credits).
    # Falls back gracefully to decimal coordinates if geocoding is unavailable.
    try:
        sheet_title, sheet_subtitle = _build_sheet_title(input_line_fc)
        add_auto_title(aprx, layout, width, height, sheet_title, sheet_subtitle)
        arcpy.AddMessage("Auto sheet title placed on layout.")
    except Exception as e:
        arcpy.AddWarning(
            f"Auto sheet title generation failed: {e}. "
            "The title block will not contain an auto-generated title. "
            "You can add it manually via the layout Contents pane."
        )

    # Restore the previous ArcGIS Pro behavior of activating the new layout
    # as soon as it has been built.
    layout.openView()

    arcpy.AddMessage(f"Layout '{layout.name}' generated successfully.")

    return {
        "layout": layout,
        "layout_name": layout.name,
        "main_map_frame": main_map_frame,
        "mini_map_frame": mini_map_frame,
        "width": width,
        "height": height,
        "map_series_info": map_series_info,
    }
