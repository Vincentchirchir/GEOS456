"""
Linear Referencing System with Temporal Versioning
ArcGIS Pro Python Script

This script creates a versioned linear referencing system that:
1. Prepares route geometry with M-values
2. Generates station points at regular intervals
3. Calculates chainage values
4. Maintains temporal versioning (from_date/to_date)

Author: Generated for ArcGIS Pro workflow
Date: 2026-04-01
"""

import arcpy
import datetime
import os
import sys


class LinearReferencingProcessor:
    """
    Handles the creation and maintenance of a temporal linear referencing system.
    """
    
    def __init__(self, output_gdb, workspace=None):
        """
        Initialize the processor.
        
        Args:
            output_gdb (str): Path to output geodatabase
            workspace (str): Optional workspace path (defaults to output_gdb)
        """
        self.output_gdb = output_gdb
        self.workspace = workspace or output_gdb
        arcpy.env.workspace = self.workspace
        arcpy.env.overwriteOutput = True
        
        # Timestamp for this processing run
        self.timestamp = datetime.datetime.now()
        
        self.log_messages = []
        
    def log(self, message, level="INFO"):
        """Log a message to both arcpy and internal log."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {level}: {message}"
        
        if level == "ERROR":
            arcpy.AddError(full_message)
        elif level == "WARNING":
            arcpy.AddWarning(full_message)
        else:
            arcpy.AddMessage(full_message)
            
        self.log_messages.append(full_message)
        
    def retire_existing_routes(self, route_fc, route_id):
        """
        Retire any existing active routes by setting their to_date.
        
        Args:
            route_fc (str): Route feature class path
            route_id (str): Route identifier to retire
        """
        self.log(f"Checking for existing active routes with Route_ID = {route_id}")
        
        # Check if the feature class exists and has the required fields
        if not arcpy.Exists(route_fc):
            self.log(f"Route feature class {route_fc} does not exist yet - nothing to retire")
            return
            
        # Verify to_date field exists
        field_names = [f.name for f in arcpy.ListFields(route_fc)]
        if "to_date" not in field_names:
            self.log(f"to_date field not found in {route_fc} - nothing to retire")
            return
        
        # Select active routes (to_date IS NULL)
        where_clause = f"to_date IS NULL AND Route_ID = '{route_id}'"
        
        with arcpy.da.UpdateCursor(route_fc, ["Route_ID", "to_date"], where_clause) as cursor:
            count = 0
            for row in cursor:
                row[1] = self.timestamp  # Set to_date
                cursor.updateRow(row)
                count += 1
                
        if count > 0:
            self.log(f"Retired {count} existing active route(s)")
        else:
            self.log("No existing active routes found to retire")
            
    def prepare_route_geometry(self, input_fc, route_id, start_measure=0, end_measure=None):
        """
        Phase 1: Prepare the route geometry.
        
        Args:
            input_fc (str): Input line feature class
            route_id (str): Route identifier
            start_measure (float): Starting measure value
            end_measure (float): Optional ending measure for trimming
            
        Returns:
            str: Path to dissolved feature class with FromM/ToM fields
        """
        self.log("=" * 60)
        self.log("PHASE 1: Preparing route geometry")
        self.log("=" * 60)
        
        # Step 1: Copy features
        copy_fc = os.path.join(self.workspace, f"{route_id}_copy")
        self.log(f"Copying features from {input_fc} to {copy_fc}")
        arcpy.management.CopyFeatures(input_fc, copy_fc)
        
        # Step 2-3: Add and calculate Route_ID field
        self.log(f"Adding Route_ID field and setting to '{route_id}'")
        arcpy.management.AddField(copy_fc, "Route_ID", "TEXT", field_length=50)
        arcpy.management.CalculateField(copy_fc, "Route_ID", f"'{route_id}'", "PYTHON3")
        
        # Step 4: Dissolve
        dissolve_fc = os.path.join(self.workspace, f"{route_id}_dissolve")
        self.log(f"Dissolving features by Route_ID")
        arcpy.management.Dissolve(
            copy_fc, 
            dissolve_fc, 
            dissolve_field=["Route_ID"],
            multi_part="MULTI_PART",
            unsplit_lines="DISSOLVE_LINES"
        )
        
        # Step 5-6: Add FromM and ToM fields
        self.log("Adding FromM and ToM fields")
        arcpy.management.AddField(dissolve_fc, "FromM", "DOUBLE")
        arcpy.management.AddField(dissolve_fc, "ToM", "DOUBLE")
        
        # Step 7: Calculate FromM
        self.log(f"Calculating FromM = {start_measure}")
        arcpy.management.CalculateField(dissolve_fc, "FromM", start_measure, "PYTHON3")
        
        # Step 8: Calculate ToM
        self.log("Calculating ToM from shape length")
        code_block = """
