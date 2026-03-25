import arcpy
from map_series_tools_v3 import create_layout_map_series
from layout_elements_v3 import (
    add_north_arrow,
    add_scale_bar,
    add_map_scale_text,
    add_standard_texts,
    add_boundary_graphics,
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
        height * 0.19767058823529400,
        width,
        height * 0.80117647058823500,
    )
    main_map_frame = layout.createMapFrame(main_extent, main_map, "Map Frame")

    main_cim = main_map_frame.getDefinition("V3")
    main_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
    main_map_frame.setDefinition(main_cim)
    main_map_frame.locked = True

    # Mini map frame
    mini_extent = arcpy.Extent(
        width * 0.32545454545454500,
        0,
        width * 0.55,
        height * 0.18443529411764700,
    )
    mini_map_frame = layout.createMapFrame(mini_extent, mini_map, "Mini Map Frame")

    mini_cim = mini_map_frame.getDefinition("V3")
    mini_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
    mini_map_frame.setDefinition(mini_cim)
    mini_map_frame.locked = True

    map_series_info = None

    if create_map_series:
        arcpy.AddMessage("Creating layout map series...")
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
    add_scale_bar(aprx, layout, main_map_frame, width, height)
    add_map_scale_text(aprx, layout, main_map_frame, width, height)
    add_standard_texts(aprx, layout, width, height)

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
