# #IMPORTS
# import arcpy
# import os
# from arcpy.sa import *

# # Set workspace
# arcpy.env.overwriteOutput=True
# arcpy.env.workspace = r"C:\GEOS456\FinalProject"
# workspace=arcpy.env.workspace

# #name and path of gdb
# gdb_name="KananaskisWildlife"
# gdb_path=os.path.join(workspace, gdb_name + ".gdb")

# #check and delete if KananaskisWildlife gdb exist
# if arcpy.Exists(gdb_path):
#     arcpy.management.Delete(gdb_path)
#     print(f"Deleted existing geodatabase: {gdb_path}")

# #creating gdb
# print(f"Creating {gdb_name}...")
# arcpy.management.CreateFileGDB(workspace, gdb_name)
# print(f"{gdb_name} created successfully.\n")
# print(arcpy.GetMessages())

# # Set up spatial reference
# coordinates=arcpy.SpatialReference("NAD 1983 UTM ZONE 11N")

# # Set cell size
# arcpy.env.cellSize = 25

# # listing features in folders
# arcpy.env.workspace=r"C:\GEOS456\FinalProject"
# workspace=arcpy.env.workspace

# def listfeatures(workspace):
#     shp_data=[]
#     for dirpath, dirnames, filenames in arcpy.da.Walk(workspace, datatype="FeatureClass"):
#         for filename in filenames:
#             shp_data.append(os.path.join(dirpath, filename))
#     return shp_data

# shp=listfeatures(workspace)
# for index, element in enumerate(shp):
#     print(index, ":", os.path.basename(element))
# print()

# #Clipping functions
# def clip_vector(input_fc, out_name, clip_feature, out_gdb, coordinates):
#     try:
#         output_fc=os.path.join(out_gdb, out_name)
#         temporary_projected=os.path.join(out_gdb, out_name + "_temporary")

#         print(f"Projecting {out_name}....")
#         arcpy.management.Project(input_fc, temporary_projected, coordinates)

#         print(f"  Clipping {out_name}...")
#         arcpy.analysis.Clip(temporary_projected, clip_feature, output_fc)
#         print(arcpy.GetMessages())

#         arcpy.management.Delete(temporary_projected)

#         return True
#     except Exception as e:
#         print(f"✗ Error: {str(e)}\n")
#         return False

# #function to clip raster to boundary
# def clip_raster(input_raster, out_name, clip_feature, out_gdb):
#     try:
#         output_raster = os.path.join(out_gdb, out_name)

#         print(f"  Clipping {out_name}...")
#         clipped = arcpy.sa.ExtractByMask(input_raster, clip_feature)
#         clipped.save(output_raster)
#         print(arcpy.GetMessages())

#         return True
#     except Exception as e:
#         print(f"  ✗ Error: {str(e)}\n")
#         return False


# #Clipping data
# for fc in shp:
#     base_name=os.path.splitext(os.path.basename(fc))[0]

#     boundary=os.path.join(workspace, "Kananaskis", "Kcountry_bound.shp")

#     projected=arcpy.Project_management(fc, fc + "_projected", coordinates)

#     #copying boundary to gdb
#     print("Copying park boundary to gdb...")
#     boundary_gdb=os.path.join(gdb_path, "Country_boundary")

#     #project


#     arcpy.analysis.Clip(projected, "KCountry_Bound.shp", fc + "_clip")

# # - Roads

# # - Trails  

# # - Hydrology

# # - Habitat locations

# # - ESA

# # - DEM (Digital Elevation Model)

# # - Landcover

# # - Townships

# # - NTS map sheets

# # Save clipped versions to the geodatabase



# #Terrain Cost Surface

# # Calculate terrain ruggedness from DEM

# #    (probably using Slope tool or similar)

# # Rescale terrain ruggedness (0-10 scale)

# #    - Higher values = more rugged = less desirable



# #Land Cover Cost Surface

# # 1. Reclassify landcover using the provided table:

# #    - Forests (Coniferous/Broadleaf/Mixed) = 1 (best)

# #    - Grassland = 2

# #    - Shrubland = 3

# #    - Exposed Land = 6

# #    - Rock/Rubble = 7

# #    - Snow/Ice = 8

# #    - Agriculture = 9

# #    - Water = 10 (worst)

# #    - Developed = 10 (worst)



# # Proximity Cost Surfaces

# # Distance Accumulation for Hydrology

# #    Rescale (0-10): closer to water = better (lower cost)



# # Distance Accumulation for Trails  

# #     Rescale (0-10): farther from trails = better (lower cost)



# # Distance Accumulation for Roads

# #    Rescale (0-10): farther from roads = better (lower cost)



# #Combine Cost Surfaces

# # Use Weighted Sum tool to combine all cost surfaces:

# # - Terrain ruggedness (rescaled)

# # - Landcover (reclassified)

# # - Hydrology proximity (rescaled)

# # - Trails proximity (rescaled)  

# # - Roads proximity (rescaled)



# # All weights = 1 (equal importance)



# # Result = Single combined cost raster



# # Calculate Optimal Routes

# #  Convert habitat polygons to points (centroids)

# #  Use Cost Distance or Cost Path analysis

# #  Calculate least-cost paths between all habitat patches

# #  Ensure routes stay within park boundary

# #  Convert raster routes to vector (polylines)



# #Calculate Statistics

# # Average elevation of Kananaskis Country

# #    - Use Zonal Statistics on DEM

   

# # Area of each landcover type within park

# #    - Use Tabulate Area or Zonal Statistics as Table

   

# # Total length of optimal routes

# #    - Use geometry token on route polylines

   

# # Identify NTS map sheets covering park

# #    - Spatial selection/intersection

   

# # Identify Townships (TWP-RGE-MER) covering park

# #    - Spatial selection/intersection



# # Store all tables in geodatabase

# # Print results to interpreter



# #Map Production

# # Open existing .aprx template

# # Add layers using arcpy.mp:

# #    - Park Boundary (polygon)

# #    - Habitat locations (points)

# #    - Proposed optimal routes (polylines)

   

# # Set proper layer order (points → lines → polygons)

# # Adjust legend to fit template

# # Export to PDF: GEOS456_FP_LastName_FirstName.pdf


import arcpy

# Landcover fields
print("=" * 50)
print("LANDCOVER FIELDS:")
print("=" * 50)
landcover = r"C:\GEOS456\FinalProject\Landcover\AB_Landcover.shp"
for field in arcpy.ListFields(landcover):
    print(f"{field.name:20s} - {field.type}")

# NTS fields
print("\n" + "=" * 50)
print("NTS SHEETS FIELDS:")
print("=" * 50)
nts = r"C:\GEOS456\FinalProject\NTS\NTS50.shp"
for field in arcpy.ListFields(nts):
    print(f"{field.name:20s} - {field.type}")

# Township fields
print("\n" + "=" * 50)
print("TOWNSHIP FIELDS:")
print("=" * 50)
townships = r"C:\GEOS456\FinalProject\ATS\AB_Township.shp"
for field in arcpy.ListFields(townships):
    print(f"{field.name:20s} - {field.type}")