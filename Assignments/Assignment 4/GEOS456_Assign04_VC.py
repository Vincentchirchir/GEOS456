# ---------------------------------------------------------------------------------------
# Name:        Assignment 4: Custom Geoprocessing Tools
# Purpose:      The purpose of this assignment is to use high-level programming (HLP) language to create a custom tool.
#
# Author:      vince
#
# Created:     02/04/2026
# Copyright:   (c) vince 2026
# Licence:     <your licence>
# ---------------------------------------------------------------------------------------
import arcpy

arcpy.env.overwriteOutput = True

# Tool parameters
output_workspace = arcpy.GetParameterAsText(0)
crime1 = arcpy.GetParameterAsText(1)
crime2 = arcpy.GetParameterAsText(2)
crime3 = arcpy.GetParameterAsText(3)
buffer_distance = arcpy.GetParameterAsText(4)

# Set workspace to INPUT data location
arcpy.env.workspace = r"C:\GEOS456\Assign03\City_of_Nice_Place.gdb"

arcpy.AddMessage("Starting crime analysis...")

# Precincts and landmarks layers
precincts = "Precincts"
landmarks = "Landmarks"

# List to store crime layers
crime_layers = [crime1, crime2, crime3]

# Intersect each crime type with precincts and generate statistics
for crime in crime_layers:
    arcpy.AddMessage(f"Processing {crime}...")

    # Intersect crime with precincts
    crime_name = arcpy.Describe(crime).baseName
    intersect_output = f"{output_workspace}\\Precincts_{crime_name}"
    arcpy.analysis.Intersect([crime, precincts], intersect_output)

    # Generate frequency statistics
    stats_table = f"{output_workspace}\\Precinct_{crime_name}_Stats"
    arcpy.analysis.Statistics(
        intersect_output, stats_table, [["OBJECTID", "COUNT"]], "Precinct"
    )

    # Sort the table in ascending order by frequency
    sorted_table = f"{output_workspace}\\Precinct_{crime_name}_Sorted"
    arcpy.management.Sort(stats_table, sorted_table, [["COUNT_OBJECTID", "ASCENDING"]])

    arcpy.AddMessage(f"Created sorted frequency table: {sorted_table}")

    # Delete intermediate stats table
    arcpy.management.Delete(stats_table)

# Analyze assaults near landmarks
arcpy.AddMessage("\nAnalyzing assaults near landmarks...")

# Buffer landmarks
landmark_buffer = f"{output_workspace}\\Landmarks_Buffer_250m"
arcpy.analysis.Buffer(
    landmarks, landmark_buffer, buffer_distance, "FULL", "ROUND", "NONE"
)

# Intersect assaults with buffered landmarks
landmarks_assaults = f"{output_workspace}\\Landmarks_Assaults"
arcpy.analysis.Intersect([crime2, landmark_buffer], landmarks_assaults)

# Count total assaults within buffer of landmarks
assault_count = int(arcpy.management.GetCount(landmarks_assaults)[0])

# Generate statistics by landmark
landmarks_assault_stats = f"{output_workspace}\\Landmarks_Assaults_Stats"
arcpy.analysis.Statistics(
    landmarks_assaults, landmarks_assault_stats, [["OBJECTID", "COUNT"]], "LANDNAME"
)

# Sort to find the landmark with most assaults (descending)
landmarks_sorted = f"{output_workspace}\\Landmarks_Assaults_Sorted"
arcpy.management.Sort(
    landmarks_assault_stats, landmarks_sorted, [["COUNT_OBJECTID", "DESCENDING"]]
)

# Get the landmark with highest assault count
with arcpy.da.SearchCursor(landmarks_sorted, ["LANDNAME", "COUNT_OBJECTID"]) as cursor:
    row = next(cursor)
    top_landmark = row[0]
    top_landmark_count = row[1]

# Print results to tool messages
arcpy.AddMessage("\n" + "=" * 50)
arcpy.AddMessage("CRIME ANALYSIS RESULTS")
arcpy.AddMessage("=" * 50)

# Print frequency tables
arcpy.AddMessage("\nCrime Frequency by Precinct:")
for crime in crime_layers:
    crime_name = arcpy.Describe(crime).baseName
    table_name = f"{output_workspace}\\Precinct_{crime_name}_Sorted"
    arcpy.AddMessage(f"\n{crime_name}:")

    with arcpy.da.SearchCursor(table_name, ["Precinct", "COUNT_OBJECTID"]) as cursor:
        for row in cursor:
            arcpy.AddMessage(f"  Precinct {row[0]}: {row[1]} incidents")

# Print assault/landmark analysis
arcpy.AddMessage("\n" + "=" * 50)
arcpy.AddMessage("ASSAULT NEAR LANDMARKS ANALYSIS")
arcpy.AddMessage("=" * 50)

arcpy.AddMessage(
    f"\nThere are {assault_count} assaults that occur within {buffer_distance} of a landmark."
)
arcpy.AddMessage(
    f"The landmark with the most assaults is: {top_landmark} ({top_landmark_count} assaults)"
)

# Clean up intermediate datasets
arcpy.AddMessage("\nCleaning up intermediate datasets...")

if arcpy.Exists(landmarks_assault_stats):
    arcpy.management.Delete(landmarks_assault_stats)
    arcpy.AddMessage(f"Deleted: {landmarks_assault_stats}")

arcpy.AddMessage("\nAnalysis complete!")
