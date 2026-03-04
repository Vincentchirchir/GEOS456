#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      954522
#
# Created:     30/01/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

#import arcpy and set the workspace environment
import arcpy
from arcgis.gis import GIS
import IPython.display

#allow for overwriting outputs
arcpy.env.workspace=r"C:\GEOS456\Module2\Data.gdb"

#define geoprocessing messages for the FIRST and LAST messages
def messages():
    print(arcpy.GetMessage(0)) #print only the FIRST geoprocessing message
    count = arcpy.GetMessageCount()#counts ALL geoprocessing messages for any tool
    print(arcpy.GetMessage(count-1))#indexes the LAST message from a tool
    print()

#create list of ffeature classes stored in the workspace
fclist=arcpy.ListFeatureClasses()

#iterate through the workspace and print all feature classes to the interpreter
##for dirnames,dirpath, filenames in arcpy.da.Walk(fclist):
##    for fc in filenames:
##        print("Feature class name: ", fc)
##        fcDesc=arcpy.Describe(fc)
##        print("Geometry: ", fcDesc.shapeType)
##        print("Spatial Reference", fcDesc.spatialReference.name)
##        print("Geographic or projected:", fcDesc.spatialReference.type)
##      print("Units: ", fcDesc.)

for fc in fclist:
    print("Feature class name: ", fc)
    fcDesc=arcpy.Describe(fc)
    print("Geometry: ", fcDesc.shapeType)
    print("Spatial Reference: ", fcDesc.spatialReference.name)
    print("Geographic or projected:", fcDesc.spatialReference.type)
    if fcDesc.spatialReference.type=="Geographic":
        print("Geographic Units: ", fcDesc.spatialReference.angularUnitName)
    else:
        print("Projected Units: ", fcDesc.spatialReference.linearUnitName)
    print("")

##    #process features that have a polygon geometry
##    if fcDesc.shapetype=="Polygon":
##        arcpy.Buffer_analysis(fc, fc + "_Buffer", "100 Meters")
##        messages()

#describe certain properties of the listed feature classes
#geometry
#spatial reference
#geographic or projected
#units of the feature

#generate a list of all rasters in a workspace and print some properties
rasterList=arcpy.ListRasters()

for raster in rasterList:
    print(raster)
    rasterDesc=arcpy.Describe(raster)
    print("cells size: ", rasterDesc.meancellHeight)
    print("Spatial Reference Name: ", rasterDesc.spatialReference.name)
    print("Spatial Reference Name: ", rasterDesc.spatialReference.type)
