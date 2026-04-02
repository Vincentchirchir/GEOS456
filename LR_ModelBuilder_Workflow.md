# ArcGIS Pro Model Builder: Linear Referencing Workflow with Temporal Versioning

## Overview
This workflow creates a versioned linear referencing system with temporal tracking. It supports route updates while maintaining historical records through `from_date` and `to_date` fields.

---

## Model Parameters (Input Variables)

Set these as model parameters for reusability:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `input_line_fc` | Feature Class | Source route geometry | `Roads\MainStreet` |
| `base_name` | String | Base name for outputs | `MainStreet_LR` |
| `route_id_value` | String | Unique route identifier | `ROUTE_01` |
| `start_measure` | Double | Starting measure value | `0` |
| `end_measure` | Double (Optional) | Ending measure for trimming | `5000` (or leave empty) |
| `station_interval` | Double | Distance between stations | `100` |
| `output_gdb` | Workspace | Target geodatabase | `C:\Project\LR.gdb` |

---

## PHASE 1: Prepare the Route

### Step 1: Copy Features
**Tool:** `Data Management Tools > General > Copy Features`

**Parameters:**
- **Input Features:** `%input_line_fc%`
- **Output Feature Class:** `%output_gdb%\%base_name%_copy`

**Purpose:** Create a working copy to protect the original data

**Output Variable:** `base_name_copy`

---

### Step 2: Add Field (Route_ID)
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%base_name_copy%`
- **Field Name:** `Route_ID`
- **Field Type:** `TEXT`
- **Field Length:** `50`

---

### Step 3: Calculate Field (Route_ID)
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%base_name_copy%`
- **Field Name:** `Route_ID`
- **Expression Type:** `Python 3`
- **Expression:** `"%route_id_value%"`

---

### Step 4: Dissolve
**Tool:** `Data Management Tools > Generalization > Dissolve`

**Parameters:**
- **Input Features:** `%base_name_copy%`
- **Output Feature Class:** `%output_gdb%\%base_name%_dissolve`
- **Dissolve Field(s):** `Route_ID`
- **Statistics Fields:** (none)
- **Multi-part features:** `MULTI_PART`
- **Unsplit lines:** `DISSOLVE_LINES`

**Purpose:** Merge any broken segments into one continuous line

**Output Variable:** `base_name_dissolve`

---

### Step 5: Add Field (FromM)
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%base_name_dissolve%`
- **Field Name:** `FromM`
- **Field Type:** `DOUBLE`

---

### Step 6: Add Field (ToM)
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%base_name_dissolve%`
- **Field Name:** `ToM`
- **Field Type:** `DOUBLE`

---

### Step 7: Calculate Field (FromM)
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%base_name_dissolve%`
- **Field Name:** `FromM`
- **Expression Type:** `Python 3`
- **Expression:** `%start_measure%`

---

### Step 8: Calculate Field (ToM)
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%base_name_dissolve%`
- **Field Name:** `ToM`
- **Expression Type:** `Python 3`
- **Code Block:**
```python
def calc_to_m(length, start):
    return float(length) + float(start)
```
- **Expression:** `calc_to_m(!shape.length!, %start_measure%)`

---

## PHASE 2: Create Route with Temporal Fields

### Step 9: Create Routes
**Tool:** `Linear Referencing Tools > Create Routes`

**Parameters:**
- **Input Line Features:** `%base_name_dissolve%`
- **Route Identifier Field:** `Route_ID`
- **Output Route Feature Class:** `%output_gdb%\%base_name%_route`
- **Measure Source:** `TWO_FIELDS`
- **From Measure Field:** `FromM`
- **To Measure Field:** `ToM`
- **Coordinate Priority:** `UPPER_LEFT`
- **Measure Factor:** `1`
- **Measure Offset:** `0`
- **Ignore spatial gaps:** `IGNORE`
- **Build index:** `INDEX`

**Output Variable:** `base_name_route`

---

### Step 10: Add Field (from_date)
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%base_name_route%`
- **Field Name:** `from_date`
- **Field Type:** `DATE`

---

### Step 11: Add Field (to_date)
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%base_name_route%`
- **Field Name:** `to_date`
- **Field Type:** `DATE`
- **Field Is Nullable:** `NULLABLE`

