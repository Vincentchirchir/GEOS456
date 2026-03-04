#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      954522
#
# Created:     04/02/2026
# Copyright:   (c) 954522 2026
# Licence:     <your licence>
#-------------------------------------------------------------------------------

#Demo the use of the cursor to access and manipulate tabular info

#import required module and set the workspace env
import arcpy
arcpy.env.workspace=r"C:\GEOS456\Module2\Data.gdb"
arcpy.env.overwriteOutput=True

def messages():
    print(arcpy.GetMessage(0)) #print only the FIRST geoprocessing message
    count = arcpy.GetMessageCount()#counts ALL geoprocessing messages for any tool
    print(arcpy.GetMessage(count-1))#indexes the LAST message from a tool
    print()

###list features
##fc=arcpy.ListFeatureClasses()
##for fclist in fc:
##    print(fclist)
##    #list fields
##    fields=arcpy.ListFields("SchoolDistricts")
##    for field in fields:
##        print(f" - {field.name}")
##
###use the searchcursor to access fields in an existing attribute table
##SCursor = arcpy.da.SearchCursor("Crime2009Table", ["XNAD83", "YNAD83"])
##
###iterate through the table and print the results
##for row in SCursor:
##    print("X:", row[0], "Y:", row[1])

##    #use an IF statement to stop an iteration process
##
##    if row[0] == "Southside ISD":
##        print(row[0], row[1])

#uSING INSERT CURSOR TO ADD NEW ROWS TO AN EXISTING ATTRIBUTE TABLE
#define a variable to store the Insert cursor

##Icursor=arcpy.da.InsertCursor("SchoolDistricts", ["Name", "District"])
##
###add 3 rows to the attribute table
###populate the new rows with text related to the fields identified in the cursor
###DONT FORGET TO APPLY THE CHANGES USING THE INSERT.ROW METHOD
##
##X = 1
##while X <=3:
##    Icursor.insertRow(["Tambul", "Keiyo"])
##    X=X+1
##    print(arcpy.GetMessages())
##
###REMOVE THE LOCK CREATED BY THE INSERT CURSOR
##del Icursor
##print(arcpy.GetMessages())


###create a new field and use the update cursor to populate the new field.
###use the Addfield management to add a new field
##arcpy.AddField_management("SchoolDistricts", "School", "TEXT", "", "", 25)
##messages()
##
###define a variable to update a cursor
##Ucursor=arcpy.da.UpdateCursor("SchoolDistricts", ["Color", "School"])
##
###use a for loop to iterate through an attribute table
###use an IF statement to update the new field values based on existing fields
##for row in Ucursor:
##    if row[0]==2: #row[0] references the "color" field in the update cursor
##        row[1]="SAIT" #row[1] refers to the newly created field
##    elif row[0]==3:
##        row[1]="U of C"
##    elif row[0]==8:
##        row[1]= "MRU"
##    else:
##        row[1]="Unknown"
##
##    Ucursor.updateRow(row)#apply changes to the table. VERY IMPORTANT
##
###remove any locks created by the cursor
##del Ucursor

'''
what if we wanted to store the burglaries that occur in one school district as their own feature class?
To do this we are going to select by attributes for the school districts and then use that selection
to select by location
once the burglaries are selected, we will save them to the workspace as its own feature class
'''

#use the select by attributes to select a school district
#optionally create a temporary layer file to store in the selection tool
district_layer=arcpy.MakeFeatureLayer_management("SchoolDistricts", "School_Layer")
messages()

#optionally use the Add Field Delimiters function
delimField=arcpy.AddFieldDelimiters("SchoolDistricts", "Name")

#Use the select by attributes to select a school district
arcpy.SelectLayerByAttribute_management(district_layer, "", delimField + " = 'Alamo Heights ISD'")
messages()

#select by location the burglaries that fall within the selected school districts
burglary_layer=arcpy.MakeFeatureLayer_management("Burglary", "Burg_Layer")
arcpy.SelectLayerByLocation_management(burglary_layer, "", district_layer)
messages()

#count the total burglaries in the feature class
burg_count_total=arcpy.GetCount_management("Burglary")
print("Total burglaries: ", burg_count_total)
messages()

#count how many burglaries are within the selected school district
burg_count_select=arcpy.GetCount_management(burglary_layer)
print("The burglaries in Alamo Heights: ", burg_count_select)

#create a permanent feature class from that selection
arcpy.ExportFeatures_conversion(burglary_layer, "Alamo_Burglaries")
messages()



