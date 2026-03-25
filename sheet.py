# # route_utils.py
# import arcpy
# import os


# def create_route_with_measure_system(
#     input_line_fc,
#     output_gdb,
#     start_measure=0,
#     route_id_field="Route_ID",
#     route_id_value="ROUTE_01",
# ):
#     desc = arcpy.Describe(input_line_fc)
#     catalog_path = desc.catalogPath

#     base_name = arcpy.ValidateTableName(
#         os.path.splitext(os.path.basename(catalog_path))[0], output_gdb
#     )

#     line_copy_fc = os.path.join(output_gdb, base_name + "_copy")
#     arcpy.management.CopyFeatures(input_line_fc, line_copy_fc)

#     field_names = [f.name for f in arcpy.ListFields(line_copy_fc)]
#     if route_id_field not in field_names:
#         arcpy.management.AddField(line_copy_fc, route_id_field, "TEXT", field_length=50)

#     arcpy.management.CalculateField(
#         line_copy_fc, route_id_field, f"'{route_id_value}'", "PYTHON3"
#     )

#     route_diss = os.path.join(output_gdb, base_name + "_dissolve")
#     arcpy.management.Dissolve(line_copy_fc, route_diss, route_id_field)

#     diss_fields = [f.name for f in arcpy.ListFields(route_diss)]
#     if "FromM" not in diss_fields:
#         arcpy.management.AddField(route_diss, "FromM", "DOUBLE")
#     if "ToM" not in diss_fields:
#         arcpy.management.AddField(route_diss, "ToM", "DOUBLE")

#     arcpy.management.CalculateField(
#         route_diss, "FromM", str(float(start_measure)), "PYTHON3"
#     )

#     code_block = """
# def calc_to_m(shape_length, start_m):
#     return float(shape_length) + float(start_m)
# """

#     arcpy.management.CalculateField(
#         route_diss,
#         "ToM",
#         f"calc_to_m(!shape.length!, {float(start_measure)})",
#         "PYTHON3",
#         code_block,
#     )

#     route_fc = os.path.join(output_gdb, base_name + "_route")
#     arcpy.lr.CreateRoutes(
#         route_diss, route_id_field, route_fc, "TWO_FIELDS", "FromM", "ToM"
#     )

#     if arcpy.Exists(line_copy_fc):
#         arcpy.management.Delete(line_copy_fc)
#     if arcpy.Exists(route_diss):
#         arcpy.management.Delete(route_diss)

#     return {
#         "route_fc": route_fc,
#         "route_id_field": route_id_field,
#         "route_id_value": route_id_value,
#         "base_name": base_name,
#     }


# def create_stationing_source_line(
#     route_fc,
#     output_gdb,
#     base_name,
#     route_id_field,
#     route_id_value,
#     start_measure=None,
#     end_measure=None,
# ):
#     if end_measure is None:
#         return route_fc

#     segment_table = os.path.join(output_gdb, f"{base_name}_segment_event")
#     if arcpy.Exists(segment_table):
#         arcpy.management.Delete(segment_table)

#     arcpy.management.CreateTable(output_gdb, f"{base_name}_segment_event")

#     seg_fields = [f.name for f in arcpy.ListFields(segment_table)]
#     if route_id_field not in seg_fields:
#         arcpy.management.AddField(
#             segment_table, route_id_field, "TEXT", field_length=50
#         )
#     if "FMEAS" not in seg_fields:
#         arcpy.management.AddField(segment_table, "FMEAS", "DOUBLE")
#     if "TMEAS" not in seg_fields:
#         arcpy.management.AddField(segment_table, "TMEAS", "DOUBLE")

#     with arcpy.da.InsertCursor(
#         segment_table, [route_id_field, "FMEAS", "TMEAS"]
#     ) as cur:
#         cur.insertRow([route_id_value, float(start_measure), float(end_measure)])

#     segment_layer = f"{base_name}_segment_lyr"
#     arcpy.lr.MakeRouteEventLayer(
#         in_routes=route_fc,
#         route_id_field=route_id_field,
#         in_table=segment_table,
#         in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
#         out_layer=segment_layer,
#     )

#     segment_fc = os.path.join(output_gdb, f"{base_name}_segment_fc")
#     if arcpy.Exists(segment_fc):
#         arcpy.management.Delete(segment_fc)

#     arcpy.management.CopyFeatures(segment_layer, segment_fc)
#     return segment_fc


# # stationing_utils.py
# import arcpy
# import os

# from route_utils import create_route_with_measure_system, create_stationing_source_line


# def remove_duplicate_station_measures(
#     station_points, station_table, measure_field="MEAS"
# ):
#     seen_measures = set()
#     duplicate_station_ids = []

#     with arcpy.da.SearchCursor(station_table, ["StationID", measure_field]) as cursor:
#         for station_id, meas in cursor:
#             key = round(float(meas), 6) if meas is not None else None

#             if key in seen_measures:
#                 duplicate_station_ids.append(station_id)
#             else:
#                 seen_measures.add(key)

#     if not duplicate_station_ids:
#         return

#     duplicate_station_ids_set = set(duplicate_station_ids)

#     with arcpy.da.UpdateCursor(station_table, ["StationID"]) as cursor:
#         for row in cursor:
#             if row[0] in duplicate_station_ids_set:
#                 cursor.deleteRow()

#     with arcpy.da.UpdateCursor(station_points, ["StationID"]) as cursor:
#         for row in cursor:
#             if row[0] in duplicate_station_ids_set:
#                 cursor.deleteRow()


# def join_station_chainage_to_points(station_points, station_table):
#     point_fields = [f.name for f in arcpy.ListFields(station_points)]

#     fields_to_delete = []
#     for fld in ["Chainage", "MEAS", "FMEAS", "TMEAS"]:
#         if fld in point_fields:
#             fields_to_delete.append(fld)

#     if fields_to_delete:
#         arcpy.management.DeleteField(station_points, fields_to_delete)

#     arcpy.management.JoinField(
#         in_data=station_points,
#         in_field="StationID",
#         join_table=station_table,
#         join_field="StationID",
#         fields=["MEAS", "Chainage"],
#     )


