import arcpy
import os


def _get_layer_data_source(layer):
    """Safely returns a layer's data source path when available."""
    try:
        return getattr(layer, "dataSource", None)
    except Exception:
        return None


def _get_layer_uri(layer):
    """Safely returns a layer's CIM URI when available."""
    try:
        lyr_cim = layer.getDefinition("V3")
        return getattr(lyr_cim, "uRI", None)
    except Exception:
        return None


def _is_tool_generated_mini_map_clutter(layer, data_source=None):
    """
    Returns True when a layer looks like a generated output that should stay
    out of the mini map overview.

    The mini map is intended to stay contextual, so generated station points,
    intersection event layers, overlap event layers, and rerun leftovers are
    filtered out even when they already existed in the shared map before the
    current tool run.
    """
    data_source = (
        data_source if data_source is not None else _get_layer_data_source(layer)
    )

    layer_name = (getattr(layer, "name", "") or "").lower()
    source_name = os.path.splitext(os.path.basename(str(data_source or "")))[0].lower()
    candidates = [layer_name, source_name]

    suffixes = (
        "_route",
        "_stations",
        "_intersections",
        "_single",
        "_overlap",
        "_overlaps",
        "_overlap_from_points",
        "_overlap_to_points",
    )
    keywords = (
        "_intersections",
        "_stations",
        "overlap_from_points",
        "overlap_to_points",
        "_station_events",
    )

    for text in candidates:
        if not text:
            continue
        if any(text.endswith(suffix) for suffix in suffixes):
            return True
        if any(keyword in text for keyword in keywords):
            return True

    return False


def _same_data_source(path_a, path_b):
    """Case-insensitive path comparison that tolerates missing values."""
    if not path_a or not path_b:
        return False
    return os.path.normcase(str(path_a)) == os.path.normcase(str(path_b))


def build_mini_map_from_main_map(source_map_name, route_fc=None):
    """
    Creates a dedicated mini-map copy from the source map and hides clutter.

    ArcGIS Pro renders all frames that reference the same Map with the same
    layer collection, so a dedicated copied map is the reliable way to keep
    the mini map contextual while the main map remains fully annotated.

    The copied map keeps the current route visible, preserves the user's
    original site/analysis layers, and hides generated stations, intersection
    event layers, overlap endpoint layers, and rerun leftovers.
    """
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    source_maps = aprx.listMaps(source_map_name)
    if not source_maps:
        arcpy.AddWarning(
            f"Could not find source map '{source_map_name}' for the mini map copy. "
            "The original map will be used for the mini map."
        )
        return source_map_name

    source_map = source_maps[0]
    mini_map_copy_name = f"__LR_V9_MINI__{source_map.name}"

    for existing_map in aprx.listMaps(mini_map_copy_name):
        try:
            aprx.deleteItem(existing_map)
        except Exception:
            pass

    try:
        mini_map = aprx.copyItem(source_map, new_name=mini_map_copy_name)
    except Exception as e:
        arcpy.AddWarning(
            f"Could not create a dedicated mini map from '{source_map.name}': {e}. "
            "The original map will be used for the mini map."
        )
        return source_map_name

    kept_route_layers = 0
    hidden_clutter_layers = 0

    for lyr in mini_map.listLayers():
        try:
            data_source = _get_layer_data_source(lyr)

            if route_fc and _same_data_source(data_source, route_fc):
                lyr.visible = True
                kept_route_layers += 1
                continue

            if _is_tool_generated_mini_map_clutter(lyr, data_source=data_source):
                lyr.visible = False
                hidden_clutter_layers += 1
        except Exception:
            continue

    arcpy.AddMessage(
        f"Dedicated mini map created from '{source_map.name}': "
        f"{kept_route_layers} route layer(s) kept visible, "
        f"{hidden_clutter_layers} clutter layer(s) hidden."
    )
    return mini_map.name


