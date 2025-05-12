import os
import sys
import shutil

# --- BEGIN PROJ_LIB FIX ---
# Attempt to set PROJ_LIB based on script location and common venv structure
proj_lib_found = False
# Determine the directory of the current script
# This is crucial for finding .venv if it's relative to the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Potential locations for proj.db relative to a base directory (like .venv or python install dir)
# Order matters: more specific/standard paths first
proj_relative_paths = [
    os.path.join('Lib', 'site-packages', 'pyproj', 'proj_dir', 'share', 'proj'), # Standard for venv
    os.path.join('Lib', 'site-packages', 'pyproj', 'data'), # Another common one for pyproj data
    os.path.join('share', 'proj') # General system-like path or older venv structure
]

# Bases to check:
# 1. .venv in the script's directory
# 2. .venv in the parent of the script's directory (if script is in a subdir like 'src')
# 3. The directory derived from sys.executable (covers global python or activated venv)
potential_bases = [
    os.path.join(script_dir, '.venv'),
    os.path.join(os.path.dirname(script_dir), '.venv'), # e.g. if script is in src/ and .venv is in project root
    os.path.dirname(os.path.dirname(sys.executable))
]
# Normalize, remove duplicates, and ensure they are absolute paths
potential_bases = sorted(list(set(os.path.abspath(p) for p in potential_bases)))

for base_path in potential_bases:
    if proj_lib_found:
        break
    for rel_path in proj_relative_paths:
        candidate_proj_lib_path = os.path.join(base_path, rel_path)
        # Check if proj.db exists in this candidate path
        if os.path.exists(os.path.join(candidate_proj_lib_path, 'proj.db')):
            os.environ['PROJ_LIB'] = candidate_proj_lib_path
            print(f"PROJ_LIB successfully set to: {candidate_proj_lib_path}")
            proj_lib_found = True
            break

if not proj_lib_found:
    # Fallback: try to use pyproj.datadir.get_data_dir()
    # This needs pyproj to be importable.
    try:
        # Import pyproj here, only if needed, to avoid issues if it's not installed
        # or if its import itself triggers PROJ errors without PROJ_LIB
        import pyproj
        pyproj_datadir = pyproj.datadir.get_data_dir()
        if pyproj_datadir and os.path.exists(os.path.join(pyproj_datadir, 'proj.db')):
            os.environ['PROJ_LIB'] = pyproj_datadir
            print(f"PROJ_LIB set using pyproj.datadir: {pyproj_datadir}")
            proj_lib_found = True
        elif pyproj_datadir:
            print(f"pyproj.datadir.get_data_dir() ({pyproj_datadir}) found, but 'proj.db' not in this directory.")
        else:
            print("pyproj.datadir.get_data_dir() did not return a valid path.")
    except ImportError:
        print("pyproj module not found. Cannot use pyproj.datadir to find PROJ_LIB.")
    except Exception as e:
        print(f"Error trying to use pyproj.datadir: {e}")

if not proj_lib_found:
    # Construct the paths that were previously being checked to inform the user
    venv_path_from_sys = os.path.dirname(os.path.dirname(sys.executable))
    original_sys_attempt_path1 = os.path.join(venv_path_from_sys, 'Lib', 'site-packages', 'pyproj', 'proj_dir', 'share', 'proj')
    original_sys_attempt_path2 = os.path.join(venv_path_from_sys, 'share', 'proj')
    
    script_venv_attempt_path1 = os.path.join(script_dir, '.venv', 'Lib', 'site-packages', 'pyproj', 'proj_dir', 'share', 'proj')
    script_venv_attempt_path2 = os.path.join(script_dir, '.venv', 'share', 'proj')

    print(f"Warning: Could not automatically find and set PROJ_LIB. PROJ errors may persist.")
    print(f"  Checked common locations based on script path ({script_dir}) and Python executable ({sys.executable}).")
    print(f"  Examples of paths derived from sys.executable ({sys.executable}):")
    print(f"    - {original_sys_attempt_path1}")
    print(f"    - {original_sys_attempt_path2}")
    print(f"  Examples of paths derived from .venv relative to script ({script_dir}):")
    print(f"    - {script_venv_attempt_path1}")
    print(f"    - {script_venv_attempt_path2}")
    print(f"  Also attempted to use pyproj.datadir.get_data_dir().")
    print("  Please ensure 'proj.db' is accessible and PROJ_LIB is set correctly, or that 'pyproj' is installed with its data files in a standard location.")
    print("  You might need to manually find 'proj.db' in your environment and set the PROJ_LIB environment variable before running the script.")

# --- END PROJ_LIB FIX ---

# Imports that depend on PROJ_LIB being potentially set
import xml.etree.ElementTree as ET
import fiona

