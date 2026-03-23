import arcpy
import math


def _leader_name_matches_page(name, page_id):
    # Leaders are named with the page number so we can later identify which
    # layout elements belong to which map series page.
    prefixes = (
        f"leader_line_{page_id}_",
        f"leader_label_{page_id}_",
    )
    return any(name.startswith(prefix) for prefix in prefixes)


def _clear_stationing_leaders(layout, page_id=None):
    for element in layout.listElements():
        try:
            name = getattr(element, "name", "") or ""
            is_leader_element = name.startswith("leader_line_") or name.startswith(
                "leader_label_"
            )

            if not is_leader_element:
                continue

            # With page_id=None we remove every leader. Otherwise we only remove
            # the leader elements that belong to the requested page.
            if page_id is None or _leader_name_matches_page(name, page_id):
                layout.deleteElement(element)
        except Exception:
            pass


def _set_stationing_leader_visibility(layout, active_page_id=None):
    for element in layout.listElements():
        try:
            name = getattr(element, "name", "") or ""
            is_leader_element = name.startswith("leader_line_") or name.startswith(
                "leader_label_"
            )

            if not is_leader_element:
                continue

            # ArcGIS layout graphic/text elements are shared across the layout,
            # so we manually hide leaders from non-active pages instead of
            # expecting map series to filter them for us.
            if active_page_id is None:
                element.visible = True
            else:
                element.visible = _leader_name_matches_page(name, active_page_id)
        except Exception:
            pass


def _build_map_frame_transform(map_frame):
    # camera.getExtent() returns an axis-aligned envelope. When the map frame is
    # rotated, that envelope is larger than the actual visible page rectangle,
    # so we derive the visible width/height in map units before placing leaders.
    camera = map_frame.camera
    extent = camera.getExtent()
    frame_width = float(map_frame.elementWidth)
    frame_height = float(map_frame.elementHeight)
    extent_width = extent.XMax - extent.XMin
    extent_height = extent.YMax - extent.YMin

    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Map frame width and height must be greater than zero.")

    if extent_width <= 0 or extent_height <= 0:
        raise ValueError("Map frame extent width and height must be greater than zero.")

    heading = float(getattr(camera, "heading", 0.0) or 0.0)
    angle_rad = math.radians(heading)
    abs_cos = abs(math.cos(angle_rad))
    abs_sin = abs(math.sin(angle_rad))
    frame_aspect = frame_width / frame_height

    visible_width = None
    visible_height = None

    try:
        spatial_ref = getattr(getattr(map_frame, "map", None), "spatialReference", None)
        meters_per_unit = float(getattr(spatial_ref, "metersPerUnit", 0.0) or 0.0)
        scale = float(getattr(camera, "scale", 0.0) or 0.0)

        # These layouts are built in inches, so we can convert the map frame
        # size to ground distance directly from the current page scale. This is
        # more reliable for rotated map-series pages than reverse-solving from
        # the axis-aligned extent envelope.
        if meters_per_unit > 0 and scale > 0:
            inches_to_meters = 0.0254
            visible_width = (frame_width * scale * inches_to_meters) / meters_per_unit
            visible_height = (frame_height * scale * inches_to_meters) / meters_per_unit
    except Exception:
        visible_width = None
        visible_height = None

    if not visible_width or not visible_height:
        visible_height_from_width = extent_width / ((frame_aspect * abs_cos) + abs_sin)
        visible_height_from_height = extent_height / (
            (frame_aspect * abs_sin) + abs_cos
        )
        visible_height = (visible_height_from_width + visible_height_from_height) / 2.0
        visible_width = visible_height * frame_aspect

    camera_x = getattr(camera, "X", None)
    camera_y = getattr(camera, "Y", None)
    center_x = (
        float(camera_x)
        if camera_x not in [None, ""]
        else (extent.XMin + extent.XMax) / 2.0
    )
    center_y = (
        float(camera_y)
        if camera_y not in [None, ""]
        else (extent.YMin + extent.YMax) / 2.0
    )

    return {
        "extent": extent,
        "heading": heading,
        "angle_rad": angle_rad,
        "center_x": center_x,
        "center_y": center_y,
        "frame_x": float(map_frame.elementPositionX),
        "frame_y": float(map_frame.elementPositionY),
        "frame_width": frame_width,
        "frame_height": frame_height,
        "visible_width": visible_width,
        "visible_height": visible_height,
    }