# def create_route_and_stationing(
#     input_line_fc,
#     output_gdb,
#     station_interval,
#     tolerance,
#     start_measure=0,
#     end_measure=None,
#     route_id_field="Route_ID",
#     route_id_value="ROUTE_01",
# ):
#     route_info = create_route_with_measure_system(
#         input_line_fc=input_line_fc,
#         output_gdb=output_gdb,
#         start_measure=start_measure,
#         route_id_field=route_id_field,
#         route_id_value=route_id_value,
#     )

#     route_fc = route_info["route_fc"]
#     base_name = route_info["base_name"]

#     station_source_fc = create_stationing_source_line(
#         route_fc=route_fc,
#         output_gdb=output_gdb,
#         base_name=base_name,
#         route_id_field=route_id_field,
#         route_id_value=route_id_value,
#         start_measure=start_measure,
#         end_measure=end_measure,
#     )

#     station_points = os.path.join(output_gdb, base_name + "_station_points")
#     if arcpy.Exists(station_points):
#         arcpy.management.Delete(station_points)

#     arcpy.management.GeneratePointsAlongLines(
#         station_source_fc,
#         station_points,
#         "DISTANCE",
#         Distance=station_interval,
#         Include_End_Points="END_POINTS",
#     )

#     if "StationID" not in [f.name for f in arcpy.ListFields(station_points)]:
#         arcpy.management.AddField(station_points, "StationID", "LONG")

#     arcpy.management.CalculateField(
#         station_points, "StationID", "!OBJECTID!", "PYTHON3"
#     )

#     station_table = os.path.join(output_gdb, base_name + "_station_events")
#     if arcpy.Exists(station_table):
#         arcpy.management.Delete(station_table)

#     arcpy.lr.LocateFeaturesAlongRoutes(
#         in_features=station_points,
#         in_routes=route_fc,
#         route_id_field=route_id_field,
#         out_table=station_table,
#         out_event_properties=f"{route_id_field} POINT MEAS",
#         radius_or_tolerance=tolerance,
#         distance_field="DISTANCE",
#     )

#     table_fields = [f.name for f in arcpy.ListFields(station_table)]
#     if "Chainage" not in table_fields:
#         arcpy.management.AddField(station_table, "Chainage", "TEXT", field_length=20)

#     calculate_field_code = r"""
# def chain(val):
#     val = int(round(float(val)))
#     km = val // 1000
#     remainder = val % 1000
#     return f"{km}+{remainder:03d}"
# """

#     arcpy.management.CalculateField(
#         station_table, "Chainage", "chain(!MEAS!)", "PYTHON3", calculate_field_code
#     )

#     remove_duplicate_station_measures(
#         station_points=station_points, station_table=station_table, measure_field="MEAS"
#     )

#     return {
#         "route_fc": route_fc,
#         "station_source_fc": station_source_fc,
#         "station_points": station_points,
#         "station_table": station_table,
#         "route_id_field": route_id_field,
#     }


# # event_utils.py
# import arcpy
# import os


# def create_intersections_and_overlaps(route_fc, output_gdb, analysis_layers):
#     point_intersections = []
#     line_overlaps = []

#     route_name = os.path.splitext(os.path.basename(route_fc))[0]

#     for lyr in analysis_layers:
#         try:
#             desc = arcpy.Describe(lyr)
#             layer_name = arcpy.ValidateTableName(desc.baseName, output_gdb)
#             shape_type = desc.shapeType

#             if layer_name.lower() == route_name.lower():
#                 continue

#             point_out = os.path.join(output_gdb, f"{layer_name}_point")
#             arcpy.analysis.Intersect([route_fc, lyr], point_out, output_type="POINT")

#             if int(arcpy.management.GetCount(point_out)[0]) > 0:
#                 point_intersections.append(point_out)
#             else:
#                 arcpy.management.Delete(point_out)

#             if shape_type in ["Polyline", "Polygon"]:
#                 overlap_out = os.path.join(output_gdb, f"{layer_name}_overlap")
#                 arcpy.analysis.Intersect(
#                     [route_fc, lyr], overlap_out, output_type="LINE"
#                 )

#                 if int(arcpy.management.GetCount(overlap_out)[0]) > 0:
#                     line_overlaps.append(overlap_out)
#                 else:
#                     arcpy.management.Delete(overlap_out)

#         except Exception as e:
#             arcpy.AddWarning(f"Skipped layer {lyr}: {e}")

#     return {
#         "point_intersections": point_intersections,
#         "line_overlaps": line_overlaps,
#     }


# def locate_intersections_and_overlaps(
#     route_fc, route_id_field, output_gdb, tolerance, point_intersections, line_overlaps
# ):
#     point_event_tables = []
#     line_event_tables = []

#     for point_fc in point_intersections:
#         point_name = arcpy.ValidateTableName(
#             os.path.splitext(os.path.basename(point_fc))[0], output_gdb
#         )
#         out_table = os.path.join(output_gdb, f"{point_name}_event")

#         arcpy.lr.LocateFeaturesAlongRoutes(
#             in_features=point_fc,
#             in_routes=route_fc,
#             route_id_field=route_id_field,
#             out_table=out_table,
#             out_event_properties=f"{route_id_field} POINT MEAS",
#             radius_or_tolerance=tolerance,
#             distance_field="DISTANCE",
#         )

#         if int(arcpy.management.GetCount(out_table)[0]) > 0:
#             point_event_tables.append(out_table)
#         else:
#             arcpy.management.Delete(out_table)

#     for overlap_fc in line_overlaps:
#         overlap_name = arcpy.ValidateTableName(
#             os.path.splitext(os.path.basename(overlap_fc))[0], output_gdb
#         )
#         out_table = os.path.join(output_gdb, f"{overlap_name}_event")

#         arcpy.lr.LocateFeaturesAlongRoutes(
#             in_features=overlap_fc,
#             in_routes=route_fc,
#             route_id_field=route_id_field,
#             out_table=out_table,
#             out_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
#             radius_or_tolerance=tolerance,
#             distance_field="DISTANCE",
#         )

#         if int(arcpy.management.GetCount(out_table)[0]) > 0:
#             line_event_tables.append(out_table)
#         else:
#             arcpy.management.Delete(out_table)

#     return {
#         "point_event_tables": point_event_tables,
#         "line_event_tables": line_event_tables,
#     }


# def chainage_code_block():
#     return r"""
# def chain(val):
#     val = int(round(float(val)))
#     km = val // 1000
#     remainder = val % 1000
#     return f"{km}+{remainder:03d}"
# """


