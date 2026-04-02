# Linear Referencing System with Temporal Versioning - Python Script

Complete Python implementation of the Linear Referencing workflow with temporal tracking.

## Features

✅ **Object-oriented design** - Clean, maintainable code structure
✅ **Full error handling** - Detailed logging and error messages
✅ **Temporal versioning** - Automatic retirement of old routes
✅ **State management** - Proper variable handling (no Model Builder limitations)
✅ **Testable** - Can run standalone or as ArcGIS Script Tool
✅ **Documented** - Comprehensive comments and logging

## Quick Start

### Option 1: Run Directly in Python

```python
import arcpy
from linear_referencing_temporal import LinearReferencingProcessor

# Initialize processor
processor = LinearReferencingProcessor(
    output_gdb=r"C:\GIS\LR_Output.gdb"
)

# Process route
outputs = processor.process_route(
    input_fc=r"C:\GIS\Data.gdb\MainStreet_Line",
    route_id="ROUTE_01",
    base_name="MainStreet_LR",
    start_measure=0,
    station_interval=100,
    tolerance=10
)

print(f"Route: {outputs['route']}")
print(f"Stations: {outputs['stations']}")
print(f"Events: {outputs['events']}")
```

### Option 2: ArcGIS Pro Script Tool

1. **Add as Script Tool in Toolbox:**
   - Right-click your toolbox → Add → Script
   - Name: "Create Linear Referencing System"
   - Script File: `linear_referencing_temporal.py`

2. **Configure Parameters:**

| Label | Name | Type | Direction | Default |
|-------|------|------|-----------|---------|
| Input Line Feature Class | input_fc | Feature Class | Input | |
| Route ID | route_id | String | Input | ROUTE_01 |
| Base Name | base_name | String | Input | |
| Output Geodatabase | output_gdb | Workspace | Input | |
| Start Measure | start_measure | Double | Input | 0 |
| End Measure (Optional) | end_measure | Double | Input (Optional) | |
| Station Interval | station_interval | Double | Input | 100 |
| Tolerance (meters) | tolerance | Double | Input | 10 |
| Output Route FC | output_route | Feature Class | Output (Derived) | |
| Output Station Points | output_stations | Feature Class | Output (Derived) | |
| Output Events Table | output_events | Table | Output (Derived) | |

### Option 3: ArcGIS Notebook

```python
# In ArcGIS Pro Notebook
%run linear_referencing_temporal.py

processor = LinearReferencingProcessor(r"C:\GIS\LR_Output.gdb")
outputs = processor.process_route(
    input_fc=r"C:\GIS\Data.gdb\MainStreet_Line",
    route_id="ROUTE_01",
    base_name="MainStreet_LR",
    station_interval=100
)
```

## Parameters

### Required Parameters

- **input_fc** - Path to input line feature class (your route geometry)
- **route_id** - Unique identifier for this route (e.g., "ROUTE_01")
- **base_name** - Base name for output files (e.g., "MainStreet_LR")
- **output_gdb** - Path to output geodatabase

### Optional Parameters

- **start_measure** - Starting measure value (default: 0)
- **end_measure** - Ending measure for trimming (default: None = full length)
- **station_interval** - Distance between station points in meters (default: 100)
- **tolerance** - Search tolerance for Locate Features in meters (default: 10)

## Outputs

The script creates three datasets in your output geodatabase:

### 1. Route Feature Class: `{base_name}_route`
M-enabled line geometry with temporal versioning

**Fields:**
- `Route_ID` - Route identifier
- `FromM` - Starting measure
- `ToM` - Ending measure  
- `from_date` - When this version became active
- `to_date` - When this version was retired (NULL = currently active)
- `Shape` - M-enabled geometry

### 2. Station Points: `{base_name}_station_points`
Points at regular intervals along the route

**Fields:**
- `StationID` - Unique station identifier (e.g., "ROUTE_01_STN_0001")
- `Route_ID` - Parent route identifier
- `MEAS` - Measure value from Locate Features
- `Chainage` - Formatted chainage (e.g., "001+234.56")
- `from_date` - When this version became active
- `to_date` - When this version was retired (NULL = currently active)
- `Shape` - Point geometry

