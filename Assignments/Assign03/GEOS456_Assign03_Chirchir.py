import arcpy
from arcpy.sa import *

# setting up workspace
arcpy.env.overwriteOutput = True
# arcpy.env.workspace = (
#     r"C:\GIS SCRIPTS\GEOS456\Assignments\Assign03\Spatial_Decisions.gdb"
# )
arcpy.env.workspace = r"C:\GEOS456\Assign03\Spatial_Decisions.gdb"
workspace = arcpy.env.workspace


def messages():
    print(arcpy.GetMessage(0))
    count = arcpy.GetMessageCount()
    print(arcpy.GetMessage(count - 1))
    print()


# Check out extension
arcpy.CheckOutExtension("Spatial")

# Describe raster dataset properties
rastersList = arcpy.ListRasters()
for raster in rastersList:
    desc = arcpy.Describe(raster)
    print(f" -{raster}".title())
    print("Data Format: ", desc.format)
    print("Cell Size: ", desc.MeanCellHeight)
    print("Coordinate System: ", desc.spatialReference.name)
    print("")

# Create slope from dem
dem = arcpy.Raster("dem")
dem_slope = Slope(dem, output_measurement="DEGREE", z_factor=1)
dem_slope.save("Slope_DEM")
print("Created slope raster: Slope_DEM")
messages()

# Elevation Criteria
dem_criteria = (dem >= 1000) & (dem <= 1500)
dem_criteria.save("DEM_Criteria")
print("Created DEM criteria raster: DEM_Criteria")
messages()

# Slope Criteria
slope_criteria = dem_slope <= 18
slope_criteria.save("Slope_Criteria")
print("Created slope criteria raster: Slope_Criteria")
messages()

# Geology criteria
geology = arcpy.Raster("geolgrid")
geology_criteria = geology == 7
geology_criteria.save("Geology_Madison_Limestone")
print("Created geology criteria raster: Geology_Madison_Limestone")
messages()

# Combine
final_raster = dem_criteria * slope_criteria * geology_criteria
final_raster.save("COMBINED_RASTER")
print("Created final raster: COMBINED_RASTER")
messages()

# Count number of cells
with arcpy.da.SearchCursor("COMBINED_RASTER", ["Value", "Count"]) as rows:
    number_cells = 0
    for values, counts in rows:
        if values == 1:
            number_cells += counts

print(f"Number of cells (Value =1): {number_cells}")
print("")

# Area
area = TabulateArea(
    "COMBINED_RASTER", "Value", "COMBINED_RASTER", "Value", "AREA_TABLE"
)
with arcpy.da.SearchCursor("AREA_TABLE", ["VALUE", "VALUE_1"]) as Scursor:
    for values, values_1 in Scursor:
        if values == 1:
            print(f"Area in square metres: {values_1}")

# Average elevation
average = ZonalStatisticsAsTable(
    "COMBINED_RASTER", "Value", "COMBINED_RASTER", "ELEVATION_RASTER", "#", "MEAN"
)
print("Created average elevation table..")

with arcpy.da.SearchCursor("ELAVATION_RASTER", ["Value", "MEAN"]) as cursor:
    for val, ave in cursor:
        if val == 1:
            print(f"Average Elevation is: {ave}")

# incorporate wshd
features = arcpy.ListFeatureClasses("wshds2c")
for feature in features:
    print(feature)
    fields = [f.name for f in arcpy.ListFields(feature)]
    if "WSHD2SC_ID" in fields:
        delim = arcpy.AddFieldDelimiters(feature, fields)
        new_selectiom=arcpy.SelectLayerByAttribute_management(feature, "NEW_SELECTION", delim + "= '291', '313', '525' ")
        average_mean=ZonalStatisticsAsTable("COMBINED_RASTER", )