def _map_point_to_page(transform, map_x, map_y):
    # Rotate the point into the page-aligned axes, then normalize it into the
    # map frame's 0-1 range so the final page position honors page rotation.
    dx = map_x - transform["center_x"]
    dy = map_y - transform["center_y"]
    angle_rad = transform["angle_rad"]

    rotated_x = (dx * math.cos(angle_rad)) - (dy * math.sin(angle_rad))
    rotated_y = (dx * math.sin(angle_rad)) + (dy * math.cos(angle_rad))

    x_ratio = (rotated_x / transform["visible_width"]) + 0.5
    y_ratio = (rotated_y / transform["visible_height"]) + 0.5

    page_x = transform["frame_x"] + (x_ratio * transform["frame_width"])
    page_y = transform["frame_y"] + (y_ratio * transform["frame_height"])
    is_visible = -1e-6 <= x_ratio <= 1.000001 and -1e-6 <= y_ratio <= 1.000001

    return page_x, page_y, is_visible


def draw_stationing_leaders_for_points(
    layout,  # the layout where the text and leader will be added
    map_frame,  # map frame nside the layout. Needed coz function must know what geogrphic area is visible
    point_event_features,  # list of point features. They are stored in events tools
    page_id=None,  # page identifier to be used in map series
    map_series=None,  # will use when applying the same leader to map series
    clear_existing=False,  # This will deletes old leader and label elements before drawing another one. Otherwise everytime you run thetool, the previous leader will still be existing
):  # below if function checks if their is an existing layout. If not, show warning and stops function with return
    if not layout:
        arcpy.AddWarning("No active layout found")
        return

    transform = _build_map_frame_transform(map_frame)
    extent = transform["extent"]
    arcpy.AddMessage(
        f"Leader transform extent: XMin={extent.XMin}, XMax={extent.XMax}, "
        f"YMin={extent.YMin}, YMax={extent.YMax}, Heading={transform['heading']}"
    )

    # Clear old leders and labels if existing
    # The function will loop through layout elements and checks for leader and lbels
    if clear_existing:
        _clear_stationing_leaders(layout, page_id=page_id)

    # the following is an empty list that will store points as the code is looping through the feature/route
    visible_points = []

    # The following code will loop through the point events features that are created and retun in event_tools.py
    # That stores the points of intersecting and overlaping features
    for point_fc in point_event_features:
        if not point_fc or not arcpy.Exists(
            point_fc
        ):  # This checks whhether the feature class path exists or valid, if no there, it skips and moves to next feature using continue
            continue

        # Once the code has looped through the point feature, it wants to check fields to see if chainage is there. Coz chainage is what will be used to label
        fields = [
            f.name for f in arcpy.ListFields(point_fc)
        ]  # Remeber we are looking for chainge field.
        if (
            "Chainage" not in fields
        ):  # if chainage field is not in the fields, meaning we are not looking for that feature. skip and continue
            continue

        # Read the true point geometry from the feature class. The point feature
        # already carries Chainage, so the leader can anchor to the raw crossing
        # instead of a route-rebuilt surrogate point.
        with arcpy.da.SearchCursor(point_fc, ["SHAPE@", "Chainage"]) as Scursor:
            for shape, chainage in Scursor:
                if not shape or chainage in [None, ""]:
                    continue

                # Build list of points (handles multipoint + point)
                point_list = []

                if shape.type.lower() == "multipoint":
                    for p in shape:
                        if p:
                            point_list.append(p)
                else:
                    if shape.firstPoint:
                        point_list.append(shape.firstPoint)

                for point_geom in point_list:
                    arcpy.AddMessage(f"Checking point FC: {point_fc}")
                    arcpy.AddMessage(
                        f"Chainage={chainage}, X={point_geom.X}, Y={point_geom.Y}"
                    )

                    try:
                        page_x, page_y, is_visible = _map_point_to_page(
                            transform, point_geom.X, point_geom.Y
                        )

                        arcpy.AddMessage(
                            f"Converted to page coords: page_x={page_x}, page_y={page_y}, visible={is_visible}"
                        )

                        if not is_visible:
                            continue

                        visible_points.append((page_x, page_y, str(chainage)))

                    except Exception as e:
                        arcpy.AddWarning(f"Conversion error: {e}")
                        continue

    arcpy.AddMessage(f"Point feature classes received: {point_event_features}")
    arcpy.AddMessage(f"Visible points count before draw: {len(visible_points)}")
    if not visible_points:
        arcpy.AddMessage("No visible points found iin the current extent")
        return

    # For the visible points that were store in the list we created above
    # We sort by page X so the label order stays left-to-right even when the
    # map frame is rotated by map series.

    xs = [pt[0] for pt in visible_points]
    ys = [pt[1] for pt in visible_points]

    x_range = max(xs) - min(xs)
    y_range = max(ys) - min(ys)

    is_vertical = y_range > x_range

    # visible_points.sort(key=lambda x: x[0])  # this sorts points by x coordinates.Meaning they will be processed from left to right

    if is_vertical:
        visible_points.sort(key=lambda x: x[1])  # bottom → top
    else:
        visible_points.sort(key=lambda x: x[0])  # left → right

    # define the top section position.How far will the line go up? Height
    # Defined using Y coordinates. Like graph. X horizontal, Y vertical
    leader_band_y = map_frame.elementPositionY + map_frame.elementHeight + 0.12
    label_base_y = (
        leader_band_y + 0.08
    )  # this  pushes the labels a bit above the to of the map frame

    stagger_step = 0.10  # this is the vertical distance between the labels. It gives room of breathing if they will be staggered

    # Now that we have looked for points, names, and ready to label, lets look for the current active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    created_leaders_count = 0  # how many leaders are created? It starts at zero. And everytime a leader is created, it increases

    # You remember the visible points we stored? Lets loop through the points now
    # enumerate gives:
    # i = index number (0, 1, 2, ...)
    # page_x, page_y, label_text = values stored in the list
    # i is later used for:
    # unique naming
    # staggering labels

    placed_labels = []
    min_spacing = 0.6
    shift_pattern = [0, 0.2, -0.2, 0.4, -0.4]
    for i, (page_x, page_y, label_text) in enumerate(visible_points):
        # label_y = label_base_y + (i % 5) * stagger_step
        label_y = label_base_y

        # base_offset = (i % 5 - 2) * 0.15
        # label_x = page_x + base_offset
        # label_x = page_x
        label_x = map_frame.elementPositionX + map_frame.elementWidth / 2
        label_y = label_base_y
        for shift in shift_pattern:
            trial_x = page_x + shift
            collision = False

            for prev_x, prev_y in placed_labels:
                too_close_x = abs(prev_x - trial_x) < min_spacing
                too_close_y = abs(prev_y - label_y) < 0.15

                if too_close_x and too_close_y:
                    collision = True
                    break

            if not collision:
                label_x = trial_x
                break

        # the above label_y code places 3 staggered rows.
        # i % 3 gives repeating values:
        # 0, 1, 2, 0, 1, 2
        # So label Y becomes:
        # row 1 = base Y
        # row 2 = base Y + 0.10
        # row 3 = base Y + 0.20
        # Then repeats.
        # Why? To reduce overlap when labels are close together horizontally.

        try:
            text = aprx.createTextElement(
                layout, arcpy.Point(label_x, label_y), "POINT", label_text, 10
            )
            text_cim = text.getDefinition("V3")

            #  anchor control
            text_cim.anchor = "CenterPoint"

            #
            text.setDefinition(text_cim)
            text.name = (
                f"leader_label_{page_id}_{i}"
                if page_id is not None
                else f"leader_label_{i}"
            )

            # The above code gives the label a unique name. Examples:
            # LR_Label_1_0, LR_Label_1_1, Or if no page ID:
            # LR_Label_0, LR_Label_1
            # Why name it? Because later we will need for map series and mabnage it per page

            text_cim = text.getDefinition("V3")  # it gets the element symbol structure
            text_cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"  # ets font style
            text_cim.graphic.symbol.symbol.height = 10  # sets text size
            text.setDefinition(text_cim)  # applies the updated style
            # The above code edits the symbol like font size, name
        except Exception as e:
            arcpy.AddWarning(f"Could not create text element for {label_text}: {e}")
            continue

        # lets now build line line
        # The following code creates a vertical line from the point position up toward the label
        try:
            # go vertically up from the point
            leader_start_y = page_y

            leader_geom = arcpy.Polyline(
                arcpy.Array(
                    [
                        arcpy.Point(page_x, leader_start_y),  #  start at point
                        arcpy.Point(page_x, leader_band_y),
                        arcpy.Point(label_x, leader_band_y),  # elbow
                        # arcpy.Point(label_x, leader_band_y), # small top tick
                    ]
                )
            )

            # creating a graphic element for the leader
            leader = aprx.createGraphicElement(
                layout,
                leader_geom,
                name=(
                    f"leader_line_{page_id}_{i}"
                    if page_id is not None
                    else f"leader_line_{i}"
                ),
            )

            leader_cim = leader.getDefinition("V3")
            leader_cim.graphic.symbol.symbol.symbolLayers[0].width = 0.5
            leader.setDefinition(leader_cim)

            placed_labels.append((label_x, label_y))
            created_leaders_count += 1
        except Exception as e:
            arcpy.AddWarning(f"Could not create leader for {label_text}: {e}")

    arcpy.AddMessage(
        f"Leader labels drawn for {created_leaders_count} visible points"
        + (f" on page {page_id}." if page_id is not None else ".")
    )


