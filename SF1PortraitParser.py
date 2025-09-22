# -*- coding: utf-8 -*-
import os
import logging

class SF1PortraitParser:
    """
    Simple parser for portraitXX.bin structure to extract blink, talk, palette, and magic blocks.
    Implemented according to rules in sf1_portrait_rules.txt (see comments).
    """
    def __init__(self, bin_path):
        # Configure logging to parser.log
        logging.basicConfig(
            filename='parser.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.bin_path = bin_path
        self.warnings = []  # Store warnings for GUI display
        with open(bin_path, "rb") as f:
            self.data = f.read()
        self.ln = len(self.data)
        self.blink = b""
        self.talk = b""
        self.palette = b""
        self.magic = b""
        self.graphic_offset = None
        self.logger.info(f"Loaded file {bin_path}, size={self.ln} bytes")
        self.logger.info(f"First 60 bytes: {self.data[:60].hex(' ').upper()}")
        self.parse()

    def _skip_block(self, data, pos):
        ln = len(data)
        if pos >= ln or data[pos] != 0x00:
            # If we're at EOF, avoid indexing error
            if pos < ln:
                self.logger.warning(f"Block at position {pos} does not start with 0x00 (found {data[pos]:02X} or end of file)")
                self.warnings.append(f"⚠️ Block at position {pos} does not start with 0x00 (found {data[pos]:02X})")
            else:
                self.logger.warning(f"Block at position {pos} is beyond file length")
                self.warnings.append(f"⚠️ Block at position {pos} is beyond file length")
            return pos
        if pos + 1 >= ln:
            self.logger.warning(f"Incomplete block at position {pos} (missing count byte)")
            self.warnings.append(f"⚠️ Incomplete block at position {pos} (missing count byte)")
            return pos + 1  # Skip only marker if no count
        count = data[pos + 1]
        skip = 2 + count * 4
        if pos + skip > ln:
            self.logger.warning(f"Block at position {pos} exceeds file length (count={count}, expected length={skip}, available={ln - pos})")
            self.warnings.append(f"⚠️ Block at position {pos} exceeds file length (count={count}, expected length={skip}, available={ln - pos})")
        self.logger.info(f"Skipping block at position {pos}, count={count}, length={skip}")
        return min(pos + skip, ln)

    def parse(self):
        data = self.data
        ln = self.ln
        pos = 0
        # Check for blink block
        if ln > 0 and data[0] == 0x00:
            blink_start = pos
            pos = self._skip_block(data, pos)
            self.blink = data[blink_start:pos]
            self.logger.info(f"Blink block parsed, size={len(self.blink)}, data={self.blink.hex(' ').upper()}, pos={pos}")
        else:
            self.logger.warning(f"File does not start with 0x00 — blink block missing or corrupted")
            self.warnings.append(f"⚠️ File does not start with 0x00 — blink block missing or corrupted")

        # Check for talk block (always expected after blink)
        if pos < ln and data[pos] == 0x00:
            talk_start = pos
            pos = self._skip_block(data, pos)
            self.talk = data[talk_start:pos]
            self.logger.info(f"Talk block parsed, size={len(self.talk)}, data={self.talk.hex(' ').upper()}, pos={pos}")
        else:
            if pos < ln:
                self.logger.warning(f"Expected talk block with 0x00 at position {pos}, but found {data[pos]:02X} — talk block missing")
                self.warnings.append(f"⚠️ Expected talk block with 0x00 at position {pos}, but found {data[pos]:02X}")
            else:
                self.logger.warning(f"Reached end of file after blink — talk block missing")
                self.warnings.append(f"⚠️ Reached end of file after blink — talk block missing")

        # Palette (32 bytes) expected next
        if pos + 32 <= ln:
            self.palette = data[pos:pos+32]
            pos += 32
            self.logger.info(f"Palette parsed, size={len(self.palette)}, data={self.palette.hex(' ').upper()}, pos={pos}")
        else:
            self.logger.warning(f"Insufficient data for palette (available {ln - pos} bytes instead of 32)")
            self.warnings.append(f"⚠️ Insufficient data for palette (available {ln - pos} bytes instead of 32)")
            self.palette = data[pos:]
            pos = ln
            self.logger.info(f"Palette parsed (incomplete), size={len(self.palette)}, data={self.palette.hex(' ').upper()}, pos={pos}")
        
        # Log data before magic bytes
        if pos < ln:
            self.logger.info(f"Data before magic bytes at position {pos}: {data[pos:min(pos+4, ln)].hex(' ').upper()}")
        
        # Magic bytes (08 08) expected after palette - LEAVE FOR DECOMPRESSOR!
        if pos + 2 <= ln:
            self.magic = data[pos:pos+2]
            self.logger.info(f"Reading magic bytes at position {pos}: {self.magic.hex(' ').upper()}")
            if self.magic != b"\x08\x08":
                self.logger.warning(f"Expected magic bytes 08 08, but found {self.magic.hex(' ').upper()} at position {pos}")
                self.warnings.append(f"⚠️ Expected magic bytes 08 08, but found {self.magic.hex(' ').upper()} at position {pos}")
            else:
                self.logger.info(f"Found magic bytes: {self.magic.hex().upper()}")
        else:
            self.magic = b""
            self.logger.warning(f"Magic bytes not found (available {ln - pos} bytes instead of 2)")
            self.warnings.append(f"⚠️ Magic bytes not found (available {ln - pos} bytes instead of 2)")
        
        # Graphics start with magic bytes (08 08)
        self.graphic_offset = pos  # pos points to start of magic bytes
        self.logger.info(f"Graphic offset (including magic bytes): {pos}")

    def get_summary_text(self):
        lines = []
        lines.append(f"Size: {self.ln} bytes")
        lines.append("")
        lines.append("Blink:")
        if self.blink:
            lines.append(f"  Hex: {self.blink[:16].hex(' ').upper()}{' ...' if len(self.blink)>16 else ''}")
        else:
            lines.append("  Missing")
        lines.append("Talk:")
        if self.talk:
            lines.append(f"  Hex: {self.talk[:16].hex(' ').upper()}{' ...' if len(self.talk)>16 else ''}")
        else:
            lines.append("  Missing")
        lines.append(f"Palette: {len(self.palette)} bytes")
        if self.palette:
            # show palette hex pairs
            pairs = [f"{self.palette[i]:02X} {self.palette[i+1]:02X}" for i in range(0, min(len(self.palette), 32), 2)]
            lines.append("  " + ", ".join(pairs))
        lines.append(f"Magic: {len(self.magic)} bytes {self.magic.hex(' ').upper() if self.magic else ''}")
        lines.append(f"Graphic offset: {self.graphic_offset}")
        lines.append(f"Graphic size: {max(0, self.ln - (self.graphic_offset or self.ln))} bytes")
        return "\n".join(lines)

    def save_sf1(self, dest_path=None):
        """
        Save the .bin file with current blink/talk/palette fields.
        If dest_path is None, overwrite the original file (self.bin_path).
        This method reconstructs the file as:
          [blink bytes] + [talk bytes] + [palette (32 bytes)] + [rest (from original graphic_offset)]
        It preserves the compressed graphics (magic bytes + data) unchanged.
        """
        try:
            if dest_path is None:
                dest_path = self.bin_path

            # Ensure we have the original raw data available
            original = getattr(self, 'data', None)
            if original is None:
                with open(self.bin_path, "rb") as f:
                    original = f.read()

            # Determine graphic_offset; if missing, try to find magic bytes, else set to end
            graph_off = getattr(self, 'graphic_offset', None)
            if graph_off is None:
                idx = original.find(b'\x08\x08')
                graph_off = idx if idx != -1 else len(original)

            # Prepare blink and talk bytes (must be bytes)
            blink_bytes = self.blink if isinstance(self.blink, (bytes, bytearray)) else bytes(self.blink or b'')
            talk_bytes  = self.talk  if isinstance(self.talk,  (bytes, bytearray)) else bytes(self.talk or b'')

            # Prepare palette: ensure exactly 32 bytes (pad or truncate)
            palette_bytes = getattr(self, 'palette', b'') or b''
            if len(palette_bytes) < 32:
                palette_bytes = palette_bytes + b'\x00' * (32 - len(palette_bytes))
            else:
                palette_bytes = palette_bytes[:32]

            # Rest of file (starting at graphic offset)
            rest = original[graph_off:] if graph_off < len(original) else b''

            new_data = bytearray()
            new_data.extend(blink_bytes)
            new_data.extend(talk_bytes)
            new_data.extend(palette_bytes)
            new_data.extend(rest)

            # Write to destination
            with open(dest_path, "wb") as out:
                out.write(new_data)

            # Update internal state to reflect new file
            self.data = bytes(new_data)
            self.ln = len(self.data)
            # After rewrite, graphic_offset becomes len(blink)+len(talk)+32 - which should equal len(blink)+len(talk)+len(palette)
            self.graphic_offset = len(blink_bytes) + len(talk_bytes) + 32
            self.logger.info(f"Saved SF1 .bin to {dest_path}, new size={self.ln}, graphic_offset={self.graphic_offset}")

            return dest_path

        except Exception as e:
            self.logger.error(f"Error saving SF1 file: {str(e)}")
            raise

    def export_blocks_text(self):
        """Returns a text report of blink/talk/palette/magic."""
        lines = []
        lines.append(f"Blink: {self.blink.hex(' ').upper() if self.blink else 'none'}")
        lines.append(f"Talk: {self.talk.hex(' ').upper() if self.talk else 'none'}")
        if self.palette:
            pairs = [f"{self.palette[i]:02X} {self.palette[i+1]:02X}" for i in range(0, len(self.palette), 2)]
            lines.append("Palette (32 bytes): " + ", ".join(pairs))
        else:
            lines.append("Palette: none")
        lines.append(f"Magic: {self.magic.hex(' ').upper() if self.magic else 'none'}")
        return "\n".join(lines)
