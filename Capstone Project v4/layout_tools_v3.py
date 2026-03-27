import arcpy
from layout_elements_v3 import (
    add_north_arrow,
    add_scale_bar,
    add_map_scale_text,
    add_standard_texts,
    add_boundary_graphics,
    add_legend,
)


def get_layout_dimensions(layout_size):
    sizes = {
        "Letter (11x8.5)": (11, 8.5),
        "Legal (14x8.5)": (14, 8.5),
        "Tabloid (17x11)": (17, 11),
        "ANSI C (22x17)": (22, 17),
        "ANSI D (34x22)": (34, 22),
        "ANSI E (44x34)": (44, 34),
    }
    return sizes.get(layout_size, (11, 8.5))


def _get_input_extent(input_line_fc):
    """Return the extent of input_line_fc, respecting any active selection.

    If the layer has selected features (i.e. the tool was run with
    'Use the selected records' enabled), only those features contribute
    to the extent.  Falls back to Describe().extent if no geometry is found.
    """
    xmin = xmax = ymin = ymax = None
    sr = None

    try:
        with arcpy.da.SearchCursor(input_line_fc, ["SHAPE@"]) as cursor:
            for (geom,) in cursor:
                if geom is None:
                    continue
                ext = geom.extent
                if sr is None:
                    sr = ext.spatialReference
                xmin = ext.XMin if xmin is None else min(xmin, ext.XMin)
                ymin = ext.YMin if ymin is None else min(ymin, ext.YMin)
                xmax = ext.XMax if xmax is None else max(xmax, ext.XMax)
                ymax = ext.YMax if ymax is None else max(ymax, ext.YMax)
    except Exception:
        pass

    if xmin is not None:
        return arcpy.Extent(xmin, ymin, xmax, ymax, spatial_reference=sr)

    # Fallback: no cursor results — use full dataset extent
    desc = arcpy.Describe(input_line_fc)
    return desc.extent


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
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    width, height = get_layout_dimensions(layout_size)
    arcpy.AddMessage(f"Creating layout '{layout_name}' with size {layout_size}.")

    main_map = aprx.listMaps(main_map_name)[0]
    mini_map = aprx.listMaps(mini_map_name)[0]
    arcpy.AddMessage(
        f"Using main map '{main_map_name}' and mini map '{mini_map_name}'."
    )

    layout = aprx.createLayout(width, height, "INCH", layout_name)

    # Main map frame
    main_extent = arcpy.Extent(
        width * 0.01181818181818180,
        height * (3.17 / 11.0),
        width,
        height * (9.50 / 11.0),
    )
    main_map_frame = layout.createMapFrame(main_extent, main_map, "Map Frame")

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

        # Apply the extent to the map frame camera
        main_map_frame.camera.setExtent(buffered_extent)

        arcpy.AddMessage(f"Map frame zoomed to input line extent with 5% buffer.")

    except Exception as e:
        arcpy.AddWarning(
            f"Could not zoom map frame to input extent: {e}. "
            "You may need to set the extent manually."
        )

    # Mini map frame
    mini_extent = arcpy.Extent(
        width * 0.32545454545454500,
        0,
        width * 0.55,
        height * 0.15181818181818200,
    )
    mini_map_frame = layout.createMapFrame(mini_extent, mini_map, "Mini Map Frame")

    mini_cim = mini_map_frame.getDefinition("V3")
    mini_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0
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

        # Apply the extent to the mini map frame camera
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
        from map_series_tools_v3 import create_layout_map_series

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

    arcpy.AddMessage("Adding layout elements...")
    add_boundary_graphics(aprx, layout, width, height)
    add_north_arrow(aprx, layout, main_map_frame, width, height)
    add_legend(aprx, layout, main_map_frame, main_map_name, width, height)
    add_scale_bar(aprx, layout, main_map_frame, width, height)
    add_map_scale_text(aprx, layout, main_map_frame, width, height)
    add_standard_texts(aprx, layout, width, height)

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