# def add_chainage_to_event_tables(point_event_tables, line_event_tables):
#     code_block = chainage_code_block()

#     for table in point_event_tables:
#         existing_fields = [f.name for f in arcpy.ListFields(table)]

#         if "Chainage" not in existing_fields:
#             arcpy.management.AddField(table, "Chainage", "TEXT", field_length=20)

#         arcpy.management.CalculateField(
#             table, "Chainage", "chain(!MEAS!)", "PYTHON3", code_block
#         )

#     for table in line_event_tables:
#         existing_fields = [f.name for f in arcpy.ListFields(table)]

#         if "FromCh" not in existing_fields:
#             arcpy.management.AddField(table, "FromCh", "TEXT", field_length=20)

#         if "ToCh" not in existing_fields:
#             arcpy.management.AddField(table, "ToCh", "TEXT", field_length=20)

#         if "ChainageRange" not in existing_fields:
#             arcpy.management.AddField(table, "ChainageRange", "TEXT", field_length=30)

#         arcpy.management.CalculateField(
#             table, "FromCh", "chain(!FMEAS!)", "PYTHON3", code_block
#         )

#         arcpy.management.CalculateField(
#             table, "ToCh", "chain(!TMEAS!)", "PYTHON3", code_block
#         )

#         arcpy.management.CalculateField(
#             table, "ChainageRange", "!FromCh! + ' - ' + !ToCh!", "PYTHON3"
#         )


# def make_event_layers_from_tables(
#     route_fc, route_id_field, output_gdb, point_event_tables, line_event_tables
# ):
#     point_event_features = []
#     line_event_features = []

#     for table in point_event_tables:
#         base_name = arcpy.ValidateTableName(
#             os.path.splitext(os.path.basename(table))[0], output_gdb
#         )

#         out_layer = f"{base_name}_lyr"
#         out_fc = os.path.join(output_gdb, f"{base_name}_fc")

#         arcpy.lr.MakeRouteEventLayer(
#             in_routes=route_fc,
#             route_id_field=route_id_field,
#             in_table=table,
#             in_event_properties=f"{route_id_field} POINT MEAS",
#             out_layer=out_layer,
#         )

#         arcpy.management.CopyFeatures(out_layer, out_fc)
#         point_event_features.append(out_fc)

#     for table in line_event_tables:
#         base_name = arcpy.ValidateTableName(
#             os.path.splitext(os.path.basename(table))[0], output_gdb
#         )

#         out_layer = f"{base_name}_lyr"
#         out_fc = os.path.join(output_gdb, f"{base_name}_fc")

#         arcpy.lr.MakeRouteEventLayer(
#             in_routes=route_fc,
#             route_id_field=route_id_field,
#             in_table=table,
#             in_event_properties=f"{route_id_field} LINE FMEAS TMEAS",
#             out_layer=out_layer,
#         )

#         arcpy.management.CopyFeatures(out_layer, out_fc)
#         line_event_features.append(out_fc)

#     return {
#         "point_event_features": point_event_features,
#         "line_event_features": line_event_features,
#     }


# # map_utils.py
# import arcpy


# def add_outputs_to_current_map(outputs):
#     try:
#         aprx = arcpy.mp.ArcGISProject("CURRENT")
#         active_map = aprx.activeMap

#         if not active_map:
#             return

#         route_layer = active_map.addDataFromPath(outputs["route_fc"])
#         station_layer = active_map.addDataFromPath(outputs["station_points"])

#         sym = route_layer.symbology
#         if sym.renderer.type == "SimpleRenderer":
#             sym.renderer.symbol.color = {"RGB": [255, 0, 0, 100]}
#             sym.renderer.symbol.width = 4
#         route_layer.symbology = sym

#         sym = station_layer.symbology
#         if sym.renderer.type == "SimpleRenderer":
#             sym.renderer.symbol.color = {"RGB": [0, 0, 255, 100]}
#             sym.renderer.symbol.size = 6
#         station_layer.symbology = sym

#         view = aprx.activeView
#         if hasattr(view, "camera"):
#             extent = arcpy.Describe(outputs["route_fc"]).extent
#             view.camera.setExtent(extent)

#         station_layer.showLabels = True
#         for lbl in station_layer.listLabelClasses():
#             lbl.expression = "$feature.Chainage"

#     except Exception as e:
#         arcpy.AddWarning(f"Could not update map display: {e}")


# # Now your .pyt becomes much smaller

# # At the top of GenerateStationing.pyt:

# import arcpy
# import os
# import sys

# tool_folder = os.path.dirname(__file__)
# if tool_folder not in sys.path:
#     sys.path.append(tool_folder)

# from stationing_utils import (
#     create_route_and_stationing,
#     join_station_chainage_to_points,
# )
# from event_utils import (
#     create_intersections_and_overlaps,
#     locate_intersections_and_overlaps,
#     add_chainage_to_event_tables,
#     make_event_layers_from_tables,
# )
# from map_utils import add_outputs_to_current_map

# # Then keep:

# # Toolbox

# # GenerateStationing

# # getParameterInfo

# # updateMessages

# # And simplify execute() to mainly orchestrate.


# # Your new execute() logic
# def execute(self, parameters, messages):
#     arcpy.env.overwriteOutput = True

#     input_line_fc = parameters[0].valueAsText
#     output_gdb = parameters[1].valueAsText
#     station_interval = parameters[2].valueAsText

#     start_measure = 0
#     if parameters[3].value is not None:
#         start_measure = float(parameters[3].value)

#     end_measure = None
#     if parameters[4].value is not None:
#         end_measure = float(parameters[4].value)

#     tolerance = "1 Meters"
#     if parameters[5].valueAsText:
#         tolerance = parameters[5].valueAsText

#     analysis_layers = []
#     if parameters[6].valueAsText:
#         analysis_layers = parameters[6].valueAsText.split(";")

#     messages.addMessage("Creating route and stationing...")

#     outputs = create_route_and_stationing(
#         input_line_fc=input_line_fc,
#         output_gdb=output_gdb,
#         station_interval=station_interval,
#         tolerance=tolerance,
#         start_measure=start_measure,
#         end_measure=end_measure,
#     )

