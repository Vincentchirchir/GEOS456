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