### 3. Station Events Table: `{base_name}_station_events`
Event table linking stations to route measures

**Fields:**
- `Route_ID` - Route identifier
- `StationID` - Station identifier
- `MEAS` - Measure along route
- `Chainage` - Formatted chainage
- `DISTANCE` - Distance from route (should be near 0)
- `from_date` - When this version became active
- `to_date` - When this version was retired (NULL = currently active)

## Temporal Versioning Logic

### How It Works

1. **First Run:** Creates new route/stations with `from_date = now()` and `to_date = NULL`
2. **Subsequent Runs:** 
   - Finds existing active records (`WHERE to_date IS NULL`)
   - Sets their `to_date = now()` (retires them)
   - Creates new version with `from_date = now()`, `to_date = NULL`

### Querying Active Records

```python
# Get currently active route
where_clause = "to_date IS NULL AND Route_ID = 'ROUTE_01'"
arcpy.management.SelectLayerByAttribute(route_fc, "NEW_SELECTION", where_clause)
```

### Querying Historical Records

```python
# Get all versions of a route, ordered by date
where_clause = "Route_ID = 'ROUTE_01'"
with arcpy.da.SearchCursor(route_fc, ["Route_ID", "from_date", "to_date"], 
                          where_clause, 
                          sql_clause=(None, "ORDER BY from_date DESC")) as cursor:
    for row in cursor:
        print(f"Route: {row[0]}, Active: {row[1]} to {row[2]}")
```

### Getting Route at Specific Date

```python
import datetime
target_date = datetime.datetime(2026, 3, 15)

where_clause = (
    f"Route_ID = 'ROUTE_01' AND "
    f"from_date <= timestamp '{target_date}' AND "
    f"(to_date > timestamp '{target_date}' OR to_date IS NULL)"
)
```

## Workflow Phases

The script executes in 7 phases (same as Model Builder workflow):

### Phase 1: Prepare Route Geometry
- Copy input features
- Add Route_ID field
- Dissolve by Route_ID
- Add FromM/ToM fields
- Calculate measure values

### Phase 2: Create Route with Temporal
- Retire existing active routes
- Create M-enabled route geometry
- Add temporal fields
- Calculate from_date/to_date

### Phase 3: Trim Route (Optional)
- Trim to end_measure if specified
- Skip if end_measure is None

### Phase 4: Generate Station Points
- Create points at station_interval
- Generate StationID values
- Add temporal fields
- Calculate from_date/to_date

### Phase 5: Locate Features Along Routes
- Select active routes and stations
- Run Locate Features Along Routes
- Calculate measure for each station

### Phase 6: Calculate Chainage
- Add Chainage field
- Format as "KKK+MMM.mm"

### Phase 7: Join Chainage to Points
- Join MEAS and Chainage back to station points
- Transfer temporal fields

## Advantages Over Model Builder

### 1. Error Handling
```python
try:
    # Process route
except Exception as e:
    self.log(f"ERROR: {str(e)}", "ERROR")
    # Detailed traceback logged
```

### 2. Conditional Logic
```python
if end_measure is None or end_measure <= 0:
    self.log("Skipping trim phase")
    return route_fc
```

### 3. State Management
```python
# Counter persists within loop
with arcpy.da.UpdateCursor(fc, ["Route_ID", "StationID", "OBJECTID"]) as cursor:
    for row in cursor:
        station_id = f"{row[0]}_STN_{row[2]:04d}"
        row[1] = station_id
        cursor.updateRow(row)
```

### 4. Logging
```python
self.log("Retiring existing active routes")
# Appears in ArcGIS messages AND internal log
```

### 5. Testability
```python
# Can test individual phases
processor = LinearReferencingProcessor(gdb)
dissolve_fc = processor.prepare_route_geometry(input_fc, "TEST_01", 0)
# Inspect output before proceeding
```

## Common Use Cases

### Update Existing Route