#     messages.addMessage(f"Route created: {outputs['route_fc']}")
#     messages.addMessage(f"Station points created: {outputs['station_points']}")
#     messages.addMessage(f"Station event table created: {outputs['station_table']}")

#     join_station_chainage_to_points(
#         station_points=outputs["station_points"], station_table=outputs["station_table"]
#     )
#     messages.addMessage("Chainage joined to station points.")

#     if analysis_layers:
#         messages.addMessage("Creating intersections and overlaps...")

#         crossing_outputs = create_intersections_and_overlaps(
#             route_fc=outputs["route_fc"],
#             output_gdb=output_gdb,
#             analysis_layers=analysis_layers,
#         )

#         event_outputs = locate_intersections_and_overlaps(
#             route_fc=outputs["route_fc"],
#             route_id_field=outputs["route_id_field"],
#             tolerance=tolerance,
#             output_gdb=output_gdb,
#             point_intersections=crossing_outputs["point_intersections"],
#             line_overlaps=crossing_outputs["line_overlaps"],
#         )

#         add_chainage_to_event_tables(
#             point_event_tables=event_outputs["point_event_tables"],
#             line_event_tables=event_outputs["line_event_tables"],
#         )

#         make_event_layers_from_tables(
#             route_fc=outputs["route_fc"],
#             route_id_field=outputs["route_id_field"],
#             output_gdb=output_gdb,
#             point_event_tables=event_outputs["point_event_tables"],
#             line_event_tables=event_outputs["line_event_tables"],
#         )
#     else:
#         messages.addMessage(
#             "No analysis layers provided. Skipping intersections and overlaps."
#         )

#     add_outputs_to_current_map(outputs)


# import arcpy


# def draw_stationing_leader_for_points(
#     layout,
#     map_frame,
#     point_event_features,
#     page_id=None,
#     clear_existing=False,
# ):
#     """
#     Draw top-band chainage labels and elbow leaders for visible point events
#     in the current map frame extent.

#     Parameters
#     ----------
#     layout : arcpy.mp.Layout
#         The layout where labels and leaders will be created.
#     map_frame : arcpy.mp.MapFrame
#         The map frame used to get the visible extent and page coordinates.
#     point_event_features : list[str]
#         List of point feature classes containing a 'Chainage' field.
#     page_id : int or None
#         Current map series page number, used for unique element naming.
#     clear_existing : bool
#         If True, delete existing leader elements for the current page first.
#     """

#     if not layout:
#         arcpy.AddWarning("No active layout found.")
#         return

#     extent = map_frame.camera.getExtent()

#     # ---------------------------------------------------------
#     # 3. Optionally clear previous labels/leaders
#     #    If page_id is given, only delete that page's elements.
#     # ---------------------------------------------------------
#     if clear_existing:
#         for element in layout.listElements():
#             try:
#                 if page_id is not None:
#                     if element.name.startswith(
#                         f"leader_line_{page_id}_"
#                     ) or element.name.startswith(f"leader_label_{page_id}_"):
#                         layout.deleteElement(element)
#                 else:
#                     if element.name.startswith(
#                         "leader_line_"
#                     ) or element.name.startswith("leader_label_"):
#                         layout.deleteElement(element)
#             except Exception:
#                 pass

#     # ---------------------------------------------------------
#     # 4. Collect visible points with Chainage
#     # ---------------------------------------------------------
#     visible_points = []

#     for point_fc in point_event_features:
#         if not point_fc or not arcpy.Exists(point_fc):
#             continue

#         fields = [f.name for f in arcpy.ListFields(point_fc)]
#         if "Chainage" not in fields:
#             continue

#         with arcpy.da.SearchCursor(point_fc, ["SHAPE@", "Chainage"]) as scursor:
#             for shape, chainage in scursor:
#                 if not shape or chainage in [None, ""]:
#                     continue

#                 pt = shape.centroid

#                 if (
#                     extent.XMin <= pt.X <= extent.XMax
#                     and extent.YMin <= pt.Y <= extent.YMax
#                 ):
#                     visible_points.append((pt.X, pt.Y, str(chainage)))

#     # ---------------------------------------------------------
#     # 5. If no points are visible, stop
#     # ---------------------------------------------------------
#     if not visible_points:
#         arcpy.AddMessage(
#             "No visible points found in current extent"
#             + (f" on page {page_id}." if page_id is not None else ".")
#         )
#         return

#     # ---------------------------------------------------------
#     # 6. Sort points from left to right
#     # ---------------------------------------------------------
#     visible_points.sort(key=lambda x: x[0])

#     # ---------------------------------------------------------
#     # 7. Define label band above map frame
#     # ---------------------------------------------------------
#     top_section_y = map_frame.elementPositionY + map_frame.elementHeight + 0.18
#     stagger_step = 0.10

#     # ---------------------------------------------------------
#     # 8. Open the current ArcGIS Pro project
#     # ---------------------------------------------------------
#     aprx = arcpy.mp.ArcGISProject("CURRENT")

#     created_leaders_count = 0

#     # ---------------------------------------------------------
#     # 9. Label placement settings
#     # ---------------------------------------------------------
#     placed_labels = []
#     min_spacing = 0.60
#     shift_pattern = [0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9, 1.2, -1.2]

#     left_limit = map_frame.elementPositionX
#     right_limit = map_frame.elementPositionX + map_frame.elementWidth

#     # ---------------------------------------------------------
#     # 10. Draw labels and elbow leaders
#     # ---------------------------------------------------------
#     for i, (map_x, map_y, label_text) in enumerate(visible_points):
#         try:
#             # Convert map coordinates to page coordinates
#             page_x = (
#                 map_frame.elementPositionX
#                 + ((map_x - extent.XMin) / (extent.XMax - extent.XMin))
#                 * map_frame.elementWidth
#             )

#             page_y = (
#                 map_frame.elementPositionY
#                 + ((map_y - extent.YMin) / (extent.YMax - extent.YMin))
#                 * map_frame.elementHeight
#             )
#         except Exception as e:
#             arcpy.AddWarning(
#                 f"Could not convert map coordinates to page coordinates: {e}"
#             )
#             continue

#         # Put labels into 3 staggered rows
#         label_y = top_section_y + (i % 3) * stagger_step

#         # Small base spread before collision checks
#         base_offset = (i % 5 - 2) * 0.15
#         initial_x = page_x + base_offset

#         label_x = initial_x

