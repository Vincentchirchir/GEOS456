"""
===============================================================================
GEOS456 Final Project: Wildlife Corridor Analysis for Kananaskis Country
===============================================================================
Author: Vincent Chirchir
Student ID: [Your Student ID]
Date: April 7, 2026

Purpose:
    This script identifies optimal wildlife corridors connecting bear habitat 
    patches in Kananaskis Country using cost-surface analysis.
    
    The analysis considers:
    - Terrain (slope) - bears prefer gentler slopes
    - Land cover types - bears prefer forests over developed areas
    - Proximity to water (hydrology) - bears need water sources
    - Proximity to roads (avoid) - minimize human interaction
    - Proximity to trails (avoid) - minimize human interaction

Workflow:
    1. Create geodatabase for storing all outputs
    2. Clip all input data to park boundary
    3. Create 5 cost surfaces (terrain, landcover, hydrology, roads, trails)
    4. Combine cost surfaces using weighted sum
    5. Calculate least-cost paths between habitat patches
    6. Generate statistics and final map

Outputs:
    - KananaskisWildlife.gdb (geodatabase with all final data)
    - GEOS456_FP_Chirchir_Vincent.pdf (map layout)
    - Statistics (elevation, landcover areas, route length, etc.)

References:
    - ArcGIS Pro Documentation: https://pro.arcgis.com/
    - Cost Distance Analysis: https://pro.arcgis.com/en/pro-app/tool-reference/spatial-analyst/
    
===============================================================================
"""

#cell2
# Print header to show script has started
print("=" * 70)
print("GEOS456 FINAL PROJECT: WILDLIFE CORRIDOR ANALYSIS")
print("=" * 70)
print(f"Author: Vincent Chirchir")
print(f"Date: April 7, 2026\n")


# Import the main ArcPy library - this provides all ArcGIS functionality
import arcpy

# Import os library - used for working with file paths and directories
import os

# Import Spatial Analyst extension - required for raster analysis (cost surfaces, slope, etc.)
from arcpy.sa import *

# Import datetime - used for timestamps in log messages
from datetime import datetime

# Import matplotlib for creating visualizations of our maps
import matplotlib.pyplot as plt

# Import Polygon from matplotlib - used to draw polygon shapes on maps
from matplotlib.patches import Polygon as MPLPolygon

# Import LineCollection - used to draw multiple lines (roads, trails, routes) efficiently
from matplotlib.collections import LineCollection

# Import patches - used to create legend items in matplotlib
import matplotlib.patches as mpatches

# Check if Spatial Analyst extension is available (required for cost surface analysis)
if arcpy.CheckExtension("Spatial") == "Available":
    # If available, check it out (like checking out a library book)
    arcpy.CheckOutExtension("Spatial")
    print("✓ Spatial Analyst extension checked out")
else:
    # If not available, print error and stop
    print("✗ ERROR: Spatial Analyst extension not available!")
    
# Confirm all libraries loaded successfully
print("✓ All libraries imported successfully")

#cell3
# Create a configuration class to store all settings in one place
# This makes it easy to change settings without searching through code
class Config:
    """
    Configuration settings for the wildlife corridor analysis.
    All paths, spatial settings, and student info stored here.
    """
    
    # =========================================================================
    # PATHS - Define where data is located and where outputs will be saved
    # =========================================================================
    
    # Main workspace folder - contains all input data folders
    WORKSPACE = r"C:\GEOS456\FinalProject"
    
    # Name of the output geodatabase (will be created in workspace)
    GDB_NAME = "KananaskisWildlife"
    
    # =========================================================================
    # SPATIAL SETTINGS - Define coordinate system and raster cell size
    # =========================================================================
    
    # Spatial reference for all outputs - NAD83 UTM Zone 11N
    # This is appropriate for Kananaskis Country area in Alberta
    SPATIAL_REF = arcpy.SpatialReference("NAD 1983 UTM Zone 11N")
    
    # Cell size for all raster outputs in meters
    # 25m is fine enough to capture terrain detail but not too large for processing
    CELL_SIZE = 25
    
    # =========================================================================
    # STUDENT INFORMATION - Used for naming output PDF map
    # =========================================================================
    
    # Student last name - used in PDF filename
    STUDENT_LAST = "Chirchir"
    
    # Student first name - used in PDF filename
    STUDENT_FIRST = "Vincent"

# =========================================================================
# SET ARCPY ENVIRONMENT VARIABLES
# =========================================================================

# Allow ArcPy to overwrite existing files without asking
# Without this, script would fail if output already exists
arcpy.env.overwriteOutput = True

# Set the output coordinate system for all new datasets
# This ensures everything is in the same projection (UTM Zone 11N)
arcpy.env.outputCoordinateSystem = Config.SPATIAL_REF

# Set the cell size for all raster operations
# This ensures consistent resolution across all cost surfaces
arcpy.env.cellSize = Config.CELL_SIZE

# Set the default workspace where ArcPy looks for data
arcpy.env.workspace = Config.WORKSPACE

# Print configuration summary so user can verify settings
print("Configuration:")
print(f"  Workspace: {Config.WORKSPACE}")
print(f"  Geodatabase: {Config.GDB_NAME}.gdb")
print(f"  Spatial Reference: {Config.SPATIAL_REF.name}")
print(f"  Cell Size: {Config.CELL_SIZE}m")
print(f"  Student: {Config.STUDENT_FIRST} {Config.STUDENT_LAST}")

#cell4
# =========================================================================
# HELPER FUNCTIONS - Reusable utility functions used throughout notebook
# =========================================================================

def print_header(message, char="="):
    """
    Print a formatted section header to organize output.
    
    Parameters:
        message (str): The text to display in the header
        char (str): The character to use for the border (default: =)
    
    Example:
        print_header("Step 1: Setup")
        Outputs:
        ======================================================================
                              STEP 1: SETUP
        ======================================================================
    """
    # Set width of header (70 characters)
    width = 70
    
    # Print top border (70 equals signs or whatever char is specified)
    print(f"\n{char * width}")
    
    # Print message centered within the 70-character width
    # .upper() converts message to uppercase
    # .center(width) adds spaces to center the text
    print(f"{message.upper().center(width)}")
    
    # Print bottom border
    print(f"{char * width}\n")


def log_message(message, level="INFO"):
    """
    Print a timestamped log message.
    Helps track what's happening and when during script execution.
    
    Parameters:
        message (str): The message to log
        level (str): The log level (INFO, SUCCESS, ERROR, WARNING)
    
    Example:
        log_message("Processing complete", "SUCCESS")
        Outputs: [19:45:32] [SUCCESS] Processing complete
    """
    # Get current time in HH:MM:SS format
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Print formatted message with timestamp and level
    print(f"[{timestamp}] [{level}] {message}")


def get_feature_count(feature_class):
    """
    Get the number of features in a feature class or table.
    
    Parameters:
        feature_class (str): Path to the feature class
    
    Returns:
        int: Number of features, or 0 if there's an error
    
    Example:
        count = get_feature_count("C:/data/roads.shp")
        print(f"Roads has {count} features")
    """
    try:
        # Use GetCount tool to count features
        # [0] gets the first (and only) output value
        # int() converts the result from string to integer
        return int(arcpy.management.GetCount(feature_class)[0])
    except:
        # If anything goes wrong (file doesn't exist, etc.), return 0
        return 0

# Confirm helper functions are loaded
print("✓ Helper functions loaded")

