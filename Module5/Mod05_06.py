#working with zonal functions

#imports
import arcpy
from arcpy.sa import *
from arcpy import env

#set workspace and overwrite
env.overwriteOutput=True
env.workspace=r"C:\GEOS456\Mod05_Activity04_Data\ZonalStats.gdb"
workspace=env.workspace

#check in
arcpy.CheckOutExtension("Spatial")

#Messages
def messages():
    print(arcpy.GetMessage(0))
    count=(arcpy.GetMessageCount())
    print(arcpy.GetMessage(count -1))
    print("")

rastersList=arcpy.ListRasters()
for rasters in rastersList:
    desc=arcpy.Describe(rasters)
    print(rasters)
    print("Format: ", desc.format)
    print("Cell Size: ", desc.meanCellWidth)
    print("Spatial Reference: ", desc.SpatialReference.name)
    print("")
messages()

#print feature classes in the workspace
FCList=arcpy.ListFeatureClasses()
for fc in FCList:
    print(fc)
    print("")
messages()

#Next Step we will use Zonal tolset to generate a new raster with the zonal statistics as Table tool
#Table to show mean, elevation for each land cover species

#define parameters for zonal stats as table
InZoneData= "Landcover"
ZoneField= "Species_gr"
InValueRaster ="DEM"
OutTable= "Landcvr_Mean_elv"

#create a table using zonal statistics as table from from the zonal toolset
#set the stats type to MEAN
print("Creating Zone Stats Table...")
outzonaltable=ZonalStatisticsAsTable(InZoneData, ZoneField, InValueRaster, OutTable, "", "MEAN")
messages()

fieldsList=arcpy.ListFields(OutTable)
print("Printing fields...")
for fields in fieldsList:
    print(fields.name)

messages()
#The table has been generated. Next, we will create a list of the fields and access the values
#from the list.

print("Accessing fields values...")
with arcpy.da.SearchCursor(OutTable, ["Species_gr", "MEAN"]) as Scursoe:
    for row in Scursoe:
        print("Species: ", row[0], " has ", "Mean Elevation of: ", row[1])
messages() 


#Using Tabulate Area
#the tabulate area tool returns tabular information abut the area of a raster dataset. It is the best method to generate areas of a raster

#specify parameters
in_zone_data="Fire_Poly"
ZoneField="FireNum"
in_class_data="Landcover"
class_field="Species_gr"
out_table="Fire_Area"

#create a table using tabulate area toolprint(')
print("Calculating area...")
OutAreaTable=TabulateArea(in_zone_data, ZoneField, in_class_data, class_field, out_table)
messages()

#use search cursor to retrieve values from fields
with arcpy.da.SearchCursor(out_table, ["FIRENUM", "PONDEROSA_PINE", "RED_FIR"]) as Scursor:
    for row in Scursor:
        print("Fire Number: ", row[0], "|", "Ponderosa Pine Area (sq/m): ", row[1], "|", "Mixed Conifer Area (sq/m): ", row[2])
messages()