import arcpy

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
        arcpy.AddMessage("Map display skipped: tool is running in a server environment.")
        return

    try:
        active_map = aprx.activeMap

        if not active_map:
            arcpy.AddWarning("No active map found.")
            return

        route_fc = outputs.get("route_fc")
        station_fc = outputs.get("station_points")

        if not route_fc or not arcpy.Exists(route_fc):
            arcpy.AddWarning("Route feature class not found.")
            return

        if not station_fc or not arcpy.Exists(station_fc):
            arcpy.AddWarning("Station points feature class not found.")
            return

        # Add layers to map
        route_layer = active_map.addDataFromPath(route_fc)
        station_layer = active_map.addDataFromPath(station_fc)

        # Symbolize route
        route_sym = route_layer.symbology
        if hasattr(route_sym, "renderer") and route_sym.renderer.type == "SimpleRenderer":
            route_sym.renderer.symbol.color = {'RGB': [255, 0, 0, 100]}
            route_sym.renderer.symbol.width = 4
            route_layer.symbology = route_sym

        # Symbolize station points
        station_sym = station_layer.symbology
        if hasattr(station_sym, "renderer") and station_sym.renderer.type == "SimpleRenderer":
            station_sym.renderer.symbol.color = {'RGB': [0, 0, 255, 100]}
            station_sym.renderer.symbol.size = 6
            station_layer.symbology = station_sym

        # Zoom to route extent
        view = aprx.activeView
        if hasattr(view, "camera"):
            desc = arcpy.Describe(route_fc)
            extent = desc.extent

            # Optional small buffer around extent
            x_buffer = (extent.XMax - extent.XMin) * 0.05
            y_buffer = (extent.YMax - extent.YMin) * 0.05

            new_extent = arcpy.Extent(
                extent.XMin - x_buffer,
                extent.YMin - y_buffer,
                extent.XMax + x_buffer,
                extent.YMax + y_buffer
            )
            view.camera.setExtent(new_extent)

        # Turn on labels
        station_layer.showLabels = True

        for lbl in station_layer.listLabelClasses():
            lbl.visible = True
            lbl.expression = "$feature.Chainage"

        arcpy.AddMessage("Outputs added to active map successfully.")

    except Exception as e:
        arcpy.AddWarning(f"Could not update map display: {e}")
