import os
import sys # Added for PROJ_LIB fix
import xml.etree.ElementTree as ET
import fiona
from xml.dom import minidom
import datetime  # Added for timestamps
import shutil  # Added for rmtree

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

def create_landxml_from_gdb(gdb_path, layer_name, xml_file_path):
    """
    Reads point features from a GDB layer and writes them to a LandXML-1.2 file
    in a format similar to Leica LandXML.

    Args:
        gdb_path (str): Path to the input File Geodatabase (.gdb folder).
        layer_name (str): Name of the point layer to read from the GDB.
        xml_file_path (str): Path to the output XML file.
    """
    points_data = []
    point_counter = 0  # For oID
    try:
        with fiona.open(gdb_path, 'r', layer=layer_name) as source:
            # Check if the geometry type is Point
            if source.schema['geometry'] not in ['Point', 'PointZ', 'PointM', '3D Point']:
                print(f"Error: Layer '{layer_name}' in {gdb_path} is not a point layer. Geometry type is {source.schema['geometry']}.")
                return False

            for feature in source:
                try:
                    geom = feature['geometry']
                    if geom and geom['type'] == 'Point':
                        point_counter += 1
                        # Coordinates are typically (easting, northing, [elevation])
                        coords = geom['coordinates']
                        easting = coords[0]
                        northing = coords[1]
                        # Elevation is optional, handle if present
                        elevation = coords[2] if len(coords) > 2 else 0.0 
                        
                        name_prop = feature['properties'].get('name', f'Point_{point_counter}')
                        point_name = str(name_prop) if name_prop else f'Point_{point_counter}'
                        
                        point_code = feature['properties'].get('code', 'DefaultCode')
                        point_desc = feature['properties'].get('description', f'Description for {point_name}')
                                                
                        points_data.append({
                            'id': str(point_counter),  # For oID
                            'name': point_name,
                            'easting': easting,
                            'northing': northing,
                            'elevation': elevation,
                            'code': point_code,
                            'desc': point_desc,
                            'pntRef': feature['properties'].get('pntRef', ""),
                            'solutionType': feature['properties'].get('solutionType', "unknown"),
                            'surveyMethod': feature['properties'].get('surveyMethod', ""),
                            'surveyOrder': feature['properties'].get('surveyOrder', ""),
                            'class_val': feature['properties'].get('class', "default"), # 'class' is a keyword, using 'class_val'
                            'latitude': feature['properties'].get('latitude', "0.0000000000"),
                            'longitude': feature['properties'].get('longitude', "0.0000000000"),
                            'ellipsoidHeight': feature['properties'].get('ellipsoidHeight', "0.000")
                        })
                except Exception as e:
                    print(f"Warning: Could not process feature: {feature.get('id', 'N/A')}. Error: {e}")
            
            if not points_data:
                print(f"No point features found or processed in layer '{layer_name}' of {gdb_path}.")
                return False

    except fiona.errors.DriverError as e:
        print(f"Fiona DriverError: Could not open GDB '{gdb_path}' or layer '{layer_name}'. Error: {e}")
        try:
            available_layers = fiona.listlayers(gdb_path)
            print(f"Available layers in {gdb_path}: {available_layers}")
        except Exception as list_e:
            print(f"Could not list layers for {gdb_path} due to: {list_e}")
        return False
    except Exception as e:
        print(f"Error reading from GDB {gdb_path} (target layer: '{layer_name}'): {e}")
        print("This might indicate the layer doesn't exist, is named differently, or is empty/corrupted.")
        try:
            available_layers = fiona.listlayers(gdb_path)
            print(f"To help diagnose, available layers in '{gdb_path}' are: {available_layers}")
        except Exception as list_e:
            print(f"Additionally, an attempt to list layers for '{gdb_path}' failed due to: {list_e}")
        return False

    # Create XML structure
    landxml_ns = "http://www.landxml.org/schema/LandXML-1.2"
    xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
    
    ET.register_namespace('', landxml_ns)  # Default namespace
    ET.register_namespace('xsi', xsi_ns)
    
    current_datetime = datetime.datetime.now(datetime.timezone.utc)
    current_date_str = current_datetime.strftime("%Y-%m-%d")
    current_time_str = current_datetime.strftime("%H:%M:%S")
    # ISO 8601 format with milliseconds and Z for UTC
    current_timestamp_iso = current_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    root_attrs = {
        "date": current_date_str,
        "time": current_time_str,
        "version": "1.2",
        "language": "English",
        "readOnly": "false",
        f"{{{xsi_ns}}}schemaLocation": f"{landxml_ns} http://www.landxml.org/schema/LandXML-1.2/LandXML-1.2.xsd"
    }
    root = ET.Element(f"{{{landxml_ns}}}LandXML", root_attrs)

    # Add Units
    units_element = ET.SubElement(root, f"{{{landxml_ns}}}Units")
    ET.SubElement(units_element, f"{{{landxml_ns}}}Metric", {
        "areaUnit": "squareMeter", "linearUnit": "meter", "volumeUnit": "cubicMeter",
        "temperatureUnit": "celsius", "pressureUnit": "pascal", "diameterUnit": "meter",
        "angularUnit": "decimal dd.mm.ss", "directionUnit": "decimal dd.mm.ss"
    })

    # Add CoordinateSystem (using placeholders from Leica example)
    ET.SubElement(root, f"{{{landxml_ns}}}CoordinateSystem", {
        "desc": "RD / NAP", "name": "RDNAP", "epsgCode": "28992+5709", 
        "horizontalDatum": "Amersfoort", "verticalDatum": "NAP", "ellipsoidName": "Bessel 1841",
        "horizontalCoordinateSystemName": "RD", "zone": "", "falseNorthing": "0", "falseEasting": "0",
        "latitudeOfNaturalOrigin": "0", "longitudeOfNaturalOrigin": "0", "naturalOriginScaleFactor": "1"
    })

    # Add Application
    app_element = ET.SubElement(root, f"{{{landxml_ns}}}Application", {
        "name": "Python GDB to LandXML Converter", "desc": "Converted from GDB", 
        "manufacturer": "Custom Script", "version": "1.0",
        "manufacturerURL": "", "timeStamp": current_timestamp_iso
    })
    ET.SubElement(app_element, f"{{{landxml_ns}}}Author", {
        "createdBy": "AutomatedProcess", "company": "N/A", 
        "companyURL": "", "timeStamp": current_timestamp_iso
    })

    cgpoints_element = ET.SubElement(root, f"{{{landxml_ns}}}CgPoints")

    for point_data in points_data:
        cgpoint_attrs = {
            "name": str(point_data['name']),
            "oID": str(point_data['id']),
            "code": str(point_data['code']),
            "desc": str(point_data['desc']),
            "role": "surveyed",
            "timeStamp": current_timestamp_iso, 
            "pointGeometry": "point",
            "pntRef": str(point_data.get('pntRef', "")), 
            "solutionType": str(point_data.get('solutionType', "unknown")),
            "surveyMethod": str(point_data.get('surveyMethod', "")), 
            "surveyOrder": str(point_data.get('surveyOrder', "")),
            "class": str(point_data.get('class_val', "default")), # Using 'class_val' from point_data
            "latitude": str(point_data.get('latitude', "0.0000000000")), 
            "longitude": str(point_data.get('longitude', "0.0000000000")), 
            "ellipsoidHeight": str(point_data.get('ellipsoidHeight', "0.000"))
        }
        cgpoint_element = ET.SubElement(cgpoints_element, f"{{{landxml_ns}}}CgPoint", cgpoint_attrs)
        # Format coordinates as "Northing Easting Elevation"
        cgpoint_element.text = f"{point_data['northing']:.3f} {point_data['easting']:.3f} {point_data['elevation']:.3f}" 

    # Write to XML file with pretty printing
    try:
        xml_string_from_et = ET.tostring(root, encoding='utf-8', method='xml')
        dom = minidom.parseString(xml_string_from_et)
        pretty_xml_bytes = dom.toprettyxml(indent="  ", encoding='utf-8')
        
        lines = pretty_xml_bytes.splitlines(True)
        if lines and lines[0].startswith(b'<?xml'):
            lines[0] = b'<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
            final_xml_bytes = b"".join(lines)
        else:
            final_xml_bytes = b'<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n' + pretty_xml_bytes
            
        with open(xml_file_path, 'wb') as f:
            f.write(final_xml_bytes)
        print(f"Successfully created XML: {xml_file_path} with {len(points_data)} points.")
        return True
    except Exception as e:
        print(f"Error writing XML file {xml_file_path}: {e}")
        return False

