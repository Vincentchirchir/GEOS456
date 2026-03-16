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

# Create slope raster from DEM
dem = arcpy.Raster("dem")
dem_slope = Slope(dem)
dem_slope.save("Slope_DEM")
messages()

# Elevation: 1,000 metres to 1,550 metres
dem_criteria = (dem >= 1000) & (dem <= 1500)
dem_criteria.save("DEM_Criteria")
messages()

# Slope: <= 18 degrees
slope_criteria = dem_slope <= 18
slope_criteria.save("Slope_Criteria")
messages()

# Geology Type: Madison Limestone
geology = arcpy.Raster("geolgrid")
geology_criteria = geology == 7
geology_criteria.save("Geology_Madison_Limestone")
messages()

#combine all the rasters
