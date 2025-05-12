# LandXML and GDB Conversion Toolkit

A Python utility for bidirectional conversion between LandXML files and ESRI File Geodatabases (.gdb).

## Overview

This toolkit provides two conversion utilities:
1. **LandXML to GDB**: Parses LandXML files and creates File Geodatabases with point data
2. **GDB to LandXML**: Extracts point features from File Geodatabases and creates LandXML files

These tools are particularly useful for surveyors and GIS professionals working with survey data across different formats.

## Features

- Bidirectional conversion between LandXML 1.2 and File Geodatabases
- Extracts and preserves point attributes (name, code, description, coordinates)
- Automatically handles PROJ_LIB environment variable setup
- Processes multiple files in batch mode
- Preserves metadata and attributes like timestamp, survey method, solution type

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

### LandXML to GDB Conversion
1. Place your LandXML files in the `input_xmls` folder
2. Run:
    ```
    python transform.py
    ```
3. Converted GDBs will be created in the `output_gdbs` folder

### GDB to LandXML Conversion
1. Place your GDB folders in the `input_gdbs` folder
2. Run:
    ```
    python transform_opposite.py
    ```
3. Converted XML files will be created in the `output_xmls` folder

## Input & Output

### LandXML to GDB
- **Input**: LandXML 1.2 files with `CgPoints` elements
- **Output**: File Geodatabases with "SurveyPoints" layer (Point geometry)

### GDB to LandXML
- **Input**: File Geodatabases with "plaatsbepalingspunt_p" point layer
- **Output**: LandXML 1.2 files with proper namespaces and metadata

## Configuration

- **Coordinate System**: Default is EPSG:28992 (RD New / Amersfoort)
- **Layer Names**: 
  - GDB output uses "SurveyPoints" (configurable in `transform.py`)
  - GDB input expects "plaatsbepalingspunt_p" (configurable in `transform_opposite.py`)

## Troubleshooting

### PROJ_LIB Issues
Both scripts include comprehensive error handling for PROJ_LIB path issues, which are common when working with projection libraries.

### Common Problems
- **Missing proj.db**: Ensure pyproj is properly installed with its data files
- **XML Parsing Errors**: Verify your XML files follow the LandXML 1.2 schema
- **GDB Access Failures**: Check that GDAL/OGR is installed with FileGDB driver support
- **Layer Name Issues**: Verify layer names match the expected names in your input files