#cell5
def visualize_map(gdb_path, layers_to_show, title="Map View"):
    """
    Create a matplotlib visualization of GIS layers and display in notebook.
    
    This function reads feature classes from the geodatabase and draws them
    on a matplotlib figure with appropriate colors and styles.
    
    Parameters:
        gdb_path (str): Path to the geodatabase containing layers
        layers_to_show (list): List of layer names to display (e.g., ['park_boundary', 'roads'])
        title (str): Title for the map
    
    Example:
        visualize_map(gdb_path, ['park_boundary', 'habitats'], "Study Area")
    """
    
    # Print a separator and title
    print(f"\n{'─' * 70}")
    print(f"📍 {title}")
    print(f"{'─' * 70}")
    
    # Create a new matplotlib figure with specified size (14 inches wide, 10 inches tall)
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # =========================================================================
    # DEFINE COLORS AND STYLES FOR EACH LAYER TYPE
    # =========================================================================
    # Dictionary mapping layer names to their display styles
    styles = {
        # Park boundary: light gray fill, black outline, semi-transparent
        'park_boundary': {
            'facecolor': '#E8E8E8',      # Light gray fill color
            'edgecolor': 'black',         # Black border
            'linewidth': 2.5,             # Thick border (2.5 points)
            'alpha': 0.6                  # 60% opaque (semi-transparent)
        },
        
        # Roads: gray lines
        'roads': {
            'color': '#666666',           # Medium gray
            'linewidth': 0.8              # Thin lines
        },
        
        # Trails: brown dashed lines
        'trails': {
            'color': '#8B4513',           # Brown color
            'linewidth': 0.6,             # Very thin lines
            'linestyle': '--'             # Dashed line style
        },
        
        # Hydrology: blue lines (represents water)
        'hydrology': {
            'color': '#1E90FF',           # Dodger blue
            'linewidth': 1.2              # Medium thickness
        },
        
        # Habitats: light green fill, dark green outline
        'habitats': {
            'facecolor': '#90EE90',       # Light green fill
            'edgecolor': '#228B22',       # Forest green outline
            'linewidth': 2,               # Thick outline
            'alpha': 0.7                  # 70% opaque
        },
        
        # Optimal routes: thick red lines (most important - stands out)
        'optimal_routes': {
            'color': '#FF0000',           # Pure red
            'linewidth': 3                # Very thick lines
        },
    }
    
    # List to store legend elements (will be added to legend later)
    legend_elements = []
    
    # =========================================================================
    # LOOP THROUGH EACH LAYER AND DRAW IT
    # =========================================================================
    for layer_name in layers_to_show:
        
        # Build full path to the layer in the geodatabase
        layer_path = os.path.join(gdb_path, layer_name)
        
        # Check if layer exists - if not, skip it
        if not arcpy.Exists(layer_path):
            continue  # Skip to next layer
        
        # Get layer information (shape type, spatial reference, etc.)
        desc = arcpy.Describe(layer_path)
        
        # Get the style for this layer from the styles dictionary
        # If layer not in dictionary, use empty dict (will use defaults)
        style = styles.get(layer_name, {})
        
        # Count features in this layer
        count = get_feature_count(layer_path)
        
        # Print progress message
        print(f"  → {layer_name} ({count} features)")
        
        # =====================================================================
        # DRAW POLYGONS (e.g., park boundary, habitats)
        # =====================================================================
        if desc.shapeType == "Polygon":
            
            # Open a cursor to read each feature's geometry
            with arcpy.da.SearchCursor(layer_path, ["SHAPE@"]) as cursor:
                
                # Loop through each polygon feature
                for row in cursor:
                    polygon = row[0]  # Get the polygon geometry
                    
                    # Make sure polygon is not None
                    if polygon:
                        
                        # Polygons can have multiple parts (e.g., islands)
                        # Loop through each part
                        for part in range(polygon.partCount):
                            
                            # Get the array of points for this part
                            # Convert each point to (X, Y) tuple
                            # Filter out None points (can occur at part boundaries)
                            coords = [(pt.X, pt.Y) for pt in polygon.getPart(part) if pt]
                            
                            # Need at least 3 points to make a polygon
                            if len(coords) >= 3:
                                
                                # Create a matplotlib Polygon object
                                poly = MPLPolygon(
                                    coords,                           # List of (X, Y) coordinates
                                    facecolor=style.get('facecolor', 'lightgray'),  # Fill color
                                    edgecolor=style.get('edgecolor', 'black'),      # Border color
                                    linewidth=style.get('linewidth', 1),            # Border thickness
                                    alpha=style.get('alpha', 0.5)                   # Transparency
                                )
                                
                                # Add the polygon to the map
                                ax.add_patch(poly)
            
            # Add this layer to the legend
            legend_elements.append(
                mpatches.Patch(
                    facecolor=style.get('facecolor', 'lightgray'),
                    edgecolor=style.get('edgecolor', 'black'),
                    label=layer_name.replace('_', ' ').title()  # Format name nicely
                )
            )
        
        # =====================================================================
        # DRAW LINES (e.g., roads, trails, routes)
        # =====================================================================
        elif desc.shapeType == "Polyline":
            
            # List to store all line segments
            lines = []
            
            # Open cursor to read polyline geometries
            with arcpy.da.SearchCursor(layer_path, ["SHAPE@"]) as cursor:
                
                # Loop through each polyline feature
                for row in cursor:
                    polyline = row[0]  # Get the polyline geometry
                    
                    # Make sure polyline is not None
                    if polyline:
                        
                        # Polylines can have multiple parts (disconnected segments)
                        for part in range(polyline.partCount):
                            
                            # Get coordinates of points along the line
                            coords = [(pt.X, pt.Y) for pt in polyline.getPart(part) if pt]
                            
                            # Need at least 2 points to make a line
                            if len(coords) >= 2:
                                lines.append(coords)  # Add to lines list
            
            # If we have any lines, draw them all at once (more efficient)
            if lines:
                
                # Create a LineCollection (draws multiple lines efficiently)
                lc = LineCollection(
                    lines,                                  # List of line coordinate arrays
                    colors=style.get('color', 'black'),     # Line color
                    linewidths=style.get('linewidth', 1),   # Line thickness
                    linestyles=style.get('linestyle', 'solid')  # Line style (solid, dashed, etc.)
                )
                
                # Add all lines to the map at once
                ax.add_collection(lc)
                
                # Add this layer to the legend
                legend_elements.append(
                    mpatches.Patch(
                        color=style.get('color', 'black'),
                        label=layer_name.replace('_', ' ').title()
                    )
                )
    
    # =========================================================================
    # SET MAP EXTENT (zoom level)
    # =========================================================================
    # Use park boundary to determine map extent (how much area to show)
    park_path = os.path.join(gdb_path, 'park_boundary')
    
    if arcpy.Exists(park_path):
        # Get the extent (bounding box) of the park boundary
        extent = arcpy.Describe(park_path).extent
        
        # Add a small buffer (2% of width/height) around the extent
        # This prevents features from being cut off at the edges
        buffer = 0.02
        x_buf = (extent.XMax - extent.XMin) * buffer
        y_buf = (extent.YMax - extent.YMin) * buffer
        
        # Set the X-axis limits (Easting coordinates)
        ax.set_xlim(extent.XMin - x_buf, extent.XMax + x_buf)
        
        # Set the Y-axis limits (Northing coordinates)
        ax.set_ylim(extent.YMin - y_buf, extent.YMax + y_buf)
    
    # =========================================================================
    # FORMAT THE MAP
    # =========================================================================
    
    # Keep aspect ratio equal (1 meter on X = 1 meter on Y)
    # This prevents distortion
    ax.set_aspect('equal')
    
    # Set the title at the top of the map
    ax.set_title(title, fontsize=18, fontweight='bold', pad=15)
    
    # Label the X-axis (Easting in meters)
    ax.set_xlabel('Easting (m)', fontsize=12)
    
    # Label the Y-axis (Northing in meters)
    ax.set_ylabel('Northing (m)', fontsize=12)
    
    # Format tick labels to show full numbers (not scientific notation)
    ax.ticklabel_format(style='plain', useOffset=False)
    
    # Add a grid for easier reading of coordinates
    ax.grid(True, alpha=0.3, linestyle='--')  # Semi-transparent dashed grid
    
    # =========================================================================
    # ADD LEGEND
    # =========================================================================
    if legend_elements:
        # Add legend in upper right corner
        ax.legend(
            handles=legend_elements,   # Legend items we created
            loc='upper right',          # Position
            fontsize=10,                # Text size
            framealpha=0.9              # Slightly transparent background
        )
    
    # =========================================================================
    # ADD NORTH ARROW
    # =========================================================================
    # Simple north arrow in upper right
    ax.text(
        0.97, 0.97,                     # Position (97% across, 97% up)
        'N',                            # Text to display
        transform=ax.transAxes,         # Use axes coordinates (0-1 instead of data coordinates)
        fontsize=20,                    # Large text
        fontweight='bold',              # Bold text
        ha='center',                    # Horizontal alignment: center
        va='top',                       # Vertical alignment: top
        bbox=dict(                      # Box around the N
            boxstyle='circle',          # Circular box
            facecolor='white',          # White background
            edgecolor='black',          # Black border
            linewidth=2                 # Thick border
        )
    )
    
    # =========================================================================
    # FINALIZE AND DISPLAY
    # =========================================================================
    
    # Adjust spacing to prevent labels from being cut off
    plt.tight_layout()
    
    # Display the map in the notebook
    plt.show()
    
    # =========================================================================
    # SAVE TO FILE
    # =========================================================================
    
    # Create filename from title (replace spaces with underscores, make lowercase)
    filename = f"{title.replace(' ', '_').lower()}.png"
    
    # Full path to save the image
    filepath = os.path.join(Config.WORKSPACE, filename)
    
    # Save the figure as a PNG file
    # dpi=300 means high resolution (300 dots per inch - good for printing)
    # bbox_inches='tight' removes extra white space around the edges
    # facecolor='white' makes the background white (not transparent)
    fig.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    
    # Print confirmation message
    print(f"  ✓ Saved: {filename}\n")

# Confirm visualization function is loaded
print("✓ Visualization function loaded")

#cell6
# =========================================================================
# STEP 1: CREATE OUTPUT GEODATABASE
# =========================================================================
# A geodatabase is a container that stores all our GIS data in one place
# It's more efficient and organized than using individual shapefiles

# Print a formatted header to show we're starting Step 1
print_header("Step 1: Create Geodatabase")

# Build the full path to the geodatabase
# os.path.join() combines the workspace path with the geodatabase name
# This creates: "C:\GEOS456\FinalProject\KananaskisWildlife.gdb"
gdb_path = os.path.join(Config.WORKSPACE, f"{Config.GDB_NAME}.gdb")

# =========================================================================
# DELETE EXISTING GEODATABASE IF IT EXISTS
# =========================================================================
# Check if a geodatabase with this name already exists
if arcpy.Exists(gdb_path):
    # If it exists, log a message
    log_message(f"Deleting existing {Config.GDB_NAME}.gdb")
    
    # Delete the old geodatabase so we can create a fresh one
    # This prevents errors from old/corrupted data
    arcpy.management.Delete(gdb_path)

# =========================================================================
# CREATE NEW GEODATABASE
# =========================================================================
# Log that we're creating the geodatabase
log_message(f"Creating {Config.GDB_NAME}.gdb")

# Create a new file geodatabase
# Parameters:
#   1. Config.WORKSPACE - where to create it (the folder)
#   2. Config.GDB_NAME - what to name it
arcpy.management.CreateFileGDB(Config.WORKSPACE, Config.GDB_NAME)

# Log success message with the full path
log_message(f"✓ Geodatabase created: {gdb_path}", "SUCCESS")

#cell 7
# =========================================================================
# STEP 2: SETUP PARK BOUNDARY
# =========================================================================
# The park boundary defines our study area
# All other data will be clipped to this boundary
# We need to project it to the correct coordinate system first

# Print header for this step
print_header("Step 2: Setup Park Boundary")

# =========================================================================
# DEFINE INPUT AND OUTPUT PATHS
# =========================================================================

# Path to the input park boundary shapefile
# This is in the Kananaskis subfolder of our workspace
park_input = os.path.join(Config.WORKSPACE, "Kananaskis", "Kcountry_bound.shp")

# Path where we'll save the projected park boundary in the geodatabase
park_boundary_gdb = os.path.join(gdb_path, "park_boundary")

# =========================================================================
# PROJECT TO CORRECT COORDINATE SYSTEM
# =========================================================================
# The input shapefile might be in a different coordinate system
# We need to project it to NAD83 UTM Zone 11N

# Log what we're doing
log_message("Projecting park boundary to UTM Zone 11N...")

# Project the park boundary
# Parameters:
#   1. park_input - the input shapefile
#   2. park_boundary_gdb - where to save the output
#   3. Config.SPATIAL_REF - the target coordinate system (UTM Zone 11N)
arcpy.management.Project(park_input, park_boundary_gdb, Config.SPATIAL_REF)

# =========================================================================
# VERIFY AND LOG RESULTS
# =========================================================================

# Count how many features are in the park boundary
# Should be 1 (one polygon representing the park)
count = get_feature_count(park_boundary_gdb)

# Log success with the feature count
log_message(f"✓ Park boundary ready ({count} feature)", "SUCCESS")