if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define input directory for GDB files relative to the script directory
    input_gdb_dir = os.path.join(script_dir, "input_gdbs")
    
    # Define output directory for XMLs relative to the script directory
    output_xml_dir = os.path.join(script_dir, "output_xmls")

    # Ensure input directory exists
    if not os.path.exists(input_gdb_dir):
        os.makedirs(input_gdb_dir)
        print(f"Created input directory: {input_gdb_dir}. Please place GDB folders there.")

    # Ensure output directory exists
    if not os.path.exists(output_xml_dir):
        os.makedirs(output_xml_dir)
        print(f"Created output directory: {output_xml_dir}")

    # Define the layer name to be read from the GDBs (must be consistent or logic added to find it)
    # For this example, we'll assume a common layer name.
    # You might need to adjust this or add logic to discover layers if they vary.
    input_layer_name = "plaatsbepalingspunt_p" # Changed from "SurveyPoints"

    processed_gdbs_count = 0
    found_gdb_folders = False

    print(f"Searching for GDB folders in: {input_gdb_dir}")
    # GDBs are folders ending with .gdb
    for item_name in os.listdir(input_gdb_dir):
        item_path = os.path.join(input_gdb_dir, item_name)
        if os.path.isdir(item_path) and item_name.lower().endswith(".gdb"):
            found_gdb_folders = True
            gdb_path = item_path
            
            # Create XML filename from GDB folder name (e.g., input.gdb -> input.xml)
            gdb_base_name = os.path.splitext(item_name)[0]
            xml_filename = f"{gdb_base_name}.xml"
            xml_output_path = os.path.join(output_xml_dir, xml_filename)

            print(f"--- Processing GDB: {gdb_path} ---")
            print(f"Target layer: {input_layer_name}")
            print(f"Output XML will be: {xml_output_path}")
            
            success = create_landxml_from_gdb(gdb_path, input_layer_name, xml_output_path)
            if success:
                processed_gdbs_count += 1
            
            print("-" * 40) # Separator for multiple GDBs

    if not found_gdb_folders:
        print(f"No GDB folders (ending with .gdb) found in '{input_gdb_dir}'.")
    elif processed_gdbs_count > 0:
        print(f"\nFinished processing. {processed_gdbs_count} GDB folder(s) converted and saved to '{output_xml_dir}'.")
    else:
        print(f"\nFinished processing. GDB folders were found, but none were successfully converted (or no valid point data in them).")

    # --- End Example Usage ---

