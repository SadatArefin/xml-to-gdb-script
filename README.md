# LandXML to GDB Converter

A Python utility to convert LandXML files to ESRI File Geodatabases (.gdb) by extracting CgPoint data.

## Overview

This utility parses LandXML files (version 1.2), extracts survey point data (CgPoints), and creates File Geodatabases with 3D point geometry. It's particularly useful for surveyors and GIS professionals working with survey data.

## Features

- Converts LandXML 1.2 format to File Geodatabases
- Extracts point name, code, description, and 3D coordinates
- Automatically handles PROJ_LIB environment variable setup
- Processes multiple XML files in batch mode
- Creates point layers with proper Z-values (elevation)

## Requirements

- Python 3.6+
- fiona
- pyproj
- A working GDAL/OGR installation with FileGDB driver support

## Installation

1. Clone or download this repository
2. Create a virtual environment:
    ```
    python -m venv .venv
    ```
3. Activate the virtual environment:
    - Windows: `.venv\Scripts\activate`
    - Unix/MacOS: `source .venv/bin/activate`
4. Install required packages:
    ```
    pip install fiona pyproj
    ```

## Usage

1. Place your LandXML files in the `input_xmls` folder (will be created if it doesn't exist)
2. Run the script:
    ```
    python transform.py
    ```
3. The converted File Geodatabases will be created in the `output_gdbs` folder

## Input & Output

### Input
- **Format**: LandXML files (.xml) following the LandXML 1.2 schema
- **Location**: Place files in the `input_xmls` directory (and subdirectories)
- **Required Elements**: Files must contain `CgPoints` elements with point data

### Output
- **Format**: ESRI File Geodatabase (.gdb)
- **Location**: Created in the `output_gdbs` directory
- **Layer Name**: "SurveyPoints" (configurable in the script)
- **Coordinate System**: EPSG:28992 (RD New / Amersfoort + NAP height)
- **Attributes**: name, code, description, and elevation

## Troubleshooting

### PROJ_LIB Issues
The script includes comprehensive error handling for PROJ_LIB path issues, which are common when working with projection libraries. If you encounter projection-related errors, the script will attempt to resolve them automatically.

### Common Problems
- **Missing proj.db**: Ensure pyproj is properly installed with its data files
- **XML Parsing Errors**: Verify your XML files follow the LandXML 1.2 schema
- **GDB Creation Failures**: Check that GDAL/OGR is installed with FileGDB driver support

## Notes
- The coordinate system is currently hardcoded to EPSG:28992 (Dutch coordinate system)
- To use a different coordinate system, modify the `crs` variable in the `create_gdb_from_landxml` function