def _apply_label_halo(layer, halo_size=2.5):
    """
    Applies a white halo to every label class on a layer via CIM.

    ArcGIS Pro has no high-level Python API for label halos — they must be
    set directly on the CIM text symbol.  The halo is a CIMPolygonSymbol
    (white solid fill) surrounding the label glyphs, controlled by haloSize
    (in points).  A size of 1.5pt is a professional default: readable without
    overwhelming thin or dense labels.

    Implementation notes
    --------------------
    - arcpy.cim.CreateCIMObjectFromClassName instantiates CIM objects by class
      name.  This is the official ArcGIS Pro API for creating new child CIM
      objects programmatically.
    - If object creation fails for any reason (unsupported CIM version, ArcGIS
      Pro build differences), haloSize is still set.  ArcGIS Pro will use its
      own default fill for the halo area, which is usually acceptable.
    - The function is non-fatal: a failure on one label class does not prevent
      other classes from being processed, and a failure on the whole layer
      issues a warning rather than raising.

    Parameters
    ----------
    layer : arcpy.mp.Layer
        The map layer whose label classes will receive the halo.
    halo_size : float
        Halo size in points.  Default 2.5pt.
    """
    try:
        lyr_cim = layer.getDefinition("V3")
        modified = False

        for lc in getattr(lyr_cim, "labelClasses", None) or []:
            try:
                sym = lc.textSymbol.symbol

                # Halo size
                sym.haloSize = halo_size

                # Halo fill symbol
                # Build a white CIMPolygonSymbol with a single solid fill layer.
                # CreateCIMObjectFromClassName is the ArcGIS Pro CIM factory —
                # it returns a properly initialised object of the named class.
                try:
                    halo_sym = arcpy.cim.CreateCIMObjectFromClassName(
                        "CIMPolygonSymbol", "V3"
                    )
                    solid_fill = arcpy.cim.CreateCIMObjectFromClassName(
                        "CIMSolidFill", "V3"
                    )
                    white_color = arcpy.cim.CreateCIMObjectFromClassName(
                        "CIMRGBColor", "V3"
                    )
                    white_color.values = [255, 255, 255, 100]  # R G B Alpha
                    solid_fill.enable = True
                    solid_fill.color = white_color

                    halo_sym.symbolLayers = [solid_fill]
                    sym.haloSymbol = halo_sym

                except Exception:
                    # haloSize is still applied — ArcGIS Pro will render a
                    # default background fill, which is an acceptable fallback
                    # if CIM object construction is unavailable.
                    pass

                modified = True

            except Exception:
                # A single label class failing must not abort the others
                continue

        if modified:
            layer.setDefinition(lyr_cim)

    except Exception as e:
        arcpy.AddWarning(f"Could not apply label halo to layer '{layer.name}': {e}")


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
            if data_source and os.path.normcase(str(data_source)) == os.path.normcase(
                str(path)
            ):
                return lyr
        except Exception:
            continue
    return None


def snapshot_site_layer_uris(map_obj):
    """
    Records the CIM URI of every layer currently present in the map.

    This function MUST be called before the tool adds any generated outputs
    (route, stations, intersections, overlaps) to the map.  The returned
    set is passed to apply_mini_map_visibility_override() after the layout
    is built, so the mini map frame knows exactly which layers belong to the
    user's original site data and which were produced by the tool.

    CIM URIs are stable per-layer identifiers internal to ArcGIS Pro
    projects.  A typical URI looks like:
        CIMPATH=map/layername.json
    They are unique per layer instance and do not change during a session
    unless the layer is removed and re-added.

    Parameters
    ----------
    map_obj : arcpy.mp.Map
        The ArcGIS Pro map object to inspect.  Should be the same map
        that will receive the tool outputs so the URI sets are comparable.

    Returns
    -------
    set of str
        One CIM URI string per layer successfully read.
        Returns an empty set if the map has no layers or on error.
        An empty set causes apply_mini_map_visibility_override() to issue
        a warning and leave the mini frame untouched — intentional
        graceful fallback so the tool does not crash over a cosmetic step.
    """
    uris = set()

    try:
        for lyr in map_obj.listLayers():
            try:
                data_source = _get_layer_data_source(lyr)
                if _is_tool_generated_mini_map_clutter(lyr, data_source=data_source):
                    continue

                uri = _get_layer_uri(lyr)
                if uri:
                    uris.add(uri)
            except Exception:
                # A single layer failing to expose its URI (e.g. broken
                # data source, unsupported layer type) must not abort the
                # entire snapshot — skip it silently and continue.
                continue

    except Exception as e:
        arcpy.AddWarning(
            f"Could not snapshot site layer URIs from map '{map_obj.name}': {e}. "
            "Mini map visibility override will be skipped — the mini map "
            "will show all layers including tool-generated outputs."
        )

    return uris


