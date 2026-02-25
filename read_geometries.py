#-------------------------------------------------------------------------------
# Name:        module2
# Purpose:
#
# Author:      954522
#
# Created:     23/02/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

#Read geometries

import arcpy
arcpy.env.workspace=r"C:\GEOS456\Module2\Data.gdb"
arcpy.env.overwriteOutput=True

#define a feature  class to extract the geometries from
##fc="Crimes2009"
##fc="BexarCountyBoundaries"

###extract the XY of the input feature class using the SHAPE@XY token
##scursor=arcpy.da.SearchCursor(fc, ["SHAPE@XY", "SHAPE@AREA"])
##
###Iterate through the feature and print all the XY to the interpreter
##for row in scursor:
##    x, y = row[0]
##    print("Centroid = ", x, y)
##
##    Area=row[1]
##    print("Area =", Area)


fc="SchoolDistricts"

#use object ID token to return each part of the features geometry
#incorporate the use of get method which will "split" the results for each feature in the feature class
#We will use the following tokens to extract desired geometry properties
#OID@ to extract the object ID
#USE SHAPE TO EXTRACT THE FULL GEOMETRY OF THE FEATURE

scursor=arcpy.da.SearchCursor(fc, ["OID@", "SHAPE@"])

#ITERATE THROUGH THE FEATURE
for row in scursor:
    print("Feature: ", row[0])
    #use get part method to retrieve the first part of the geometry of each feature in the for loop
    for point in row[1].getPart(0):
        #print the x and y coordinates of each vertex in the feature
        #reference the "point" variable in the FOR loop
        #use predefined ".X", and ".Y" to extract AND PRINT THE xy coordinates
        print("X:", point.X, "Y:", point.Y)


