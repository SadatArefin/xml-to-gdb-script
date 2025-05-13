import os
import sys # Added for PROJ_LIB fix
import xml.etree.ElementTree as ET
import fiona # Added for listing layers
from xml.dom import minidom
import datetime # Added for timestamps
import pyproj # Added for PROJ_LIB fix and PyInstaller

# --- BEGIN PROJ_LIB FIX ---
# Attempt to set PROJ_LIB based on script location and common venv structure
proj_lib_found = False

# Check if running in a PyInstaller bundle
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # This is the path to the bundled 'proj' data folder
    # The data is bundled to 'pyproj/proj_dir/share/proj' relative to sys._MEIPASS
    bundled_proj_path = os.path.join(sys._MEIPASS, 'pyproj', 'proj_dir', 'share', 'proj')
    if os.path.exists(os.path.join(bundled_proj_path, 'proj.db')):
        os.environ['PROJ_LIB'] = bundled_proj_path
        print(f"PROJ_LIB successfully set from PyInstaller bundle: {bundled_proj_path}")
        proj_lib_found = True
    else:
        # Fallback for older pyproj versions that might place data directly in _MEIPASS/pyproj/data
        bundled_proj_path_alt = os.path.join(sys._MEIPASS, 'pyproj', 'data')
        if os.path.exists(os.path.join(bundled_proj_path_alt, 'proj.db')):
            os.environ['PROJ_LIB'] = bundled_proj_path_alt
            print(f"PROJ_LIB successfully set from PyInstaller bundle (alternative path): {bundled_proj_path_alt}")
            proj_lib_found = True
        else:
            print(f"Warning: Running in PyInstaller bundle, but 'proj.db' not found at expected bundled paths:"
                  f" {os.path.join(bundled_proj_path, 'proj.db')} or {os.path.join(bundled_proj_path_alt, 'proj.db')}")

if not proj_lib_found:
    script_dir = os.path.dirname(os.path.abspath(__file__))

    proj_relative_paths = [
        os.path.join('Lib', 'site-packages', 'pyproj', 'proj_dir', 'share', 'proj'),
        os.path.join('Lib', 'site-packages', 'pyproj', 'data'),
        os.path.join('share', 'proj')
    ]

    potential_bases = [
        os.path.join(script_dir, '.venv'),
        os.path.join(os.path.dirname(script_dir), '.venv'),
        os.path.dirname(os.path.dirname(sys.executable))
    ]
    potential_bases = sorted(list(set(os.path.abspath(p) for p in potential_bases)))

    for base_path in potential_bases:
        if proj_lib_found:
            break
        for rel_path in proj_relative_paths:
            candidate_proj_lib_path = os.path.join(base_path, rel_path)
            if os.path.exists(os.path.join(candidate_proj_lib_path, 'proj.db')):
                os.environ['PROJ_LIB'] = candidate_proj_lib_path
                print(f"PROJ_LIB successfully set to: {candidate_proj_lib_path}")
                proj_lib_found = True
                break