# =========================================================================
# VISUALIZE THE PARK BOUNDARY
# =========================================================================
# Display the park boundary on a map so we can see our study area

# Call the visualization function
# Parameters:
#   1. gdb_path - where to find the data
#   2. ['park_boundary'] - list of layers to show (just park boundary for now)
#   3. "Step 2 - Park Boundary" - title for the map
visualize_map(gdb_path, ['park_boundary'], "Step 2 - Park Boundary")

#cell 8
# =========================================================================
# STEP 3: CLIP VECTOR DATA TO PARK BOUNDARY
# =========================================================================
# We need to clip all input datasets to the park boundary
# This ensures we only analyze data within Kananaskis Country
# Clipping also makes processing faster (smaller datasets)

# Print header for this step
print_header("Step 3: Clip Vector Data to Park Boundary")

# =========================================================================
# DEFINE ALL INPUT VECTOR DATASETS
# =========================================================================
# Create a dictionary mapping output names to input file paths
# Dictionary format: 'output_name': 'input_file_path'

vector_inputs = {
    # Roads - transportation network
    'roads': os.path.join(Config.WORKSPACE, "Kananaskis", "Road.shp"),
    
    # Trails - hiking trails (bears avoid these)
    'trails': os.path.join(Config.WORKSPACE, "Kananaskis", "Trails.shp"),
    
    # Hydrology - water features (rivers, streams, lakes)
    'hydrology': os.path.join(Config.WORKSPACE, "Kananaskis", "Hydro.shp"),
    
    # Habitats - bear habitat patches (what we're connecting)
    'habitats': os.path.join(Config.WORKSPACE, "Wildlife", "Bear_Habitat.shp"),
    
    # ESA - Environmentally Significant Areas
    'esa': os.path.join(Config.WORKSPACE, "Kananaskis", "ESA.shp"),
    
    # Townships - Alberta Township System grid (for reference)
    'townships': os.path.join(Config.WORKSPACE, "ATS", "AB_Township.shp"),
    
    # NTS Sheets - National Topographic System map sheets (for reference)
    'nts_sheets': os.path.join(Config.WORKSPACE, "NTS", "NTS50.shp")
}

# =========================================================================
# CLIP EACH DATASET
# =========================================================================
# Loop through each dataset and clip it to the park boundary

# .items() gives us both the name and path for each dataset
for name, input_path in vector_inputs.items():
    
    # Log which dataset we're processing
    log_message(f"Processing {name}...")
    
    # ---------------------------------------------------------------------
    # DEFINE TEMPORARY AND FINAL OUTPUT PATHS
    # ---------------------------------------------------------------------
    
    # Temporary file for the projected (but not yet clipped) data
    # We'll delete this after clipping
    temp_proj = os.path.join(gdb_path, f"{name}_temp")
    
    # Final output path in the geodatabase
    output_fc = os.path.join(gdb_path, name)
    
    # ---------------------------------------------------------------------
    # STEP 1: PROJECT TO CORRECT COORDINATE SYSTEM
    # ---------------------------------------------------------------------
    # Input files might be in different coordinate systems
    # Project them all to UTM Zone 11N first
    
    arcpy.management.Project(
        input_path,              # Input shapefile
        temp_proj,               # Temporary output (projected)
        Config.SPATIAL_REF       # Target coordinate system
    )
    
    # ---------------------------------------------------------------------
    # STEP 2: CLIP TO PARK BOUNDARY
    # ---------------------------------------------------------------------
    # Now clip the projected data to the park boundary
    # This removes everything outside the park
    
    arcpy.analysis.Clip(
        temp_proj,               # Input (projected data)
        park_boundary_gdb,       # Clip feature (park boundary)
        output_fc                # Output (clipped data in geodatabase)
    )
    
    # ---------------------------------------------------------------------
    # STEP 3: DELETE TEMPORARY FILE
    # ---------------------------------------------------------------------
    # We don't need the temporary projected file anymore
    # Delete it to save disk space and keep geodatabase clean
    
    arcpy.management.Delete(temp_proj)
    
    # ---------------------------------------------------------------------
    # VERIFY AND LOG RESULTS
    # ---------------------------------------------------------------------
    
    # Count how many features remain after clipping
    count = get_feature_count(output_fc)
    
    # Log success with feature count
    # This helps verify the clipping worked correctly
    log_message(f"  ✓ {name}: {count} features", "SUCCESS")

# Print blank line for spacing
print()

# Log that all vector clipping is complete
log_message("✓ All vector data clipped", "SUCCESS")

# =========================================================================
# VISUALIZE CLIPPED DATA
# =========================================================================
# Show a map with several clipped layers to verify results

visualize_map(
    gdb_path,                    # Where to find the data
    [                             # List of layers to display
        'park_boundary',          # The park boundary (for context)
        'roads',                  # Roads (gray lines)
        'trails',                 # Trails (brown dashed lines)
        'hydrology',              # Water features (blue lines)
        'habitats'                # Bear habitats (green polygons)
    ],
    "Step 3 - Clipped Vector Data"  # Map title
)

#cell 9
# =========================================================================
# STEP 4: CLIP DEM RASTER TO PARK BOUNDARY
# =========================================================================
# DEM = Digital Elevation Model (raster showing elevation/height)
# We need this to calculate slope (terrain ruggedness)
# Clipping process is different for rasters than for vectors

# Print header for this step
print_header("Step 4: Clip DEM Raster")

# =========================================================================
# DEFINE INPUT AND OUTPUT PATHS
# =========================================================================

# Path to input DEM raster (in the dem subfolder)
dem_input = os.path.join(Config.WORKSPACE, "dem", "ab_dem")

# Path where we'll save the clipped DEM in the geodatabase
dem_output = os.path.join(gdb_path, "dem")

# =========================================================================
# CLIP RASTER USING EXTRACT BY MASK
# =========================================================================
# For rasters, we use "Extract by Mask" instead of "Clip"
# This is a Spatial Analyst tool (which is why we needed the extension)

# Log what we're doing
log_message("Clipping DEM to park boundary...")

# Extract by Mask extracts raster cells that fall within the mask (park boundary)
# Parameters:
#   1. dem_input - the input raster to clip
#   2. park_boundary_gdb - the mask (park boundary polygon)
# Returns: a raster object in memory (not yet saved to disk)
dem_clipped = arcpy.sa.ExtractByMask(dem_input, park_boundary_gdb)

# Save the clipped raster to the geodatabase
# .save() writes the raster from memory to disk
dem_clipped.save(dem_output)

# Log success
log_message("✓ DEM clipped successfully", "SUCCESS")

# Note: We don't visualize the DEM here because it's a raster (elevation values)
# It would just show as a colored elevation map
# We'll use it to calculate slope in the next steps

#cell 10
# =========================================================================
# STEP 5: PROCESS LANDCOVER DATA
# =========================================================================
# Landcover is currently a shapefile (vector)
# We need to convert it to raster format for cost surface analysis
# Different landcover types have different costs for bear movement

# Print header for this step
print_header("Step 5: Process Landcover")

# =========================================================================
# DEFINE PATHS
# =========================================================================

# Input landcover shapefile
landcover_input = os.path.join(Config.WORKSPACE, "Landcover", "AB_Landcover.shp")

# Temporary clipped landcover (still vector)
landcover_vector = os.path.join(gdb_path, "landcover_vector")

# Final landcover raster output
landcover_output = os.path.join(gdb_path, "landcover")

# =========================================================================
# STEP 1: CLIP LANDCOVER SHAPEFILE
# =========================================================================
# First clip the landcover shapefile to the park boundary
# This removes landcover polygons outside the park

# Log what we're doing
log_message("Clipping landcover shapefile...")

# Clip the landcover shapefile
arcpy.analysis.Clip(
    landcover_input,         # Input landcover shapefile
    park_boundary_gdb,       # Clip feature (park boundary)
    landcover_vector         # Output clipped shapefile
)

# =========================================================================
# STEP 2: CHECK AVAILABLE FIELDS
# =========================================================================
# We need to know which field contains the landcover classification values
# Let's list all fields so we can identify the correct one

# Get list of all fields in the clipped landcover
fields = arcpy.ListFields(landcover_vector)

# Print header for field list
print("\n  Available fields:")

# Loop through fields and print their names and types
for field in fields:
    # Skip OID and Geometry fields (we don't need those)
    if field.type not in ['OID', 'Geometry']:
        # Print field name and type
        # Format: "    - FIELDNAME (Type)"
        print(f"    - {field.name} ({field.type})")

# =========================================================================
# STEP 3: CONVERT TO RASTER
# =========================================================================
# Now convert the vector landcover to raster format

# IMPORTANT: This field name might be different in your data!
# Look at the field list above and update this if needed
# Common field names: GRIDCODE, VALUE, CLASS, LANDCOVER
value_field = "GRIDCODE"  # ← UPDATE THIS if your field is named differently

# Log what we're doing
log_message(f"Converting to raster using field: {value_field}...")

# Convert feature class to raster
# This creates a raster where each cell has a landcover code
arcpy.conversion.FeatureToRaster(
    landcover_vector,        # Input: clipped landcover shapefile
    value_field,             # Field containing landcover codes
    landcover_output,        # Output: landcover raster
    Config.CELL_SIZE         # Cell size: 25 meters
)

# =========================================================================
# STEP 4: CLEANUP
# =========================================================================
# Delete the intermediate vector landcover (we only need the raster now)

arcpy.management.Delete(landcover_vector)

# Log success
log_message("✓ Landcover raster created", "SUCCESS")

# Note: We now have a raster where each 25m cell has a landcover code
# For example: 1 = forest, 2 = grassland, 10 = water, etc.
# We'll reclassify these codes to cost values in the next step

#cell 11
# =========================================================================
# STEP 6: CREATE COST SURFACES
# =========================================================================
# Cost surfaces represent how difficult it is for bears to travel through
# different areas. Lower cost = easier travel, Higher cost = harder travel
#
# We create 5 separate cost surfaces, then combine them:
#   1. Terrain (slope) - steep slopes are harder to traverse
#   2. Landcover - forests are preferred, developed areas avoided
#   3. Hydrology - bears need to stay near water
#   4. Roads - bears avoid roads (human activity)
#   5. Trails - bears avoid trails (human activity)

# Print header for this step
print_header("Step 6: Create Cost Surfaces")

