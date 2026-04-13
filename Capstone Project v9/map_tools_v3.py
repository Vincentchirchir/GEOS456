import arcpy
import os


def _get_target_maps(aprx, target_map_names=None):
    """
    Resolves the maps that should receive newly created outputs.

    Relying on aprx.activeMap is fragile once layouts enter the workflow,
    because the active view may be a mini map or some unrelated map. v9 uses
    separate main/mini maps in the layout, so we explicitly target those maps
    when names are supplied and fall back to the active map only when needed.
    """
    if target_map_names:
        resolved = []
        seen = set()

        for map_name in target_map_names:
            if not map_name or map_name in seen:
                continue

            maps = aprx.listMaps(map_name)
            if maps:
                resolved.append(maps[0])
                seen.add(map_name)
            else:
                arcpy.AddWarning(f"Could not find target map '{map_name}'.")

        if resolved:
            return resolved

    active_map = aprx.activeMap
    return [active_map] if active_map else []


def _find_existing_layer_by_path(map_obj, path):
    """
    Returns an existing layer in map_obj that already points to path.

    Reusing layers avoids stacking duplicates every time the tool reruns.
    """
    for lyr in map_obj.listLayers():
        try:
            data_source = getattr(lyr, "dataSource", None)
            if data_source and os.path.normcase(str(data_source)) == os.path.normcase(str(path)):
                return lyr
        except Exception:
            continue
    return None


def add_output_to_current_map(outputs, target_map_names=None):
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        target_maps = _get_target_maps(aprx, target_map_names=target_map_names)

        if not target_maps:
            arcpy.AddWarning("No target maps found.")
            return

        added_layers = []

        def add_layer_if_exists(path):
            if path and arcpy.Exists(path):
                last_layer = None

                for target_map in target_maps:
                    try:
                        existing_layer = _find_existing_layer_by_path(target_map, path)
                        if existing_layer:
                            layer = existing_layer
                        else:
                            layer = target_map.addDataFromPath(path)

                        try:
                            layer.visible = True
                        except Exception:
                            pass

                        added_layers.append((target_map.name, path, layer))
                        last_layer = layer
                    except Exception as e:
                        print(
                            f"Could not add layer to map '{target_map.name}': {path}. {e}"
                        )
                return last_layer
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
        for _, path, lyr in added_layers:

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
