import arcpy


class Toolbox(object):
    def __init__(self):
        self.label = "Crime Analysis Tool"
        self.alias = "CrimeAnalysisTool"
        self.tools = [CrimeAnalysisTool]


class CrimeAnalysisTool(object):
    def __init__(self):
        self.label = "Crime Analysis Tool"
        self.description = "Create a Python script tool that analyzes crime data for the City of Nice Place police department."

    def getParameterInfo(self):
        output_gdb = arcpy.Parameter(
            displayName="Workspace",
            name="output_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )

        # setting default gdb
        try:
            output_gdb.value = arcpy.mp.ArcGISProject("CURRENT").defaultGeodatabase
        except:
            pass

        crime1 = arcpy.Parameter(
            displayName="Crime Type 1",
            name="crime1",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        crime2 = arcpy.Parameter(
            displayName="Crime Type 2",
            name="crime2",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        crime3 = arcpy.Parameter(
            displayName="Crime Type 3",
            name="crime3",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        buffer = arcpy.Parameter(
            displayName="Buffer Distance",
            name="buffer",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input",
        )

        return [
            output_gdb,
            crime1,
            crime2,
            crime3,
            buffer,
        ]

    def updateMessages(self, parameters):
        output_gdb = parameters[0]
        crime1 = parameters[1]
        crime2 = parameters[2]
        crime3 = parameters[3]
        buffer = parameters[4]

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True

        # Get parameter values
        workspace = parameters[0].valueAsText
        crime1 = parameters[1].valueAsText
        crime2 = parameters[2].valueAsText
        crime3 = parameters[3].valueAsText
        buffer_distance = parameters[4].valueAsText

        # Set workspace
        arcpy.env.workspace = workspace

        arcpy.AddMessage("Starting crime analysis...")

        # recincts and landmarks layers
        precincts = "Precincts"
        landmarks = "Landmarks"

        # List to store crime layers
        crime_layers = [crime1, crime2, crime3]

        # Intersect each crime type with precincts and generate statistics

        for crime in crime_layers:
            # Get the base name of the crime layer
            crime_name = arcpy.Describe(crime).baseName

            arcpy.AddMessage(f"Processing {crime_name}...")

            # Intersect crime with precincts
            intersect_output = f"Precincts_{crime_name}"
            arcpy.analysis.Intersect([crime, precincts], intersect_output)

            # Get the first field from precincts
            precinct_fields = [
                f.name
                for f in arcpy.ListFields(precincts)
                if f.type not in ["OID", "Geometry"]
                and f.name not in ["Shape_Length", "Shape_Area"]
            ]
            precinct_id_field = precinct_fields[0] if precinct_fields else "OBJECTID"

            # Generate frequency statistics
            stats_table = f"Precinct_{crime_name}_Stats"
            arcpy.analysis.Statistics(
                intersect_output,
                stats_table,
                [["OBJECTID", "COUNT"]],
                precinct_id_field,
            )

            # Sort the table in ascending order by frequency
            sorted_table = f"Precinct_{crime_name}_Sorted"
            arcpy.management.Sort(
                stats_table, sorted_table, [["FREQUENCY", "ASCENDING"]]
            )

            arcpy.AddMessage(f"Created sorted frequency table: {sorted_table}")

            # Delete intermediate files
            arcpy.management.Delete(intersect_output)
            arcpy.management.Delete(stats_table)

        # Analyze assaults near landmarks
        arcpy.AddMessage("\nAnalyzing assaults near landmarks...")

        # Buffer landmarks
        landmark_buffer = "Landmarks_Buffer_250m"
        arcpy.analysis.Buffer(
            landmarks, landmark_buffer, buffer_distance, "FULL", "ROUND", "ALL"
        )

        # Find which crime layer is Assaults (look for "Assault" in the name)
        assault_layer = None
        for crime in crime_layers:
            crime_name = arcpy.Describe(crime).baseName.upper()
            if "ASSAULT" in crime_name:
                assault_layer = crime
                break

        if assault_layer is None:
            arcpy.AddError(
                "Could not find Assault layer! Make sure one of the crime types has 'Assault' in its name."
            )
            return

        # Intersect assaults with buffered landmarks
        # Intersect assaults with buffered landmarks
        landmarks_assaults = "Landmarks_Assaults"
        arcpy.analysis.Intersect([assault_layer, landmark_buffer], landmarks_assaults)

        # Count total assaults within buffer of landmarks
        assault_count = int(arcpy.management.GetCount(landmarks_assaults)[0])

        # Get the landmark name field from the INTERSECTED result
        # List all fields in the intersected output
        intersect_fields = [f.name for f in arcpy.ListFields(landmarks_assaults)]
        arcpy.AddMessage(f"Available fields in intersected layer: {intersect_fields}")

        # Look for landmark name field in the intersected output
        landmark_name_field = None
        for field in intersect_fields:
            if any(
                name in field.upper()
                for name in ["LANDNAME", "NAME", "LANDMARK", "LM_NAME"]
            ):
                landmark_name_field = field
                break

        #
        if not landmark_name_field:
            string_fields = [
                f.name
                for f in arcpy.ListFields(landmarks_assaults)
                if f.type == "String" and f.name not in ["Shape", "SHAPE"]
            ]
            landmark_name_field = string_fields[0] if string_fields else "OBJECTID"

        arcpy.AddMessage(f"Using landmark field: {landmark_name_field}")

        # Generate statistics by landmark to find which has most assaults
        landmarks_assault_stats = "Landmarks_Assaults_Stats"
        arcpy.analysis.Statistics(
            landmarks_assaults,
            landmarks_assault_stats,
            [["OBJECTID", "COUNT"]],
            landmark_name_field,
        )

        # Sort to find the landmark with most assaults (descending)
        landmarks_sorted = "Landmarks_Assaults_Sorted"
        arcpy.management.Sort(
            landmarks_assault_stats, landmarks_sorted, [["FREQUENCY", "DESCENDING"]]
        )

        # Get the landmark with highest assault count
        with arcpy.da.SearchCursor(
            landmarks_sorted, [landmark_name_field, "FREQUENCY"]
        ) as cursor:
            row = next(cursor)
            top_landmark = row[0]
            top_landmark_count = row[1]

        # Print results to tool messages

        arcpy.AddMessage("\n" + "=" * 60)
        arcpy.AddMessage("CRIME ANALYSIS RESULTS")
        arcpy.AddMessage("=" * 60)

        # Print frequency tables
        arcpy.AddMessage("\nCrime Frequency by Precinct:")
        for crime in crime_layers:
            crime_name = arcpy.Describe(crime).baseName
            table_name = f"Precinct_{crime_name}_Sorted"
            arcpy.AddMessage(f"\n{crime_name}:")

            # Get the precinct field name from the table
            table_fields = [f.name for f in arcpy.ListFields(table_name)]
            precinct_field = [
                f
                for f in table_fields
                if f not in ["OBJECTID", "FREQUENCY", "Shape_Length", "Shape_Area"]
            ][0]

            with arcpy.da.SearchCursor(
                table_name, [precinct_field, "FREQUENCY"]
            ) as cursor:
                for row in cursor:
                    arcpy.AddMessage(f"  Precinct {row[0]}: {row[1]} incidents")

        # Print assault/landmark analysis
        arcpy.AddMessage("\n" + "-" * 60)
        arcpy.AddMessage("ASSAULT NEAR LANDMARKS ANALYSIS")
        arcpy.AddMessage("-" * 60)
        arcpy.AddMessage(
            f"There are {assault_count} assaults that occur within {buffer_distance} of a landmark."
        )
        arcpy.AddMessage(
            f"The landmark with the most assaults is: {top_landmark} ({top_landmark_count} assaults)"
        )

        # Clean up intermediate datasets

        arcpy.AddMessage("\nCleaning up intermediate datasets...")

        # Delete temporary files
        delete_list = [
            landmark_buffer,
            landmarks_assaults,
            landmarks_assault_stats,
            landmarks_sorted,
        ]

        for item in delete_list:
            if arcpy.Exists(item):
                arcpy.management.Delete(item)
                arcpy.AddMessage(f"Deleted: {item}")

        arcpy.AddMessage("\nAnalysis complete!")