# =========================================================================
# DEFINE PATHS TO CLIPPED DATA
# =========================================================================
# We'll use the clipped data we created in previous steps

dem_path = os.path.join(gdb_path, "dem")                 # Elevation raster
landcover_path = os.path.join(gdb_path, "landcover")     # Landcover raster
roads_path = os.path.join(gdb_path, "roads")             # Roads (vector)
trails_path = os.path.join(gdb_path, "trails")           # Trails (vector)
hydrology_path = os.path.join(gdb_path, "hydrology")     # Water features (vector)

# =========================================================================
# COST SURFACE 1: TERRAIN (from slope)
# =========================================================================
# Steeper slopes are harder for bears to traverse
# We calculate slope from the DEM, then rescale to 0-10

log_message("Creating terrain cost surface...")

# ---------------------------------------------------------------------
# Calculate slope in degrees from the DEM
# ---------------------------------------------------------------------
# Slope tool calculates the rate of elevation change
# "DEGREE" parameter means output is in degrees (0° = flat, 90° = vertical)
slope = arcpy.sa.Slope(dem_path, "DEGREE")

# Get the maximum slope value in the dataset
# .maximum is a property of the raster object
# We need this to know the range for rescaling
slope_max = float(slope.maximum)

# Print the max slope so user can see the terrain steepness
print(f"  Max slope: {slope_max:.1f}°")

# ---------------------------------------------------------------------
# Rescale slope to 0-10 cost scale
# ---------------------------------------------------------------------
# We want: flat areas (0°) = low cost (0), steep areas = high cost (10)
# TfLinear creates a linear transformation function

# Create transformation: input range (0 to slope_max) → output range (0 to 10)
transformation = arcpy.sa.TfLinear(
    0,              # Input minimum (0 degrees = flat)
    slope_max,      # Input maximum (steepest slope in our data)
    0,              # Output minimum (low cost for flat areas)
    10              # Output maximum (high cost for steep areas)
)

# Apply the transformation to rescale slope to 0-10
terrain_cost = arcpy.sa.RescaleByFunction(
    slope,              # Input raster (slope)
    transformation,     # Transformation function (linear 0-10)
    0,                  # Minimum input value
    slope_max           # Maximum input value
)

# Save the terrain cost surface to geodatabase
terrain_cost_path = os.path.join(gdb_path, "cost_terrain")
terrain_cost.save(terrain_cost_path)

# Log success
log_message("  ✓ Terrain cost created", "SUCCESS")

# =========================================================================
# COST SURFACE 2: LANDCOVER (reclassification)
# =========================================================================
# Different landcover types have different values for bears
# Forests = good (low cost), developed areas = bad (high cost)

log_message("Creating landcover cost surface...")

# ---------------------------------------------------------------------
# Define reclassification values
# ---------------------------------------------------------------------
# Dictionary mapping: original landcover code → cost value (1-10)
# Based on bear preferences:
#   - Forests (codes 1,2,3) = cost 1 (best - cover and food)
#   - Grassland (code 4) = cost 2 (good - open but safe)
#   - Shrubland (code 5) = cost 3 (moderate)
#   - Exposed/Rock (codes 6,7) = cost 6-7 (poor - no cover)
#   - Snow/Ice (code 8) = cost 8 (difficult to traverse)
#   - Agriculture (code 9) = cost 9 (human activity)
#   - Water/Developed (codes 10,11) = cost 10 (worst - can't traverse)

landcover_reclass = {
    1: 1,       # Coniferous Forest → cost 1 (best)
    2: 1,       # Broadleaf Forest → cost 1 (best)
    3: 1,       # Mixed Forest → cost 1 (best)
    4: 2,       # Grassland → cost 2
    5: 3,       # Shrubland → cost 3
    6: 6,       # Exposed Land → cost 6
    7: 7,       # Rock/Rubble → cost 7
    8: 8,       # Snow/Ice → cost 8
    9: 9,       # Agriculture → cost 9
    10: 10,     # Water → cost 10 (can't traverse)
    11: 10      # Developed → cost 10 (avoid humans)
}

# ---------------------------------------------------------------------
# Create remap object
# ---------------------------------------------------------------------
# RemapValue creates a lookup table for reclassification
# Convert dictionary to list of [old, new] pairs
remap = arcpy.sa.RemapValue([[k, v] for k, v in landcover_reclass.items()])

# ---------------------------------------------------------------------
# Reclassify the landcover raster
# ---------------------------------------------------------------------
# Reclassify tool changes cell values based on the remap table
landcover_cost = arcpy.sa.Reclassify(
    landcover_path,     # Input raster
    "Value",            # Field to reclassify (the cell values)
    remap,              # Remap table (old → new values)
    "NODATA"            # What to do with values not in remap (set to NoData)
)

# Save landcover cost surface
landcover_cost_path = os.path.join(gdb_path, "cost_landcover")
landcover_cost.save(landcover_cost_path)

# Log success
log_message("  ✓ Landcover cost created", "SUCCESS")

# =========================================================================
# COST SURFACE 3: HYDROLOGY PROXIMITY
# =========================================================================
# Bears need to stay near water sources
# Close to water = low cost, Far from water = high cost

log_message("Creating hydrology proximity cost surface...")

# ---------------------------------------------------------------------
# Set processing extent
# ---------------------------------------------------------------------
# Limit processing to park boundary area (speeds up processing)
arcpy.env.extent = park_boundary_gdb

# ---------------------------------------------------------------------
# Calculate distance to water features
# ---------------------------------------------------------------------
# DistanceAccumulation calculates distance from each cell to nearest water
# Result: raster where each cell value = distance to nearest water in meters
hydro_dist = arcpy.sa.DistanceAccumulation(hydrology_path)

# Get maximum distance value
# This tells us the farthest any point is from water
hydro_max = float(hydro_dist.maximum)

# Print max distance for reference
print(f"  Max distance to water: {hydro_max:.0f}m")

# ---------------------------------------------------------------------
# Rescale to 0-10 cost scale (INVERSE relationship)
# ---------------------------------------------------------------------
# We want: close to water = LOW cost, far from water = HIGH cost
# So we use an INVERSE transformation

# Create transformation: far (hydro_max) → 0, close (0) → 10
# Then we'll flip it so close = 0, far = 10
transformation = arcpy.sa.TfLinear(
    hydro_max,      # Input minimum (far from water)
    0,              # Input maximum (close to water)
    0,              # Output minimum (low cost)
    10              # Output maximum (high cost)
)

# Apply transformation
hydro_cost = arcpy.sa.RescaleByFunction(
    hydro_dist,         # Input (distance to water)
    transformation,     # Transformation (inverse relationship)
    0,                  # Min input
    hydro_max           # Max input
)

# Save hydrology cost surface
hydro_cost_path = os.path.join(gdb_path, "cost_hydrology")
hydro_cost.save(hydro_cost_path)

# Log success
log_message("  ✓ Hydrology cost created", "SUCCESS")

# =========================================================================
# COST SURFACE 4: ROADS PROXIMITY
# =========================================================================
# Bears avoid roads due to vehicle traffic and human activity
# Close to roads = HIGH cost, Far from roads = LOW cost

log_message("Creating roads proximity cost surface...")

# Calculate distance to roads
roads_dist = arcpy.sa.DistanceAccumulation(roads_path)

# Get maximum distance
roads_max = float(roads_dist.maximum)
print(f"  Max distance to roads: {roads_max:.0f}m")

# ---------------------------------------------------------------------
# Rescale to 0-10 cost scale (DIRECT relationship)
# ---------------------------------------------------------------------
# Close to roads = HIGH cost (10), Far from roads = LOW cost (0)

transformation = arcpy.sa.TfLinear(
    0,              # Input minimum (close to roads)
    roads_max,      # Input maximum (far from roads)
    10,             # Output minimum (high cost when close)
    0               # Output maximum (low cost when far)
)

# Apply transformation
roads_cost = arcpy.sa.RescaleByFunction(roads_dist, transformation, 0, roads_max)

# Save roads cost surface
roads_cost_path = os.path.join(gdb_path, "cost_roads")
roads_cost.save(roads_cost_path)

log_message("  ✓ Roads cost created", "SUCCESS")

# =========================================================================
# COST SURFACE 5: TRAILS PROXIMITY
# =========================================================================
# Bears avoid trails due to hikers and human activity
# Close to trails = HIGH cost, Far from trails = LOW cost

log_message("Creating trails proximity cost surface...")

# Calculate distance to trails
trails_dist = arcpy.sa.DistanceAccumulation(trails_path)

# Get maximum distance
trails_max = float(trails_dist.maximum)
print(f"  Max distance to trails: {trails_max:.0f}m")

# Rescale (same logic as roads)
transformation = arcpy.sa.TfLinear(0, trails_max, 10, 0)
trails_cost = arcpy.sa.RescaleByFunction(trails_dist, transformation, 0, trails_max)

# Save trails cost surface
trails_cost_path = os.path.join(gdb_path, "cost_trails")
trails_cost.save(trails_cost_path)

log_message("  ✓ Trails cost created", "SUCCESS")

# =========================================================================
# COMBINE ALL 5 COST SURFACES
# =========================================================================
# Use weighted sum to combine all cost surfaces into one
# All weights = 1 (equal importance) per assignment requirements

log_message("Combining all cost surfaces...")

# ---------------------------------------------------------------------
# Create weighted sum table
# ---------------------------------------------------------------------
# WSTable defines which rasters to combine and their weights
# Format: [[raster_path, "VALUE", weight], ...]
ws_table = arcpy.sa.WSTable([
    [terrain_cost_path, "VALUE", 1],      # Terrain cost, weight = 1
    [landcover_cost_path, "VALUE", 1],    # Landcover cost, weight = 1
    [hydro_cost_path, "VALUE", 1],        # Hydrology cost, weight = 1
    [roads_cost_path, "VALUE", 1],        # Roads cost, weight = 1
    [trails_cost_path, "VALUE", 1]        # Trails cost, weight = 1
])

# ---------------------------------------------------------------------
# Perform weighted sum
# ---------------------------------------------------------------------
# WeightedSum adds all cost surfaces together
# Each cell in output = (terrain*1 + landcover*1 + hydro*1 + roads*1 + trails*1) / 5
combined_cost = arcpy.sa.WeightedSum(ws_table)

