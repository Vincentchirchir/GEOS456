import arcpy

# setting up workspace
arcpy.env.overwriteOutput = True
arcpy.env.workspace = (
    r"C:\GIS SCRIPTS\GEOS456\Assignments\Assign03\Spatial_Decisions.gdb"
)

def messages():
    print(arcpy.GetMessage(0)) #print only the FIRST geoprocessing message
    count = arcpy.GetMessageCount()#counts ALL geoprocessing messages for any tool
    print(arcpy.GetMessage(count-1))#indexes the LAST message from a tool
    print()

# Check out extension
arcpy.CheckOutExtension("Spatial")

##Describe the following dem raster dataset properties:
##a. Data format
##b. Cell size
##c. Coordinate system
rastersList = arcpy.ListRasters()
for rasters in rastersList:
    desc = arcpy.Describe(rasters)
    print(f" -{rasters}".title())
    print("Data Format: ", desc.format)
    print("Cell Size: ", desc.MeanCellHeight)
    print("Coordinate System: ", desc.spatialReference.name)
    print("")

##Use the dem and geolgrid rasters to assign the following criteria:
##a. Elevation: 1,000 metres to 1,550 metres
##b. Slope: <= 18 degrees
##c. Geology Type: Madison Limestone
# dem = arcpy.Raster("dem")
# dem_slope = Slope(dem)
# dem_slope.save("Slope_DEM")
# messages()
