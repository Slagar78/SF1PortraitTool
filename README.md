SF1 Portrait Tool
A Python-based GUI tool for viewing, compressing, and decompressing character portraits from Shining Force 1 and custom portraits created with a modified compressor. This tool supports both original Shining Force 1 portrait formats and custom-compressed .bin files, providing a user-friendly interface for developers and enthusiasts.
Features

Open and View Portraits:

Load original Shining Force 1 portraits using the SF1PortraitDecompressor (currently in development).
Load custom portraits compressed with SF1PortraitCompressor using the RLEDecompressor.
Load and preview PNG images (64x64 pixels).


Compression and Decompression:

Compress PNG images into .bin format using a custom RLE-based compressor.
Decompress .bin files back to PNG for viewing or editing.


Palette Management:

Supports a 3-3-2 RGB color palette (8 bits per channel, up to 15 colors + 1 transparent).
Save palette data as text for analysis or reuse.


Logging:

Generate detailed logs with file metadata, non-transparent pixel counts, and palette information.


Multilingual Interface:

Supports multiple languages (Russian, English, French, Spanish, Italian, Japanese, Portuguese, Greek).


Zoom Functionality:

Zoom in/out on portraits for detailed inspection.



Installation

Ensure you have Python 3.8 or higher installed (python --version to check).
Install required dependencies:pip install Pillow


Navigate to the project directory and run:python SF1PortraitTool.py


Note: The tkinter library is required and typically included with Python. Ensure it is available on your system.
Usage

Launch the application by running SF1PortraitTool.py.
Use the GUI buttons to perform actions:
Open SF1 Portrait: Load an original Shining Force 1 .bin portrait file (uses SF1PortraitDecompressor, in development).
Open Portrait: Load a custom .bin portrait file created with SF1PortraitCompressor (uses RLEDecompressor).
Open PNG: Load a 64x64 PNG image for preview or compression.
Save PNG: Save the current portrait as a PNG file.
Save BIN: Compress the current image to a .bin file using SF1PortraitCompressor.
Save Log: Export log details (file metadata, palette, pixel counts) to a text file.
Palette: Save the current palette as a text file.
Zoom In/Out: Adjust the preview scale for better inspection.


Select a language from the dropdown menu to switch the interface language.

Example
To decompress a custom portrait:

Click Open Portrait.
Select a .bin file compressed with SF1PortraitCompressor.
View the decompressed image in the canvas and check the log for details (palette, non-transparent pixels).

To compress a PNG:

Click Open PNG and select a 64x64 PNG image.
Click Save BIN to compress it to a .bin file.
Use Open Portrait to verify the compressed file.

Technical Details
Palette

Format: 3-3-2 RGB (3 bits for red, 3 bits for green, 2 bits for blue).
Colors: Up to 15 colors + 1 transparent color (index 0).
Storage: Encoded in the .bin file header (32 bytes, 16 colors, 2 bytes per color).
Conversion: Colors are scaled to 8-bit RGB (0-255) for PNG output using round(value * 255 / 15).

Encoding

Original SF1 Portraits:
Uses the Shining Force 1 proprietary compression format.
Decompressed with SF1PortraitDecompressor (in development).


Custom Portraits:
Uses a custom Run-Length Encoding (RLE) scheme optimized for 64x64 portraits.
Compressed with SF1PortraitCompressor and decompressed with RLEDecompressor.
Supports efficient storage of pixel runs and copy-down-left operations.


Data: RLE-compressed pixel data (4-bit indices referencing the palette).

Decompressors

SF1PortraitDecompressor: Handles original Shining Force 1 portrait files, parsing the proprietary format and extracting pixel data (currently in development).
RLEDecompressor: Designed for custom .bin files created by SF1PortraitCompressor. Implements bit-level RLE decoding with support for copy-down-left operations.

Dependencies

Python 3.8+
Pillow (PIL) for image processing
tkinter for GUI
Custom modules:
SF1PortraitParser.py
SF1PortraitDecompressor.py
SF1PortraitCompressor.py
RLEDecompressor.py
Lingua.py (for multilingual support)
AnimationEditor.py

For questions or feedback, open an issue on GitHub.
