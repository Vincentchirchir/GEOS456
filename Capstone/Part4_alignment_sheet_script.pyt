'''
Project: Alignment Sheet Automation Using Python (GEOS459 - Capstone)
Purpose: Generate a script to automate a procedure to creating alignment sheets in ArcGIS Pro
Creators: Nail Murshudov, Vincent Chirchir, Siqin Xiong
Client: Associated Environmental (Tiffany Gauce, Wallace La)
Date Created: January 26th, 2026
'''

#Importing required parameters
import arcpy
import os
import time
# import importlib
# import layout_script
# import stationing_script

# #Python Scripts
# importlib.reload(layout_script)
# importlib.reload(stationing_script)

#Overwriting the outputs
arcpy.env.overwriteOutput = True

#CREATING A CUSTOM GEOPROCESSING TOOL:
class Toolbox(object):
    def __init__(self):
        self.label = "Generator"
        self.alias = "generator" 
        self.tools = [AlignmentSheetGenerator] #This gives a name to the geoprocessing tool that you want to create 

class AlignmentSheetGenerator: #This class basically covers everything from parameters, to executing the tool
    def __init__(self):
        self.label = "Alignment Sheet Generator" #Gives the name of the geoprocessing tool.
        self.description = "Generates an alignment sheet using a layout template \nONLY PRODUCES LANDSCAPE LAYOUT SHEET" #This gives information on the custom Geoprocessing tool

    #Defining parameters in the geoprocessing tool:
    def getParameterInfo(self):
        #Layout Name
        layout_name = arcpy.Parameter(
            displayName = "Alignment Sheet Name",
            name = "alignment_sheet_name",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        #Layout Size
        layout_size = arcpy.Parameter(
            displayName = "Page Size",
            name = "page_size",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        #Size Options
        layout_size.filter.type = "ValueList"
        layout_size.filter.list = ["Letter (11x8.5)",
                                   "Legal (14x8.5)",
                                   "Tabloid (17x11)",
                                   "ANSI C (22x17)",
                                   "ANSI D (34x22)",
                                   "ANSI E (44x34)"]

        #Main Map
        layout_main_map = arcpy.Parameter(
            displayName = "Input Main Map",
            name = "input_main_map",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        #Mini Map
        layout_mini_map = arcpy.Parameter(
            displayName = "Input Mini Map",
            name = "input_mini_map",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        maps = arcpy.mp.ArcGISProject("CURRENT").listMaps()
        maps_names = [all_maps.name for all_maps in maps] #GEMINI helped with this (Helped to iterate)
        layout_main_map.filter.type = "ValueList"
        layout_main_map.filter.list = maps_names
        layout_mini_map.filter.type = "ValueList"
        layout_mini_map.filter.list = maps_names

        #Stationing Boolean
        stationings = arcpy.Parameter(
            displayName = "Stationing",
            name = "show_stationing",
            datatype = "GPBoolean",
            parameterType = "Required",
            direction = "Input"
        )

        stationings.enabled = True
        stationings.values = False

        #Select your linear data (This is for stationings)
        input_line = arcpy.Parameter(
            displayName = "Input Linear Feature",
            name = "input_line_or_polyline_feature",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input"
        )

        #Intervals in meters for the stationings (5m = 0+005m, 0+010m. 20m = 0+020m, 0+040m, etc.)
        stationings_interval = arcpy.Parameter(
            displayName = "Stationing Interval (m)",
            name = "interval_in_meters",
            datatype = "GPLinearUnit",
            parameterType = "Required",
            direction = "Input"
        )

        stationings_interval.value = "100 Meters"

        #Intesection
        intersection_layers = arcpy.Parameter(
            displayName = "Intersecting Features",
            name = "intersection_layers",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input",
            multiValue = True,
        )

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap

        if active_map:
            polyline_layers = []
            for lyr in active_map.listLayers():
                if lyr.isFeatureLayer:
                    try:
                        desc = arcpy.Describe(lyr.dataSource)
                        if desc.shapeType == "Polyline":
                            polyline_layers.append(lyr.name)
                    except:
                        pass

            input_line.filter.list = polyline_layers

        #Output GDB
        output_gdb = arcpy.Parameter(
            displayName = "Output Feature Class",
            name = "output_gdb",
            datatype = ["DEWorkspace", "DEFeatureDataset"],
            parameterType = "Required",
            direction= "Input",
        )

        #Map Series Boolean
        map_series = arcpy.Parameter(
            displayName = "Map Series",
            name = "map_series",
            datatype = "GPBoolean",
            parameterType = "Required",
            direction = "Input"
        )

        map_series.enabled = True
        map_series.values = False

        #Select your map scale
        map_series_scale = arcpy.Parameter(
            displayName = "Scale",
            name = "map_series_scale",
            datatype = "GPLong",
            parameterType = "Required",
            direction = "Input"
        )

        #Map Series Orientation
        map_series_orientation = arcpy.Parameter(
            displayName = "Page Orientation",
            name = "map_series_orientation",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input"
        )

        map_series_orientation.filter.type = "ValueList"
        map_series_orientation.filter.list = ["Horizontal",
                                              "Vertical"]
        #Map Series Overlap
        map_series_overlap = arcpy.Parameter(
            displayName = "Overlap (%)",
            name = "map_series_overlap",
            datatype = "GPLong",
            parameterType = "Required",
            direction = "Input"
        )

        parameters = [layout_name, #0
                      layout_size, #1
                      layout_main_map, #2
                      layout_mini_map, #3
                      stationings, #4
                      input_line, #5
                      stationings_interval, #6
                      intersection_layers, #7
                      output_gdb, #8
                      map_series, #9
                      map_series_scale, #10
                      map_series_orientation, #11
                      map_series_overlap #12
                      ]

        return parameters

    def updateParameters(self, parameters):
        if parameters[4].value == True:
            for station in [5, 6, 7, 8]:
                parameters[station].enabled = True

            parameters[5].filter.list = ["Polyline"]

        else:
            for station in [5, 6, 7, 8]:
                parameters[station].enabled = False

        if parameters[9].value == True:
            for mapseries in [10, 11, 12]:
                parameters[mapseries].enabled = True

        else:
            for mapseries in [10, 11, 12]:
                parameters[mapseries].enabled = False

        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        #Defining Variables
        lyt_name = parameters[0].valueAsText
        lyt_size = parameters[1].value
        lyt_main_map_frame = parameters[2].valueAsText
        lyt_mini_map_frame = parameters[3].valueAsText
        input_line_fc = parameters[5].valueAsText
        station_interval = parameters[6].value
        st_intersect_text = parameters[7].valueAsText
        output_gdb = parameters[8].valueAsText
        mp_series_scale = parameters[10].value
        mp_series_orientation = parameters[11].value
        mp_series_overlap = parameters[12].value

        #Setting up the project reference
        arcgispro_project = arcpy.mp.ArcGISProject("CURRENT") #This references the ArcGIS Pro Project (This is needed so python knows what project you are working in)
        targeted_main_map = arcgispro_project.listMaps(lyt_main_map_frame)[0] #Lists the first map select for the main map frame for the alignment sheet
        targeted_mini_map = arcgispro_project.listMaps(lyt_mini_map_frame)[0] #Lists the second map select for the mini map frame for the alignment sheet

        #CREATING THE LAYOUT, MAP FRAME, and setting locations for other features (DIFFERENT LAYOUT SIZE = DIFFERENT MAP FRAME SIZE)
        #Setting different layout sizes
        letter = [11, 8.5] 
        legal = [14, 8.5]
        tabloid = [17, 11]
        ansi_c = [22, 17]
        ansi_d = [34, 22]
        ansi_e = [44, 34]

        sizes = { 
                "Letter (11x8.5)": letter,
                "Legal (14x8.5)": legal,
                "Tabloid (17x11)": tabloid,
                "ANSI C (22x17)": ansi_c,
                "ANSI D (34x22)": ansi_d,
                "ANSI E (44x34)": ansi_e
                }

        layout_size = sizes.get(lyt_size, letter)

        #CREATING A LAYOUT SHEET
        #Layout Size
        width = layout_size[0]
        height = layout_size[1]

        #Creating Layout
        layout = arcgispro_project.createLayout(width,
                                                height,
                                                "INCH",
                                                lyt_name) #This setting creates the layout sheet in ArcGIS Pro.

        #CREATING A MAP FRAME
        #Map Frame Sizes - MAIN
        x_min = width * 0.01181818181818180
        y_min = height * 0.19767058823529400
        x_max = width
        y_max = height * 0.80117647058823500

        #MINI
        x_min_mini = width * 0.32545454545454500
        y_min_mini = height * 0
        x_max_mini = width * 0.48090909090909100
        y_max_mini = height * 0.18443529411764700

        #Creating Map Frame
        mp_frame_main_extent = arcpy.Extent(x_min,
                                            y_min,
                                            x_max,
                                            y_max)

        mp_frame = layout.createMapFrame(mp_frame_main_extent,
                                         targeted_main_map,
                                         "Map Frame")

        mp_frame_cim = mp_frame.getDefinition("V3")
        mp_frame_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
        mp_frame.setDefinition(mp_frame_cim)
        mp_frame.locked = True

        #Creating Mini Map Frame
        mp_frame_main_extent_mini = arcpy.Extent(x_min_mini,
                                                 y_min_mini,
                                                 x_max_mini,
                                                 y_max_mini)

        mp_frame_mini = layout.createMapFrame(mp_frame_main_extent_mini,
                                              targeted_mini_map,
                                              "Mini Map Frame")

        mp_frame_mini_cim = mp_frame_mini.getDefinition("V3")
        mp_frame_mini_cim.graphicFrame.borderSymbol.symbol.symbolLayers[0].width = 0.5
        mp_frame_mini.setDefinition(mp_frame_mini_cim)
        mp_frame_mini.locked = True

        #STATIONING
        def create_route_and_stationing(
                input_line_fc,
                output_gdb,
                station_interval,
                route_id_field="Route_ID",
                route_id_value="ROUTE_01",
            ):
                desc = arcpy.Describe(input_line_fc)
                catalog_path = desc.catalogPath

                base_name = arcpy.ValidateTableName(
                    os.path.splitext(os.path.basename(catalog_path))[0],
                    output_gdb
                )

                # Temporary copy
                line_copy_fc = os.path.join(output_gdb,
                                            base_name + "_copy")

                arcpy.management.CopyFeatures(input_line_fc,
                                            line_copy_fc)

                # Add route ID field if missing
                field_names = [f.name for f in arcpy.ListFields(line_copy_fc)]
                if route_id_field not in field_names:
                    arcpy.management.AddField(line_copy_fc,
                                            route_id_field,
                                            "TEXT",
                                            field_length=50)

                # Assign one route ID to all features
                arcpy.management.CalculateField(
                    line_copy_fc,
                    route_id_field,
                    f"'{route_id_value}'",
                    "PYTHON3"
                )

                # Temporary dissolve
                route_diss = os.path.join(output_gdb,
                                        base_name +
                                        "_dissolve")

                arcpy.management.Dissolve(line_copy_fc,
                                        route_diss,
                                        route_id_field)

                # Final route output
                route_fc = os.path.join(output_gdb,
                                        base_name +
                                        "_route")

                arcpy.lr.CreateRoutes(route_diss,
                                    route_id_field,
                                    route_fc,
                                    "LENGTH")

                # Final station points output
                station_points = os.path.join(output_gdb,
                                            base_name +
                                            "_Stationing")

                arcpy.management.GeneratePointsAlongLines(
                    route_fc,
                    station_points,
                    "DISTANCE",
                    Distance=station_interval,
                    Include_End_Points="END_POINTS",
                )

                if "StationID" not in [f.name for f in arcpy.ListFields(station_points)]:
                    arcpy.management.AddField(station_points,
                                            "StationID",
                                            "LONG")

                arcpy.management.CalculateField(
                    station_points,
                    "StationID",
                    "!OBJECTID!",
                    "PYTHON3"
                )

                # Final station event table output
                station_table = os.path.join(output_gdb,
                                            base_name +
                                            "_station_events")

                arcpy.lr.LocateFeaturesAlongRoutes(
                    in_features=station_points,
                    in_routes=route_fc,
                    route_id_field=route_id_field,
                    out_table=station_table,
                    out_event_properties=f"{route_id_field} POINT MEAS",
                    radius_or_tolerance="1 Meters",
                    distance_field="DISTANCE",
                )

                # Add Chainage field
                table_fields = [f.name for f in arcpy.ListFields(station_table)]
                if "Chainage" not in table_fields:
                    arcpy.management.AddField(station_table,
                                            "Chainage",
                                            "TEXT",
                                            field_length=20)

                calculate_field_code = r"""def chain(val):
                val = int(round(float(val)))
                km = val // 1000
                remainder = val % 1000
                return f"{km}+{remainder:03d}"
            """

                arcpy.management.CalculateField(
                    station_table, "Chainage",
                    "chain(!MEAS!)",
                    "PYTHON3",
                    calculate_field_code
                )

                # Delete temporary datasets
                if arcpy.Exists(line_copy_fc):
                    arcpy.management.Delete(line_copy_fc)

                if arcpy.Exists(route_diss):
                    arcpy.management.Delete(route_diss)

                return {
                    "route_fc": route_fc,
                    "Stationing": station_points,
                    "station_table": station_table,
                    "route_id_field": route_id_field,
                }

        intersection_layers = []
        if st_intersect_text:
            intersection_layers = st_intersect_text.split(";")

            messages.addMessage("Creating route and stationing...")

            outputs = create_route_and_stationing(
                input_line_fc=input_line_fc,
                output_gdb=output_gdb,
                station_interval=station_interval,
            )

            messages.addMessage(f"Route created: {outputs["route_fc"]}")
            messages.addMessage(f"Station points created: {outputs["Stationing"]}")
            messages.addMessage(f"Station event table created: {outputs["station_table"]}")

            def join_station_chainage_to_points(
                    station_points,
                    station_table):

                point_fields = [f.name for f in arcpy.ListFields(station_points)]
                if "Chainage" in point_fields:
                    arcpy.management.DeleteField(station_points, "Chainage")

                arcpy.management.JoinField(
                    in_data=station_points,
                    in_field="StationID",
                    join_table=station_table,
                    join_field="StationID",
                    fields=["Chainage"]
                )

            # Join chainage to station points first
            join_station_chainage_to_points(
            station_points=outputs["Stationing"],
            station_table=outputs["station_table"]
            )

            messages.addMessage("Chainage joined to station points.")

            def create_intersections_and_overlaps(
                    route_fc,
                    output_gdb,
                    intersection_layers):

                point_intersections = []
                line_overlaps = []

                route_name = os.path.splitext(os.path.basename(route_fc))[0]

                for lyr in intersection_layers:
                    try:
                        desc = arcpy.Describe(lyr)
                        layer_name = arcpy.ValidateTableName(
                            desc.baseName,
                            output_gdb)

                        shape_type = desc.shapeType

                        if layer_name.lower() == route_name.lower():
                            continue

                        # Point intersection output
                        point_out = os.path.join(output_gdb,
                                                f"{layer_name}_temp_points")

                        arcpy.analysis.Intersect(
                            [route_fc, lyr],
                            point_out,
                            output_type="POINT")

                        if int(arcpy.management.GetCount(point_out)[0]) > 0:
                            point_intersections.append(point_out)

                        else:
                            arcpy.management.Delete(point_out)

                        # Overlap output for line and polygon layers
                        if shape_type in ["Polyline", "Polygon"]:
                            overlap_out = os.path.join(output_gdb,
                                                    f"{layer_name}_overlap")

                            arcpy.analysis.Intersect([route_fc, lyr],
                                                        overlap_out,
                                                    output_type="LINE")

                            if int(arcpy.management.GetCount(overlap_out)[0]) > 0:
                                line_overlaps.append(overlap_out)

                            else:
                                arcpy.management.Delete(overlap_out)

                    except Exception as e:
                        arcpy.AddWarning(f"Skipped layer {lyr}: {e}")

                return {"point_intersections": point_intersections,
                        "line_overlaps": line_overlaps}

            # Only do crossings/overlaps if optional layers were provided
            if intersection_layers:
                messages.addMessage("Creating intersections and overlaps...")

                crossing_outputs = create_intersections_and_overlaps(
                    route_fc=outputs["route_fc"],
                    output_gdb=output_gdb,
                    intersection_layers=intersection_layers,
                )

                messages.addMessage(
                    f"Point intersections created: {len(crossing_outputs["point_intersections"])}"
                )
                messages.addMessage(
                    f"Line overlaps created: {len(crossing_outputs["line_overlaps"])}"
                )
                messages.addMessage("Locating intersections and overlaps along route...")

            def locate_intersections_and_overlaps(
                route_fc,
                route_id_field,
                output_gdb,
                point_intersections,
                line_overlaps):

                point_event_tables = []
                line_event_tables = []

                # Point events
                for point_fc in point_intersections:
                    point_name = arcpy.ValidateTableName(
                        os.path.splitext(os.path.basename(point_fc))[0],
                        output_gdb)

                    out_table = os.path.join(output_gdb,
                                            f"{point_name}_event")

                    arcpy.lr.LocateFeaturesAlongRoutes(
                        in_features=point_fc,
                        in_routes=route_fc,
                        route_id_field=route_id_field,
                        out_table=out_table,
                        out_event_properties=f"{route_id_field} POINT MEAS",
                        radius_or_tolerance="1 Meters",
                        distance_field="DISTANCE",
                    )

                    if int(arcpy.management.GetCount(out_table)[0]) > 0:
                        point_event_tables.append(out_table)

                    else:
                        arcpy.management.Delete(out_table)

                # Line events
                for overlap_fc in line_overlaps:
                    overlap_name = arcpy.ValidateTableName(os.path.splitext(os.path.basename(overlap_fc))[0], output_gdb)

                    out_table = os.path.join(output_gdb,
                                            f"{overlap_name}_event")

                    arcpy.lr.LocateFeaturesAlongRoutes(
                        in_features=overlap_fc,
                        in_routes=route_fc,
                        route_id_field=route_id_field,
                        out_table=out_table,
                        out_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
                        radius_or_tolerance="1 Meters",
                        distance_field="DISTANCE",
                    )

                    if int(arcpy.management.GetCount(out_table)[0]) > 0:
                        line_event_tables.append(out_table)
                    else:
                        arcpy.management.Delete(out_table)

                return {
                    "point_event_tables": point_event_tables,
                    "line_event_tables": line_event_tables,
                }

            event_outputs = locate_intersections_and_overlaps(
                            route_fc=outputs["route_fc"],
                            route_id_field=outputs["route_id_field"],
                            output_gdb=output_gdb,
                            point_intersections=crossing_outputs["point_intersections"],
                            line_overlaps=crossing_outputs["line_overlaps"],
                        )

            messages.addMessage(
                            f"Point event tables created: {len(event_outputs["point_event_tables"])}"
                        )
            messages.addMessage(
                            f"Line event tables created: {len(event_outputs["line_event_tables"])}"
                        )
            messages.addMessage("Calculating chainage for event tables...")

            def chainage_code_block():
                return r"""def chain(val):
                val = int(round(float(val)))
                km = val // 1000
                remainder = val % 1000
                return f"{km}+{remainder:03d}"
            """

            def add_chainage_to_event_tables(point_event_tables,
                                                line_event_tables):

                code_block = chainage_code_block()

                # Point event tables
                for table in point_event_tables:
                    existing_fields = [f.name for f in arcpy.ListFields(table)]

                    if "Chainage" not in existing_fields:
                        arcpy.management.AddField(table,
                                                "Chainage",
                                                "TEXT",
                                                field_length=20)

                    arcpy.management.CalculateField(
                        table, "Chainage",
                        "chain(!MEAS!)",
                        "PYTHON3",
                        code_block
                    )

                # Line event tables
                for table in line_event_tables:
                    existing_fields = [f.name for f in arcpy.ListFields(table)]

                    if "FromCh" not in existing_fields:
                        arcpy.management.AddField(table,
                                                "FromCh",
                                                "TEXT",
                                                field_length=20)

                    if "ToCh" not in existing_fields:
                        arcpy.management.AddField(table,
                                                "ToCh",
                                                "TEXT",
                                                field_length=20)

                    if "ChainageRange" not in existing_fields:
                        arcpy.management.AddField(table,
                                                "ChainageRange",
                                                "TEXT",
                                                field_length=30)

                    arcpy.management.CalculateField(
                        table, "FromCh",
                        "chain(!FMEAS!)",
                        "PYTHON3",
                        code_block
                    )

                    arcpy.management.CalculateField(
                        table, "ToCh",
                        "chain(!TMEAS!)",
                        "PYTHON3",
                        code_block
                    )

                    arcpy.management.CalculateField(
                        table,
                        "ChainageRange",
                        "!FromCh! + ' - ' + !ToCh!",
                        "PYTHON3"
                    )

            add_chainage_to_event_tables(
                            point_event_tables=event_outputs["point_event_tables"],
                            line_event_tables=event_outputs["line_event_tables"],
                        )

            messages.addMessage("Chainage fields added to event tables.")
            messages.addMessage("Creating event feature layers...")

            def make_event_layers_from_tables(
                route_fc,
                route_id_field,
                output_gdb,
                point_event_tables,
                line_event_tables
            ):
                point_event_features = []
                line_event_features = []

                # Point event layers
                for table in point_event_tables:
                    intersection_names = os.path.splitext(os.path.basename(table))[0]

                    name_cleaning_intersection = intersection_names.replace("_temp_points",
                                                                                "").replace("_event",
                                                                                            "")

                    base_name = arcpy.ValidateTableName(
                        name_cleaning_intersection,
                        output_gdb
                    )

                    out_layer = f"{base_name}_lyr"
                    out_fc = os.path.join(output_gdb,
                                        f"{base_name}_Intersection")

                    arcpy.lr.MakeRouteEventLayer(
                        in_routes=route_fc,
                        route_id_field=route_id_field,
                        in_table=table,
                        in_event_properties=f"{route_id_field} POINT MEAS",
                        out_layer=out_layer,
                    )

                    arcpy.management.CopyFeatures(out_layer, out_fc)
                    point_event_features.append(out_fc)

                # Line event layers
                for table in line_event_tables:
                    intersection_names = os.path.splitext(os.path.basename(table))[0]

                    name_cleaning_intersection = intersection_names.replace("_overlap",
                                                                                "").replace("_event",
                                                                                            "")

                    base_name = arcpy.ValidateTableName(
                        name_cleaning_intersection,
                        output_gdb
                    )

                    out_layer = f"{base_name}_lyr"
                    out_fc = os.path.join(output_gdb,
                                        f"{base_name}_Overlap")

                    arcpy.lr.MakeRouteEventLayer(
                        in_routes=route_fc,
                        route_id_field=route_id_field,
                        in_table=table,
                        in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
                        out_layer=out_layer,
                    )

                    arcpy.management.CopyFeatures(out_layer, out_fc)
                    line_event_features.append(out_fc)

                return {
                    "point_event_features": point_event_features,
                    "line_event_features": line_event_features,
                }

            event_feature_outputs = make_event_layers_from_tables(
                route_fc=outputs["route_fc"],
                route_id_field=outputs["route_id_field"],
                output_gdb=output_gdb,
                point_event_tables=event_outputs["point_event_tables"],
                line_event_tables=event_outputs["line_event_tables"],
            )

            messages.addMessage(
                f"Point event features created: {len(event_feature_outputs["point_event_features"])}"
            )
            messages.addMessage(
                f"Line event features created: {len(event_feature_outputs["line_event_features"])}"
            )

            def delete_intermidiate_data(dataset_list):
                messages.addMessage("Deleting intermidiate datasets...")
                for delete_data in dataset_list:
                    if arcpy.Exists(delete_data):
                        arcpy.management.Delete(delete_data)

            deleting_data = []

            if intersection_layers:

                deleting_data = (
                    crossing_outputs.get("point_intersections", []) +
                    crossing_outputs.get("line_overlaps", []) +
                    event_outputs.get("point_event_tables", []) +
                    event_outputs.get("line_event_tables", [])
                    )

            route_data = outputs.get("route_fc")

            if route_data:
                deleting_data.append(route_data)

            tabular_data = outputs.get("station_table")

            if tabular_data:
                deleting_data.append(tabular_data)

            deleting_data = list(set([delete for delete in deleting_data if delete])) #AI Helped with this.

            if deleting_data:
                delete_intermidiate_data(deleting_data)
                messages.addMessage("Intermidiate datasets deleted.")

            else:
                messages.addMessage("No analysis layers provided. Skipping intersections and overlaps.")

        stationing_labelling = targeted_main_map.addDataFromPath(outputs["Stationing"])

        if stationing_labelling.supports("SHOWLABELS"): #https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/labelclass-class.htm
            stationing_labelling.showLabels = True

            stationing_labelling_cim = stationing_labelling.getDefinition("V3")

            if stationing_labelling_cim.labelClasses:
                sl_cim = stationing_labelling_cim.labelClasses[0]
                sl_cim.expression = "$feature.Chainage"

            stationing_labelling.setDefinition(stationing_labelling_cim)
            
        for intersections in event_feature_outputs["point_event_features"]:
            intersections_labelling = targeted_main_map.addDataFromPath(intersections)

            if intersections_labelling.supports("SHOWLABELS"):
                intersections_labelling.showLabels = True

                intersections_labelling_cim = intersections_labelling.getDefinition("V3")

                if intersections_labelling_cim.labelClasses:
                    inter_cim = intersections_labelling_cim.labelClasses[0]
                    inter_cim.expression = "$feature.Chainage"
            
                intersections_labelling.setDefinition(intersections_labelling_cim)
                
        #Map Series
        data_input = os.path.basename(str(input_line_fc))
        index_output = os.path.join(output_gdb, f"{data_input}_index")

        #Setting up the margin
        mf_width_float = float(mp_frame.elementWidth) * 0.90
        mf_height_float = float(mp_frame.elementHeight) * 0.90
        mf_width = f"{mf_width_float} Inches"  #Map Frame Width
        mf_height = f"{mf_height_float} Inches" #Map Frame Height
        locked_scale = int(mp_series_scale)

        #Orientation
        selected_orientation = str(mp_series_orientation).upper()

        #Creating strips for the Map Series
        arcpy.cartography.StripMapIndexFeatures(
            in_features = input_line_fc,
            out_feature_class = index_output,
            use_page_unit = "USEPAGEUNIT",
            scale = mp_series_scale,
            length_along_line = mf_width, #Map Frame Width in Inches
            length_perpendicular_to_line = mf_height, #Map Frame Height in Inches
            page_orientation = selected_orientation,
            overlap_percentage = mp_series_overlap
        )

        index_layer_map_series = targeted_main_map.addDataFromPath(index_output)
        index_layer_map_series.visible = False

        #Creating Map Series
        mapseries = layout.createSpatialMapSeries(
            mapframe = mp_frame,
            index_layer = index_layer_map_series,
            name_field = "PageNumber",
            sort_field = "PageNumber"
        )

        #Making Map Series Properties
        mapseries_cim = mapseries.getDefinition("V3")
        mapseries_cim.enabled = True

        mapseries_cim.mapFrameName = mp_frame.name
        index_layer_cim = index_layer_map_series.getDefinition("V3")
        mapseries_cim.indexLayerURI = index_layer_cim.uRI

        mapseries_cim.sortAscending = True
        mapseries_cim.extentOptions = "ExtentCenter"
        mapseries_cim.rotationField = "Angle"
        mapseries_cim.scaleField = None 
        mapseries_cim.startingPageNumber = 1

        mapseries.setDefinition(mapseries_cim)

        mp_frame.camera.scale = locked_scale

        #MAKING ATTRIBUTES IN THE LAYOUT
        width_ratio = width / 11
        height_ratio = height / 8.5

        #Legend Creation
        legend_x = width * 0.019090909
        legend_y = height * 0.192941176

        legend_location = arcpy.Point(legend_x,
                                      legend_y)

        legend_style = arcgispro_project.listStyleItems("ArcGIS 2D",
                                                        "LEGEND",
                                                        "Legend 1")[0]

        legend = layout.createMapSurroundElement(legend_location,
                                                 "LEGEND",
                                                 mp_frame,
                                                 legend_style,
                                                 "Legend")

        legend.syncLayerVisibility = True

        #Legend Size
        legend.elementWidth = 3.314 * width_ratio
        legend.elementHeight = 1.5835 * height_ratio

        legend_patch_width = 15
        legend_patch_height = 10
        legend_font = 6

        dynamic_patch_width = legend_patch_width * width_ratio
        dynamic_patch_height = legend_patch_height * height_ratio
        dynamic_font_size = legend_font * height_ratio

        #Legend Setting
        legend_cim = legend.getDefinition("V3")
        legend_cim.showTitle = False

        legend_cim.fittingStrategy = "AdjustColumnsAndFont"
        legend_cim.columns = 3
        legend_cim.minFontSize = dynamic_font_size
        legend_cim.defaultPatchWidth = dynamic_patch_width
        legend_cim.defaultPatchHeight = dynamic_patch_height 

        legend_cim.useMapSeriesShape = True
        for legend_items in legend_cim.items:
            legend_items.showVisibleFeaturesOnly = True
            legend_items.showLayerName = False
            legend_items.showHeading = False
            legend_items.showGroupLayerName = False

            legend_items.patchWidth = dynamic_patch_width
            legend_items.patchHeight = dynamic_patch_height
            
            legend_symbols = getattr(legend_items, "labelSymbol", None)

            if legend_symbols is not None:
                    legend_symbols.symbol.height = dynamic_font_size

        order = {
                 "Point": 1,
                 "Polyline": 2,
                 "Polygon": 3,
                 "RasterLayer": 4
                 }
        
        def ordering(features):
            try:
                legend_list = targeted_main_map.listLayers(features.name)

                if not legend_list:
                    return 99
                
                info = legend_list[0]

                if info.isFeatureLayer:
                    vector_data = arcpy.Describe(info.dataSource).shapeType
                    return order.get(vector_data, 3)
                
                if info.isRasterLayer:
                    return 4
                return 99
            
            except:
                return 99
                
        if legend_cim.items:
            legend_cim.items = sorted(legend_cim.items, key=ordering)

        legend.setDefinition(legend_cim) 

        #NORTH ARROW
        #North Arrow Creation
        north_arrow_x = width * 0.9247818181818180
        north_arrow_y = height * 0.0404588235294118
        north_arrow_location = arcpy.Point(north_arrow_x,
                                           north_arrow_y)

        north_arrow_style = arcgispro_project.listStyleItems("ArcGIS 2D",
                                                             "North_Arrow",
                                                             "ArcGIS North 3")[0]

        north_arrow = layout.createMapSurroundElement(north_arrow_location,
                                                      "North_Arrow",
                                                      mp_frame,
                                                      north_arrow_style,
                                                      "North Arrow")
        north_arrow.locked = True

        #North Arrow Size
        north_arrow.elementWidth = 0.0719 * width_ratio
        north_arrow.elementHeight = 0.1497 * height_ratio

        #SCALE BAR
        #Scale Bar Creation
        scale_bar_x = width * 0.9204636363636360
        scale_bar_y = height * 0.0534470588235294
        scale_bar_location = arcpy.Point(scale_bar_x,
                                         scale_bar_y)

        scale_bar_style = arcgispro_project.listStyleItems("ArcGIS 2D",
                                                           "SCALE_BAR",
                                                           "Alternating Scale Bar 1 Metric")[0]

        scale_bar = layout.createMapSurroundElement(scale_bar_location,
                                                    "SCALE_BAR",
                                                    mp_frame,
                                                    scale_bar_style,
                                                    "Scale Bar")

        #Scale Bar Size
        scale_bar.elementWidth = 0.7725 * width_ratio
        scale_bar.elementHeight = 0.3148 * height_ratio

        #Scale Bar Properties
        scale_bar_cim = scale_bar.getDefinition("V3")
        scale_bar_cim.unitLabelPosition = "Below"
        scale_bar_cim.divisions = 1
        scale_bar_cim.subdivisions = 3
        scale_bar_cim.fittingStrategy = "AdjustDivision"
        scale_bar_cim.markPosition = "BelowBar"
        scale_bar_cim.unitLabelGap = 3 * height_ratio
        scale_bar_cim.labelSymbol.symbol.height = 4 * height_ratio
        scale_bar_cim.unitLabelSymbol.symbol.height = 4 * height_ratio
        scale_bar.setDefinition(scale_bar_cim)

        #Map Scale
        original_size = 4
        dynamic_size = original_size * (height / 8.5)
        map_scale_x = width * 0.9489818181818180
        map_scale_y = height * 0.03927058823529414
        map_scale_location = arcpy.Point(map_scale_x,
                                         map_scale_y)

        map_scale = arcgispro_project.createTextElement(layout, map_scale_location,
                                                        "POINT",
                                                        '<dyn type="mapFrame" name="Map Frame" property="scale" preStr="1:"/>',
                                                        original_size)
        map_scale.name = "Map Scale"
        map_scale.locked = True

        #Map Scale Properties
        map_scale_cim = map_scale.getDefinition("V3")
        map_scale_cim.fontFamilyName = "Tahoma"
        map_scale_cim.graphic.symbol.symbol.height = dynamic_size
        map_scale.setDefinition(map_scale_cim)

        #MAKING TEXTS
        #Setting Properties
        locked_texts = []
        unlocked_texts = []

        def text_properties(titles, layout, height):

            location = arcpy.Point(titles["text_x"],
                                   titles["text_y"])

            create_text = arcgispro_project.createTextElement(layout,
                                                              location,
                                                              "POINT",
                                                              titles["text"],
                                                              titles["font_size"])

            create_text.elementRotation = titles["rotation"]
            create_text.name = titles["name"]

            original_size = titles["font_size"]
            dynamic_size = original_size * (height / 8.5)

            cim = None
            for timer in range(2):
                try:
                    cim = create_text.getDefinition("V3")
                    if cim: break   #AI HELPED WITH THIS
                except:
                    time.sleep(0.1)

            if cim:
                cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
                cim.graphic.symbol.symbol.fontStyleName = titles["font_style"]
                cim.graphic.symbol.symbol.underline = titles["underline"]
                cim.graphic.symbol.symbol.height = dynamic_size
                cim.locked = titles["locked"]
                create_text.setDefinition(cim)

            return create_text

        #Creating Texts
        texts = [{
            "text": "Legend",
            "text_x": width * 0.0100636363636364,
            "text_y": height * 0.0809058823529412,
            "rotation": 90,
            "name": "Legend Text",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Plan View",
            "text_x": width * 0.0100636363636364,
            "text_y": height * 0.4750941176470590,
            "rotation": 90,
            "name": "Plan View",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Stationing",
            "text_x": width * 0.0100636363636364,
            "text_y": height * 0.8750235294117650,
            "rotation": 90,
            "name": "Stationing",
            "font_size": 6,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Site Area",
            "text_x": width * 0.39314545454545500,
            "text_y": height * 0.18712941176470600,
            "rotation": 0,
            "name": "Site Area",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Summary Table",
            "text_x": width * 0.52360909090909100,
            "text_y": height * 0.18716470588235300,
            "rotation": 0,
            "name": "Summary Table",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Intersection Table",
            "text_x": width * 0.665454545454546,
            "text_y": height * 0.187058823529412,
            "rotation": 0,
            "name": "Intersection Table",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Intersection Summary",
            "text_x": width * 0.778181818181818,
            "text_y": height * 0.187058823529412,
            "rotation": 0,
            "name": "Intersection Summary",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Project Name",
            "text_x": width * 0.860909090909091,
            "text_y": height * 0.187058823529412,
            "rotation": 0,
            "name": "Project Name",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Project Number",
            "text_x": width * 0.85814545454545500,
            "text_y": height * 0.16167058823529400,
            "rotation": 0,
            "name": "Project Number",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Location Address",
            "text_x": width * 0.85640909090909100,
            "text_y": height * 0.13356470588235300,
            "rotation": 0,
            "name": "Location Address",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Client",
            "text_x": width * 0.87070909090909100,
            "text_y": height * 0.10138823529411800,
            "rotation": 0,
            "name": "Client",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Notes",
            "text_x": width * 0.87080909090909100,
            "text_y": height * 0.06797647058823530,
            "rotation": 0,
            "name": "Notes",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Data Sources",
            "text_x": width * 0.78954545454545500,
            "text_y": height * 0.06797647058823530,
            "rotation": 0,
            "name": "Data Sources",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Disclaimer",
            "text_x": width * 0.52998181818181800,
            "text_y": height * 0.04317647058823530,
            "rotation": 0,
            "name": "Disclaimer",
            "font_size": 4,
            "underline": True,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "ID",
            "text_x": width * 0.63047272727272700,
            "text_y": height * 0.17443529411764700,
            "rotation": 0,
            "name": "Point ID",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Stationing",
            "text_x": width * 0.67589090909090900,
            "text_y": height * 0.17443529411764700,
            "rotation": 0,
            "name": "Stationing Info",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Type",
            "text_x": width * 0.73805454545454600,
            "text_y": height * 0.17443529411764700,
            "rotation": 0,
            "name": "Intersection Type",
            "font_size": 4,
            "underline": False,
            "font_style": "Bold",
            "locked": True
        },{
            "text": "Company Logo",
            "text_x": width * 0.9258000000000000,
            "text_y": height * 0.1644117647058820,
            "rotation": 0,
            "name": "Company Logo",
            "font_size": 8,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Completed By:",
            "text_x": width * 0.92046363636363600,
            "text_y": height * 0.13342352941176500,
            "rotation": 0,
            "name": "Completed By",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Reviewed By:",
            "text_x": width * 0.92046363636363600,
            "text_y": height * 0.11680000000000000,
            "rotation": 0,
            "name": "Reviewed By",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Signed By:",
            "text_x": width * 0.92046363636363600,
            "text_y": height * 0.10018823529411800,
            "rotation": 0,
            "name": "Signed By",
            "font_size": 3,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Coordinate System",
            "text_x": width * 0.94052727272727300,
            "text_y": height * 0.02751764705882350,
            "rotation": 0,
            "name": "Coordinate System",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "??/??/20??",
            "text_x": width * 0.92413636363636400,
            "text_y": height * 0.00757647058823529,
            "rotation": 0,
            "name": "Date",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Pipe Name",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1740235294117650,
            "rotation": 0,
            "name": "Pipe Name",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Starting Station: <>",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1610941176470590,
            "rotation": 0,
            "name": "Starting Station",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": True
        },{
            "text": "Ending Station: <>",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1481647058823530,
            "rotation": 0,
            "name": "Ending Station",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": True
        },{
            "text": "Total Length: <>",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1352235294117650,
            "rotation": 0,
            "name": "Total Length",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": True
        },{
            "text": "From:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1222941176470590,
            "rotation": 0,
            "name": "From",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "To:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.1093529411764710,
            "rotation": 0,
            "name": "To",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Diameter:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.0964235294117647,
            "rotation": 0,
            "name": "Diameter",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Material:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.0834352941176471,
            "rotation": 0,
            "name": "Material",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Type:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.0704941176470588,
            "rotation": 0,
            "name": "Type",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Company:",
            "text_x": width * 0.5170454545454550,
            "text_y": height * 0.0575647058823529,
            "rotation": 0,
            "name": "Company",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        },{
            "text": "Page <dyn type='page' property='index'/> of <dyn type='page' property='count'/>",
            "text_x": width * 0.9640090909090910,
            "text_y": height * 0.007576470588235290,
            "rotation": 0,
            "name": "Pages",
            "font_size": 4,
            "underline": False,
            "font_style": "Regular",
            "locked": False
        }
        ]

        for titles in texts:
            text_group = text_properties(titles, layout, height)
            if titles["locked"]:
                locked_texts.append(text_group)
            else:
                unlocked_texts.append(text_group)

        if locked_texts:
            group_locked_text = arcgispro_project.createGroupElement(layout,
                                                                     locked_texts,
                                                                    "DO NOT TOUCH (Text)"
                                                                    )
            
            group_locked_cim = group_locked_text.getDefinition("V3")
            group_locked_cim.locked = True
            group_locked_text.setDefinition(group_locked_cim)

        if unlocked_texts:
            group_unlocked_text = arcgispro_project.createGroupElement(layout,
                                                                       unlocked_texts,
                                                                       "Editable Text"
                                                                       )
            
            group_unlocked_cim = group_unlocked_text.getDefinition("V3")
            group_unlocked_cim.locked = False
            group_unlocked_text.setDefinition(group_unlocked_cim)

        #Making Boundaries
        grouping_polygons = []

        def boundary_properties(boundary):

            poly_blc = arcpy.Point(boundary["x_min_poly"],
                                   boundary["y_min_poly"])

            poly_tlc = arcpy.Point(boundary["x_min_poly"],
                                   boundary["y_max_poly"])

            poly_trc = arcpy.Point(boundary["x_max_poly"],
                                   boundary["y_max_poly"])

            poly_brc = arcpy.Point(boundary["x_max_poly"],
                                   boundary["y_min_poly"])

            poly_array = arcpy.Array([poly_blc,
                                      poly_tlc,
                                      poly_trc,
                                      poly_brc,
                                      poly_blc])

            poly_extent = arcpy.Polygon(poly_array)

            poly_type = arcgispro_project.listStyleItems("ArcGIS 2D",
                                                         "Polygon",
                                                         "Black Outline (1pt)")[0]

            poly = arcgispro_project.createGraphicElement(layout,
                                                          poly_extent,
                                                          poly_type,
                                                          name=boundary["polygon_name"])

            poly_cim = poly.getDefinition("V3")
            poly_cim.graphic.symbol.symbol.symbolLayers[0].width = boundary["outline"]
            poly.setDefinition(poly_cim)

            return poly

        #Creating boundaries
        boundaries = [{
            "polygon_name": "Legend",
            "x_min_poly": width * 0.011818181818182,
            "y_min_poly": 0,
            "x_max_poly": width * 0.325454545454545,
            "y_max_poly": height * 0.197647058823529,
            "outline": 0.5
        },{
            "polygon_name": "Legend Title",
            "x_min_poly": 0,
            "y_min_poly": 0,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * 0.197647058823529,
            "outline": 0.5
        },{
            "polygon_name": "Plan View",
            "x_min_poly": 0,
            "y_min_poly": height * 0.197647058823529,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * 0.801176470588235,
            "outline": 0.5
        },{
            "polygon_name": "Stationing",
            "x_min_poly": 0,
            "y_min_poly": height * 0.801176470588235,
            "x_max_poly": width * 0.011818181818182,
            "y_max_poly": height * 1,
            "outline": 0.5
        },{
            "polygon_name": "Site Area Title",
            "x_min_poly": width * 0.32545454545454500,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.48090909090909100,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5
        },{
            "polygon_name": "Summary Table Title",
            "x_min_poly": width * 0.48090909090909100,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.60580000000000000,
            "y_max_poly": height * 0.19767058823529400,
            "outline": 0.5
        },{
            "polygon_name": "Summary Table Column 1",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1585647058823530,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1714941176470590,
            "outline": 0.25
        },{
            "polygon_name": "Summary Table Column 2",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1327058823529410,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1456352941176470,
            "outline": 0.25
        },{
            "polygon_name": "Summary Table Column 3",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.1068352941176470,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.1197647058823530,
            "outline": 0.25
        },{
            "polygon_name": "Summary Table Column 4",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0939058823529412,
            "outline": 0.25
        },{
            "polygon_name": "Summary Table Column 5",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": height * 0.0550470588235294,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0679764705882353,
            "outline": 0.25
        },{
            "polygon_name": "Disclaimer Boundary",
            "x_min_poly": width * 0.4809090909090910,
            "y_min_poly": 0,
            "x_max_poly": width * 0.6058000000000000,
            "y_max_poly": height * 0.0550470588235294,
            "outline": 0.5
        },{
            "polygon_name": "Intersection Table",
            "x_min_poly": width * 0.60580000000000000,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.77154545454545500,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5
        },{
            "polygon_name": "Intersection Table Row",
            "x_min_poly": width * 0.6612818181818180,
            "y_min_poly": 0,
            "x_max_poly": width * 0.7167363636363640,
            "y_max_poly": height * 0.1844352941176470,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column 1",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.1600000000000000,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.1723176470588240,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column 2",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.1353647058823530,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.1476823529411760,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column 3",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.1107294117647060,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.1230470588235290,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column 4",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0984117647058824,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.1107294117647060,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column 5",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0737764705882353,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.0860941176470588,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column 6",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0491411764705882,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.0614588235294118,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column 7",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0245058823529412,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.0368235294117647,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column 8",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": height * 0.0121882352941176,
            "x_max_poly": width * 0.7715000000000000,
            "y_max_poly": height * 0.0245058823529412,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Table Column Border",
            "x_min_poly": width * 0.6058000000000000,
            "y_min_poly": 0,
            "x_max_poly": width * 0.7715454545454550,
            "y_max_poly": height * 0.1844352941176470,
            "outline": 0.5
        },{
            "polygon_name": "Intersection Summary Border",
            "x_min_poly": width * 0.77154545454545500,
            "y_min_poly": height * 0.18443529411764700,
            "x_max_poly": width * 0.84103636363636400,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5
        },{
            "polygon_name": "Intersection Summary Column 1",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1585529411764710,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1714941176470590,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Summary Column 2",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1326352941176470,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1455764705882350,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Summary Column 3",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.1068117647058820,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.1197647058823530,
            "outline": 0.25
        },{
            "polygon_name": "Intersection Summary Column 4",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.0944000000000000,
            "outline": 0.25
        },{
            "polygon_name": "Data Sources",
            "x_min_poly": width * 0.7715454545454550,
            "y_min_poly": 0,
            "x_max_poly": width * 0.8410363636363640,
            "y_max_poly": height * 0.0809058823529412,
            "outline": 0.5
        },{
            "polygon_name": "Project Name",
            "x_min_poly": width * 0.84103636363636400,
            "y_min_poly": height * 0.17149411764705900,
            "x_max_poly": width * 0.91529090909090900,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5
        },{
            "polygon_name": "Project Number",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.1452235294117650,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1715058823529410,
            "outline": 0.5
        },{
            "polygon_name": "Location Address",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height* 0.1133294117647060,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1452235294117650,
            "outline": 0.5
        },{
            "polygon_name": "Client",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": height * 0.0809058823529412,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.1133294117647060,
            "outline": 0.5
        },{
            "polygon_name": "Notes",
            "x_min_poly": width * 0.8410363636363640,
            "y_min_poly": 0,
            "x_max_poly": width * 0.9152909090909090,
            "y_max_poly": height * 0.0809058823529412,
            "outline": 0.5
        },{
            "polygon_name": "Insert Logo",
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.1452235294117650,
            "x_max_poly": width,
            "y_max_poly": height * 0.19764705882352900,
            "outline": 0.5
        },{
            "polygon_name": "Names",
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.0943058823529412,
            "x_max_poly": width,
            "y_max_poly": height * 0.1452235294117650,
            "outline": 0.5
        },{
            "polygon_name": "Names",
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": height * 0.0230588235294118,
            "x_max_poly": width,
            "y_max_poly": height * 0.0943058823529412,
            "outline": 0.5
        },{
            "polygon_name": "Date",
            "x_min_poly": width * 0.9152909090909090,
            "y_min_poly": 0,
            "x_max_poly": width * 0.9589090909090910,
            "y_max_poly": height * 0.0230470588235294,
            "outline": 0.5
        },{
            "polygon_name": "Page",
            "x_min_poly": width * 0.9589090909090910,
            "y_min_poly": 0,
            "x_max_poly": width,
            "y_max_poly": height * 0.0230470588235294,
            "outline": 0.5
        },{
            "polygon_name": "Stationing Bar 1",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.9796117647058820,
            "x_max_poly": width,
            "y_max_poly": height,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar 2",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.9398470588235290,
            "x_max_poly": width,
            "y_max_poly": height * 0.9597294117647060,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar 3",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.9000823529411760,
            "x_max_poly": width,
            "y_max_poly": height * 0.9199647058823530,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar 4",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.8603176470588240,
            "x_max_poly": width,
            "y_max_poly": height * 0.8802000000000000,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar 5",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.82055294117647100,
            "x_max_poly": width,
            "y_max_poly": height * 0.84043529411764700,
            "outline": 0.25
        },{
            "polygon_name": "Stationing Bar Border",
            "x_min_poly": width * 0.01176363636363640,
            "y_min_poly": height * 0.80117647058823500,
            "x_max_poly": width,
            "y_max_poly": height,
            "outline": 0.5
        },{
            "polygon_name": "Summary Table Features",
            "x_min_poly": width * 0.4912909090909090,
            "y_min_poly": height * 0.0553058823529412,
            "x_max_poly": width * 0.5913545454545450,
            "y_max_poly": height * 0.1823176470588240,
            "outline": 0
        }
        ]

        for boundary in boundaries:
            poly_group = boundary_properties(boundary)
            grouping_polygons.append(poly_group)

        if grouping_polygons:
            group_polygons = arcgispro_project.createGroupElement(layout,
                                                                  grouping_polygons,
                                                                  "DO NOT TOUCH (Boundaries)"
                                                                  )

            group_cim = group_polygons.getDefinition("V3")
            group_cim.locked = True
            group_polygons.setDefinition(group_cim)

        openlayout = layout.openView()
        if openlayout:
            openlayout.refresh()

#
    # def postExecute():
    #     sdfsdf

# '''
# References
# 1. Esri arcpy guides (ALOT OF GUIDES).
# 2. This video helped with the geoprocessing tool: https://www.youtube.com/watch?v=nPUkTyDaIhg
# 3. https://www.w3schools.com/python/ref_dictionary_get.asp
# 4. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/layout-class.htm
# 5. https://pro.arcgis.com/en/pro-app/3.5/arcpy/mapping/legendelement-class.htm
# 6. https://desktop.arcgis.com/en/arcmap/latest/analyze/arcpy-mapping/legendelement-class.htm
# 7. https://pro.arcgis.com/en/pro-app/3.4/arcpy/mapping/python-cim-access.htm
# 8. https://github.com/Esri/cim-spec?tab=readme-ov-file
# 9. https://community.esri.com/t5/python-questions/modifying-scale-bar-with-cim/td-p/1614800
# 10. https://github.com/Esri/cim-spec/blob/809fb365d8d204d1fbdc51b3fab5bd17d88de2d1/docs/v3/CIMLayout.md#cimscalebar
# 11. https://community.esri.com/t5/arcgis-pro-questions/adjusting-units-of-a-scale-bar-with-arcpy/td-p/1351689
# 12. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/textelement-class.htm
# 13. https://pro.arcgis.com/en/pro-app/latest/help/layouts/add-and-modify-dynamic-text.htm
# 14. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/graphicelement-class.htm
# 15. https://pro.arcgis.com/en/pro-app/latest/tool-reference/cartography/strip-map-index-features.htm
# 16. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/layout-class.htm
# 17. https://pro.arcgis.com/en/pro-app/latest/help/layouts/add-and-modify-dynamic-text.htm
# 18. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/arcgisproject-class.htm
# 19. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/python-cim-access.htm
# 20. https://pro.arcgis.com/en/pro-app/3.4/arcpy/mapping/textelement-class.htm
# 21. https://www.w3schools.com/python/ref_module_time.asp
# 22. https://www.w3schools.com/python/python_try_except.asp
# 23. https://pro.arcgis.com/en/pro-app/latest/tool-reference/cartography/strip-map-index-features.htm
# 24. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/mapseries-class.htm
# 25. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/python-cim-access.htm
# 26. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/map-class.htm
# 27. #https://www.w3schools.com/python/ref_func_hasattr.asp
# 28. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/labelclass-class.htm
# 29. https://pro.arcgis.com/en/pro-app/3.5/tool-reference/environment-settings/output-m-domain.htm
# 30. https://www.w3schools.com/python/ref_func_hasattr.asp
# 31. https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/labelclass-class.htm
# 60. GEMINI HELPED WITH TROUBLESHOOTING
# '''

