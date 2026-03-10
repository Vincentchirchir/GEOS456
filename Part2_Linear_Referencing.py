import arcpy
import os  # python library for joining folders, getting filenames
import shutil


# CREATING A CUSTOM GEOPROCESSING TOOL:
class Toolbox(object):
    def __init__(self):
        self.label = "Generator"
        self.alias = "generator"
        self.tools = [AlignmentSheetGenerator]


class AlignmentSheetGenerator:
    def __init__(self):
        self.label = (
            "Alignment Sheet Generator"  # Gives the name of the geoprocessing tool.
        )
        self.description = "Generates an alignment sheet using a layout template \nONLY PRODUCES LANDSCAPE LAYOUT SHEET"  # This gives information on the custom Geoprocessing tool

    # Defining parameters in the geoprocessing tool:
    def getParameterInfo(self):
        # Layout Name
        layout_name = arcpy.Parameter(
            displayName="Alignment Sheet Name",
            name="alignment_sheet_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        # Layout Size
        layout_size = arcpy.Parameter(
            displayName="Page Size",
            name="page_size",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        # Size Options
        layout_size.filter.type = "ValueList"
        layout_size.filter.list = [
            "Letter (11x8.5)",
            "Legal (14x8.5)",
            "Tabloid (17x11)",
            "ANSI C (22x17)",
            "ANSI D (34x22)",
            "ANSI E (44x34)",
        ]

        # Main Map
        layout_main_map = arcpy.Parameter(
            displayName="Input Main Map",
            name="input_main_map",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        # Mini Map
        layout_mini_map = arcpy.Parameter(
            displayName="Input Mini Map",
            name="input_mini_map",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        maps = arcpy.mp.ArcGISProject("CURRENT").listMaps()
        maps_names = [
            all_maps.name for all_maps in maps
        ]  # GEMINI helped with this (Helped to iterate)
        layout_main_map.filter.type = "valueList"
        layout_main_map.filter.list = maps_names
        layout_mini_map.filter.type = "valueList"
        layout_mini_map.filter.list = maps_names

        # Include Stations?
        show_stationing = arcpy.Parameter(
            displayName="Show Stationing?",
            name="show_stationing",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )

        show_stationing.enabled = True
        show_stationing.values = False

        # Select your linear data (This is for stationings)
        stationing_data = arcpy.Parameter(
            displayName="Input Linear Feature",
            name="input_line_or_polyline_feature",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
        )

        stationing_data.filter.list = ["Polyline"]

        # Intervals in meters for the stationings (5m = 0+005m, 0+010m. 20m = 0+020m, 0+040m, etc.)
        stationings_interval = arcpy.Parameter(
            displayName="Stationing Interval (m)",
            name="interval_in_meters",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )

        # Exclude features you do not want to have intersection points
        exclude_intersect_features = arcpy.Parameter(
            displayName="Exclude Features from Intersect",
            name="exclude_layers_from_intersect",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
        )

        exclude_intersect_features.filter.type = "ValueList"
        arcgispro_project = arcpy.mp.ArcGISProject("CURRENT")
        main_map = arcgispro_project.listMaps()[0]
        exclude_intersect_features.filter.list = [
            feature.name for feature in main_map.listLayers() if feature.isFeatureLayer
        ]

        # Implement Map Series?
        map_series = arcpy.Parameter(
            displayName="Implement Map Series?",
            name="implement_map_series",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )

        map_series.enabled = True
        map_series.values = False

        # Select your map scale
        map_series_scale = arcpy.Parameter(
            displayName="Map Series Scale",
            name="map_series_scale",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )

        parameters = [
            layout_name,  # 0
            layout_size,  # 1
            layout_main_map,  # 2
            layout_mini_map,  # 3
            show_stationing,  # 4
            stationing_data,  # 5
            stationings_interval,  # 6
            exclude_intersect_features,  # 7
            map_series,  # 8
            map_series_scale,  # 9
        ]

        return parameters

    def updateParameters(self, parameters):
        arcgispro_project = arcpy.mp.ArcGISProject("CURRENT")
        if parameters[4].value == True:
            for station in [5, 6, 7]:
                parameters[station].enabled = True
            selected_map = arcgispro_project.activeMap
            if selected_map:
                selected_data = parameters[5].valueAsText
                if selected_data:
                    data_name = os.path.basename(selected_data).split(".")[0]
                else:
                    data_name = ""
                data = [
                    feature.name
                    for feature in selected_map.listLayers()
                    if feature.isFeatureLayer and feature.name != data_name
                ]
                parameters[7].filter.list = data

        else:
            for station in [5, 6, 7]:
                parameters[station].enabled = False

        if parameters[8].value == True:
            for mapseries in [9]:
                parameters[mapseries].enabled = True

        else:
            for mapseries in [9]:
                parameters[mapseries].enabled = False

        return

    def updateMessages(self, parameters):
        if parameters[4].value == True:
            for st in [5, 6, 7]:
                parameters[st].parameterType = "Required"
                if not parameters[st].value:
                    parameters[st].setErrorMessage("This parameter is required!")

        else:
            for ms in [5, 6, 7]:
                parameters[ms].parameterType = "Optional"
                parameters[ms].clearMessage()

        if parameters[8].value == True:
            for ms in [9]:
                parameters[ms].parameterType = "Required"
                if not parameters[ms].value:
                    parameters[ms].setErrorMessage("This parameter is required!")

        else:
            for ms in [9]:
                parameters[ms].parameterType = "Optional"
                parameters[ms].clearMessage()

        return

    def execute(self, parameters, messages):
        # Defining Variables  #USE THIS FOR REFERENCING THE PARAMETER!
        lyt_name = parameters[0].valueAsText
        lyt_size = parameters[1].value
        lyt_main_map_frame = parameters[2].valueAsText
        lyt_mini_map_frame = parameters[3].valueAsText
        st_data = parameters[5].valueAsText
        st_interval = parameters[6].value
        st_data_exclude = parameters[7].valueAsText
        mp_series_scale = parameters[9].value

        # Setting up the project reference
        arcgispro_project = arcpy.mp.ArcGISProject(
            "CURRENT"
        )  # This references the ArcGIS Pro Project (This is needed so python knows what project you are working in)
        gdb_path = arcgispro_project.defaultGeodatabase
        targeted_main_map = arcgispro_project.listMaps(lyt_main_map_frame)[0]
        targeted_mini_map = arcgispro_project.listMaps(lyt_mini_map_frame)[0]


        # workspace settings
        arcpy.env.overwriteOutput = True  # can overwrite output datasets that already exist
        arcpy.env.workspace = r"C:\Capstone\processing_data"  # Data path
        workspace = arcpy.env.workspace
        aprx_path = r"C:\Capstone\Capstone_Project.aprx"

        # projection settings
        projection = arcpy.SpatialReference("NAD 1983 CSRS 3TM 114")
        define_projection = arcpy.SpatialReference(3780)

        # geodatabase settings
        gdb_name = "Group2_Capstone"  # name of new gdb
        gdb_path = os.path.join(workspace, gdb_name + ".gdb")  # saving the full path of gdb

        # Study Area Settings
        study_area_section_name = "V4-1_SEC.shp"
        study_area_field = "DESCRIPTOR"
        study_area_ATS = "SEC-01 TWP-027 RGE-29 MER-4"
        studyarea_path = os.path.join(gdb_path, "Study_Area")

        # Pipeline features settings
        pipeline_name = "Pipelines_GCS_NAD83.shp"
        route_id_field = "Route_ID"  # field used as the route identifier
        route_id_value = "PIPE_01"  # constant route ID assigned to the dissolved pipeline route

        # stations settings
        station_interval = f"{st_interval} meters"

        # user input data settings
        analysis_layers = [
            "Subsurface_Lineaments__WebM.shp",
            "glac_landform_ln_ll.shp",
            "Base_Waterbody_Polygon.shp",
            "Target_A",
        ]
        input_layers = [pipeline_name] + analysis_layers


        # function to list all data and store the path for further processing
        def features(workspace):
            data = []  # create a list to store data and path
            for dirpath, dirname, filenames in arcpy.da.Walk(workspace):
                for f in filenames:
                    data_path = os.path.join(dirpath, f)  # for each file in f, create path
                    data.append(data_path)  # Store the data path in data
            return data  # return the full list of data paths found


        print("")

        data_shp = features(
            workspace
        )  # calls the feature function to get all data and its path stored earlier

        # print all data and path
        print("Listing all data and their paths...")
        for data in data_shp:
            print(data)
            print(arcpy.GetMessages())
            print("")

        # Delete any gdb found and create a new one
        wkspace = arcpy.ListWorkspaces("", "FileGDB")  # LIST ALL GDB IN THE WORKSPACE
        for gdb in wkspace:
            if arcpy.Exists(gdb):  # checks if there is any existing gdb
                arcpy.management.Delete(gdb)  # if any gdb is found, it deletes
                print("Deleting existing gdb...")
                print(arcpy.GetMessages())
                print("")

        # Creating a new gdb
        arcpy.management.CreateFileGDB(
            workspace, gdb_name + ".gdb"
        )  # creates the gdb in workspace folder
        print(arcpy.GetMessages())
        print("")

        # identifying studying area
        study_area_section = next(
            p
            for p in data_shp
            if os.path.basename(p).lower() == study_area_section_name.lower()
        )  # Searches through the data_shp to find section

        # Create a temporary feature layer  of all section, before identifying the section we want
        section_layer = arcpy.MakeFeatureLayer_management(study_area_section, "sections_layer")

        # Create SQL function to select from the temporary layer
        delimfield = arcpy.AddFieldDelimiters(study_area_section, study_area_field)
        sql_query = f"{delimfield} = '{study_area_ATS}'"

        # Select features from sections_layer whose DESCRIPTOR equals that exact text
        arcpy.SelectLayerByAttribute_management(section_layer, "NEW_SELECTION", sql_query)

        # project study area and store in gdb
        arcpy.management.Project("sections_layer", studyarea_path, projection)

        # clip needed data to study area
        for data_list in input_layers:
            dataList_path = next(
                p for p in data_shp if os.path.basename(p).lower() == data_list.lower()
            )  # Finds the full path of that shapefile in your workspace (case-insensitive).

            base = os.path.splitext(data_list)[
                0
            ]  # Removes .shp to get the base name (example: "Airdrie_Roads")
            valid_name = arcpy.ValidateTableName(
                base, gdb_path
            )  # validating names before building output

            # Describing data to understand for example coordinates, geometry, shapetype
            desc = arcpy.Describe(dataList_path)
            print("Data Type: ", desc.dataType)
            print("Spatial Reference: ", desc.spatialReference.name)

            # set names
            projected_data = os.path.join(
                gdb_path, valid_name + "_prj"
            )  # sets names for projected data. projected data will end with _prj
            clipped_data = os.path.join(
                gdb_path, valid_name + "_clip"
            )  # clipped data will end with _clip
            contour_output = os.path.join(
                gdb_path, valid_name + "_contours"
            )  # name and path for contours

            # Define projection data
            if desc.spatialReference.name == "Unknown":
                arcpy.DefineProjection_management(dataList_path, define_projection)
                print(arcpy.GetMessages())
                print("")

            # project
            if desc.dataType in ["FeatureClass", "ShapeFile"]:
                arcpy.management.Project(dataList_path, projected_data, projection)
                arcpy.analysis.Clip(projected_data, studyarea_path, clipped_data)
                print(arcpy.GetMessages())
                print("")

            elif desc.dataType == "RasterDataset":
                arcpy.management.ProjectRaster(
                    dataList_path, projected_data, projection, "BILINEAR"
                )

            elif desc.dataType == "Tin":
                # converting Lidar to contour
                interval = 5
                print("Generating Contours...")
                arcpy.ddd.SurfaceContour(dataList_path, contour_output, interval)

                # Project
                arcpy.management.Project(contour_output, projected_data, projection)

                # Clip
                arcpy.analysis.Clip(projected_data, studyarea_path, clipped_data)

                print(arcpy.GetMessages())
                print("")

            # Delete internediate projected data
            print("Deleting...")
            arcpy.management.Delete(projected_data)
            print(arcpy.GetMessages())
            print("")

            print(f"Successfully projected and clipped {data_list} = {clipped_data}")
            print(arcpy.GetMessages())
            print("")

        # creating a route [linear referencing]
        pipeline_base = os.path.splitext(pipeline_name)[0]
        pipeline_fc = os.path.join(gdb_path, f"{pipeline_base}_clip")

        # create a new field for route ID if the data do not have
        if route_id_field not in [
            f.name for f in arcpy.ListFields(pipeline_fc)
        ]:  # check if the field RouteID exists in pipeline data
            arcpy.management.AddField(
                pipeline_fc, route_id_field, "TEXT", field_length=50
            )  # if not, add a new field

        # calculate the new field
        arcpy.management.CalculateField(
            pipeline_fc, route_id_field, f"'{route_id_value}'", "PYTHON3"
        )  # CALCULATES A CONSTATNT VALUE FROM PIPE_01 for every pipe

        # Dissolve pipeline to one feature or one per routeID
        pipeline_diss = os.path.join(gdb_path, "Pipeline_Dissolve")
        arcpy.management.Dissolve(pipeline_fc, pipeline_diss, route_id_field)

        # CREATING M ENABLED ROUTE FEATURE CLASS
        routes_fc = os.path.join(gdb_path, "Pipeline_Route")  # path for output route
        arcpy.lr.CreateRoutes(
            pipeline_diss, route_id_field, routes_fc, "LENGTH"
        )  # LENGTH tells ArcGIS to create measures from 0 to total length coz we dont have starting and ending distance

        # Calculating Chainage field
        calculate_field = r"""
        def chain(m):
            m=int(round(float(m)))
            km=m//1000
            remainder=m % 1000
            return f"{km}+{remainder:03d}"

        """

        # Generate points along the route
        station_points = os.path.join(gdb_path, "Station_Points")
        arcpy.management.GeneratePointsAlongLines(
            routes_fc,
            station_points,
            "DISTANCE",
            Distance=station_interval,
            Include_End_Points="END_POINTS",
        )


        def locate_features(
            in_features,
            in_routes,
            route_id_field,
            out_table,
            out_event_properties,
            radius_or_tolerance="5 Meters",
            distance_field="DISTANCE",
        ):
            # Locate station points along the route

            arcpy.lr.LocateFeaturesAlongRoutes(
                in_features=in_features,
                in_routes=in_routes,
                route_id_field=route_id_field,
                radius_or_tolerance=radius_or_tolerance,
                out_table=out_table,
                out_event_properties=out_event_properties,
                distance_field=distance_field,
            )
            # Adding chainage labels to station table
            if "Chainage" not in [f.name for f in arcpy.ListFields(station_table)]:
                arcpy.management.AddField(station_table, "Chainage", "TEXT", field_length=20)
            arcpy.management.CalculateField(
                station_table, "Chainage", "chain(!MEAS!)", "PYTHON3", calculate_field
            )
            return out_table


        station_table = os.path.join(gdb_path, "Station_Events")
        station_table = locate_features(
            in_features=station_points,
            in_routes=routes_fc,
            route_id_field=route_id_field,
            out_table=station_table,
            out_event_properties=f"{route_id_field} POINT MEAS",
        )
        # Make station event layer
        station_lyr = "Station_Events_lyr"
        arcpy.lr.MakeRouteEventLayer(
            in_routes=routes_fc,
            route_id_field=route_id_field,
            in_table=station_table,
            in_event_properties=f"{route_id_field} POINT MEAS",
            out_layer=station_lyr,
        )
        station_fc = os.path.join(gdb_path, "Station_Events_fc")
        arcpy.management.CopyFeatures(station_lyr, station_fc)

        # excluding features here coz pipeline is the main route we are checking it interscts with which feature
        arcpy.env.workspace = gdb_path
        fc_gdb = arcpy.ListFeatureClasses()
        exclude_fc = {
            "pipelines_gcs_nad83_clip",  # the clipped pipe
            "pipeline_dissolve",  # dissolve output
            "pipeline_route",  # route output
            "study_area",
            "station_points",
            "station_events_fc",
        }
        include_fc = [fc for fc in fc_gdb if fc.lower() not in exclude_fc]
        for fc in include_fc:
            print(fc)

        # Where does pipeline Intersect/overlap with other features?
        intersect_points = []  # it will store points where it intersect with pipeline
        overlap = []  # it will store where pipeline overlaps other features

        for f in include_fc:
            fc_path = os.path.join(gdb_path, f)
            desc = arcpy.Describe(fc_path)  # describe features that will be inlcuded
            geom = desc.shapeType

            base_name = os.path.basename(f)

            out_point = os.path.join(
                gdb_path, arcpy.ValidateTableName(base_name + "_point", gdb_path)
            )
            arcpy.analysis.Intersect([pipeline_diss, fc_path], out_point, output_type="POINT")
            intersect_points.append(out_point)
            print(f"Point Intersect created: {out_point}")

            if geom == "Polygon":
                out_overlap = os.path.join(
                    gdb_path, arcpy.ValidateTableName(base_name + "_overlap", gdb_path)
                )
                arcpy.analysis.Intersect(
                    [pipeline_diss, fc_path], out_overlap, "", "", output_type="LINE"
                )
                overlap.append(out_overlap)
                print(f"Overlap Created: {out_overlap}")

        # Locating features along the route. It produces table
        event_tables_points = []
        event_tables_lines = []

        # locate points intersecting pipeline
        for point_fc in intersect_points:
            out_table = os.path.join(
                gdb_path,
                arcpy.ValidateTableName(os.path.basename(point_fc) + "_event", gdb_path),
            )

            out_table = locate_features(
                in_features=point_fc,
                in_routes=routes_fc,
                route_id_field=route_id_field,
                out_table=out_table,
                out_event_properties=f"{route_id_field} POINT MEAS",
            )
            event_tables_points.append(out_table)
            print("Created event table: ", out_table)
            print(arcpy.GetMessages())

            # locating overlps
        for overlaps in overlap:
            out_table_overlap = os.path.join(
                gdb_path,
                arcpy.ValidateTableName(os.path.basename(overlaps) + "_events", gdb_path),
            )
            print("Overlap shapeType:", arcpy.Describe(overlaps).shapeType)

            out_table_overlap = locate_features(
                in_features=overlaps,
                in_routes=routes_fc,
                route_id_field=route_id_field,
                out_table=out_table_overlap,
                out_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
            )
            event_tables_lines.append(out_table_overlap)
            print("Overlap Event Table: ", out_table_overlap)
            print(arcpy.GetMessages())

        # Chainage
        # chainage for point
        for table in event_tables_points:
            if "Chainage" not in [f.name for f in arcpy.ListFields(table)]:
                arcpy.management.AddField(table, "Chainage", "TEXT", field_length=20)

            arcpy.management.CalculateField(
                table, "Chainage", "chain(!MEAS!)", "PYTHON3", calculate_field
            )
            print("Chainage added (points):", table)

        # For LINE event tables (overlaps)
        for table_overlap in event_tables_lines:
            existing = [f.name for f in arcpy.ListFields(table_overlap)]

            if "FromCh" not in existing:
                arcpy.management.AddField(table_overlap, "FromCh", "TEXT", field_length=20)
            if "ToCh" not in existing:
                arcpy.management.AddField(table_overlap, "ToCh", "TEXT", field_length=20)
            if "ChainageRange" not in existing:
                arcpy.management.AddField(
                    table_overlap, "ChainageRange", "TEXT", field_length=30
                )

            arcpy.management.CalculateField(
                table_overlap, "FromCh", "chain(!FMEAS!)", "PYTHON3", calculate_field
            )
            arcpy.management.CalculateField(
                table_overlap, "ToCh", "chain(!TMEAS!)", "PYTHON3", calculate_field
            )
            arcpy.management.CalculateField(
                table_overlap, "ChainageRange", "!FromCh! + ' – ' + !ToCh!", "PYTHON3"
            )
            print("Chainage range added (lines):", table_overlap)

        # Create Route Event Layers for display
        # POINT event layers
        for tbl in event_tables_points:
            lyr_name = os.path.basename(tbl) + "_lyr"
            arcpy.lr.MakeRouteEventLayer(
                in_routes=routes_fc,
                route_id_field=route_id_field,
                in_table=tbl,
                in_event_properties=f"{route_id_field} POINT MEAS",
                out_layer=lyr_name,
            )
            out_layer = os.path.join(
                gdb_path, arcpy.ValidateTableName(lyr_name + "_fc", gdb_path)
            )
            arcpy.management.CopyFeatures(lyr_name, out_layer)
            print("Made POINT event layer:", lyr_name)

        # LINE event layers
        for tbl in event_tables_lines:
            lyr_name = os.path.basename(tbl) + "_lyr"
            arcpy.lr.MakeRouteEventLayer(
                in_routes=routes_fc,
                route_id_field=route_id_field,
                in_table=tbl,
                in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
                out_layer=lyr_name,
            )
            out_fc = os.path.join(gdb_path, arcpy.ValidateTableName(lyr_name + "_fc", gdb_path))
            arcpy.management.CopyFeatures(lyr_name, out_fc)
            print("Made LINE event layer:", lyr_name)

        # APRX SETUP
        template_aprx = r"C:\Capstone\Alignmentsheet\Alignmentsheet.aprx"
        output_aprx = aprx_path

        if os.path.exists(output_aprx):
            os.remove(output_aprx)

        shutil.copy(template_aprx, output_aprx)

        aprx = arcpy.mp.ArcGISProject(output_aprx)

        # CREATE OR GET MAP
        map_name = "Capstone Map"

        existing_maps = aprx.listMaps(map_name)
        if existing_maps:
            m = existing_maps[0]
        else:
            m = aprx.createMap(map_name)

        # ADD DATA
        layers_to_add = [
            os.path.join(gdb_path, "Study_Area"),
            os.path.join(gdb_path, "Pipeline_Route"),
            os.path.join(gdb_path, "Station_Events_fc"),
            os.path.join(gdb_path, "Base_Waterbody_Polygon_clip"),
            os.path.join(gdb_path, "Base_Waterbody_Polygon_clip_point_event_lyr_fc"),
            os.path.join(gdb_path, "glac_landform_ln_ll_clip"),
            os.path.join(gdb_path, "glac_landform_ln_ll_clip_point_event_lyr_fc"),
            os.path.join(gdb_path, "Subsurface_Lineaments__WebM_clip"),
            os.path.join(gdb_path, "Subsurface_Lineaments__WebM_clip_point_event_lyr_fc"),
        ]

        for lyr in layers_to_add:
            if arcpy.Exists(lyr):
                m.addDataFromPath(lyr)
                print(f"Added: {lyr}")
            else:
                print(f"Missing: {lyr}")

        # CONNECT LAYOUT MAP FRAME
        layouts = aprx.listLayouts("Alignment_Sheet")
        if layouts:
            layout = layouts[0]

            mapframes = layout.listElements("MAPFRAME_ELEMENT", "Main Map Frame")
            if mapframes:
                mf = mapframes[0]
                mf.map = m

                route_layers = m.listLayers("Pipeline_Route")
                if route_layers:
                    mf.camera.setExtent(mf.getLayerExtent(route_layers[0], False, True))


        aprx.save()
        del aprx

        print(f"Project saved successfully: {output_aprx}")