---

### Step 12: Calculate Field (from_date)
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%base_name_route%`
- **Field Name:** `from_date`
- **Expression Type:** `Python 3`
- **Expression:** `datetime.datetime.now()`

**Purpose:** Timestamp when this route version became active

---

### Step 13: Calculate Field (to_date)
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%base_name_route%`
- **Field Name:** `to_date`
- **Expression Type:** `Python 3`
- **Expression:** `None`

**Purpose:** NULL indicates this is the currently active version

---

### Step 14: Select Layer By Attribute (Retirement Check)
**Tool:** `Data Management Tools > Layers and Table Views > Select Layer By Attribute`

**Parameters:**
- **Input Layer:** `%base_name_route%`
- **Selection Type:** `NEW_SELECTION`
- **Where Clause:** `to_date IS NULL AND Route_ID = '%route_id_value%'`

**Purpose:** Find existing active routes that need to be retired

**Note:** This step should be moved BEFORE Step 9 in actual implementation to retire old routes before creating new ones.

---

### Step 15: Calculate Field (Retire Old Route)
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** Output from Step 14 (selected features)
- **Field Name:** `to_date`
- **Expression Type:** `Python 3`
- **Expression:** `datetime.datetime.now()`

**Purpose:** Mark old route version as no longer active

**Important:** Run this BEFORE Step 9 in production workflow

---

### Step 16: Delete (Cleanup)
**Tool:** `Data Management Tools > General > Delete`

**Parameters:**
- **Input Data Elements:** 
  - `%base_name_copy%`
  - `%base_name_dissolve%`

**Purpose:** Remove intermediate datasets (NOT the route)

---

## PHASE 3: Trim Route to End Measure (Optional)

**Condition:** Only execute if `%end_measure%` parameter is provided and > 0

### Step 17: Make Route Event Layer
**Tool:** `Linear Referencing Tools > Make Route Event Layer`

**Parameters:**
- **Input Route Features:** `%base_name_route%`
- **Route Identifier Field:** `Route_ID`
- **Event Table:** `%base_name_route%` (same as routes)
- **Event Route Identifier Field:** `Route_ID`
- **Event Type:** `LINE`
- **From-Measure Field:** `FromM`
- **To-Measure Field:** Create calculated field = `min(!ToM!, %end_measure%)`
- **Output Layer Name:** `trimmed_route_layer`

---

### Step 18: Copy Features (Trimmed Route)
**Tool:** `Data Management Tools > General > Copy Features`

**Parameters:**
- **Input Features:** `trimmed_route_layer`
- **Output Feature Class:** `%output_gdb%\%base_name%_route_trimmed`

---

### Step 19: Delete (Original Untrimmed)
**Tool:** `Data Management Tools > General > Delete`

**Parameters:**
- **Input Data Elements:** `%base_name_route%`

---

### Step 20: Rename (Make Trimmed the Primary)
**Tool:** `Data Management Tools > General > Rename`

**Parameters:**
- **Input Data Element:** `%base_name%_route_trimmed`
- **Output Data Element:** `%base_name%_route`

**Update Variable:** `base_name_route` now points to trimmed version

---

## PHASE 4: Generate Station Points with Temporal Fields

### Step 21: Generate Points Along Lines
**Tool:** `Data Management Tools > Features > Generate Points Along Lines`

**Parameters:**
- **Input Features:** `%base_name_route%`
- **Output Feature Class:** `%output_gdb%\%base_name%_station_points`
- **Point Placement:** `DISTANCE`
- **Distance:** `%station_interval%`
- **Include End Points:** `END_POINTS`

**Output Variable:** `base_name_station_points`

---

### Step 22: Add Field (StationID)
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%base_name_station_points%`
- **Field Name:** `StationID`
- **Field Type:** `TEXT`
- **Field Length:** `50`

---

### Step 23: Calculate Field (StationID)
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%base_name_station_points%`
- **Field Name:** `StationID`
- **Expression Type:** `Python 3`
- **Code Block:**
```python
counter = 0
def generate_id(route_id):
    global counter
    counter += 1
    return f"{route_id}_STN_{counter:04d}"
```
- **Expression:** `generate_id(!Route_ID!)`

---

