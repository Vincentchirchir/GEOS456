import arcpy


def draw_stationing_leaders_for_points(
    layout,
    map_frame,
    point_event_features,
    page_id=None,
    map_series=None,
    clear_existing=False,
):
    if not layout:
        arcpy.AddWarning("No active layout found.")
        return

    extent = map_frame.camera.getExtent()

    if clear_existing:
        for elm in layout.listElements():
            try:
                if elm.name.startswith("LR_Leader_") or elm.name.startswith(
                    "LR_Label_"
                ):
                    layout.deleteElement(elm)
            except Exception:
                pass

    visible_points = []

    for point_fc in point_event_features:
        if not point_fc or not arcpy.Exists(point_fc):
            continue

        fields = [f.name for f in arcpy.ListFields(point_fc)]
        if "Chainage" not in fields:
            continue

        with arcpy.da.SearchCursor(point_fc, ["SHAPE@", "Chainage"]) as scur:
            for shape, chainage in scur:
                if not shape or chainage in [None, ""]:
                    continue

                pt = shape.centroid

                if (
                    extent.XMin <= pt.X <= extent.XMax
                    and extent.YMin <= pt.Y <= extent.YMax
                ):
                    visible_points.append((pt.X, pt.Y, str(chainage)))

    if not visible_points:
        arcpy.AddMessage("No visible point events found in current extent.")
        return

    visible_points.sort(key=lambda x: x[0])

    top_band_base_y = map_frame.elementPositionY + map_frame.elementHeight + 0.18
    stagger_step = 0.10

    aprx = arcpy.mp.ArcGISProject("CURRENT")
    created_count = 0

    for i, (map_x, map_y, label_text) in enumerate(visible_points):
        try:
            page_x = (
                map_frame.elementPositionX
                + ((map_x - extent.XMin) / (extent.XMax - extent.XMin))
                * map_frame.elementWidth
            )

            page_y = (
                map_frame.elementPositionY
                + ((map_y - extent.YMin) / (extent.YMax - extent.YMin))
                * map_frame.elementHeight
            )
        except Exception as e:
            arcpy.AddWarning(
                f"Could not convert map coordinates to page coordinates: {e}"
            )
            continue

        label_y = top_band_base_y + (i % 3) * stagger_step

        try:
            txt = aprx.createTextElement(
                layout,
                arcpy.Point(page_x, label_y),
                "POINT",
                label_text,
                6,
            )
            txt.name = (
                f"LR_Label_{page_id}_{i}" if page_id is not None else f"LR_Label_{i}"
            )

            txt_cim = txt.getDefinition("V3")
            txt_cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
            txt_cim.graphic.symbol.symbol.height = 6
            txt.setDefinition(txt_cim)
        except Exception as e:
            arcpy.AddWarning(f"Could not create text element for {label_text}: {e}")
            continue

        try:
            leader_geom = arcpy.Polyline(
                arcpy.Array(
                    [
                        arcpy.Point(page_x, page_y),
                        arcpy.Point(page_x, label_y - 0.03),
                    ]
                )
            )

            leader = aprx.createGraphicElement(
                layout,
                leader_geom,
                name=(
                    f"LR_Leader_{page_id}_{i}"
                    if page_id is not None
                    else f"LR_Leader_{i}"
                ),
            )

            leader_cim = leader.getDefinition("V3")
            leader_cim.graphic.symbol.symbol.symbolLayers[0].width = 0.5
            leader.setDefinition(leader_cim)

            created_count += 1
        except Exception as e:
            arcpy.AddWarning(f"Could not create leader for {label_text}: {e}")

    arcpy.AddMessage(
        f"Leader labels drawn for {created_count} visible point events"
        + (f" on page {page_id}." if page_id is not None else ".")
    )