#         # Try a few positions to avoid overlap
#         for shift in shift_pattern:
#             trial_x = initial_x + shift
#             trial_x = max(left_limit, min(trial_x, right_limit))

#             collision = False

#             for prev_x, prev_y in placed_labels:
#                 too_close_x = abs(prev_x - trial_x) < min_spacing
#                 too_close_y = abs(prev_y - label_y) < 0.15

#                 if too_close_x and too_close_y:
#                     collision = True
#                     break

#             if not collision:
#                 label_x = trial_x
#                 break

#         # -----------------------------------------------------
#         # Create label text
#         # -----------------------------------------------------
#         try:
#             text = aprx.createTextElement(
#                 layout,
#                 arcpy.Point(label_x, label_y),
#                 "POINT",
#                 label_text,
#                 6,
#             )

#             text.name = (
#                 f"leader_label_{page_id}_{i}"
#                 if page_id is not None
#                 else f"leader_label_{i}"
#             )

#             text_cim = text.getDefinition("V3")
#             text_cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
#             text_cim.graphic.symbol.symbol.height = 6
#             text.setDefinition(text_cim)

#         except Exception as e:
#             arcpy.AddWarning(f"Could not create text element for {label_text}: {e}")
#             continue

#         # -----------------------------------------------------
#         # Create elbow leader
#         # -----------------------------------------------------
#         try:
#             elbow_y = label_y - 0.08

#             leader_geom = arcpy.Polyline(
#                 arcpy.Array(
#                     [
#                         arcpy.Point(page_x, page_y),  # start at point
#                         arcpy.Point(page_x, elbow_y),  # vertical up
#                         arcpy.Point(label_x, elbow_y),  # horizontal to label zone
#                     ]
#                 )
#             )

#             leader = aprx.createGraphicElement(
#                 layout,
#                 leader_geom,
#                 name=(
#                     f"leader_line_{page_id}_{i}"
#                     if page_id is not None
#                     else f"leader_line_{i}"
#                 ),
#             )

#             leader_cim = leader.getDefinition("V3")
#             leader_cim.graphic.symbol.symbol.symbolLayers[0].width = 0.5
#             leader.setDefinition(leader_cim)

#             placed_labels.append((label_x, label_y))
#             created_leaders_count += 1

#         except Exception as e:
#             arcpy.AddWarning(f"Could not create leader for {label_text}: {e}")

#     arcpy.AddMessage(
#         f"Leader labels drawn for {created_leaders_count} visible points"
#         + (f" on page {page_id}." if page_id is not None else ".")
#     )


# def apply_leaders_to_layout_map_series(
#     layout_name,
#     map_frame_name,
#     point_event_features,
# ):
#     """
#     Apply elbow leaders to a layout.
#     If map series is enabled, process each page.
#     If map series is not enabled, process the current layout once.

#     Parameters
#     ----------
#     layout_name : str
#         Name of the layout in the current ArcGIS Pro project.
#     map_frame_name : str
#         Name of the map frame in the layout.
#     point_event_features : list[str]
#         List of point feature classes containing a 'Chainage' field.
#     """

#     aprx = arcpy.mp.ArcGISProject("CURRENT")

#     # ---------------------------------------------------------
#     # 1. Get layout
#     # ---------------------------------------------------------
#     layouts = aprx.listLayouts(layout_name)
#     if not layouts:
#         raise ValueError(f"Layout '{layout_name}' not found.")

#     layout = layouts[0]

#     # ---------------------------------------------------------
#     # 2. Get map frame
#     # ---------------------------------------------------------
#     map_frames = layout.listElements("MAPFRAME_ELEMENT", map_frame_name)
#     if not map_frames:
#         raise ValueError(
#             f"Map frame '{map_frame_name}' not found in layout '{layout_name}'."
#         )

#     map_frame = map_frames[0]

#     # ---------------------------------------------------------
#     # 3. Check whether map series is enabled
#     # ---------------------------------------------------------
#     map_series = layout.mapSeries

#     if map_series and map_series.enabled:
#         arcpy.AddMessage(
#             f"Map series detected. Applying leaders to {map_series.pageCount} pages."
#         )

#         for page_num in range(1, map_series.pageCount + 1):
#             map_series.currentPageNumber = page_num

#             draw_stationing_leader_for_points(
#                 layout=layout,
#                 map_frame=map_frame,
#                 point_event_features=point_event_features,
#                 page_id=page_num,
#                 clear_existing=True,
#             )

#             arcpy.AddMessage(f"Finished page {page_num}.")

#     else:
#         arcpy.AddMessage("No enabled map series found. Applying leaders once.")

#         draw_stationing_leader_for_points(
#             layout=layout,
#             map_frame=map_frame,
#             point_event_features=point_event_features,
#             page_id=None,
#             clear_existing=True,
#         )


# # -----------------------------------------------------------------
# # EXAMPLE USAGE
# # Replace these values with your actual names/paths
# # -----------------------------------------------------------------
# if __name__ == "__main__":
#     layout_name = "Alignment Layout"
#     map_frame_name = "Main Map Frame"

#     point_event_features = [
#         r"C:\Capstone\Alignmentsheet\Alignmentsheet.gdb\Point_Intersections",
#         r"C:\Capstone\Alignmentsheet\Alignmentsheet.gdb\Station_Points",
#     ]

#     apply_leaders_to_layout_map_series(
#         layout_name=layout_name,
#         map_frame_name=map_frame_name,
#         point_event_features=point_event_features,
#     )


# import arcpy
# import os


# def draw_stationing_leader_for_points(
#     layout,
#     map_frame,
#     point_event_features,
#     page_id=None,
#     clear_existing=False,
# ):
#     """
#     Draw top-band chainage labels and elbow leaders for visible point events
#     in the current map frame extent.

#     Parameters
#     ----------
#     layout : arcpy.mp.Layout
#         The layout where labels and leaders will be created.
#     map_frame : arcpy.mp.MapFrame
#         The map frame used to get the visible extent and page coordinates.
#     point_event_features : list[str]
#         List of point feature classes containing a 'Chainage' field.
#     page_id : int or None
#         Current map series page number, used for unique element naming.
#     clear_existing : bool
#         If True, delete existing leader elements for the current page first.
#     """

#     # ---------------------------------------------------------
#     # 1. Safety check
#     # ---------------------------------------------------------
#     if not layout:
#         arcpy.AddWarning("No active layout found.")
#         return

