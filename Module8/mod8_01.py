#-------------------------------------------------------------------------------
# Name:        module 08
# Purpose:      Custom Tools
#
# Author:      954522
#
# Created:     23/03/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

#Generata a simple buffer process based on the data in the workspace
#import all required modules
import arcpy

#set up the workspace and environment
arcpy.env.workspace =r"C:\GEOS456\Module8\CustomTools.gdb"
arcpy.env.overwriteOutput=True

#define variables to store the values for the buffer tool
inputFc="CALGIS_CITYBOUND_LIMIT"
outputFC="CityBoundary_Buffer"
bufferDist="500 Meters"

#Call the buffer tool and use the variable as inputs
arcpy.Buffer_analysis(inputFc, outputFC, bufferDist)

#-------------------------------------------------------------------------------
#rework the above script and substitute GetParameterAsText() for the feature class

#import all required modules
import arcpy

#set up the workspace and environment
arcpy.env.workspace =r"C:\GEOS456\Module8\CustomTools.gdb"
arcpy.env.overwriteOutput=True

#define variables to store the values for the buffer tool
inputFc= arcpy.GetParameterAsText(0)
outputFC=arcpy.GetParameterAsText(1)
bufferDist=arcpy.GetParameterAsText(2)

#Call the buffer tool and use the variable as inputs
arcpy.Buffer_analysis(inputFc, outputFC, bufferDist)

def getParameterInfo(self):
    inputFc=arcpy.Parameter