### Step 24: Add Field (from_date) - Station Points
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%base_name_station_points%`
- **Field Name:** `from_date`
- **Field Type:** `DATE`

---

### Step 25: Add Field (to_date) - Station Points
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%base_name_station_points%`
- **Field Name:** `to_date`
- **Field Type:** `DATE`
- **Field Is Nullable:** `NULLABLE`

---

### Step 26: Calculate Field (from_date) - Station Points
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%base_name_station_points%`
- **Field Name:** `from_date`
- **Expression Type:** `Python 3`
- **Expression:** `datetime.datetime.now()`

---

### Step 27: Calculate Field (to_date) - Station Points
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%base_name_station_points%`
- **Field Name:** `to_date`
- **Expression Type:** `Python 3`
- **Expression:** `None`

---

## PHASE 5: Locate Features Along Routes

### Step 28: Select Layer By Attribute (Active Routes Only)
**Tool:** `Data Management Tools > Layers and Table Views > Select Layer By Attribute`

**Parameters:**
- **Input Layer:** `%base_name_route%`
- **Selection Type:** `NEW_SELECTION`
- **Where Clause:** `to_date IS NULL`

**Purpose:** Ensure Locate Features only uses the currently active route version

**Output Variable:** `active_route_layer`

---

### Step 29: Select Layer By Attribute (Active Station Points)
**Tool:** `Data Management Tools > Layers and Table Views > Select Layer By Attribute`

**Parameters:**
- **Input Layer:** `%base_name_station_points%`
- **Selection Type:** `NEW_SELECTION`
- **Where Clause:** `to_date IS NULL`

**Output Variable:** `active_station_points_layer`

---

### Step 30: Locate Features Along Routes
**Tool:** `Linear Referencing Tools > Locate Features Along Routes`

**Parameters:**
- **Input Features:** `%active_station_points_layer%`
- **Input Route Features:** `%active_route_layer%`
- **Route Identifier Field:** `Route_ID`
- **Radius or Tolerance:** `10 Meters` (adjust as needed)
- **Output Event Table:** `%output_gdb%\%base_name%_station_events`
- **Output Event Properties:** `Route_ID POINT MEAS`
- **Route Location Fields:** `DISTANCE` and `NO_ANGLE` and `NORMAL`
- **Keep only closest route location:** `FIRST`
- **Include distance field:** `DISTANCE`
- **Zero length events:** `ZERO`
- **Generate a unique event ID:** `NO_EVENT_ID`

**Output Variable:** `station_events`

---

## PHASE 6: Calculate Chainage

### Step 31: Add Field (Chainage)
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%station_events%`
- **Field Name:** `Chainage`
- **Field Type:** `TEXT`
- **Field Length:** `20`

---

### Step 32: Calculate Field (Chainage)
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%station_events%`
- **Field Name:** `Chainage`
- **Expression Type:** `Python 3`
- **Code Block:**
```python
def format_chainage(meas):
    km = int(meas / 1000)
    m = meas % 1000
    return f"{km:03d}+{m:06.2f}"
```
- **Expression:** `format_chainage(!MEAS!)`

**Purpose:** Convert measure to chainage format (e.g., "001+234.56")

---

## PHASE 7: Join Chainage Back to Points with Temporal Fields

### Step 33: Add Field (from_date) - Station Events
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%station_events%`
- **Field Name:** `from_date`
- **Field Type:** `DATE`

---

### Step 34: Add Field (to_date) - Station Events
**Tool:** `Data Management Tools > Fields > Add Field`

**Parameters:**
- **Input Table:** `%station_events%`
- **Field Name:** `to_date`
- **Field Type:** `DATE`
- **Field Is Nullable:** `NULLABLE`

---

### Step 35: Calculate Field (from_date) - Station Events
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%station_events%`
- **Field Name:** `from_date`
- **Expression Type:** `Python 3`
- **Expression:** `datetime.datetime.now()`

---

### Step 36: Calculate Field (to_date) - Station Events
**Tool:** `Data Management Tools > Fields > Calculate Field`

**Parameters:**
- **Input Table:** `%station_events%`
- **Field Name:** `to_date`
- **Expression Type:** `Python 3`
- **Expression:** `None`

---