def leaders_to_map_series(
    layout_name,
    map_frame,
    point_event_features,
):
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    # get the layout first before going to map series
    layouts = aprx.listLayouts(layout_name)
    if not layouts:
        raise ValueError(
            f"Layout '{layout_name}' not found"
        )  # if layout is not there, then raise error

    layout = layouts[0]  # This

    # Now lets get the map frame
    map_frames = layout.listElements("MAPFRAME_ELEMENT", map_frame)
    if not map_frames:
        raise ValueError(f"Map frame '{map_frame}' not found in layout '{layout_name}'")

    map_frame_name = map_frames[0]

    # Check whether map series is checked
    map_series = layout.mapSeries

    if map_series and map_series.enabled:
        current_page_number = map_series.currentPageNumber
        try:
            map_series.refresh()
            map_series.currentPageNumber = current_page_number
        except Exception as e:
            arcpy.AddWarning(f"Map series refresh warning: {e}")

        arcpy.AddMessage(
            "Map series detected. Layout leader graphics do not honor page-based "
            "visibility automatically, so leaders will be refreshed for the "
            f"active page only (page {current_page_number})."
        )
        arcpy.AddMessage(
            f"Map series camera after refresh: scale={map_frame_name.camera.scale}, "
            f"heading={map_frame_name.camera.heading}"
        )

        # Layout graphic and text elements are shared by the entire layout, so
        # generating one set per page causes them to stack on every page.
        _clear_stationing_leaders(layout)

        # Only build leaders for the page the user is currently viewing. This
        # keeps the layout clean and prevents leaders from unrelated pages from
        # being visible together.
        draw_stationing_leaders_for_points(
            layout=layout,
            map_frame=map_frame_name,
            point_event_features=point_event_features,
            page_id=current_page_number,
            map_series=map_series,
            clear_existing=False,
        )

        # After creating the leaders, make sure only the active page's leaders
        # remain visible in case older page-tagged elements already exist.
        _set_stationing_leader_visibility(layout, active_page_id=current_page_number)

        arcpy.AddMessage(
            "If you change the active map series page, run the leaders step again "
            "to refresh the page-specific leader graphics."
        )
    else:
        arcpy.AddMessage("No enabled map series found. Applying leaders once")

        draw_stationing_leaders_for_points(
            layout=layout,
            map_frame=map_frame_name,
            point_event_features=point_event_features,
            page_id=None,
            clear_existing=True,
        )
        _set_stationing_leader_visibility(layout, active_page_id=None)


# shift_pattern = [0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5]
# min_spacing = 0.8

# placed_labels = []
# min_spacing = 1.0
# shift_pattern = [0, 0.6, -0.6, 1.2, -1.2, 1.8, -1.8]

# Keep leader vertical
# leader_geom = arcpy.Polyline(
#     arcpy.Array(
#         [
#             arcpy.Point(page_x, leader_start_y),
#             arcpy.Point(page_x, leader_band_y),
#         ]
#     )
# )
