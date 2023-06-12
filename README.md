# SoXspectroGUI
A PyQt GUI app to generate spectrograms using SoX.

## Requirements
A valid SoX installation is required.
This script uses several libraries. Be sure to install:
 - PyQt5
 - winsound
 - pydub
 - cv2

## Usage
By default, SoX is assumed to be in *Path* environment variable. One may however specify the full path to the *sox.exe* executable in the global variables.
Two versions of this script are available.

#### SoXspectroGUI
Built-in file explorer to create spectrograms of all audio files of the selected foler.
Using a system argument to a file or a folder will open the script at this location. Made for "SendTo".

#### SoXspectroD&D
Drag and drop files on the window will add them to the queue. No system arguments handling implemented.

#### Settings
In both cases, one may customize the app through local variables set at the beginning of the file. The SoX command was not made to be customizable yet.
One may change the script extension to ".pyw" to hide the python console. The python console can however help with debugging.

## Known Issues
- Selecting an empty folder in SoXspectroGUI may show folders in the list of files.
- No error handling for writing images or reading audio files.
