#-------------------------------------------------------------------------------
# Name:     Intro to arcpy
# Purpose:  Introduction to arcpy
#
# Author:      954522
#
# Created:     16/01/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

###import the arcpy module and set the workspace environment
##import arcpy
##workspace=arcpy.env.workspace
##folder1=workspace
##folder2=workspace
##
##folder1=r"C:\GEOS456\Module2\Data.gdb"
##
##
###set the overwrite output to equal to true=
##arcpy.env.overwriteOutput=True
##
###generate a list of all the feature classes in workspace
##fc_list = arcpy.ListFeatureClasses()
##fc_list=arcpy.ListRasters()
##
###iterate through a workspace to print a list of all the feature classes
##for fc in fc_list:
##    print(fc)


import arcpy
arcpy.env.workspace=r"C:\GEOS456\Module2\Data.gdb"

#set the overwrite output to equal true
arcpy.env.overwriteOutput=True

#DEFINE TOOL MESSAGES FOR USE THROUGHOUT THE ENTIRE SCRIPT
def messages():
    print(arcpy.GetMessage(0)) #print only the FIRST geoprocessing message
    count = arcpy.GetMessageCount()#counts ALL geoprocessing messages for any tool
    print(arcpy.GetMessage(count-1))#indexes the LAST message from a tool
    print()

#generate a list of all the feature classes in the workspace
fc_list = arcpy.ListFeatureClasses("C*", "Polygon")

#iterate through the workspace to print a list of all the feature classes
for fc in fc_list:
    print(fc)
    print("Buffering: ", fc)
    arcpy.Buffer_analysis(fc, fc + "_buffer", "50 Meters")
    messages()

##    #Retrieve tool messages using the GetMessages() function
##    #The GetMessages() function is an arcpy function to access geoprocessing tool messages
##    #returns a string of all the messages for any tool function
####    print(arcpy.GetMessages())
####    print()
##
##    #index or isolate certain messages
##    #use the GetMessage() function to index geoprocessing message from  a tool
##    print(arcpy.GetMessage(0))
##
##    #use the GetMessageCount() function to count ALL geoprocessing messages regardless of the tool being run
##    count = arcpy.GeMessageCount()
##
##    #Index the count variable to extract the LAST message from the tool
##    print(arcpy.GetMessage(count-1))

#generate another list of all the features in the workspace including all the buffered ones
NewFCList=arcpy.ListFeatureClasses("*_buffer")

for newFC in NewFCList:
    print(newFC)
    print("Deleting all the buffers that was created")
    arcpy.Delete_management(newFC)
    messages()

#Create one more list of features to show remaining feature classes in the workspace
anotherList=arcpy.ListFeatureClasses()
print("\nHere are the feature classes in the workspace: ")
for allfeatures in anotherList:
    print(f" - {allfeatures}")
    messages()

#generate a List of rasters in the workspace
##rasterlist=arcpy.ListRasters()

#iterate through the workspace and print all the rasters to the interpreter
##for raster in rasterlist:
##    print(raster)

#lets buffer the city boundaries feature class
#you can define variable for the tool parameter values
##inBuffer="CityBoundaries"
##outBuffer="City_Buffer"
##bufferDistance="100 Meters"
##
##arcpy.Buffer_analysis(inBuffer, outBuffer, bufferDistance)
##print("Buffer Complete!")

###generate a list of all the feature classes in the workspace
##fc_list = arcpy.ListFeatureClasses()
##
###iterate through the workspace to print a list of all the feature classes
##for fc in fc_list:
##    print(fc)