def calc_to_m(length, start):
    return float(length) + float(start)
"""
        arcpy.management.CalculateField(
            dissolve_fc, 
            "ToM", 
            f"calc_to_m(!shape.length!, {start_measure})", 
            "PYTHON3",
            code_block=code_block
        )
        
        # Cleanup temporary copy
        self.log("Cleaning up temporary copy feature class")
        arcpy.management.Delete(copy_fc)
        
        self.log(f"Route geometry prepared: {dissolve_fc}")
        return dissolve_fc
        
    def create_route_with_temporal(self, dissolve_fc, route_id, base_name):
        """
        Phase 2: Create route with temporal tracking.
        
        Args:
            dissolve_fc (str): Dissolved feature class with FromM/ToM
            route_id (str): Route identifier
            base_name (str): Base name for output
            
        Returns:
            str: Path to route feature class
        """
        self.log("=" * 60)
        self.log("PHASE 2: Creating route with temporal tracking")
        self.log("=" * 60)
        
        route_fc = os.path.join(self.output_gdb, f"{base_name}_route")
        
        # Retire existing active routes BEFORE creating new one
        self.retire_existing_routes(route_fc, route_id)
        
        # Step 9: Create Routes
        self.log(f"Creating routes with M-values: {route_fc}")
        arcpy.lr.CreateRoutes(
            in_line_features=dissolve_fc,
            route_id_field="Route_ID",
            out_feature_class=route_fc,
            measure_source="TWO_FIELDS",
            from_measure_field="FromM",
            to_measure_field="ToM",
            coordinate_priority="UPPER_LEFT",
            measure_factor=1,
            measure_offset=0,
            ignore_gaps="IGNORE",
            build_index="INDEX"
        )
        
        # Step 10-11: Add temporal fields
        self.log("Adding temporal fields (from_date, to_date)")
        
        # Check if fields already exist
        existing_fields = [f.name for f in arcpy.ListFields(route_fc)]
        
        if "from_date" not in existing_fields:
            arcpy.management.AddField(route_fc, "from_date", "DATE")
        if "to_date" not in existing_fields:
            arcpy.management.AddField(route_fc, "to_date", "DATE", field_is_nullable="NULLABLE")
        
        # Step 12-13: Calculate temporal fields for new route
        self.log(f"Setting from_date = {self.timestamp}, to_date = NULL")
        
        # Only update the newly created route (the one without temporal values set)
        where_clause = f"Route_ID = '{route_id}' AND from_date IS NULL"
        
        with arcpy.da.UpdateCursor(route_fc, ["from_date", "to_date"], where_clause) as cursor:
            for row in cursor:
                row[0] = self.timestamp  # from_date
                row[1] = None  # to_date (NULL = active)
                cursor.updateRow(row)
        
        # Cleanup dissolve feature class
        self.log("Cleaning up temporary dissolve feature class")
        arcpy.management.Delete(dissolve_fc)
        
        self.log(f"Route created successfully: {route_fc}")
        return route_fc
        
    def trim_route(self, route_fc, route_id, end_measure, base_name):
        """
        Phase 3: Trim route to specific end measure (optional).
        
        Args:
            route_fc (str): Route feature class
            route_id (str): Route identifier
            end_measure (float): Ending measure
            base_name (str): Base name for output
            
        Returns:
            str: Path to trimmed route feature class
        """
        if end_measure is None or end_measure <= 0:
            self.log("No end_measure specified - skipping trim phase")
            return route_fc
            
        self.log("=" * 60)
        self.log(f"PHASE 3: Trimming route to end measure {end_measure}")
        self.log("=" * 60)
        
        # Create event table for trimming
        event_table = os.path.join("memory", "trim_events")
        trimmed_layer = "trimmed_route_layer"
        
        # Make route event layer
        self.log("Creating route event layer for trimming")
        arcpy.lr.MakeRouteEventLayer(
            in_routes=route_fc,
            route_id_field="Route_ID",
            in_table=route_fc,
            in_event_properties=f"Route_ID LINE FromM ToM",
            out_layer=trimmed_layer,
            offset_field="",
            add_error_field="NO_ERROR_FIELD",
            add_angle_field="NO_ANGLE_FIELD",
            angle_type="NORMAL",
            complement_angle="ANGLE",
            offset_direction="LEFT",
            point_event_type="POINT"
        )
        
        # Note: Actual trimming would require modifying the ToM values
        # This is a simplified placeholder
        self.log("Warning: Route trimming requires custom implementation")
        
        return route_fc
        
    def generate_station_points(self, route_fc, station_interval, base_name):
        """
        Phase 4: Generate station points along the route.
        
        Args:
            route_fc (str): Route feature class
            station_interval (float): Distance between stations
            base_name (str): Base name for output
            
        Returns:
            str: Path to station points feature class
        """
        self.log("=" * 60)
        self.log(f"PHASE 4: Generating station points at {station_interval}m intervals")
        self.log("=" * 60)
        
        station_fc = os.path.join(self.output_gdb, f"{base_name}_station_points")
        
        # Step 21: Generate points along lines
        self.log(f"Generating points: {station_fc}")
        arcpy.management.GeneratePointsAlongLines(
            Input_Features=route_fc,
            Output_Feature_Class=station_fc,
            Point_Placement="DISTANCE",
            Distance=station_interval,
            Include_End_Points="END_POINTS"
        )
        
        # Step 22-23: Add and calculate StationID
        self.log("Adding StationID field")
        arcpy.management.AddField(station_fc, "StationID", "TEXT", field_length=50)
        
        self.log("Calculating StationID values")
        
        # Use update cursor to generate sequential IDs
        with arcpy.da.UpdateCursor(station_fc, ["Route_ID", "StationID", "OBJECTID"]) as cursor:
            for row in cursor:
                route_id = row[0]
                obj_id = row[2]
                station_id = f"{route_id}_STN_{obj_id:04d}"
                row[1] = station_id
                cursor.updateRow(row)
        
        # Step 24-27: Add and calculate temporal fields
        self.log("Adding temporal fields to station points")
        arcpy.management.AddField(station_fc, "from_date", "DATE")
        arcpy.management.AddField(station_fc, "to_date", "DATE", field_is_nullable="NULLABLE")
        
        self.log(f"Setting temporal values: from_date = {self.timestamp}, to_date = NULL")
        with arcpy.da.UpdateCursor(station_fc, ["from_date", "to_date"]) as cursor:
            for row in cursor:
                row[0] = self.timestamp
                row[1] = None
                cursor.updateRow(row)
        
        self.log(f"Station points generated: {station_fc}")
        return station_fc
        
    def locate_features_along_routes(self, route_fc, station_fc, route_id, base_name, tolerance=10):
        """
        Phase 5: Locate features along routes.
        
        Args:
            route_fc (str): Route feature class
            station_fc (str): Station points feature class
            route_id (str): Route identifier
            base_name (str): Base name for output
            tolerance (float): Search tolerance in meters
            
        Returns:
            str: Path to station events table
        """
        self.log("=" * 60)
        self.log("PHASE 5: Locating features along routes")
        self.log("=" * 60)
        
        events_table = os.path.join(self.output_gdb, f"{base_name}_station_events")
        
        # Make temporary layers for selection
        route_layer = "active_routes_layer"
        station_layer = "active_stations_layer"
        
        # Step 28-29: Create layers and select only active records
        self.log("Creating feature layers")
        arcpy.management.MakeFeatureLayer(route_fc, route_layer)
        arcpy.management.MakeFeatureLayer(station_fc, station_layer)
        
        self.log("Selecting only active routes and stations (to_date IS NULL)")
        arcpy.management.SelectLayerByAttribute(route_layer, "NEW_SELECTION", "to_date IS NULL")
        arcpy.management.SelectLayerByAttribute(station_layer, "NEW_SELECTION", "to_date IS NULL")
        
        # Step 30: Locate Features Along Routes
        self.log(f"Locating features along routes (tolerance: {tolerance}m)")
        arcpy.lr.LocateFeaturesAlongRoutes(
            in_features=station_layer,
            in_routes=route_layer,
            route_id_field="Route_ID",
            radius_or_tolerance=f"{tolerance} Meters",
            out_table=events_table,
            out_event_properties="Route_ID POINT MEAS",
            route_locations="FIRST",
            distance_field="DISTANCE",
            zero_length_events="ZERO",
            in_fields="FIELDS",
            m_direction_offsetting="NO_M_DIRECTION"
        )
        
        self.log(f"Station events created: {events_table}")
        return events_table
        
    def calculate_chainage(self, events_table):
        """
        Phase 6: Calculate chainage values.
        
        Args:
            events_table (str): Station events table
        """
        self.log("=" * 60)
        self.log("PHASE 6: Calculating chainage")
        self.log("=" * 60)
        
        # Step 31: Add Chainage field
        self.log("Adding Chainage field")
        arcpy.management.AddField(events_table, "Chainage", "TEXT", field_length=20)
        
        # Step 32: Calculate Chainage
        self.log("Calculating chainage values (format: KKK+MMM.mm)")
        
        code_block = """