#     # ---------------------------------------------------------
#     # 2. Get the current visible extent from the map frame
#     # ---------------------------------------------------------
#     extent = map_frame.camera.getExtent()

#     # ---------------------------------------------------------
#     # 3. Optionally clear previous labels/leaders
#     #    If page_id is given, only delete that page's elements.
#     # ---------------------------------------------------------
#     if clear_existing:
#         for element in layout.listElements():
#             try:
#                 if page_id is not None:
#                     if element.name.startswith(
#                         f"leader_line_{page_id}_"
#                     ) or element.name.startswith(f"leader_label_{page_id}_"):
#                         layout.deleteElement(element)
#                 else:
#                     if element.name.startswith(
#                         "leader_line_"
#                     ) or element.name.startswith("leader_label_"):
#                         layout.deleteElement(element)
#             except Exception:
#                 pass

#     # ---------------------------------------------------------
#     # 4. Collect visible points with Chainage
#     # ---------------------------------------------------------
#     visible_points = []

#     for point_fc in point_event_features:
#         if not point_fc or not arcpy.Exists(point_fc):
#             continue

#         fields = [f.name for f in arcpy.ListFields(point_fc)]
#         if "Chainage" not in fields:
#             continue

#         with arcpy.da.SearchCursor(point_fc, ["SHAPE@", "Chainage"]) as scursor:
#             for shape, chainage in scursor:
#                 if not shape or chainage in [None, ""]:
#                     continue

#                 pt = shape.centroid

#                 if (
#                     extent.XMin <= pt.X <= extent.XMax
#                     and extent.YMin <= pt.Y <= extent.YMax
#                 ):
#                     visible_points.append((pt.X, pt.Y, str(chainage)))

#     if not visible_points:
#         arcpy.AddMessage(
#             f"No visible points found in current extent"
#             + (f" on page {page_id}." if page_id is not None else ".")
#         )
#         return

#     # ---------------------------------------------------------
#     # 5. Sort left to right for predictable labeling
#     # ---------------------------------------------------------
#     visible_points.sort(key=lambda x: x[0])

#     # ---------------------------------------------------------
#     # 6. Top label band settings
#     # ---------------------------------------------------------
#     top_section_y = map_frame.elementPositionY + map_frame.elementHeight + 0.18
#     stagger_step = 0.10

#     # ---------------------------------------------------------
#     # 7. Get current ArcGIS Pro project
#     # ---------------------------------------------------------
#     aprx = arcpy.mp.ArcGISProject("CURRENT")

#     created_leaders_count = 0

#     # ---------------------------------------------------------
#     # 8. Label placement settings
#     # ---------------------------------------------------------
#     placed_labels = []
#     min_spacing = 0.60
#     shift_pattern = [0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9, 1.2, -1.2]

#     left_limit = map_frame.elementPositionX
#     right_limit = map_frame.elementPositionX + map_frame.elementWidth

#     # ---------------------------------------------------------
#     # 9. Draw labels and elbow leaders
#     # ---------------------------------------------------------
#     for i, (map_x, map_y, label_text) in enumerate(visible_points):
#         try:
#             # Convert map coordinates to page coordinates
#             page_x = (
#                 map_frame.elementPositionX
#                 + ((map_x - extent.XMin) / (extent.XMax - extent.XMin))
#                 * map_frame.elementWidth
#             )

#             page_y = (
#                 map_frame.elementPositionY
#                 + ((map_y - extent.YMin) / (extent.YMax - extent.YMin))
#                 * map_frame.elementHeight
#             )
#         except Exception as e:
#             arcpy.AddWarning(
#                 f"Could not convert map coordinates to page coordinates: {e}"
#             )
#             continue

#         # Put labels in 3 staggered rows
#         label_y = top_section_y + (i % 3) * stagger_step

#         # Give labels a small natural spread before collision checks
#         base_offset = (i % 5 - 2) * 0.15
#         initial_x = page_x + base_offset

#         # Find a collision-free x-position
#         label_x = initial_x

#         for shift in shift_pattern:
#             trial_x = initial_x + shift
#             trial_x = max(left_limit, min(trial_x, right_limit))

#             collision = False

#             for prev_x, prev_y in placed_labels:
#                 too_close_x = abs(prev_x - trial_x) < min_spacing
#                 too_close_y = abs(prev_y - label_y) < 0.15

#                 if too_close_x and too_close_y:
#                     collision = True
#                     break

#             if not collision:
#                 label_x = trial_x
#                 break

#         # -----------------------------------------------------
#         # Create text label
#         # -----------------------------------------------------
#         try:
#             text = aprx.createTextElement(
#                 layout,
#                 arcpy.Point(label_x, label_y),
#                 "POINT",
#                 label_text,
#                 6,
#             )

#             text.name = (
#                 f"leader_label_{page_id}_{i}"
#                 if page_id is not None
#                 else f"leader_label_{i}"
#             )

#             text_cim = text.getDefinition("V3")
#             text_cim.graphic.symbol.symbol.fontFamilyName = "Tahoma"
#             text_cim.graphic.symbol.symbol.height = 6
#             text.setDefinition(text_cim)

#         except Exception as e:
#             arcpy.AddWarning(f"Could not create text element for {label_text}: {e}")
#             continue

#         # -----------------------------------------------------
#         # Create elbow leader
#         # 3 points:
#         # 1. actual point
#         # 2. straight up to elbow level
#         # 3. across to under the label
#         # -----------------------------------------------------
#         try:
#             elbow_y = label_y - 0.08

#             leader_geom = arcpy.Polyline(
#                 arcpy.Array(
#                     [
#                         arcpy.Point(page_x, page_y),
#                         arcpy.Point(page_x, elbow_y),
#                         arcpy.Point(label_x, elbow_y),
#                     ]
#                 )
#             )

#             leader = aprx.createGraphicElement(
#                 layout,
#                 leader_geom,
#                 name=(
#                     f"leader_line_{page_id}_{i}"
#                     if page_id is not None
#                     else f"leader_line_{i}"
#                 ),
#             )

#             leader_cim = leader.getDefinition("V3")
#             leader_cim.graphic.symbol.symbol.symbolLayers[0].width = 0.5
#             leader.setDefinition(leader_cim)

