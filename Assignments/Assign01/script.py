#---------------------------------------------------------------------------------------
# Name:        Assignment 1
# Purpose:     This script identifies top 3 townships in Communes that contain the most amount of cycling networks
#
# Author:      Chirchir Vincent
#
# Created:     21/01/2026
# Copyright:   (c) vince 2026
# Licence:     <your licence>
#---------------------------------------------------------------------------------------
import arcpy
import os

arcpy.env.workspace=r"C:\GEOS456\Assign01"
arcpy.env.overwriteOutput = True
projection=arcpy.SpatialReference("NTF (PARIS) Lambert Sud France")
gdb=r"C:\GEOS456\Assign01\Toulouse.gdb"
raw_datasets=[]

#Create a list of the RAW data (shapefiles) provided in the assignment data folder
print("1.Below is the list of the RAW data (shapefiles) in the folder: ")
for dirpath, dirnames, filenames in arcpy.da.Walk(arcpy.env.workspace):
    for raw_data in filenames:
        if raw_data.endswith(".shp"):
            raw_datasets.append(os.path.join(dirpath, raw_data))
            print(f" - {raw_data}")

            shp_path=os.path.join(dirpath, raw_data)
            desc=arcpy.da.Describe(shp_path)

            #exportING the shapefiles to the geodatabase
            out_gdb=os.path.join(gdb, desc["baseName"] + "_projected")

            #projectING the feature classes
            arcpy.management.Project(shp_path, out_gdb, projection)


#Features in gdb before intersecting
arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"
print("2.Below is the list of features stored in gdb before intersecting: ")
fc_gdb=arcpy.ListFeatureClasses()
for fc in fc_gdb:
    print(f" - {fc}")


#Use geoprocessing to intersect each cycling network to the Toulouse townships
arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"
cyclable=["Bande_Cyclable_projected", "Piste_Cyclable_projected", "ReseauVert_projected"]
township="communes_projected"

for network in cyclable:
    out_cyclable=os.path.join(arcpy.env.workspace, f"{network}_by_commune")
    intersect_input=[network, township]
    arcpy.analysis.Intersect(intersect_input, out_cyclable)
    print(f"{network} successfully intersected")
    print()

#Features in gdb after intersecting
arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"
print("2.Below is the list of features stored in gdb after intersecting: ")
fc_gdb=arcpy.ListFeatureClasses()
for fc in fc_gdb:
    print(f" - {fc}")

#Summarize the total length (km) of each cycle network within each township
#Adding field to Intersect_network
arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"

input_fc=["Bande_Cyclable_projected_by_commune", "Piste_Cyclable_projected_by_commune", "ReseauVert_projected_by_commune"]
field_name="length_KM"
field_type="DOUBLE"

for features in input_fc:
    arcpy.management.AddField(features,field_name, field_type)
    print(f"Field added to {features}")
    print()


#Calculatinng the added field
arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"
input_fc=["Bande_Cyclable_projected_by_commune", "Piste_Cyclable_projected_by_commune", "ReseauVert_projected_by_commune"]

for fc in input_fc:
    arcpy.management.CalculateGeometryAttributes(fc, [["Length_Km", "LENGTH"]], "KILOMETERS")
    print(f"Field calculated successfully to {fc}")
    print()


#Summarize the total length (km) of each cycle network within each township
arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"
input_fc=["Bande_Cyclable_projected_by_commune", "Piste_Cyclable_projected_by_commune", "ReseauVert_projected_by_commune"]
case_field="libelle"

for fc in input_fc:
    out_table=os.path.join(arcpy.env.workspace, f"{fc}_sum")
    arcpy.analysis.Statistics(fc, out_table, [["length_KM", "SUM" ]], case_field)
##    print(f"Below is the summary table of top 3 townships in {fc}")
    print()

#Identifying top 3
print("Below is the summary table of the top 3 townships: ")
tables = [
    ("Bande_Cyclable_projected_by_commune_sum", "Bande Cyclable"),
    ("Piste_Cyclable_projected_by_commune_sum", "Piste Cyclable"),
    ("ReseauVert_projected_by_commune_sum", "ReseauVert")
]

name_field = "libelle"
length_field = "SUM_Length_Km"

for table, label in tables:
    rows = []

    with arcpy.da.SearchCursor(table, [name_field, length_field]) as cursor:
        for name, length_km in cursor:
            rows.append((name, length_km))

    rows_sorted = sorted(rows, key=lambda x: x[1], reverse=True)

    print(f"\nTop 3 townships – {label}:")
    for name, km in rows_sorted[:3]:
        print(f" - {name}: {km:.2f} km")

#Delete gdb after every run
arcpy.env.workspace=r"C:\GEOS456\Assign01\Toulouse.gdb"
fc_deletes=arcpy.ListFeatureClasses()
for fc_delete in fc_deletes:
    arcpy.management.Delete(fc_delete)

