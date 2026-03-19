import arcpy

"""  We are going to create a function that looks for a point features that are visible on the current map 
Then read their chainage values from chainage field
Then place the labels above the map frame and draw vertical leader lines from the point up to the label
"""


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

    # below extent gets the current visible map extent of the map frame
    extent = map_frame.camera.getExtent()

    # Clear old leders and labels if existing
    # The function will loop through layout elements and checks for leader and lbels
    if clear_existing:
        for element in layout.listElements():
            try:
                if element.name.startswith("leader_line_") or element.name.startswith(
                    "leader_label_"
                ):  # Leader_line is the line drawn from point upwards, leader_label is the chainge/ intersection of that point
                    layout.deleteElement(element)
            except Exception:
                pass

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

        # Now, as the script is looking for chainage field, it will also look for geometry object. And centroid of the point where leader line will be place.
        # Geometry will be used by script to store the location of that point
        # Coz when we store geometry of a point, it becomes unique and dynamic.

        with arcpy.da.SearchCursor(point_fc, ["SHAPE@", "Chainage"]) as Scursor:
            for shape, chainage in Scursor:
                if not shape or chainage in [None, ""]:
                    continue

                point_centroid = (
                    shape.centroid
                )  # This gets the centroid of the geometry

                # the following if statemment checks if the point lies inside the current map extent now that we store shape/geomerty
                if (
                    extent.XMin <= point_centroid.X <= extent.XMax
                    and extent.YMin <= point_centroid.Y <= extent.YMax
                ):
                    visible_points.append(
                        (point_centroid.X, point_centroid.Y, str(chainage))
                    )  # if the point is there, it is appended/stored in the list

    # if there is not point, exits with a message
    if not visible_points:
        arcpy.AddMessage("No visible points found iin the current extent")
        return

    # For the visible points that were store in the list we created above
    # We want to sort the points left to right
    # This will help the labels appear in a logical order across the top section
    visible_points.sort(
        key=lambda x: x[0]
    )  # this sorts points by x coordinates.Meaning they will be processed from left to right

    # define the top section position.How far will the line go up? Height
    # Defined using Y coordinates. Like graph. X horizontal, Y vertical
    top_section_y = (
        map_frame.elementPositionY + map_frame.elementHeight + 0.18
    )  # this 0.18 pushes the labels a bit above the to of the map frame

    stagger_step = 0.10  # this is the vertical distance between the labels. It gives room of breathing if they will be staggered

    # Now that we have looked for points, names, and ready to label, lets look for the current active map
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    created_leaders_count = 0  # how many leaders are created? It starts at zero. And everytime a leader is created, it increases

    # You remember the visible points we stored? Lets loop through the points now
    # enumerate gives:
    # i = index number (0, 1, 2, ...)
    # map_x, map_y, label_text = values stored in the list
    # i is later used for:
    # unique naming
    # staggering labels

    placed_labels = []
    min_spacing = 0.6
    shift_pattern = [0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9, 1.2, -1.2]
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

        # The above code again:
        # Remember the points were captured in geometry/map coordinates but layout elements must be placed in not as coordinates
        # So the code converts the point’s geographic/map position into its matching page position inside the map frame.
        # page_x works like this:
        # Find how far the point is across the map extent horizontally
        # Convert that proportion into page width
        # Add the map frame’s page X origin
        # page_y
        # Find how far the point is up the extent
        # Convert that proportion into page height
        # Add the map frame’s page Y origin

        label_y = top_section_y + (i % 3) * stagger_step

        base_offset = (i % 5 - 2) * 0.15
        label_x = page_x + base_offset
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
            leader_geom = arcpy.Polyline(
                arcpy.Array(
                    [
                        arcpy.Point(
                            page_x, page_y
                        ),  # start point. This is the page location corresponding to the actual point on the map
                        arcpy.Point(label_x, label_y - 0.03),  # End point
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