#             placed_labels.append((label_x, label_y))
#             created_leaders_count += 1

#         except Exception as e:
#             arcpy.AddWarning(f"Could not create leader for {label_text}: {e}")

#     arcpy.AddMessage(
#         f"Leader labels drawn for {created_leaders_count} visible points"
#         + (f" on page {page_id}." if page_id is not None else ".")
#     )


# def export_layout_with_map_series_and_leaders(
#     layout_name,
#     map_frame_name,
#     point_event_features,
#     output_folder,
#     pdf_prefix="AlignmentSheet",
# ):
#     """
#     Export a layout page-by-page to PDF using map series, while drawing
#     elbow leaders for visible point events on each page.

#     Parameters
#     ----------
#     layout_name : str
#         Name of the layout in the current ArcGIS Pro project.
#     map_frame_name : str
#         Name of the map frame inside the layout.
#     point_event_features : list[str]
#         Point feature classes containing a 'Chainage' field.
#     output_folder : str
#         Folder where PDFs will be exported.
#     pdf_prefix : str
#         Prefix for exported PDF filenames.
#     """

#     aprx = arcpy.mp.ArcGISProject("CURRENT")

#     # ---------------------------------------------------------
#     # 1. Find the layout by name
#     # ---------------------------------------------------------
#     layouts = aprx.listLayouts(layout_name)
#     if not layouts:
#         raise ValueError(f"Layout '{layout_name}' not found.")

#     layout = layouts[0]

#     # ---------------------------------------------------------
#     # 2. Find the map frame by name
#     # ---------------------------------------------------------
#     map_frames = layout.listElements("MAPFRAME_ELEMENT", map_frame_name)
#     if not map_frames:
#         raise ValueError(
#             f"Map frame '{map_frame_name}' not found in layout '{layout_name}'."
#         )

#     map_frame = map_frames[0]

#     # ---------------------------------------------------------
#     # 3. Make sure output folder exists
#     # ---------------------------------------------------------
#     if not os.path.exists(output_folder):
#         os.makedirs(output_folder)

#     # ---------------------------------------------------------
#     # 4. Check map series
#     # ---------------------------------------------------------
#     map_series = layout.mapSeries

#     if map_series and map_series.enabled:
#         arcpy.AddMessage(
#             f"Map series detected. Exporting {map_series.pageCount} pages."
#         )

#         for page_num in range(1, map_series.pageCount + 1):
#             # Set the active page
#             map_series.currentPageNumber = page_num

#             # Redraw labels and elbow leaders for this page only
#             draw_stationing_leader_for_points(
#                 layout=layout,
#                 map_frame=map_frame,
#                 point_event_features=point_event_features,
#                 page_id=page_num,
#                 clear_existing=True,
#             )

#             # Build output PDF name
#             pdf_name = f"{pdf_prefix}_Page_{page_num}.pdf"
#             pdf_path = os.path.join(output_folder, pdf_name)

#             # Export current page to PDF
#             layout.exportToPDF(pdf_path)

#             arcpy.AddMessage(f"Exported page {page_num} to: {pdf_path}")

#     else:
#         arcpy.AddMessage("No enabled map series found. Exporting single layout.")

#         # Draw leaders once
#         draw_stationing_leader_for_points(
#             layout=layout,
#             map_frame=map_frame,
#             point_event_features=point_event_features,
#             page_id=None,
#             clear_existing=True,
#         )

#         # Export single PDF
#         pdf_name = f"{pdf_prefix}.pdf"
#         pdf_path = os.path.join(output_folder, pdf_name)
#         layout.exportToPDF(pdf_path)

#         arcpy.AddMessage(f"Exported layout to: {pdf_path}")


# # -----------------------------------------------------------------
# # EXAMPLE USAGE
# # Replace these names/paths with your actual project values
# # -----------------------------------------------------------------
# if __name__ == "__main__":
#     layout_name = "Alignment Layout"
#     map_frame_name = "Main Map Frame"

#     point_event_features = [
#         r"C:\Capstone\Alignmentsheet\Alignmentsheet.gdb\Point_Intersections",
#         r"C:\Capstone\Alignmentsheet\Alignmentsheet.gdb\Station_Points",
#     ]

#     output_folder = r"C:\Capstone\Alignmentsheet\Exports"

#     export_layout_with_map_series_and_leaders(
#         layout_name=layout_name,
#         map_frame_name=map_frame_name,
#         point_event_features=point_event_features,
#         output_folder=output_folder,
#         pdf_prefix="AlignmentSheet",
#     )





# 1) Update build_band_records()

# Replace your current function with this:

# import arcpy
# import os


# def get_base_feature_name(path_or_name):
#     name = os.path.splitext(os.path.basename(str(path_or_name)))[0]

#     suffixes = [
#         "_intersect_event_single",
#         "_intersect_event",
#         "_overlap_event",
#         "_intersect",
#         "_overlap",
#         "_event_single",
#         "_event",
#         "_single",
#     ]

#     for suffix in suffixes:
#         if name.lower().endswith(suffix.lower()):
#             name = name[: -len(suffix)]
#             break

#     return name


# def build_band_records(point_event_tables, line_event_tables):
#     records = []

#     for table in point_event_tables:
#         source_table_name = os.path.basename(table)
#         source_name = get_base_feature_name(source_table_name)

#         with arcpy.da.SearchCursor(table, ["MEAS", "Chainage"]) as cursor:
#             for meas, chainage in cursor:
#                 records.append(
#                     {
#                         "type": "POINT",
#                         "meas": meas,
#                         "chainage": chainage,
#                         "source_table": source_table_name,
#                         "source_name": source_name,
#                     }
#                 )

#     for table in line_event_tables:
#         source_table_name = os.path.basename(table)
#         source_name = get_base_feature_name(source_table_name)

#         with arcpy.da.SearchCursor(
#             table, ["FMEAS", "TMEAS", "ChainageRange"]
#         ) as cursor:
#             for fmeas, tmeas, chainage_range in cursor:
#                 start = min(fmeas, tmeas)
#                 end = max(fmeas, tmeas)

#                 records.append(
#                     {
#                         "type": "LINE",
#                         "fmeas": start,
#                         "tmeas": end,
#                         "range": chainage_range,
#                         "source_table": source_table_name,
#                         "source_name": source_name,
#                     }
#                 )