### Step 37: Join Field
**Tool:** `Data Management Tools > Joins and Relates > Join Field`

**Parameters:**
- **Input Table:** `%base_name_station_points%`
- **Input Join Field:** `StationID`
- **Join Table:** `%station_events%`
- **Join Table Field:** `StationID`
- **Transfer Fields:** 
  - `MEAS`
  - `Chainage`
  - `from_date`
  - `to_date`

**Purpose:** Add measure and chainage values back to the station point features

---

## Final Outputs

After completing all phases, you will have:

1. **`%base_name%_route`** - Versioned route feature class with M-values and temporal tracking
   - Fields: `Route_ID`, `FromM`, `ToM`, `from_date`, `to_date`, `Shape`

2. **`%base_name%_station_points`** - Station points with chainage and temporal tracking
   - Fields: `StationID`, `Route_ID`, `MEAS`, `Chainage`, `from_date`, `to_date`, `Shape`

3. **`%base_name%_station_events`** - Event table for station measures
   - Fields: `Route_ID`, `StationID`, `MEAS`, `Chainage`, `from_date`, `to_date`

---

## Temporal Versioning Logic

### Active Records
- Records where `to_date IS NULL` are currently active
- Each new route/point creation sets `from_date = now()` and `to_date = NULL`

### Historical Records
- When creating a new version, old records are retired by setting `to_date = now()`
- Historical records remain in the database for audit trails

### Query Examples

**Get current active route:**
```sql
SELECT * FROM base_name_route 
WHERE to_date IS NULL AND Route_ID = 'ROUTE_01'
```

**Get route history:**
```sql
SELECT * FROM base_name_route 
WHERE Route_ID = 'ROUTE_01' 
ORDER BY from_date DESC
```

**Get route valid at specific date:**
```sql
SELECT * FROM base_name_route 
WHERE Route_ID = 'ROUTE_01' 
  AND from_date <= '2024-03-15' 
  AND (to_date > '2024-03-15' OR to_date IS NULL)
```

---

## Model Builder Tips

### Preconditions
Use preconditions to control execution flow:
- Make Step 15 (retire old routes) a precondition for Step 9 (create new route)
- Make Phase 3 (trimming) conditional on `%end_measure% > 0`

### Variables
Create derived variables for:
- `active_route_layer` (output from Step 28)
- `active_station_points_layer` (output from Step 29)

### Error Handling
Add validation:
- Check if `%route_id_value%` already exists before creating
- Verify `%station_interval%` is positive
- Ensure `%end_measure%` > `%start_measure%` if provided

### Performance
- Build spatial indexes after creating feature classes
- Use appropriate spatial references
- Consider batch processing for multiple routes

---

## Workflow Sequence Correction

**CRITICAL:** The retirement step (Step 14-15) should occur BEFORE route creation (Step 9). 

### Corrected Order for Phase 2:
1. Steps 1-8 (Prepare the route)
2. **Step 14:** Select existing active routes
3. **Step 15:** Retire old routes (set `to_date`)
4. **Step 9:** Create new route
5. Steps 10-13 (Add temporal fields to new route)
6. Step 16 (Cleanup)

This ensures only one active version exists at any time.

---

## Maintenance Queries

### Find Orphaned Records
```sql
-- Records that should be retired but aren't
SELECT * FROM base_name_route 
WHERE to_date IS NULL 
GROUP BY Route_ID 
HAVING COUNT(*) > 1
```

### Audit Trail Report
```sql
SELECT Route_ID, from_date, to_date, 
       DATEDIFF(day, from_date, COALESCE(to_date, GETDATE())) AS days_active
FROM base_name_route 
ORDER BY Route_ID, from_date DESC
```

---

## Next Steps

1. Build the model in ArcGIS Pro Model Builder
2. Set up model parameters for reusability
3. Test with sample data
4. Document any custom modifications
5. Export as Python script for automation
6. Schedule for periodic updates if needed

---

## Additional Resources

- **ArcGIS Pro Documentation:** Linear Referencing Tools
- **Best Practices:** LRS Network Management
- **Temporal Data:** Managing Time-Enabled Data
- **Python Integration:** arcpy.lr module reference

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-01  
**Workflow Compatibility:** ArcGIS Pro 3.x