```python
# Route geometry has changed - create new version
processor = LinearReferencingProcessor(r"C:\GIS\LR.gdb")

# This automatically retires the old version
outputs = processor.process_route(
    input_fc=r"C:\GIS\Data.gdb\MainStreet_Updated",
    route_id="ROUTE_01",  # Same Route_ID
    base_name="MainStreet_LR",
    station_interval=100
)
```

### Process Multiple Routes

```python
routes = [
    ("ROUTE_01", r"C:\GIS\Data.gdb\Route01_Line", "Route01_LR"),
    ("ROUTE_02", r"C:\GIS\Data.gdb\Route02_Line", "Route02_LR"),
    ("ROUTE_03", r"C:\GIS\Data.gdb\Route03_Line", "Route03_LR"),
]

processor = LinearReferencingProcessor(r"C:\GIS\LR.gdb")

for route_id, input_fc, base_name in routes:
    try:
        processor.process_route(
            input_fc=input_fc,
            route_id=route_id,
            base_name=base_name,
            station_interval=50
        )
        print(f"✓ {route_id} processed successfully")
    except Exception as e:
        print(f"✗ {route_id} failed: {str(e)}")
```

### Custom Station Intervals by Route Type

```python
route_configs = {
    "HIGHWAY_01": {"interval": 100, "tolerance": 15},
    "LOCAL_ST_01": {"interval": 25, "tolerance": 5},
    "TRAIL_01": {"interval": 50, "tolerance": 10}
}

processor = LinearReferencingProcessor(r"C:\GIS\LR.gdb")

for route_id, config in route_configs.items():
    input_fc = rf"C:\GIS\Data.gdb\{route_id}_Line"
    base_name = f"{route_id}_LR"
    
    processor.process_route(
        input_fc=input_fc,
        route_id=route_id,
        base_name=base_name,
        station_interval=config["interval"],
        tolerance=config["tolerance"]
    )
```

## Troubleshooting

### "Route feature class does not exist yet"
- Normal on first run - no existing routes to retire
- Informational message, not an error

### "No existing active routes found to retire"
- Either first run OR all previous routes already retired
- Check: `SELECT * FROM route WHERE to_date IS NULL`

### "Locate Features returns no results"
- Check tolerance - may need to increase
- Verify route and station geometries overlap
- Check coordinate system match

### Python expressions not working
- Ensure proper indentation in code blocks
- Check field names (case-sensitive)
- Verify field types match expression output

## Extending the Script

### Add Custom Fields

```python
# In create_route_with_temporal method, after creating route:
arcpy.management.AddField(route_fc, "Pavement_Type", "TEXT", field_length=20)
arcpy.management.CalculateField(route_fc, "Pavement_Type", "'Asphalt'", "PYTHON3")
```

### Add Email Notification

```python
def send_notification(self, outputs):
    import smtplib
    from email.message import EmailMessage
    
    msg = EmailMessage()
    msg['Subject'] = f'LR Processing Complete: {outputs["route"]}'
    msg['From'] = 'gis@company.com'
    msg['To'] = 'manager@company.com'
    msg.set_content('\n'.join(self.log_messages))
    
    # Send email...
```

### Export to Excel Report

```python
# At end of process_route method:
import pandas as pd

# Get station data
station_data = []
with arcpy.da.SearchCursor(station_fc, ["StationID", "MEAS", "Chainage"]) as cursor:
    for row in cursor:
        station_data.append(row)

df = pd.DataFrame(station_data, columns=["StationID", "Measure", "Chainage"])
df.to_excel(r"C:\Reports\{base_name}_stations.xlsx", index=False)
```

## Requirements

- ArcGIS Pro 3.x (tested with 3.0+)
- Python 3.9+ (comes with ArcGIS Pro)
- arcpy license with Linear Referencing extension
- Spatial Analyst extension (for some operations)

## Version History

- **1.0** (2026-04-01) - Initial release
  - Full temporal versioning support
  - 7-phase workflow implementation
  - Object-oriented design
  - Comprehensive logging

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review ArcGIS Pro Linear Referencing documentation
3. Examine log messages for specific error details

## License

This script is provided as-is for use with ArcGIS Pro.
Modify and extend as needed for your organization.