# Save combined cost surface
combined_cost_path = os.path.join(gdb_path, "cost_combined")
combined_cost.save(combined_cost_path)

# ---------------------------------------------------------------------
# Get statistics of combined cost surface
# ---------------------------------------------------------------------
# Get min, max, and mean values to understand cost distribution
combined_min = float(combined_cost.minimum)
combined_max = float(combined_cost.maximum)
combined_mean = float(combined_cost.mean)

# Print statistics
print(f"  Combined cost statistics:")
print(f"    Min: {combined_min:.2f}")       # Lowest cost in study area
print(f"    Max: {combined_max:.2f}")       # Highest cost in study area
print(f"    Mean: {combined_mean:.2f}")     # Average cost

# Log final success
log_message("✓ All cost surfaces created and combined", "SUCCESS")

# Now we have one raster (cost_combined) where each cell has a value from 0-10
# representing how difficult it is for bears to travel through that area

#cell 12
# =========================================================================
# STEP 7: CALCULATE OPTIMAL WILDLIFE CORRIDORS
# =========================================================================
# Now we use the combined cost surface to find the least-cost paths
# between bear habitat patches. These paths represent optimal corridors
# where bears can travel with minimum cost (avoiding roads, steep terrain, etc.)

# Print header for this step
print_header("Step 7: Calculate Optimal Wildlife Corridors")

# =========================================================================
# DEFINE PATHS
# =========================================================================

# Path to habitat polygons (the patches we want to connect)
habitats_path = os.path.join(gdb_path, "habitats")

# Path to combined cost surface (created in previous step)
combined_cost_path = os.path.join(gdb_path, "cost_combined")

# =========================================================================
# STEP 7A: CONVERT HABITAT POLYGONS TO CENTROIDS (POINTS)
# =========================================================================
# Cost path analysis works with points, not polygons
# So we convert each habitat polygon to a point at its center

log_message("Converting habitat polygons to centroids...")

# Path for temporary habitat centroids
habitat_centroids = os.path.join(gdb_path, "habitat_centroids_temp")

# FeatureToPoint creates a point at the center of each polygon
# "INSIDE" parameter ensures point is inside the polygon (not outside)
arcpy.management.FeatureToPoint(
    habitats_path,           # Input: habitat polygons
    habitat_centroids,       # Output: habitat centroids (points)
    "INSIDE"                 # Ensure points are inside polygons
)

# Count how many habitat patches we have
habitat_count = get_feature_count(habitat_centroids)

# Log success
log_message(f"  ✓ Created {habitat_count} habitat centroids", "SUCCESS")

# =========================================================================
# STEP 7B: CALCULATE COST DISTANCE
# =========================================================================
# Cost Distance calculates the accumulated cost to reach each cell
# from the nearest habitat patch, traveling across the cost surface

log_message("Calculating cost distance from habitats...")

# ---------------------------------------------------------------------
# Run Cost Distance tool
# ---------------------------------------------------------------------
# This creates two outputs:
#   1. Cost distance raster - shows accumulated cost from each cell to nearest habitat
#   2. Backlink raster - shows direction to travel to reach nearest habitat
cost_distance = arcpy.sa.CostDistance(
    habitat_centroids,       # Source points (habitat centroids)
    combined_cost_path,      # Cost surface to traverse
    out_backlink_raster=os.path.join(gdb_path, "cost_backlink_temp")  # Direction raster
)

# Save cost distance raster
cost_dist_path = os.path.join(gdb_path, "cost_distance_temp")
cost_distance.save(cost_dist_path)

# Log success
log_message("  ✓ Cost distance calculated", "SUCCESS")

# =========================================================================
# STEP 7C: CALCULATE LEAST-COST PATHS BETWEEN HABITAT PAIRS
# =========================================================================
# Now calculate the optimal path from each habitat to every other habitat
# This creates a network of corridors connecting all patches

log_message("Calculating least-cost paths between habitat pairs...")

# ---------------------------------------------------------------------
# Get coordinates of all habitat centroids
# ---------------------------------------------------------------------
# We need to store coordinates and IDs for each habitat

# List to store habitat information
habitats_list = []

# Open cursor to read centroid coordinates and IDs
with arcpy.da.SearchCursor(habitat_centroids, ["SHAPE@XY", "OBJECTID"]) as cursor:
    # Loop through each habitat centroid
    for row in cursor:
        # Create dictionary with coordinates and ID
        habitats_list.append({
            'coords': row[0],      # SHAPE@XY gives (X, Y) tuple
            'oid': row[1]          # OBJECTID is unique ID
        })

# Print info about how many patches we're connecting
print(f"  Connecting {habitat_count} habitat patches...")

# ---------------------------------------------------------------------
# Calculate paths between all unique pairs
# ---------------------------------------------------------------------
# We use nested loops to create all unique pairs
# For example, if we have habitats A, B, C:
#   - Calculate path from A to B
#   - Calculate path from A to C  
#   - Calculate path from B to C
# (We don't calculate B to A because it's the same as A to B)

# List to store temporary path rasters
path_rasters = []

# Counter for number of paths created
pair_count = 0

# Outer loop: iterate through each habitat (i = starting habitat)
for i in range(len(habitats_list)):
    
    # Inner loop: iterate through remaining habitats (j = destination habitat)
    # Start at i+1 to avoid duplicate pairs (A→B is same as B→A)
    for j in range(i + 1, len(habitats_list)):
        
        # -------------------------------------------------------------
        # Create destination point geometry
        # -------------------------------------------------------------
        
        # Get coordinates of destination habitat
        dest_coords = habitats_list[j]['coords']
        
        # Create a Point object from coordinates
        dest_point = arcpy.Point(dest_coords[0], dest_coords[1])
        
        # Create a PointGeometry object with spatial reference
        dest_geom = arcpy.PointGeometry(dest_point, Config.SPATIAL_REF)
        
        # -------------------------------------------------------------
        # Calculate cost path
        # -------------------------------------------------------------
        try:
            # CostPath finds the least-cost route from destination to source
            # It uses the cost distance and backlink rasters
            cost_path = arcpy.sa.CostPath(
                dest_geom,                                          # Destination point
                cost_dist_path,                                     # Cost distance raster
                os.path.join(gdb_path, "cost_backlink_temp")       # Backlink raster
            )
            
            # Create unique name for this path raster
            path_temp = os.path.join(gdb_path, f"path_{i}_{j}_temp")
            
            # Save the path raster
            cost_path.save(path_temp)
            
            # Add to list of path rasters
            path_rasters.append(path_temp)
            
            # Increment counter
            pair_count += 1
            
        except Exception as e:
            # If path calculation fails (rare), print warning and continue
            print(f"  Warning: Could not create path {i}→{j}")
            # Continue to next pair instead of stopping the whole process

# Log how many paths were created
log_message(f"  ✓ Generated {pair_count} path segments", "SUCCESS")

# =========================================================================
# STEP 7D: CONVERT RASTER PATHS TO POLYLINES (VECTOR)
# =========================================================================
# The cost paths are currently rasters (grid of cells)
# We need to convert them to vector polylines for better visualization

log_message("Converting paths to polylines...")

# List to store polyline paths
all_polylines = []

# Loop through each path raster
for path_raster in path_rasters:
    
    # Create output name for polyline version
    # Replace "_temp" with "_line_temp"
    polyline_temp = path_raster.replace("_temp", "_line_temp")
    
    # Convert raster to polyline
    arcpy.conversion.RasterToPolyline(
        path_raster,        # Input raster path
        polyline_temp,      # Output polyline
        "ZERO",             # Background value (areas that are NOT the path)
        0,                  # Minimum dangle length
        "SIMPLIFY"          # Simplify geometry (remove unnecessary vertices)
    )
    
    # Add to list of polylines
    all_polylines.append(polyline_temp)

# Log success
log_message(f"  ✓ Converted {len(all_polylines)} paths", "SUCCESS")

# =========================================================================
# STEP 7E: MERGE ALL PATHS INTO SINGLE FEATURE CLASS
# =========================================================================
# Now we have many separate polyline files
# Merge them all into one feature class

log_message("Merging all path segments...")

# Path for merged routes (still temporary)
optimal_routes_temp = os.path.join(gdb_path, "optimal_routes_temp")

# Merge all polylines into one feature class
# Merge combines multiple feature classes into one
arcpy.management.Merge(
    all_polylines,          # List of input polylines
    optimal_routes_temp     # Output merged feature class
)

# Log success
log_message(f"  ✓ Merged all segments", "SUCCESS")

# =========================================================================
# STEP 7F: CLIP ROUTES TO PARK BOUNDARY
# =========================================================================
# Some routes might extend slightly outside park boundary due to raster processing
# Clip them to ensure all routes are within the park

log_message("Clipping routes to park boundary...")

# Path for final routes
optimal_routes_final = os.path.join(gdb_path, "optimal_routes")

# Clip merged routes to park boundary
arcpy.analysis.Clip(
    optimal_routes_temp,        # Input routes
    park_boundary_gdb,          # Clip feature (park boundary)
    optimal_routes_final        # Output clipped routes
)

# Log success
log_message(f"  ✓ Routes clipped to park boundary", "SUCCESS")

# =========================================================================
# STEP 7G: CALCULATE ROUTE LENGTH
# =========================================================================
# Add a field with the length of each route segment in meters

log_message("Calculating route statistics...")

# AddGeometryAttributes adds fields with geometric properties
# "LENGTH_GEODESIC" calculates accurate length in meters
# "METERS" specifies the unit
arcpy.management.AddGeometryAttributes(
    optimal_routes_final,       # Feature class to add fields to
    "LENGTH_GEODESIC",          # Type of geometry attribute
    "METERS"                    # Length unit
)

# ---------------------------------------------------------------------
# Sum all route lengths to get total corridor length
# ---------------------------------------------------------------------

# Initialize total length variable
total_length_m = 0

# Open cursor to read length values
# LENGTH_GEO is the field created by AddGeometryAttributes
with arcpy.da.SearchCursor(optimal_routes_final, ["LENGTH_GEO"]) as cursor:
    # Loop through each route segment
    for row in cursor:
        # Add this segment's length to total
        total_length_m += row[0]

# Convert meters to kilometers for easier reading
total_length_km = total_length_m / 1000

