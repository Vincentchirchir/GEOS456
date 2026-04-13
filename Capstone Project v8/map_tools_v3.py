import arcpy
import os


def add_output_to_current_map(outputs):
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap

        if not active_map:
            arcpy.AddWarning("No active map found.")
            return

        added_layers = []

        def add_layer_if_exists(path):
            if path and arcpy.Exists(path):
                try:
                    layer = active_map.addDataFromPath(path)
                    added_layers.append((path, layer))
                    return layer
                except Exception as e:
                    print(f"Could not add layer to map: {path}. {e}")
            return None

        # single outputs
        route_fc = outputs.get("route_fc")
        station_fc = outputs.get("station_points")

        route_layer = add_layer_if_exists(route_fc)
        station_layer = add_layer_if_exists(station_fc)

        # list outputs
        for key in [
            "point_event_features",
            "line_event_features",
            "overlap_from_points",
            "overlap_to_points",
        ]:
            value = outputs.get(key)
            if isinstance(value, list):
                for path in value:
                    add_layer_if_exists(path)

        # symbolize route
        if route_layer:
            try:
                route_sym = route_layer.symbology
                if (
                    hasattr(route_sym, "renderer")
                    and route_sym.renderer.type == "SimpleRenderer"
                ):
                    route_sym.renderer.symbol.color = {"RGB": [255, 0, 0, 100]}
                    route_sym.renderer.symbol.width = 4
                    route_layer.symbology = route_sym
            except:
                pass

        # symbolize station points
        if station_layer:
            try:
                station_sym = station_layer.symbology
                if (
                    hasattr(station_sym, "renderer")
                    and station_sym.renderer.type == "SimpleRenderer"
                ):
                    station_sym.renderer.symbol.color = {"RGB": [0, 0, 255, 100]}
                    station_sym.renderer.symbol.size = 6
                    station_layer.symbology = station_sym
            except:
                pass

            # turn on labels for station points
            try:
                station_layer.showLabels = True
                for lbl in station_layer.listLabelClasses():
                    lbl.visible = True
                    lbl.expression = "$feature.Chainage"
            except:
                pass

        # symbolize and label added point event / overlap endpoint layers
        for path, lyr in added_layers:

            try:
                if not lyr or path in [route_fc, station_fc]:
                    continue

                desc = arcpy.Describe(path)
                shape_type = getattr(desc, "shapeType", None)
                field_names = [f.name for f in arcpy.ListFields(path)]

                sym = lyr.symbology
                if hasattr(sym, "renderer") and sym.renderer.type == "SimpleRenderer":
                    if shape_type == "Point":
                        sym.renderer.symbol.color = {"RGB": [230, 200, 255, 100]}
                        sym.renderer.symbol.size = 5
                    elif shape_type == "Polyline":
                        sym.renderer.symbol.color = {"RGB": [0, 150, 0, 100]}
                        sym.renderer.symbol.width = 3
                    lyr.symbology = sym

                #     # label point layers that have Chainage
                if shape_type == "Point" and "Chainage" in field_names:
                    lyr.showLabels = True
                    for lbl in lyr.listLabelClasses():
                        lbl.visible = True
                        lbl.expression = "$feature.Chainage"

                # label overlap lines if desired
                elif shape_type == "Polyline" and "ChainageRange" in field_names:
                    lyr.showLabels = True
                    for lbl in lyr.listLabelClasses():
                        lbl.visible = True
                        lbl.expression = "$feature.ChainageRange"

            except Exception as e:
                arcpy.AddWarning(f"Could not symbolize or label {path}: {e}")

        # zoom to route extent
        if route_fc and arcpy.Exists(route_fc):
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
