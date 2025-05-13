# Leica XML and GDB Conversion Toolkit

A Python utility for bidirectional conversion between Leica XML files and ESRI File Geodatabases (.gdb).

## Overview

This toolkit provides:

1.  **A Graphical User Interface (GUI)**: For easy selection of conversion type, input/output paths, and layer names.
2.  **Command-Line Interface**: For batch processing and integration with other workflows.
3.  **GDB to Leica XML Script**: Extracts point features from File Geodatabases and creates Leica XML files.

These tools are particularly useful for surveyors and GIS professionals working with survey data across different formats.

## Features

- Graphical User Interface for ease of use.
- Bidirectional conversion between Leica XML 1.2 and File Geodatabases
- Extracts and preserves point attributes (name, code, description, coordinates)
- Automatically handles PROJ_LIB environment variable setup (including when bundled as an executable)
- Processes multiple files in batch mode
- Preserves metadata and attributes like timestamp, survey method, solution type

## Requirements

- Python 3.6+
- fiona
- pyproj
- pyinstaller (for building the executable)
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
   pip install fiona pyproj pyinstaller
   ```
5. Build the executable (optional, for creating a standalone distributable application):
   To create a standalone executable:
   a. Ensure your virtual environment is activated.
   b. Find your `pyproj` data directory. You can find this by running the following in your activated environment's Python interpreter:
   ```python
   import pyproj
   print(pyproj.datadir.get_data_dir())
   ```
   c. Run PyInstaller from the project root directory. Replace `YOUR_PYPROJ_DATA_PATH` with the full path obtained in step 5b. The command should be run in PowerShell or a similar terminal:
   ```powershell
   python -m PyInstaller --onefile --windowed --add-data "YOUR_PYPROJ_DATA_PATH;pyproj/proj_dir/share/proj" gdb_to_xml_gui.py
   ```
   For example, if `pyproj.datadir.get_data_dir()` outputs `D:\core\quick\.venv\Lib\site-packages\pyproj\proj_dir\share\proj`, the command would be:
   ```powershell
   python -m PyInstaller --onefile --windowed --add-data "D:\core\quick\.venv\Lib\site-packages\pyproj\proj_dir\share\proj;pyproj/proj_dir/share/proj" gdb_to_xml_gui.py
   ```
   d. The executable will be created in a `dist` folder within your project directory (e.g., `dist\gdb_to_xml_gui.exe`).

## Usage

There are two main ways to use the toolkit:

### 1. Using the Graphical User Interface (Recommended)

**Option A: Running the Executable (if built)**

1.  Navigate to the `dist` folder (created after following step 5 in the "Installation" section).
2.  Run the `gdb_to_xml_gui.exe` (or similarly named) executable.
3.  In the GUI:
    - Select the desired **Conversion Type** (e.g., "Leica XML to GDB" or "GDB to Leica XML").
    - Specify the **Input Path** (folder containing your source files) and **Output Path** (folder where converted files will be saved). You can use the "Browse..." buttons.
    - If applicable, adjust the **GDB Layer Name** for the relevant conversion.
    - Click the "Start Conversion" button.
4.  Converted files will be created in the specified output folder. Log messages will appear in the GUI.

**Option B: Running directly with Python (for development or if not building an executable)**

1.  Ensure your virtual environment is activated (see Installation step 3).
2.  Run the GUI script from the project root directory:
    ```
    python gdb_to_xml_gui.py
    ```
3.  In the GUI:
    - Select the desired **Conversion Type** (e.g., "Leica XML to GDB" or "GDB to Leica XML").
    - Specify the **Input Path** (folder containing your source files) and **Output Path** (folder where converted files will be saved). You can use the "Browse..." buttons.
    - If applicable, adjust the **GDB Layer Name** for the relevant conversion.
    - Click the "Start Conversion" button.
4.  Converted files will be created in the specified output folder. Log messages will appear in the GUI.

### 2. Using Command-Line Scripts (Advanced)

The original scripts can still be run directly from the command line for batch processing or integration into other workflows. Ensure your virtual environment is activated.

#### Leica XML to GDB Conversion

1. Place your Leica XML files in the `input_xmls` folder (or a custom input folder).
2. Run:
   ```
   python transform.py
   ```
   This will use `input_xmls` as input and `output_gdbs` as output by default. The script can be modified for different default paths if needed.
3. Converted GDBs will be created in the `output_gdbs` folder.

#### GDB to Leica XML Conversion

1. Place your GDB folders in the `input_gdbs` folder (or a custom input folder).
2. Run:
   ```
   python transform_opposite.py
   ```
   This will use `input_gdbs` as input and `output_xmls` as output by default. The script can be modified for different default paths if needed.
3. Converted XML files will be created in the `output_xmls` folder.

## Input & Output

### Leica XML to GDB

- **Input**: Leica XML 1.2 files with `CgPoints` elements
- **Output**: File Geodatabases with "SurveyPoints" layer (Point geometry)

### GDB to Leica XML

- **Input**: File Geodatabases with point layers (the script attempts to process various geometry types that can yield points/vertices).
- **Output**: Leica XML 1.2 files with proper namespaces and metadata, combining points from all processable layers in each GDB into a single XML.

## Configuration

- **Coordinate System**: Default is EPSG:28992 (RD New / Amersfoort) for Leica XML output.
- **Layer Names**:
  - GDB output from Leica XML uses "SurveyPoints" (configurable in `transform.py`)
  - GDB input for GDB to Leica XML processes all layers found within the GDB.

## Troubleshooting

### PROJ_LIB Issues

Both scripts include comprehensive error handling for PROJ_LIB path issues, which are common when working with projection libraries. The PyInstaller build process also requires correct handling of these data files. If the executable has issues, ensure the `--add-data` path for PyInstaller was correct.

### Common Problems

- **Missing proj.db**: Ensure pyproj is properly installed with its data files. If running the executable, this means the data was correctly bundled.
- **XML Parsing Errors**: Verify your XML files follow the Leica XML 1.2 schema
- **GDB Access Failures**: Check that GDAL/OGR is installed with FileGDB driver support. For the executable to work on a machine without a full GDAL install, all necessary DLLs for Fiona/GDAL to read GDBs must be bundled by PyInstaller (which it usually attempts to do).
- **Layer Name Issues**: Verify layer names match the expected names in your input files if using older versions or modified scripts. The current `transform_opposite.py` attempts to read all layers.
