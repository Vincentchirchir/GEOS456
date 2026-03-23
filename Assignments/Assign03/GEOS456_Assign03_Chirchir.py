# ---------------------------------------------------------------------------------------
# Name:        Assignment 3
# Purpose:      The purpose of this assignment is to apply grid statistics to analyze raster datasets using high-level/
# programming (HLP) language through geographic information system (GIS) extensions.
#
# Author:      Chirchir Vincent
#
# Created:     20/03/2026
# Copyright:   (c) vincent 2026
# Licence:     <your licence>
# ---------------------------------------------------------------------------------------

import arcpy
from arcpy.sa import *

# setting environment
arcpy.env.overwriteOutput = True
arcpy.env.workspace = r"C:\GEOS456\Assign03\Spatial_Decisions.gdb"
workspace = arcpy.env.workspace


# messages
def messages():
    count = arcpy.GetMessageCount()
    if count > 0:
        print(arcpy.GetMessage(0))
        if count > 1:
            print(arcpy.GetMessage(count - 1))
    print()


# Check out Spatial Analyst
arcpy.CheckOutExtension("Spatial")

# 1. Describe DEM raster
dem = Raster("dem")
desc = arcpy.Describe(dem)

print("")
print("  DEM Raster Properties")
print("Data Format:", desc.format)
print("Cell Size:", desc.meanCellHeight)
print("Coordinate System:", desc.spatialReference.name)
print()

# 2. Create slope raster
dem_slope = Slope(dem, output_measurement="DEGREE", z_factor=1)
dem_slope.save("Slope_DEM")
print("Created slope: Slope_DEM")
messages()

# 3. Apply criteria

# Elevation: 1000 to 1550
dem_criteria = (dem >= 1000) & (dem <= 1550)
dem_criteria.save("DEM_Criteria")
print("Created DEM criteria: DEM_Criteria")
messages()

# Slope: <= 18
slope_criteria = dem_slope <= 18
slope_criteria.save("Slope_Criteria")
print("Created slope criteria: Slope_Criteria")
messages()

# Geology: Madison Limestone
geology = Raster("geolgrid")
geology_criteria = geology == 7
geology_criteria.save("Geology_Madison_Limestone")
print("Created geology criteria: Geology_Madison_Limestone")
messages()

# 4. Combine criteria

final_raster = dem_criteria * slope_criteria * geology_criteria
final_raster.save("COMBINED_RASTER")
print("Created final raster: COMBINED_RASTER")
messages()


# 5. Number of cells meeting criteria
number_cells = 0
with arcpy.da.SearchCursor("COMBINED_RASTER", ["Value", "Count"]) as rows:
    for value, count in rows:
        if value == 1:
            number_cells = count

print(f"Number of cells meeting criteria: {number_cells}")
print()

# 6. Area in square metres
TabulateArea(
    in_zone_data="COMBINED_RASTER",
    zone_field="Value",
    in_class_data="COMBINED_RASTER",
    class_field="Value",
    out_table="AREA_TABLE",
)
with arcpy.da.SearchCursor("AREA_TABLE", ["VALUE", "VALUE_1"]) as cursor:
    for value, values in cursor:
        if value == 1:
            print(f"Area in square metres: {values}")

# 7. Average elevation of selected pixels
ZonalStatisticsAsTable(
    "COMBINED_RASTER", "Value", dem, "ELEVATION_TABLE", "DATA", "MEAN"
)
print("Created average elevation table: ELEVATION_TABLE")
messages()

with arcpy.da.SearchCursor("ELEVATION_TABLE", ["Value", "MEAN"]) as cursor:
    for value, mean_val in cursor:
        if value == 1:
            print(f"Average elevation: {mean_val}")
print()

# 8. Mean slope for selected watersheds
watersheds = "wshds2c"
watershed_layer = arcpy.MakeFeatureLayer_management(watersheds, "watersheds_layer")
field_delim = arcpy.AddFieldDelimiters(watersheds, "WSHDS2C_ID")
values = f"{field_delim} IN (291, 313, 525)"
arcpy.SelectLayerByAttribute_management(watershed_layer, "NEW_SELECTION", values)
print("Selected watersheds 291, 313, and 525")
messages()

ZonalStatisticsAsTable(
    "watersheds_layer", "WSHDS2C_ID", "Slope_DEM", "AVERAGE_MEAN_SLOPE", "DATA", "MEAN"
)
print("Created watershed slope table: AVERAGE_MEAN_SLOPE")
messages()

with arcpy.da.SearchCursor("AVERAGE_MEAN_SLOPE", ["WSHDS2C_ID", "MEAN"]) as cursor:
    for wshd_id, mean_slope in cursor:
        print(f"Watershed {wshd_id} average slope: {mean_slope}")
print("")

# Check in extension
arcpy.CheckInExtension("Spatial")