def format_chainage(meas):
    if meas is None:
        return "000+000.00"
    km = int(meas / 1000)
    m = meas % 1000
    return f"{km:03d}+{m:06.2f}"
"""
        
        arcpy.management.CalculateField(
            events_table,
            "Chainage",
            "format_chainage(!MEAS!)",
            "PYTHON3",
            code_block=code_block
        )
        
        self.log("Chainage values calculated")
        
    def add_temporal_to_events(self, events_table):
        """
        Add temporal fields to events table.
        
        Args:
            events_table (str): Station events table
        """
        self.log("Adding temporal fields to events table")
        
        # Step 33-34: Add temporal fields
        arcpy.management.AddField(events_table, "from_date", "DATE")
        arcpy.management.AddField(events_table, "to_date", "DATE", field_is_nullable="NULLABLE")
        
        # Step 35-36: Calculate temporal values
        self.log(f"Setting temporal values: from_date = {self.timestamp}, to_date = NULL")
        with arcpy.da.UpdateCursor(events_table, ["from_date", "to_date"]) as cursor:
            for row in cursor:
                row[0] = self.timestamp
                row[1] = None
                cursor.updateRow(row)
                
    def join_chainage_to_points(self, station_fc, events_table):
        """
        Phase 7: Join chainage back to station points.
        
        Args:
            station_fc (str): Station points feature class
            events_table (str): Station events table
        """
        self.log("=" * 60)
        self.log("PHASE 7: Joining chainage back to station points")
        self.log("=" * 60)
        
        # Step 37: Join Field
        self.log("Joining MEAS, Chainage, and temporal fields to station points")
        
        join_fields = ["MEAS", "Chainage", "from_date", "to_date"]
        
        arcpy.management.JoinField(
            in_data=station_fc,
            in_field="StationID",
            join_table=events_table,
            join_field="StationID",
            fields=join_fields
        )
        
        self.log("Join completed successfully")
        
    def process_route(self, input_fc, route_id, base_name, 
                     start_measure=0, end_measure=None, 
                     station_interval=100, tolerance=10):
        """
        Complete processing workflow.
        
        Args:
            input_fc (str): Input line feature class
            route_id (str): Route identifier
            base_name (str): Base name for outputs
            start_measure (float): Starting measure
            end_measure (float): Optional ending measure
            station_interval (float): Distance between stations
            tolerance (float): Search tolerance for locate
            
        Returns:
            dict: Paths to output feature classes and tables
        """
        try:
            self.log("=" * 60)
            self.log("LINEAR REFERENCING WORKFLOW - START")
            self.log("=" * 60)
            self.log(f"Input Feature Class: {input_fc}")
            self.log(f"Route ID: {route_id}")
            self.log(f"Base Name: {base_name}")
            self.log(f"Start Measure: {start_measure}")
            self.log(f"End Measure: {end_measure if end_measure else 'None (full length)'}")
            self.log(f"Station Interval: {station_interval}")
            self.log(f"Tolerance: {tolerance}")
            self.log(f"Timestamp: {self.timestamp}")
            
            # Phase 1: Prepare route geometry
            dissolve_fc = self.prepare_route_geometry(input_fc, route_id, start_measure, end_measure)
            
            # Phase 2: Create route with temporal
            route_fc = self.create_route_with_temporal(dissolve_fc, route_id, base_name)
            
            # Phase 3: Trim route (optional)
            route_fc = self.trim_route(route_fc, route_id, end_measure, base_name)
            
            # Phase 4: Generate station points
            station_fc = self.generate_station_points(route_fc, station_interval, base_name)
            
            # Phase 5: Locate features along routes
            events_table = self.locate_features_along_routes(route_fc, station_fc, route_id, base_name, tolerance)
            
            # Phase 6: Calculate chainage
            self.calculate_chainage(events_table)
            
            # Add temporal fields to events
            self.add_temporal_to_events(events_table)
            
            # Phase 7: Join chainage to points
            self.join_chainage_to_points(station_fc, events_table)
            
            self.log("=" * 60)
            self.log("LINEAR REFERENCING WORKFLOW - COMPLETE")
            self.log("=" * 60)
            
            outputs = {
                "route": route_fc,
                "stations": station_fc,
                "events": events_table
            }
            
            for key, value in outputs.items():
                self.log(f"Output {key}: {value}")
            
            return outputs
            
        except Exception as e:
            self.log(f"ERROR during processing: {str(e)}", "ERROR")
            self.log(f"Error type: {type(e).__name__}", "ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            raise
            

def main():
    """
    Main execution function - can be called as a script tool or standalone.
    """
    try:
        # Get parameters (from script tool or hardcoded for testing)
        if len(sys.argv) > 1:
            # Running as script tool
            input_fc = arcpy.GetParameterAsText(0)
            route_id = arcpy.GetParameterAsText(1)
            base_name = arcpy.GetParameterAsText(2)
            output_gdb = arcpy.GetParameterAsText(3)
            start_measure = float(arcpy.GetParameterAsText(4)) if arcpy.GetParameterAsText(4) else 0
            end_measure = float(arcpy.GetParameterAsText(5)) if arcpy.GetParameterAsText(5) else None
            station_interval = float(arcpy.GetParameterAsText(6)) if arcpy.GetParameterAsText(6) else 100
            tolerance = float(arcpy.GetParameterAsText(7)) if arcpy.GetParameterAsText(7) else 10
        else:
            # Example parameters for testing
            arcpy.AddMessage("No parameters provided - using example values")
            arcpy.AddMessage("To use as script tool, provide parameters:")
            arcpy.AddMessage("  0: Input Line Feature Class")
            arcpy.AddMessage("  1: Route ID")
            arcpy.AddMessage("  2: Base Name")
            arcpy.AddMessage("  3: Output Geodatabase")
            arcpy.AddMessage("  4: Start Measure (optional, default 0)")
            arcpy.AddMessage("  5: End Measure (optional)")
            arcpy.AddMessage("  6: Station Interval (optional, default 100)")
            arcpy.AddMessage("  7: Tolerance (optional, default 10)")
            
            # Example - modify these for your environment
            input_fc = r"C:\GIS\Data.gdb\MainStreet_Line"
            route_id = "ROUTE_01"
            base_name = "MainStreet_LR"
            output_gdb = r"C:\GIS\LR_Output.gdb"
            start_measure = 0
            end_measure = None
            station_interval = 100
            tolerance = 10
        
        # Create processor and run
        processor = LinearReferencingProcessor(output_gdb)
        
        outputs = processor.process_route(
            input_fc=input_fc,
            route_id=route_id,
            base_name=base_name,
            start_measure=start_measure,
            end_measure=end_measure,
            station_interval=station_interval,
            tolerance=tolerance
        )
        
        # Set output parameters if running as script tool
        if len(sys.argv) > 8:
            arcpy.SetParameterAsText(8, outputs["route"])
            arcpy.SetParameterAsText(9, outputs["stations"])
            arcpy.SetParameterAsText(10, outputs["events"])
        
        arcpy.AddMessage("Processing completed successfully!")
        
    except Exception as e:
        arcpy.AddError(f"Script failed: {str(e)}")
        import traceback
        arcpy.AddError(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