# ---------------------------------------------------------------------
# Print summary statistics
# ---------------------------------------------------------------------
print(f"\n  Results:")
print(f"    Habitat patches: {habitat_count}")                  # Number of patches connected
print(f"    Corridor segments: {pair_count}")                   # Number of route segments
print(f"    Total corridor length: {total_length_km:.2f} km")  # Total length of all routes

# Log success
log_message("✓ Optimal routes calculated", "SUCCESS")

# =========================================================================
# STEP 7H: CLEANUP INTERMEDIATE DATA
# =========================================================================
# Delete all temporary files to keep geodatabase clean

log_message("Cleaning up intermediate data...")

# List of all temporary files to delete
cleanup_list = [
    habitat_centroids,                                  # Habitat centroids (temp)
    cost_dist_path,                                     # Cost distance raster (temp)
    os.path.join(gdb_path, "cost_backlink_temp"),     # Backlink raster (temp)
    optimal_routes_temp                                 # Merged routes before clipping (temp)
] + path_rasters + all_polylines  # Add all individual path rasters and polylines

# Counter for deleted files
deleted = 0

# Loop through cleanup list
for item in cleanup_list:
    # Check if file exists
    if arcpy.Exists(item):
        # Delete it
        arcpy.management.Delete(item)
        # Increment counter
        deleted += 1

# Log how many files were deleted
log_message(f"  ✓ Deleted {deleted} temporary files", "SUCCESS")

# =========================================================================
# VISUALIZE FINAL ROUTES
# =========================================================================
# Show map with park boundary, habitats, and optimal routes

visualize_map(
    gdb_path,                               # Geodatabase path
    ['park_boundary', 'habitats', 'optimal_routes'],  # Layers to show
    "Step 7 - Optimal Wildlife Corridors"   # Map title
)

# Now we have our final optimal routes!
# These represent the best paths for bears to travel between habitat patches
# considering terrain, landcover, water proximity, and avoiding roads/trails

#cell 13
# =========================================================================
# STEP 8: CALCULATE STATISTICS
# =========================================================================
# Calculate various statistics required by the assignment:
#   - Average elevation of Kananaskis Country
#   - Area of each landcover type
#   - Total length of optimal routes
#   - NTS map sheets covering the park
#   - Townships covering the park

# Print header for this step
print_header("Step 8: Calculate Statistics")

# =========================================================================
# DEFINE PATHS
# =========================================================================

# Path to DEM (for elevation statistics)
dem_path = os.path.join(gdb_path, "dem")

# Path to landcover raster (for area calculations)
landcover_path = os.path.join(gdb_path, "landcover")

# Path to optimal routes (already have length from previous step)
optimal_routes_path = os.path.join(gdb_path, "optimal_routes")

# =========================================================================
# STATISTIC 1: ELEVATION STATISTICS
# =========================================================================
# Calculate average, minimum, maximum, and standard deviation of elevation

log_message("Calculating elevation statistics...")

# Path for output table
elev_stats_table = os.path.join(gdb_path, "elevation_stats")

# ---------------------------------------------------------------------
# Run Zonal Statistics as Table
# ---------------------------------------------------------------------
# This calculates statistics of the DEM within the park boundary zone
arcpy.sa.ZonalStatisticsAsTable(
    park_boundary_gdb,      # Zone dataset (park boundary)
    "OBJECTID",             # Zone field (unique ID for each zone)
    dem_path,               # Value raster (DEM - what we're analyzing)
    elev_stats_table,       # Output table
    "DATA",                 # Ignore NoData cells
    "ALL"                   # Calculate all statistics (min, max, mean, std, etc.)
)

# ---------------------------------------------------------------------
# Read statistics from table
# ---------------------------------------------------------------------
# The table has one row with all statistics

# Open cursor to read the statistics
# We want: MIN, MAX, MEAN (average), STD (standard deviation)
with arcpy.da.SearchCursor(elev_stats_table, ["MIN", "MAX", "MEAN", "STD"]) as cursor:
    # Loop through rows (there's only one row)
    for row in cursor:
        # Store statistics in a dictionary
        elev_stats = {
            'min': row[0],      # Minimum elevation
            'max': row[1],      # Maximum elevation
            'mean': row[2],     # Average elevation (REQUIRED BY ASSIGNMENT)
            'std': row[3]       # Standard deviation
        }

# ---------------------------------------------------------------------
# Print elevation statistics
# ---------------------------------------------------------------------
print(f"  Elevation Statistics:")
print(f"    Average: {elev_stats['mean']:.2f} m")    # Average (REQUIRED)
print(f"    Minimum: {elev_stats['min']:.2f} m")     # Lowest point
print(f"    Maximum: {elev_stats['max']:.2f} m")     # Highest point
print(f"    Std Dev: {elev_stats['std']:.2f} m")     # Variation

# =========================================================================
# STATISTIC 2: LANDCOVER AREAS
# =========================================================================
# Calculate the area (in km²) of each landcover type

log_message("Calculating landcover areas...")

# Path for output table
landcover_area_table = os.path.join(gdb_path, "landcover_areas")

# ---------------------------------------------------------------------
# Run Tabulate Area
# ---------------------------------------------------------------------
# This calculates the area of each landcover class within the park
arcpy.sa.TabulateArea(
    park_boundary_gdb,          # Zone dataset (park boundary)
    "OBJECTID",                 # Zone field
    landcover_path,             # Class raster (landcover)
    "Value",                    # Class field (landcover codes)
    landcover_area_table        # Output table
)

# ---------------------------------------------------------------------
# Read and print landcover areas
# ---------------------------------------------------------------------
print(f"\n  Landcover Areas (km²):")

# Get field names from the table
# Fields are named like "VALUE_1", "VALUE_2", etc.
# Each represents a different landcover class
fields = [f.name for f in arcpy.ListFields(landcover_area_table) 
          if f.name.startswith("VALUE_")]

# Open cursor to read areas
with arcpy.da.SearchCursor(landcover_area_table, fields) as cursor:
    # Loop through rows (one row with all class areas)
    for row in cursor:
        # Loop through each field/class
        for i, field in enumerate(fields):
            # Extract class number from field name
            # "VALUE_1" → "1"
            value = field.replace("VALUE_", "")
            
            # Get area in square meters
            area_sqm = row[i]
            
            # Convert to square kilometers
            area_sqkm = area_sqm / 1_000_000
            
            # Only print if area > 0 (class exists in park)
            if area_sqkm > 0:
                print(f"    Class {value}: {area_sqkm:.2f} km²")

# =========================================================================
# STATISTIC 3: ROUTE LENGTH
# =========================================================================
# Total length of optimal routes (already calculated in previous step)

print(f"\n  Optimal Routes:")
print(f"    Total Length: {total_length_km:.2f} km")  # REQUIRED BY ASSIGNMENT

# =========================================================================
# STATISTIC 4: NTS MAP SHEETS
# =========================================================================
# Identify which 1:50,000 NTS map sheets cover the park

log_message("Identifying NTS map sheets...")

# Path to NTS sheets feature class
nts_path = os.path.join(gdb_path, "nts_sheets")

# ---------------------------------------------------------------------
# Select NTS sheets that intersect the park
# ---------------------------------------------------------------------

# Create a temporary layer for selection
arcpy.management.MakeFeatureLayer(nts_path, "nts_layer")

# Select NTS sheets that intersect (overlap) the park boundary
arcpy.management.SelectLayerByLocation(
    "nts_layer",                # Layer to select from
    "INTERSECT",                # Spatial relationship (overlaps)
    park_boundary_gdb           # Selection feature (park boundary)
)

# ---------------------------------------------------------------------
# Find the field containing NTS sheet identifiers
# ---------------------------------------------------------------------
# The field name varies, so we search for common patterns

# Get all fields in the NTS layer
fields = arcpy.ListFields("nts_layer")

# Variable to store the NTS identifier field name
nts_field = None

# Loop through fields looking for NTS-related names
for field in fields:
    # Check if field name contains NTS, SHEET, or MAP
    if any(x in field.name.upper() for x in ['NTS', 'SHEET', 'MAP']):
        nts_field = field.name
        break  # Found it, stop searching

# If we didn't find a specific field, use first string field
if not nts_field:
    # Get first text field
    nts_field = [f.name for f in fields if f.type == 'String'][0]

# ---------------------------------------------------------------------
# Read NTS sheet identifiers
# ---------------------------------------------------------------------

# List to store NTS sheet names
nts_sheets = []

# Open cursor to read selected NTS sheets
with arcpy.da.SearchCursor("nts_layer", [nts_field]) as cursor:
    # Loop through selected sheets
    for row in cursor:
        # If value is not None/null
        if row[0]:
            # Add to list (convert to string)
            nts_sheets.append(str(row[0]))

# ---------------------------------------------------------------------
# Print NTS sheets
# ---------------------------------------------------------------------
print(f"\n  NTS Map Sheets ({len(nts_sheets)} sheets):")
print(f"    {', '.join(sorted(nts_sheets))}")  # Print sorted, comma-separated

# =========================================================================
# STATISTIC 5: TOWNSHIPS
# =========================================================================
# Identify which townships (TWP-RGE-MER) cover the park

log_message("Identifying townships...")

# Path to townships feature class
townships_path = os.path.join(gdb_path, "townships")

# ---------------------------------------------------------------------
# Select townships that intersect the park
# ---------------------------------------------------------------------

# Create temporary layer
arcpy.management.MakeFeatureLayer(townships_path, "township_layer")

# Select townships that intersect park
arcpy.management.SelectLayerByLocation(
    "township_layer",           # Layer to select from
    "INTERSECT",                # Spatial relationship
    park_boundary_gdb           # Selection feature
)

# ---------------------------------------------------------------------
# Find township fields (TWP, RGE, MER)
# ---------------------------------------------------------------------
# Alberta Township System uses three components:
#   - TWP = Township
#   - RGE = Range
#   - MER = Meridian

# Get all fields
fields = arcpy.ListFields("township_layer")

# Variables to store field names
twp_field = None    # Township field
rge_field = None    # Range field
mer_field = None    # Meridian field

# Search for each component
for field in fields:
    name = field.name.upper()  # Convert to uppercase for comparison
    
    # Check for township field
    if 'TWP' in name or 'TOWNSHIP' in name:
        twp_field = field.name
    
    # Check for range field
    elif 'RGE' in name or 'RANGE' in name:
        rge_field = field.name
    
    # Check for meridian field
    elif 'MER' in name or 'MERIDIAN' in name:
        mer_field = field.name

