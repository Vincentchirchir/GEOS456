import arcpy


def apply_layer_labels(layer, feature_class, candidate_fields):
    field_names = [f.name for f in arcpy.ListFields(feature_class)]
    label_field = next((name for name in candidate_fields if name in field_names), None)
    if not label_field:
        return

    layer.showLabels = True
    for lbl in layer.listLabelClasses():
        lbl.visible = True
        lbl.expression = f"$feature.{label_field}"


def add_output_to_current_map(outputs):
    # This function adds results to the active ArcGIS Pro map and applies
    # symbology, zoom, and labels. It is desktop-only behaviour.
    # On ArcGIS Server (Enterprise web tool) arcpy.mp is not available,
    # so the function detects that and exits cleanly without raising an error.
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
    except Exception:
        # Running on ArcGIS Server or outside an ArcGIS Pro session.
        # Map interaction is not possible — outputs are returned to the
        # client via the declared Derived output parameters instead.
        arcpy.AddMessage(
            "Map display skipped: tool is running in a server environment."
        )
        return

    try:
        active_map = aprx.activeMap

        if not active_map:
            arcpy.AddWarning("No active map found.")
            return

        route_fc = getattr(outputs, "route", None)
        station_fc = getattr(outputs, "stations", None)

        if not route_fc or not arcpy.Exists(route_fc):
            arcpy.AddWarning("Route feature class not found.")
            return

        if not station_fc or not arcpy.Exists(station_fc):
            arcpy.AddWarning("Station points feature class not found.")
            return

        # Add route and stations
        route_layer = active_map.addDataFromPath(route_fc)
        station_layer = active_map.addDataFromPath(station_fc)

        # Symbolize route
        route_sym = route_layer.symbology
        if (
            hasattr(route_sym, "renderer")
            and route_sym.renderer.type == "SimpleRenderer"
        ):
            route_sym.renderer.symbol.color = {"RGB": [255, 0, 0, 100]}
            route_sym.renderer.symbol.width = 4
            route_layer.symbology = route_sym

        # Symbolize station points
        station_sym = station_layer.symbology
        if (
            hasattr(station_sym, "renderer")
            and station_sym.renderer.type == "SimpleRenderer"
        ):
            station_sym.renderer.symbol.color = {"RGB": [0, 0, 255, 100]}
            station_sym.renderer.symbol.size = 6
            station_layer.symbology = station_sym

        apply_layer_labels(station_layer, station_fc, ["Label_Text", "LabelText", "Chainage"])

        # Add segment line (trimmed route when start/end measure is set)
        segment_fc = getattr(outputs, "segment", None)
        if segment_fc and arcpy.Exists(segment_fc) and segment_fc != route_fc:
            try:
                seg_layer = active_map.addDataFromPath(segment_fc)
                seg_sym = seg_layer.symbology
                if (
                    hasattr(seg_sym, "renderer")
                    and seg_sym.renderer.type == "SimpleRenderer"
                ):
                    seg_sym.renderer.symbol.color = {"RGB": [0, 200, 0, 100]}
                    seg_sym.renderer.symbol.width = 3
                    seg_layer.symbology = seg_sym
            except Exception as e:
                arcpy.AddWarning(f"Could not add segment layer: {e}")

        # Add intersection point features (one per analysis layer)
        for fc in getattr(outputs, "intersections", []):
            try:
                if arcpy.Exists(fc):
                    lyr = active_map.addDataFromPath(fc)
                    sym = lyr.symbology
                    if (
                        hasattr(sym, "renderer")
                        and sym.renderer.type == "SimpleRenderer"
                    ):
                        sym.renderer.symbol.color = {"RGB": [255, 165, 0, 100]}
                        sym.renderer.symbol.size = 8
                        lyr.symbology = sym
                    apply_layer_labels(lyr, fc, ["Label_Text", "LabelText", "Chainage"])
            except Exception as e:
                arcpy.AddWarning(f"Could not add intersection layer: {e}")

        # Add overlap line features (one per analysis layer)
        for fc in getattr(outputs, "overlaps", []):
            try:
                if arcpy.Exists(fc):
                    lyr = active_map.addDataFromPath(fc)
                    sym = lyr.symbology
                    if (
                        hasattr(sym, "renderer")
                        and sym.renderer.type == "SimpleRenderer"
                    ):
                        sym.renderer.symbol.color = {"RGB": [128, 0, 128, 100]}
                        sym.renderer.symbol.width = 3
                        lyr.symbology = sym
                    apply_layer_labels(lyr, fc, ["Label_Text", "Range_Text", "ChainageRange"])
            except Exception as e:
                arcpy.AddWarning(f"Could not add overlap layer: {e}")

        # Zoom to route extent
        view = aprx.activeView
        if hasattr(view, "camera"):
            desc = arcpy.Describe(route_fc)
            extent = desc.extent
            x_buffer = (extent.XMax - extent.XMin) * 0.05
            y_buffer = (extent.YMax - extent.YMin) * 0.05
            new_extent = arcpy.Extent(
                extent.XMin - x_buffer,
                extent.YMin - y_buffer,
                extent.XMax + x_buffer,
                extent.YMax + y_buffer,
            )
            view.camera.setExtent(new_extent)

        arcpy.AddMessage("Outputs added to active map successfully.")

    except Exception as e:
        arcpy.AddWarning(f"Could not update map display: {e}")