#     return records

# That changes the records from names like Base_Waterbody_Polygon_overlap_event in your logs to a clean Base_Waterbody_Polygon field for display.

# 2) Replace draw_point_band_labels()

# Use this version so you can choose whether the point band shows source name, chainage, or both:

# def draw_point_band_labels(
#     layout,
#     point_records,
#     label_y,
#     text_height=0.12,
#     font_name="Tahoma",
#     prefix="BandPointLabel",
#     label_mode="source_name",  # "source_name", "chainage", or "both"
# ):
#     """
#     Draw point labels in the layout using precomputed x positions.
#     """

#     created_elements = []
#     aprx = arcpy.mp.ArcGISProject("CURRENT")
#     text_size_points = (
#         text_height * 72 if text_height and text_height < 1 else text_height
#     )

#     for i, rec in enumerate(point_records, start=1):
#         if rec.get("type") != "POINT":
#             continue

#         x = rec.get("x")
#         source_name = rec.get("source_name", "")
#         chainage = rec.get("chainage", "")

#         if label_mode == "source_name":
#             label_text = source_name
#         elif label_mode == "both":
#             if source_name and chainage:
#                 label_text = f"{source_name} ({chainage})"
#             else:
#                 label_text = source_name or chainage
#         else:
#             label_text = chainage

#         if x is None or not label_text:
#             continue

#         safe_text = (
#             label_text.replace("+", "_")
#             .replace(" ", "_")
#             .replace("(", "")
#             .replace(")", "")
#             .replace("-", "_")
#         )
#         element_name = f"{prefix}_{i}_{safe_text}"
#         point_geom = arcpy.Point(x, label_y)

#         try:
#             txt = aprx.createTextElement(
#                 layout,
#                 point_geom,
#                 "POINT",
#                 label_text,
#                 text_size_points,
#             )
#             txt.name = element_name

#             cim = txt.getDefinition("V3")
#             cim.anchor = "CenterPoint"
#             cim.graphic.symbol.symbol.fontFamilyName = font_name
#             cim.graphic.symbol.symbol.height = text_size_points
#             txt.setDefinition(cim)

#         except Exception as e:
#             arcpy.AddWarning(
#                 f"Could not create band point label '{label_text}': {e}"
#             )
#             continue

#         created_elements.append(txt)

#     return created_elements
# 3) Add a new draw_line_band_labels() right below it

# This one draws the line-feature name centered between x1 and x2:

# def draw_line_band_labels(
#     layout,
#     line_records,
#     label_y,
#     text_height=0.12,
#     font_name="Tahoma",
#     prefix="BandLineLabel",
#     label_mode="source_name",  # "source_name", "range", or "both"
# ):
#     """
#     Draw line labels in the layout using the midpoint of x1 and x2.
#     """

#     created_elements = []
#     aprx = arcpy.mp.ArcGISProject("CURRENT")
#     text_size_points = (
#         text_height * 72 if text_height and text_height < 1 else text_height
#     )

#     for i, rec in enumerate(line_records, start=1):
#         if rec.get("type") != "LINE":
#             continue

#         x1 = rec.get("x1")
#         x2 = rec.get("x2")
#         source_name = rec.get("source_name", "")
#         range_text = rec.get("range", "")

#         if label_mode == "source_name":
#             label_text = source_name
#         elif label_mode == "both":
#             if source_name and range_text:
#                 label_text = f"{source_name} ({range_text})"
#             else:
#                 label_text = source_name or range_text
#         else:
#             label_text = range_text

#         if x1 is None or x2 is None or not label_text:
#             continue

#         x_mid = (x1 + x2) / 2.0

#         safe_text = (
#             label_text.replace("+", "_")
#             .replace(" ", "_")
#             .replace("(", "")
#             .replace(")", "")
#             .replace("-", "_")
#         )
#         element_name = f"{prefix}_{i}_{safe_text}"
#         point_geom = arcpy.Point(x_mid, label_y)

#         try:
#             txt = aprx.createTextElement(
#                 layout,
#                 point_geom,
#                 "POINT",
#                 label_text,
#                 text_size_points,
#             )
#             txt.name = element_name

#             cim = txt.getDefinition("V3")
#             cim.anchor = "CenterPoint"
#             cim.graphic.symbol.symbol.fontFamilyName = font_name
#             cim.graphic.symbol.symbol.height = text_size_points
#             txt.setDefinition(cim)

#         except Exception as e:
#             arcpy.AddWarning(
#                 f"Could not create band line label '{label_text}': {e}"
#             )
#             continue

#         created_elements.append(txt)

#     return created_elements
# 4) Add a matching clear function

# Put this below clear_point_band_labels(), since your current file only clears point labels.

# def clear_line_band_labels(layout, prefix="BandLineLabel"):
#     """
#     Deletes previously created line band labels from the layout.
#     """
#     if not layout:
#         raise ValueError("Layout is required.")

#     to_delete = []
#     for elm in layout.listElements("TEXT_ELEMENT"):
#         if elm.name.startswith(prefix):
#             to_delete.append(elm)

#     for elm in to_delete:
#         elm.delete()

#     return len(to_delete)
# 5) How to call both

# After prepare_layout_band_records() returns row_ready_records, split them into point and line lists. Your preparation pipeline already adds x/x1/x2 and row y values, so this is the right stage to draw from.

# row_ready_records = prep["row_ready_records"]

# point_records = [r for r in row_ready_records if r["type"] == "POINT"]
# line_records = [r for r in row_ready_records if r["type"] == "LINE"]

# deleted_points = clear_point_band_labels(layout)
# deleted_lines = clear_line_band_labels(layout)

# arcpy.AddMessage(f"Deleted {deleted_points} old point band labels.")
# arcpy.AddMessage(f"Deleted {deleted_lines} old line band labels.")

# created_point_labels = draw_point_band_labels(
#     layout,
#     point_records,
#     label_y=point_row_y,
#     label_mode="source_name",
# )

# created_line_labels = draw_line_band_labels(
#     layout,
#     line_records,
#     label_y=line_row_y,
#     label_mode="source_name",
# )

# arcpy.AddMessage(f"Created {len(created_point_labels)} point band labels.")
# arcpy.AddMessage(f"Created {len(created_line_labels)} line band labels.")
# 6) Best mode to use right now

# Use:

# label_mode="source_name"