# Build list of fields to query (only include fields we found)
query_fields = [f for f in [twp_field, rge_field, mer_field] if f]

# ---------------------------------------------------------------------
# Read township identifiers
# ---------------------------------------------------------------------

# List to store township IDs
townships = []

# Open cursor to read selected townships
with arcpy.da.SearchCursor("township_layer", query_fields) as cursor:
    # Loop through each selected township
    for row in cursor:
        # Build identifier from available fields
        # Convert each value to string, filter out None values
        values = [str(v) for v in row if v is not None]
        
        # If we have at least one value
        if values:
            # Join values with hyphens (e.g., "23-8-W5")
            township_id = "-".join(values)
            # Add to list
            townships.append(township_id)

# Remove duplicates and sort
townships = sorted(set(townships))

# ---------------------------------------------------------------------
# Print townships
# ---------------------------------------------------------------------
print(f"\n  Townships ({len(townships)} townships):")

# Print first 10 townships
print(f"    {', '.join(townships[:10])}")

# If more than 10, indicate there are more
if len(townships) > 10:
    print(f"    ... and {len(townships) - 10} more")

# Log that all statistics are calculated
log_message("✓ All statistics calculated", "SUCCESS")

# All required statistics are now calculated and stored!

#cell 14
# =========================================================================
# STEP 9: FINAL CLEANUP
# =========================================================================
# Delete any remaining temporary or intermediate files
# This ensures the geodatabase only contains final deliverables

# Print header for this step
print_header("Step 9: Final Cleanup")

# Set workspace to geodatabase so we can list its contents
arcpy.env.workspace = gdb_path

# =========================================================================
# DEFINE CLEANUP PATTERNS
# =========================================================================
# List of patterns that identify temporary/intermediate files
# Any feature class or raster containing these strings will be deleted

cleanup_patterns = [
    '_temp',            # Files ending with _temp
    '_dist_',           # Distance rasters (intermediate)
    'cost_backlink',    # Backlink rasters (intermediate)
    'cost_distance',    # Cost distance rasters (intermediate)
    'habitat_centroids',# Habitat centroids (intermediate)
    'path_',            # Individual path rasters (intermediate)
    '_line'             # Individual path polylines (intermediate)
]

# Counter for deleted items
deleted_count = 0

# =========================================================================
# DELETE TEMPORARY FEATURE CLASSES
# =========================================================================
# List all feature classes in the geodatabase
for fc in arcpy.ListFeatureClasses():
    
    # Check if this feature class matches any cleanup pattern
    # any() returns True if at least one pattern is found in the name
    if any(pattern in fc for pattern in cleanup_patterns):
        
        # Delete this feature class
        arcpy.management.Delete(fc)
        
        # Increment counter
        deleted_count += 1

# =========================================================================
# DELETE TEMPORARY RASTERS
# =========================================================================
# List all rasters in the geodatabase
for raster in arcpy.ListRasters():
    
    # Check if this raster matches any cleanup pattern
    if any(pattern in raster for pattern in cleanup_patterns):
        
        # Delete this raster
        arcpy.management.Delete(raster)
        
        # Increment counter
        deleted_count += 1

# Log how many files were deleted
log_message(f"Deleted {deleted_count} intermediate files", "SUCCESS")

# Now the geodatabase only contains final deliverables:
#   - park_boundary
#   - roads, trails, hydrology (clipped)
#   - habitats, esa (clipped)
#   - townships, nts_sheets (clipped)
#   - dem, landcover (rasters)
#   - cost_terrain, cost_landcover, cost_hydrology, cost_roads, cost_trails
#   - cost_combined
#   - optimal_routes (FINAL RESULT!)
#   - elevation_stats, landcover_areas (tables)

#cell 15
# =========================================================================
# FINAL GEODATABASE INVENTORY
# =========================================================================
# List all contents of the geodatabase to verify everything is in place
# This serves as a final check and documentation of deliverables

# Print header
print_header("Final Geodatabase Inventory")

# Set workspace to geodatabase
arcpy.env.workspace = gdb_path

# =========================================================================
# LIST FEATURE CLASSES
# =========================================================================
print("FEATURE CLASSES:")
print("-" * 70)

# Get list of all feature classes and sort alphabetically
for fc in sorted(arcpy.ListFeatureClasses()):
    
    # Get feature count
    count = get_feature_count(fc)
    
    # Get feature type (Point, Polyline, Polygon)
    desc = arcpy.Describe(fc)
    
    # Print formatted information
    # Format: "  ✓ name                    type        (count features)"
    print(f"  ✓ {fc:25s} {desc.shapeType:12s} ({count:,} features)")

# =========================================================================
# LIST RASTERS
# =========================================================================
print("\nRASTERS:")
print("-" * 70)

# Get list of all rasters and sort alphabetically
for raster in sorted(arcpy.ListRasters()):
    
    # Get raster properties
    desc = arcpy.Describe(raster)
    
    # Print formatted information
    # Format: "  ✓ name                    (25m cell size)"
    print(f"  ✓ {raster:25s} ({desc.meanCellWidth}m cell size)")

# =========================================================================
# LIST TABLES
# =========================================================================
print("\nTABLES:")
print("-" * 70)

# Get list of all tables and sort alphabetically
for table in sorted(arcpy.ListTables()):
    
    # Get row count
    count = int(arcpy.management.GetCount(table)[0])
    
    # Print formatted information
    # Format: "  ✓ name                    (count rows)"
    print(f"  ✓ {table:25s} ({count:,} rows)")

# This inventory shows all final deliverables required by the assignment!

#cell 16
# =========================================================================
# PROJECT COMPLETE!
# =========================================================================
# Print a comprehensive summary of the entire analysis

# Print header with special formatting
print_header("PROJECT COMPLETE!", "=")

print("📊 FINAL SUMMARY")
print("=" * 70)

# =========================================================================
# OUTPUT LOCATION
# =========================================================================
print(f"\n✓ Geodatabase: {Config.GDB_NAME}.gdb")
print(f"✓ Location: {Config.WORKSPACE}")

# =========================================================================
# KEY RESULTS (Assignment Requirements)
# =========================================================================
print(f"\n📈 Key Results:")

# Print elevation statistics
print(f"  • Average Elevation: {elev_stats['mean']:.2f} m")
print(f"    (Range: {elev_stats['min']:.2f} - {elev_stats['max']:.2f} m)")

# Print corridor length
print(f"  • Total Corridor Length: {total_length_km:.2f} km")

# Print habitat information
print(f"  • Habitat Patches Connected: {habitat_count}")

# Print reference grid information
print(f"  • NTS Map Sheets: {len(nts_sheets)}")
print(f"  • Townships: {len(townships)}")

# =========================================================================
# DELIVERABLES CHECKLIST
# =========================================================================
print(f"\n✅ Deliverables:")
print(f"  ✓ Geodatabase with all final datasets")
print(f"  ✓ Optimal wildlife corridor routes")
print(f"  ✓ Cost surface analysis (5 surfaces combined)")
print(f"  ✓ Elevation statistics")
print(f"  ✓ Landcover area statistics")
print(f"  ✓ Route length calculations")
print(f"  ✓ NTS map sheets identified")
print(f"  ✓ Townships identified")

# =========================================================================
# NEXT STEPS
# =========================================================================
print(f"\n📋 Next Steps:")
print(f"  1. Create PDF map in ArcGIS Pro layout")
print(f"  2. Export as: GEOS456_FP_{Config.STUDENT_LAST}_{Config.STUDENT_FIRST}.pdf")
print(f"  3. Export this notebook as .py script")
print(f"  4. Submit geodatabase, PDF, and script to Brightspace")

# Final message
print("\n" + "=" * 70)
print("✓ All processing complete!")
print("✓ Ready for map production and submission")
print("=" * 70)

# =========================================================================
# FINAL VISUALIZATION - COMPLETE ANALYSIS
# =========================================================================
# Show one final map with all major layers

visualize_map(
    gdb_path,                   # Geodatabase path
    [                            # All important layers
        'park_boundary',         # Study area boundary
        'roads',                 # Road network
        'trails',                # Trail network
        'hydrology',             # Water features
        'habitats',              # Bear habitat patches
        'optimal_routes'         # OPTIMAL CORRIDORS (main result!)
    ],
    "FINAL RESULT - Complete Wildlife Corridor Analysis"  # Title
)

# Congratulations! The analysis is complete!
# You now have:
#   - A geodatabase with all clipped and processed data
#   - 5 cost surfaces representing different factors
#   - 1 combined cost surface
#   - Optimal routes connecting all bear habitat patches
#   - All required statistics
#   - Visualizations showing your results

#cell 17
# =========================================================================
# EXPORT MAP TO PDF (OPTIONAL)
# =========================================================================
# This cell exports the map layout to PDF
# REQUIREMENT: Your .aprx project must have a layout configured

print_header("Export Map to PDF (Optional)")

# Try to export PDF - if it fails, provide instructions
try:
    # ---------------------------------------------------------------------
    # Get current ArcGIS Pro project
    # ---------------------------------------------------------------------
    # "CURRENT" refers to the project this notebook is part of
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    
    # ---------------------------------------------------------------------
    # Get the first layout
    # ---------------------------------------------------------------------
    # A layout is where you arrange maps for printing/exporting
    # Get list of all layouts in the project
    layouts = aprx.listLayouts()
    
    # Check if any layouts exist
    if not layouts:
        # No layouts found - print instructions
        print("  ⚠ No layout found in project")
        print("  To export PDF:")
        print("    1. Open ArcGIS Pro")
        print("    2. Insert → New Layout")
        print("    3. Add map frame with your data")
        print("    4. Run this cell again")
    else:
        # Use the first layout
        layout = layouts[0]
        
        # -----------------------------------------------------------------
        # Define PDF filename
        # -----------------------------------------------------------------
        # Format: GEOS456_FP_LastName_FirstName.pdf
        pdf_filename = f"GEOS456_FP_{Config.STUDENT_LAST}_{Config.STUDENT_FIRST}.pdf"
        
        # Full path to save PDF
        pdf_path = os.path.join(Config.WORKSPACE, pdf_filename)
        
        # -----------------------------------------------------------------
        # Export layout to PDF
        # -----------------------------------------------------------------
        log_message(f"Exporting map to PDF...")
        
        layout.exportToPDF(
            pdf_path,               # Output path
            resolution=300          # High quality (300 DPI)
        )
        
        # Log success
        log_message(f"✓ Map exported: {pdf_filename}", "SUCCESS")
        print(f"  Location: {pdf_path}")
        