print(f"Fiona supported drivers: {fiona.supported_drivers}") # Add this line to check drivers

def create_gdb_from_landxml(xml_file_path, gdb_path, layer_name="CgPoints"):
    """
    Parses a LandXML file to extract CgPoint data and writes it to a File Geodatabase.

    Args:
        xml_file_path (str): Path to the LandXML file.
        gdb_path (str): Path to the output File Geodatabase (.gdb folder).
        layer_name (str): Name of the point layer to be created in the GDB.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        print(f"XML Root tag: {root.tag}") # Print root tag
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return
    except FileNotFoundError:
        print(f"Error: XML file not found at {xml_file_path}")
        return

    # Namespace for LandXML-1.2
    ns = {'landxml': 'http://www.landxml.org/schema/LandXML-1.2'}
    # Try to find CgPoints using the LandXML namespace first
    cgpoints_element = root.find('landxml:CgPoints', ns)

    # If not found with LandXML namespace, try without a namespace (common for simpler XMLs or different schemas)
    if cgpoints_element is None:
        # Attempt to find CgPoints without a namespace, which might occur if the default namespace is not explicitly declared for child elements
        # or if the XML is not strictly adhering to namespace prefixes for all elements.
        print("CgPoints element not found with explicit LandXML-1.2 namespace prefix. Trying to find 'CgPoints' using the declared default namespace...")
        cgpoints_element = root.find('{http://www.landxml.org/schema/LandXML-1.2}CgPoints')

    if cgpoints_element is None:
        print("Still not found. Trying to find 'CgPoints' without any namespace qualification (less likely for LandXML but a fallback)...")
        cgpoints_element = root.find('CgPoints') # Try finding CgPoints without namespace as a last resort

    # If still not found, it might be under a different parent or Leica-specific structure
    if cgpoints_element is None:
        print("No CgPoints element found directly under the root (with or without LandXML namespace).")
        # Placeholder for trying other common Leica structures if known, e.g. root.find('.//LeicaPointsContainer')
        # For now, we'll just report it's not found and exit for this file.
        return

    print(f"Found CgPoints element: {cgpoints_element.tag}")

    points_data = []
    # Adjust findall to match how cgpoints_element was found
    point_elements_to_search = cgpoints_element.findall('landxml:CgPoint', ns) if 'landxml' in ns and root.find('landxml:CgPoints', ns) is not None else cgpoints_element.findall('CgPoint')
    
    print(f"Found {len(point_elements_to_search)} CgPoint potential elements.")
    
    for i, cgpoint in enumerate(point_elements_to_search):
        name = cgpoint.get('name')
        oID = cgpoint.get('oID')
        code = cgpoint.get('code')
        desc = cgpoint.get('desc')
        role = cgpoint.get('role')
        timeStamp = cgpoint.get('timeStamp')
        pointGeometry_xml = cgpoint.get('pointGeometry') # XML attribute name
        pntRef = cgpoint.get('pntRef')
        solutionType = cgpoint.get('solutionType')
        surveyMethod = cgpoint.get('surveyMethod')
        surveyOrder = cgpoint.get('surveyOrder')
        class_val = cgpoint.get('class') # XML attribute name
        latitude = cgpoint.get('latitude')
        longitude = cgpoint.get('longitude')
        ellipsoidHeight = cgpoint.get('ellipsoidHeight')
        
        coords_text = cgpoint.text
        if i < 5: # Print details for the first 5 points for debugging
            print(f"  Point {i+1}: Name='{name}', CoordsRaw='{coords_text}'")
        
        if coords_text:
            try:
                parts = coords_text.split()
                easting = float(parts[0])
                northing = float(parts[1])
                points_data.append({
                    'geometry': {'type': 'Point', 'coordinates': (easting, northing)}, # Removed elevation
                    'properties': {
                        'name': name if name is not None else "",
                        'oID': oID if oID is not None else "",
                        'code': code if code is not None else "DefaultCode",
                        'desc': desc if desc is not None else "",
                        'role': role if role is not None else "surveyed",
                        'timeStamp': timeStamp if timeStamp is not None else "",
                        'pointGeometry': pointGeometry_xml if pointGeometry_xml is not None else "point", # GDB field name
                        'pntRef': pntRef if pntRef is not None else "",
                        'solutionType': solutionType if solutionType is not None else "unknown",
                        'surveyMethod': surveyMethod if surveyMethod is not None else "",
                        'surveyOrder': surveyOrder if surveyOrder is not None else "",
                        'class': class_val if class_val is not None else "default", # GDB field name
                        'latitude': latitude if latitude is not None else "0.0000000000",
                        'longitude': longitude if longitude is not None else "0.0000000000",
                        'ellipsoidHeight': ellipsoidHeight if ellipsoidHeight is not None else "0.000",
                    }
                })
            except (IndexError, ValueError) as e:
                print(f"Warning: Could not parse coordinates for point {name}: {coords_text}. Error: {e}")
        else:
            print(f"Warning: No coordinate data for point {name}")

    if not points_data:
        print("No valid point data extracted from the XML.")
        return

    # Define the schema for the GDB layer - SIMPLIFIED FOR DEBUGGING
    crs = 'EPSG:28992' 
    schema = {
        'geometry': 'Point',  # Changed from PointZ to Point (2D)
        'properties': {
            'name': 'str', # Simplified to only name
            'oID': 'str',
            'code': 'str',
            'desc': 'str',
            'role': 'str',
            'timeStamp': 'str',
            'pointGeometry': 'str', # GDB field name
            'pntRef': 'str',
            'solutionType': 'str',
            'surveyMethod': 'str',
            'surveyOrder': 'str',
            'class': 'str', # GDB field name
            'latitude': 'str',
            'longitude': 'str',
            'ellipsoidHeight': 'str',
        }
    }

    # Ensure the target GDB directory is removed if it exists, to avoid conflicts
    if os.path.exists(gdb_path):
        print(f"Attempting to remove existing GDB directory: {gdb_path}")
        try:
            shutil.rmtree(gdb_path)
            print(f"Successfully removed existing GDB directory: {gdb_path}")
        except Exception as e:
            print(f"Error removing existing GDB directory {gdb_path}: {e}. "
                  "Please check if the GDB is open in another application or if you have permissions.")
            return # Stop if we can't clean up

    try:
        print(f"Attempting to create GDB: {gdb_path} with layer: {layer_name}")
        # Added layer=layer_name and changed context variable to 'dst'
        with fiona.open(gdb_path, 'w', driver='OpenFileGDB', schema=schema, crs=crs, layer=layer_name) as dst:
            dst.writerecords(points_data)
        print(f"Successfully created GDB: {gdb_path} with layer: {layer_name}")
        print(f"{len(points_data)} points written.")
    except Exception as e:
        print(f"Error writing to GDB: {e}")

if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define input directory for XML files relative to the script directory
    # All .xml files in this directory and its subdirectories will be processed.
    # You might need to create this folder and place your XML files there.
    input_xml_dir = os.path.join(script_dir, "input_xmls") 
    
    # Define output directory for GDBs relative to the script directory
    # GDBs will be created in this folder.
    output_gdb_dir = os.path.join(script_dir, "output_gdbs")

    # Ensure input directory exists
    if not os.path.exists(input_xml_dir):
        os.makedirs(input_xml_dir)
        print(f"Created input directory: {input_xml_dir}. Please place XML files there.")

    # Ensure output directory exists
    if not os.path.exists(output_gdb_dir):
        os.makedirs(output_gdb_dir)
        print(f"Created output directory: {output_gdb_dir}")

    # Define the layer name within the GDB (can be constant for all GDBs)
    output_layer_name = "SurveyPoints" 

    processed_files_count = 0
    found_xml_files = False

    print(f"Searching for XML files in: {input_xml_dir}")
    for root, dirs, files in os.walk(input_xml_dir):
        for filename in files:
            if filename.lower().endswith(".xml"):
                found_xml_files = True
                xml_file_path = os.path.join(root, filename)
                
                # Create GDB name from XML filename (e.g., input.xml -> input.gdb)
                xml_base_name = os.path.splitext(filename)[0]
                gdb_name = f"{xml_base_name}.gdb"
                gdb_output_path = os.path.join(output_gdb_dir, gdb_name)

                print(f"--- Processing XML: {xml_file_path} ---")
                print(f"Output GDB will be: {gdb_output_path}")
                
                create_gdb_from_landxml(xml_file_path, gdb_output_path, layer_name=output_layer_name)
                processed_files_count += 1
                
                # Optional: Verification for each created GDB
                # try:
                #     with fiona.open(gdb_output_path, 'r', layer=output_layer_name) as source:
                #         print(f"Verification: Found {len(list(source))} features in '{output_layer_name}' of {gdb_name}.")
                # except Exception as e:
                #     print(f"Could not verify GDB {gdb_name}: {e}")
                print("-" * 40) # Separator for multiple files

    if not found_xml_files:
        print(f"No XML files found in '{input_xml_dir}' or its subdirectories.")
    elif processed_files_count > 0:
        print(f"\nFinished processing. {processed_files_count} XML file(s) converted and saved to '{output_gdb_dir}'.")
    else:
        print(f"\nFinished processing. XML files were found, but none were successfully converted.")