if not proj_lib_found:
    try:
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
    # Only print these detailed warnings if not running bundled,
    # as the bundled check has its own warning.
    if not (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')):
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

def populate_cgpoints_from_layer(gdb_path, layer_name, cgpoints_element_to_populate, starting_oid, current_timestamp_iso, landxml_namespace_uri, status_callback=print):
    """
    Reads features from a GDB layer and adds their point data (original points or
    vertices from lines/polygons) as CgPoint elements to an existing CgPoints XML element.

    Args:
        gdb_path (str): Path to the input File Geodatabase (.gdb folder).
        layer_name (str): Name of the point layer to read from the GDB.
        cgpoints_element_to_populate (ET.Element): The <CgPoints> XML element to add points to.
        starting_oid (int): The starting oID for points from this layer.
        current_timestamp_iso (str): The ISO timestamp string for CgPoint elements.
        landxml_namespace_uri (str): The LandXML namespace URI string.
        status_callback (function): Function to call for status updates.

    Returns:
        tuple: (number_of_points_added, next_available_oid)
    """
    points_added_this_layer = 0
    current_oid = starting_oid
    
    try:
        with fiona.open(gdb_path, 'r', layer=layer_name) as source:
            layer_geom_type = source.schema.get('geometry')

            processable_schema_geom_types = [
                'Point', 'PointZ', 'PointM', '3D Point',
                'LineString', '3D LineString', 'MultiLineString', '3D MultiLineString',
                'Polygon', '3D Polygon', 'MultiPolygon', '3D MultiPolygon'
            ]

            if layer_geom_type not in processable_schema_geom_types:
                status_callback(f"Info: Layer '{layer_name}' in {gdb_path} has a geometry type ({layer_geom_type}) that cannot be processed for CgPoints. Skipping layer for this GDB's XML.")
                return 0, starting_oid

            for feature_idx, feature in enumerate(source):
                geom = feature.get('geometry')
                if not geom:
                    continue

                coords_to_extract = []
                actual_geom_type = geom.get('type')
                raw_coords = geom.get('coordinates')

                if actual_geom_type == 'Point':
                    if raw_coords and isinstance(raw_coords, (list, tuple)) and len(raw_coords) >= 2:
                        coords_to_extract.append(raw_coords)
                elif actual_geom_type in ['LineString', '3D LineString']:
                    if raw_coords:
                        coords_to_extract.extend(raw_coords)
                elif actual_geom_type in ['MultiLineString', '3D MultiLineString']:
                    if raw_coords:
                        for line_coords in raw_coords: 
                            coords_to_extract.extend(line_coords)
                elif actual_geom_type in ['Polygon', '3D Polygon']:
                    if raw_coords:
                        for ring in raw_coords: 
                            coords_to_extract.extend(ring[:-1] if len(ring) > 1 and tuple(ring[0]) == tuple(ring[-1]) else ring)
                elif actual_geom_type in ['MultiPolygon', '3D MultiPolygon']:
                    if raw_coords:
                        for polygon_rings in raw_coords: 
                            for ring in polygon_rings: 
                                coords_to_extract.extend(ring[:-1] if len(ring) > 1 and tuple(ring[0]) == tuple(ring[-1]) else ring)
                
                vertex_in_feature_counter_for_name = 0
                for coord_tuple in coords_to_extract:
                    if not (isinstance(coord_tuple, (list, tuple)) and 2 <= len(coord_tuple) <= 3 and all(isinstance(c, (int, float)) for c in coord_tuple)):
                        continue
                    
                    current_oid += 1
                    vertex_in_feature_counter_for_name += 1
                    points_added_this_layer += 1

                    easting = coord_tuple[0]
                    northing = coord_tuple[1]
                    elevation = coord_tuple[2] if len(coord_tuple) > 2 else 0.0

                    props = feature.get('properties', {})
                    original_feature_id_str = str(feature.get('id', f"feat{feature_idx}"))

                    if actual_geom_type == 'Point':
                        point_name_str = str(props.get('name', f'Point_{current_oid}'))
                        point_code = str(props.get('code', 'DefaultCode'))
                        point_desc = str(props.get('description', f'Desc_{current_oid}'))
                        solution_type = str(props.get('solutionType', "unknown"))
                        survey_method = str(props.get('surveyMethod', ""))
                        class_val = str(props.get('class', "default"))
                    else: 
                        base_name_prop = props.get('name', f'Feat_{original_feature_id_str}')
                        point_name_str = f"{base_name_prop}_L{layer_name[:8].replace(' ','_')}_V{vertex_in_feature_counter_for_name}"
                        point_code = "DerivedVertex"
                        point_desc = f"Vtx {vertex_in_feature_counter_for_name} of {base_name_prop} from Lyr {layer_name}"
                        solution_type = "derived_vertex"
                        survey_method = "extracted_from_geometry"
                        class_val = "derived_default"
                    
                    if not point_name_str: point_name_str = f"Point_{current_oid}"

                    cgpoint_attrs = {
                        "name": point_name_str, "oID": str(current_oid), "code": point_code,
                        "desc": point_desc, "role": "surveyed", "timeStamp": current_timestamp_iso,
                        "pointGeometry": "point", "pntRef": str(props.get('pntRef', "")),
                        "solutionType": solution_type, "surveyMethod": survey_method,
                        "surveyOrder": str(props.get('surveyOrder', "")), "class": class_val,
                        "latitude": str(props.get('latitude', "0.0000000000")),
                        "longitude": str(props.get('longitude', "0.0000000000")),
                        "ellipsoidHeight": str(props.get('ellipsoidHeight', "0.000"))
                    }
                    cgpoint_element = ET.SubElement(cgpoints_element_to_populate, f"{{{landxml_namespace_uri}}}CgPoint", cgpoint_attrs)
                    cgpoint_element.text = f"{northing:.3f} {easting:.3f} {elevation:.3f}"
            
            if points_added_this_layer > 0:
                status_callback(f"  Added {points_added_this_layer} points from layer '{layer_name}' to current GDB's XML.")

    except fiona.errors.DriverError as e:
        status_callback(f"Fiona DriverError for layer '{layer_name}' in GDB '{gdb_path}': {e}. Skipping layer.")
        try:
            available_layers_info = fiona.listlayers(gdb_path)
            status_callback(f"  (Context: Available layers in {gdb_path} are: {available_layers_info})")
        except Exception:
            pass 
        return 0, starting_oid 
    except Exception as e:
        status_callback(f"Error reading from layer '{layer_name}' in GDB {gdb_path}: {e}. Skipping layer.")
        return 0, starting_oid 
    
    return points_added_this_layer, current_oid

def run_conversion(input_gdb_dir_param, output_xml_dir_param, status_callback=print):
    """
    Main function to process GDBs and convert them to combined LandXML files.
    Args:
        input_gdb_dir_param (str): Path to the directory containing GDB folders.
        output_xml_dir_param (str): Path to the directory where XML files will be saved.
        status_callback (function): Function to call for status updates.
    """
    if not os.path.exists(input_gdb_dir_param):
        os.makedirs(input_gdb_dir_param)
        status_callback(f"Created input directory: {input_gdb_dir_param}. Please place GDB folders there.")
    
    if not os.path.exists(output_xml_dir_param):
        os.makedirs(output_xml_dir_param)
        status_callback(f"Created output directory: {output_xml_dir_param}")

    processed_gdb_to_xml_count = 0
    found_gdb_folders = False

    status_callback(f"Searching for GDB folders in: {input_gdb_dir_param}")
    for item_name in os.listdir(input_gdb_dir_param):
        item_path = os.path.join(input_gdb_dir_param, item_name)
        if os.path.isdir(item_path) and item_name.lower().endswith(".gdb"):
            found_gdb_folders = True
            gdb_path = item_path
            gdb_base_name = os.path.splitext(item_name)[0]
            
            status_callback(f"--- Processing GDB: {gdb_path} ---")

            landxml_ns = "http://www.landxml.org/schema/LandXML-1.2"
            xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
            ET.register_namespace('', landxml_ns)
            ET.register_namespace('xsi', xsi_ns)

            current_datetime = datetime.datetime.now(datetime.timezone.utc)
            current_date_str = current_datetime.strftime("%Y-%m-%d")
            current_time_str = current_datetime.strftime("%H:%M:%S")
            current_timestamp_iso = current_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            root_attrs = {
                "date": current_date_str, "time": current_time_str, "version": "1.2",
                "language": "English", "readOnly": "false",
                f"{{{xsi_ns}}}schemaLocation": f"{landxml_ns} http://www.landxml.org/schema/LandXML-1.2/LandXML-1.2.xsd"
            }
            root = ET.Element(f"{{{landxml_ns}}}LandXML", root_attrs)
            units_element = ET.SubElement(root, f"{{{landxml_ns}}}Units")
            ET.SubElement(units_element, f"{{{landxml_ns}}}Metric", {
                "areaUnit": "squareMeter", "linearUnit": "meter", "volumeUnit": "cubicMeter",
                "temperatureUnit": "celsius", "pressureUnit": "pascal", "diameterUnit": "meter",
                "angularUnit": "decimal dd.mm.ss", "directionUnit": "decimal dd.mm.ss"
            })
            ET.SubElement(root, f"{{{landxml_ns}}}CoordinateSystem", {
                "desc": "RD / NAP", "name": "RDNAP", "epsgCode": "28992+5709", 
                "horizontalDatum": "Amersfoort", "verticalDatum": "NAP", "ellipsoidName": "Bessel 1841",
                "horizontalCoordinateSystemName": "RD", "zone": "", "falseNorthing": "0", "falseEasting": "0",
                "latitudeOfNaturalOrigin": "0", "longitudeOfNaturalOrigin": "0", "naturalOriginScaleFactor": "1"
            })
            app_element = ET.SubElement(root, f"{{{landxml_ns}}}Application", {
                "name": "Python GDB to LandXML Converter", "desc": f"Converted from GDB: {gdb_base_name}", 
                "manufacturer": "Custom Script", "version": "1.1",
                "manufacturerURL": "", "timeStamp": current_timestamp_iso
            })
            ET.SubElement(app_element, f"{{{landxml_ns}}}Author", {
                "createdBy": "AutomatedProcess", "company": "N/A", 
                "companyURL": "", "timeStamp": current_timestamp_iso
            })
            cgpoints_element = ET.SubElement(root, f"{{{landxml_ns}}}CgPoints")
            
            gdb_total_points_added = 0
            master_oid_counter = 0 

            try:
                available_layers = fiona.listlayers(gdb_path)
                if not available_layers:
                    status_callback(f"No layers found in GDB: {gdb_path}")
                    status_callback("-" * 40)
                    continue
            except Exception as e:
                status_callback(f"Error listing layers for GDB {gdb_path}: {e}")
                status_callback("-" * 40)
                continue

            status_callback(f"Found layers in {gdb_base_name}: {available_layers}. Processing for combined XML...")
            
            for current_layer_name in available_layers:
                status_callback(f"  Attempting to process layer: '{current_layer_name}' for GDB '{gdb_base_name}'")
                points_from_layer, updated_oid = populate_cgpoints_from_layer(
                    gdb_path, 
                    current_layer_name, 
                    cgpoints_element, 
                    master_oid_counter,
                    current_timestamp_iso,
                    landxml_ns,
                    status_callback
                )
                gdb_total_points_added += points_from_layer
                master_oid_counter = updated_oid
            
            if gdb_total_points_added > 0:
                xml_filename = f"{gdb_base_name}_combined.xml"
                xml_output_path = os.path.join(output_xml_dir_param, xml_filename)
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
                        
                    with open(xml_output_path, 'wb') as f:
                        f.write(final_xml_bytes)
                    status_callback(f"Successfully created combined XML: {xml_output_path} with {gdb_total_points_added} total points from GDB '{gdb_base_name}'.")
                    processed_gdb_to_xml_count += 1
                except Exception as e:
                    status_callback(f"Error writing combined XML file {xml_output_path} for GDB '{gdb_base_name}': {e}")
            else:
                status_callback(f"No points were added from any layer in GDB '{gdb_base_name}'. Combined XML not created.")

            status_callback("-" * 40) 

    if not found_gdb_folders:
        status_callback(f"No GDB folders (ending with .gdb) found in '{input_gdb_dir_param}'.")
    elif processed_gdb_to_xml_count > 0:
        status_callback(f"\nFinished processing. {processed_gdb_to_xml_count} combined XML file(s) created and saved to '{output_xml_dir_param}'.")
    else: 
        status_callback(f"\nFinished processing. GDB folders might have been found, but no combined XML files were successfully created (e.g., no processable layers or points found).")
    status_callback("Conversion process complete.")


if __name__ == "__main__":
    print("Running transform_opposite.py directly for testing...")
    
    script_dir_main = os.path.dirname(os.path.abspath(__file__))
    default_input_gdb_dir = os.path.join(script_dir_main, "input_gdbs")
    default_output_xml_dir = os.path.join(script_dir_main, "output_xmls")

    print(f"To test, you can call: run_conversion('{default_input_gdb_dir}', '{default_output_xml_dir}')")
    print("Or, run the gdb_to_xml_gui.py script.")