except Exception as e:
    # If export fails, print error and instructions
    print(f"  ⚠ Could not export PDF: {str(e)}")
    print("\n  You can export manually:")
    print("    1. In ArcGIS Pro, go to the Layout view")
    print("    2. Share → Export Layout → PDF")
    print(f"    3. Save as: GEOS456_FP_{Config.STUDENT_LAST}_{Config.STUDENT_FIRST}.pdf")

# Note: Manual export is often easier than automated export
# The important thing is to have a properly formatted PDF map

#cell 18
# =========================================================================
# CHECK IN SPATIAL ANALYST EXTENSION
# =========================================================================
# Return the Spatial Analyst license
# This is good practice - like returning a library book when done

arcpy.CheckInExtension("Spatial")

# =========================================================================
# FINAL COMPLETION MESSAGE
# =========================================================================

print("\n" + "=" * 70)
print("✅ NOTEBOOK COMPLETE!")
print("=" * 70)

print(f"\nYour final deliverables are ready:")
print(f"  1. {Config.GDB_NAME}.gdb (geodatabase with all data)")
print(f"  2. GEOS456_FP_{Config.STUDENT_LAST}_{Config.STUDENT_FIRST}.pdf (map)")
print(f"  3. This notebook (code and documentation)")

print(f"\n📝 To Submit:")
print(f"  1. Zip the geodatabase folder")
print(f"  2. Include the PDF map")
print(f"  3. Export this notebook as .py:")
print(f"     File → Download Notebook → Download as .py")
print(f"  4. Submit all files to Brightspace")

print(f"\n💡 Understanding Check:")
print(f"  • Cost surfaces: Lower values = easier for bears to travel")
print(f"  • Optimal routes: Least-cost paths between habitats")
print(f"  • Total analysis: Combines terrain, landcover, water, roads, trails")

print("\n" + "=" * 70)
print("Good luck with your submission! 🎓")
print("=" * 70)

#cell 11
# =========================================================================
# STEP 6: CREATE COST SURFACES
# =========================================================================
# Cost surfaces represent how difficult it is for bears to travel through
# different areas. Lower cost = easier travel, Higher cost = harder travel

print_header("Step 6: Create Cost Surfaces")

# =========================================================================
# DEFINE PATHS TO CLIPPED DATA
# =========================================================================
dem_path = os.path.join(gdb_path, "dem")
landcover_path = os.path.join(gdb_path, "landcover")
roads_path = os.path.join(gdb_path, "roads")
trails_path = os.path.join(gdb_path, "trails")
hydrology_path = os.path.join(gdb_path, "hydrology")

# =========================================================================
# COST SURFACE 1: TERRAIN (from slope)
# =========================================================================
log_message("Creating terrain cost surface...")

# Calculate slope in degrees
slope = arcpy.sa.Slope(dem_path, "DEGREE")

# Save temporarily to get statistics
slope_temp = os.path.join(gdb_path, "slope_temp_stats")
slope.save(slope_temp)

# Calculate statistics so we can get max value
arcpy.management.CalculateStatistics(slope_temp)

# Get maximum slope value
slope_max = float(arcpy.management.GetRasterProperties(
    slope_temp, "MAXIMUM").getOutput(0))

print(f"  Max slope: {slope_max:.1f}°")

# Rescale to 0-10 (flat=0/good, steep=10/bad)
transformation = arcpy.sa.TfLinear(0, slope_max, 0, 10)
terrain_cost = arcpy.sa.RescaleByFunction(slope, transformation, 0, slope_max)

# Save final terrain cost
terrain_cost_path = os.path.join(gdb_path, "cost_terrain")
terrain_cost.save(terrain_cost_path)

# Delete temporary slope raster
arcpy.management.Delete(slope_temp)

log_message("  ✓ Terrain cost created", "SUCCESS")

# =========================================================================
# COST SURFACE 2: LANDCOVER (reclassification)
# =========================================================================
log_message("Creating landcover cost surface...")

# Reclassification values
landcover_reclass = {
    1: 1, 2: 1, 3: 1,  # Forests (best)
    4: 2,              # Grassland
    5: 3,              # Shrubland
    6: 6,              # Exposed Land
    7: 7,              # Rock/Rubble
    8: 8,              # Snow/Ice
    9: 9,              # Agriculture
    10: 10, 11: 10     # Water, Developed (worst)
}

# Create remap
remap = arcpy.sa.RemapValue([[k, v] for k, v in landcover_reclass.items()])

# Reclassify
landcover_cost = arcpy.sa.Reclassify(landcover_path, "Value", remap, "NODATA")

# Save landcover cost
landcover_cost_path = os.path.join(gdb_path, "cost_landcover")
landcover_cost.save(landcover_cost_path)

log_message("  ✓ Landcover cost created", "SUCCESS")

# =========================================================================
# COST SURFACE 3: HYDROLOGY PROXIMITY
# =========================================================================
log_message("Creating hydrology proximity cost surface...")

# Set extent
arcpy.env.extent = park_boundary_gdb

# Calculate distance to water
hydro_dist = arcpy.sa.DistanceAccumulation(hydrology_path)

# Save temporarily to get statistics
hydro_dist_temp = os.path.join(gdb_path, "hydro_dist_temp_stats")
hydro_dist.save(hydro_dist_temp)

# Calculate statistics
arcpy.management.CalculateStatistics(hydro_dist_temp)

# Get maximum distance
hydro_max = float(arcpy.management.GetRasterProperties(
    hydro_dist_temp, "MAXIMUM").getOutput(0))

print(f"  Max distance to water: {hydro_max:.0f}m")

# Rescale: close to water=0/good, far from water=10/bad (INVERSE)
transformation = arcpy.sa.TfLinear(hydro_max, 0, 0, 10)
hydro_cost = arcpy.sa.RescaleByFunction(hydro_dist, transformation, 0, hydro_max)

# Save hydrology cost
hydro_cost_path = os.path.join(gdb_path, "cost_hydrology")
hydro_cost.save(hydro_cost_path)

# Delete temporary distance raster
arcpy.management.Delete(hydro_dist_temp)

log_message("  ✓ Hydrology cost created", "SUCCESS")

# =========================================================================
# COST SURFACE 4: ROADS PROXIMITY
# =========================================================================
log_message("Creating roads proximity cost surface...")

# Calculate distance to roads
roads_dist = arcpy.sa.DistanceAccumulation(roads_path)

# Save temporarily
roads_dist_temp = os.path.join(gdb_path, "roads_dist_temp_stats")
roads_dist.save(roads_dist_temp)

# Calculate statistics
arcpy.management.CalculateStatistics(roads_dist_temp)

# Get maximum distance
roads_max = float(arcpy.management.GetRasterProperties(
    roads_dist_temp, "MAXIMUM").getOutput(0))

print(f"  Max distance to roads: {roads_max:.0f}m")

# Rescale: close to roads=10/bad, far from roads=0/good
transformation = arcpy.sa.TfLinear(0, roads_max, 10, 0)
roads_cost = arcpy.sa.RescaleByFunction(roads_dist, transformation, 0, roads_max)

# Save roads cost
roads_cost_path = os.path.join(gdb_path, "cost_roads")
roads_cost.save(roads_cost_path)

# Delete temporary distance raster
arcpy.management.Delete(roads_dist_temp)

log_message("  ✓ Roads cost created", "SUCCESS")

# =========================================================================
# COST SURFACE 5: TRAILS PROXIMITY
# =========================================================================
log_message("Creating trails proximity cost surface...")

# Calculate distance to trails
trails_dist = arcpy.sa.DistanceAccumulation(trails_path)

# Save temporarily
trails_dist_temp = os.path.join(gdb_path, "trails_dist_temp_stats")
trails_dist.save(trails_dist_temp)

# Calculate statistics
arcpy.management.CalculateStatistics(trails_dist_temp)

# Get maximum distance
trails_max = float(arcpy.management.GetRasterProperties(
    trails_dist_temp, "MAXIMUM").getOutput(0))

print(f"  Max distance to trails: {trails_max:.0f}m")

# Rescale: close to trails=10/bad, far from trails=0/good
transformation = arcpy.sa.TfLinear(0, trails_max, 10, 0)
trails_cost = arcpy.sa.RescaleByFunction(trails_dist, transformation, 0, trails_max)

# Save trails cost
trails_cost_path = os.path.join(gdb_path, "cost_trails")
trails_cost.save(trails_cost_path)

# Delete temporary distance raster
arcpy.management.Delete(trails_dist_temp)

log_message("  ✓ Trails cost created", "SUCCESS")

# =========================================================================
# COMBINE ALL 5 COST SURFACES
# =========================================================================
log_message("Combining all cost surfaces...")

# Create weighted sum table (all weights = 1)
ws_table = arcpy.sa.WSTable([
    [terrain_cost_path, "VALUE", 1],
    [landcover_cost_path, "VALUE", 1],
    [hydro_cost_path, "VALUE", 1],
    [roads_cost_path, "VALUE", 1],
    [trails_cost_path, "VALUE", 1]
])

# Perform weighted sum
combined_cost = arcpy.sa.WeightedSum(ws_table)

# Save combined cost surface
combined_cost_path = os.path.join(gdb_path, "cost_combined")
combined_cost.save(combined_cost_path)

# =========================================================================
# CALCULATE STATISTICS FOR COMBINED COST SURFACE
# =========================================================================
# THIS IS THE KEY - Calculate statistics BEFORE trying to read them
log_message("Calculating combined cost statistics...")

arcpy.management.CalculateStatistics(combined_cost_path)

# Now get statistics - they're guaranteed to exist
combined_min = float(arcpy.management.GetRasterProperties(
    combined_cost_path, "MINIMUM").getOutput(0))

combined_max = float(arcpy.management.GetRasterProperties(
    combined_cost_path, "MAXIMUM").getOutput(0))

combined_mean = float(arcpy.management.GetRasterProperties(
    combined_cost_path, "MEAN").getOutput(0))

# Print statistics
print(f"  Combined cost statistics:")
print(f"    Min: {combined_min:.2f}")
print(f"    Max: {combined_max:.2f}")
print(f"    Mean: {combined_mean:.2f}")

log_message("✓ All cost surfaces created and combined", "SUCCESS")