def apply_mini_map_visibility_override(mini_map_frame, site_layer_uris, route_fc=None):
    """
    Restricts the mini map frame to display only the user's original site
    layers, hiding all tool-generated outputs (route, stations, intersections,
    overlaps) from it without affecting the main map frame.

    How it works
    ------------
    ArcGIS Pro's CIM exposes a 'visibleLayers' property on CIMMapFrame.
    When this list is populated, the frame acts as a strict whitelist:
    only layers whose CIM URIs appear in the list are rendered, regardless
    of their map-level visibility setting.  Layers added by the tool are
    absent from the list and are therefore invisible in the mini frame
    while remaining fully visible in the main map frame.

    This approach works even when both frames reference the same single map
    in the ArcGIS Pro project — no second map needs to be created.

    Failure handling
    ----------------
    This function is intentionally non-fatal.  If the CIM override cannot
    be applied for any reason (empty URI set, unsupported CIM version,
    serialisation error), a descriptive warning is issued and the mini
    frame falls back to its default behaviour of showing all layers.
    A cosmetic limitation should never block the rest of the tool output.

    Parameters
    ----------
    mini_map_frame : arcpy.mp.MapFrame
        The mini map frame element from the layout, as returned in the
        'mini_map_frame' key of generate_alignment_layout()'s result dict.

    site_layer_uris : set of str
        CIM URI strings captured by snapshot_site_layer_uris() before any
        tool outputs were added to the map.  Typically of the form
        "CIMPATH=map/layername.json".
    route_fc : str, optional
        Current run's generated route feature class. This layer is explicitly
        re-included in the mini map so the route remains visible while other
        generated outputs stay hidden.
    """
    if not site_layer_uris:
        arcpy.AddWarning(
            "Mini map visibility override skipped: no pre-existing site "
            "layer URIs were captured before the tool ran.  The mini map "
            "will show all layers, including tool-generated outputs.  "
            "To resolve this, ensure the map contains at least one site "
            "layer before running the tool."
        )
        return

    try:
        visible_uris = set(site_layer_uris)
        route_uri_count = 0
        hidden_generated_count = 0

        for lyr in mini_map_frame.map.listLayers():
            uri = _get_layer_uri(lyr)
            if not uri:
                continue

            data_source = _get_layer_data_source(lyr)

            if route_fc and _same_data_source(data_source, route_fc):
                visible_uris.add(uri)
                route_uri_count += 1
                continue

            if _is_tool_generated_mini_map_clutter(lyr, data_source=data_source):
                visible_uris.discard(uri)
                hidden_generated_count += 1

        cim = mini_map_frame.getDefinition("V3")

        # Assign the whitelist.  From this point the mini frame renders only
        # the layers whose URIs appear here — the user's original site data
        # plus the current route layer. Generated stations/intersections remain
        # invisible in this frame only. The main map frame is unaffected.
        cim.visibleLayers = list(visible_uris)

        mini_map_frame.setDefinition(cim)

        arcpy.AddMessage(
            f"Mini map frame visibility override applied: "
            f"{len(visible_uris)} layer URI(s) visible; "
            f"{route_uri_count} route layer(s) kept; "
            f"{hidden_generated_count} generated clutter layer(s) hidden in the mini map."
        )

    except Exception as e:
        arcpy.AddWarning(
            f"Could not apply mini map CIM visibility override: {e}. "
            "The mini map will display all layers including tool outputs. "
            "To manually correct this, open the layout Contents pane, "
            "select the Mini Map Frame, and toggle layer visibility there."
        )


def add_output_to_current_map(outputs, target_map_names=None):
    """
    Adds tool outputs to the target maps and applies symbology and labels.

    Adds the route, station points, intersection features, and overlap features
    to the specified maps. Symbolizes each layer type and turns on Chainage
    labels where available. Zooms the active view to the route extent.

    Parameters
    ----------
    outputs : dict
        Keys: route_fc, station_points, point_event_features, line_event_features,
        overlap_from_points, overlap_to_points.
    target_map_names : list of str, optional
        Names of the maps to add outputs to. Falls back to the active map if not given.
    """
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

        route_fc = outputs.get("route_fc")
        station_fc = outputs.get("station_points")

        route_layer = add_layer_if_exists(route_fc)
        station_layer = add_layer_if_exists(station_fc)

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
                    station_sym.renderer.symbol.color = {"RGB": [144, 238, 144, 30]}
                    station_sym.renderer.symbol.outlineColor = {"RGB": [0, 0, 0, 100]}
                    station_sym.renderer.symbol.outlineWidth = 0.25
                    station_sym.renderer.symbol.size = 12
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

            # Apply halo to station chainage labels
            _apply_label_halo(station_layer)

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
                        sym.renderer.symbol.color = {"RGB": [0, 0, 0, 0]}
                        sym.renderer.symbol.outlineColor = {"RGB": [0, 0, 0, 100]}
                        sym.renderer.symbol.outlineWidth = 0.5
                        sym.renderer.symbol.size = 9
                    elif shape_type == "Polyline":
                        sym.renderer.symbol.color = {"RGB": [0, 150, 0, 100]}
                        sym.renderer.symbol.width = 3
                    lyr.symbology = sym

                if shape_type == "Point" and "Chainage" in field_names:
                    lyr.showLabels = True
                    for lbl in lyr.listLabelClasses():
                        lbl.visible = True
                        lbl.expression = "$feature.Chainage"
                    _apply_label_halo(lyr)

                elif shape_type == "Polyline" and "ChainageRange" in field_names:
                    lyr.showLabels = True
                    for lbl in lyr.listLabelClasses():
                        lbl.visible = True
                        lbl.expression = "$feature.ChainageRange"
                    _apply_label_halo(lyr)

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
