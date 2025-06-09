#!/usr/bin/env python3
"""
Split large XML file into smaller chunks for uploading
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
import os
import tempfile

def split_xml_file(zip_path, races_per_chunk=2):
    """Split XML file in ZIP into smaller chunks"""
    print(f"Processing: {zip_path}")
    
    # Extract XML from ZIP
    with zipfile.ZipFile(zip_path, 'r') as zf:
        xml_files = [f for f in zf.namelist() if f.lower().endswith('.xml')]
        if not xml_files:
            print("No XML files found in ZIP")
            return
        
        xml_content = zf.read(xml_files[0])
    
    # Parse XML
    root = ET.fromstring(xml_content)
    
    # Find all races
    races = []
    for meeting in root.findall('.//meeting'):
        meeting_data = {
            'date': meeting.findtext('date'),
            'track': meeting.findtext('track'),
            'country': meeting.findtext('country'),
            'races': meeting.find('races')
        }
        
        for race in meeting.findall('.//race'):
            races.append({
                'meeting': meeting_data,
                'race': race
            })
    
    print(f"Found {len(races)} races total")
    
    # Create output directory
    output_dir = os.path.splitext(zip_path)[0] + "_split"
    os.makedirs(output_dir, exist_ok=True)
    
    # Split into chunks
    chunk_num = 1
    for i in range(0, len(races), races_per_chunk):
        chunk_races = races[i:i + races_per_chunk]
        
        # Create new XML for this chunk
        chunk_root = ET.Element('data')
        chunk_meeting = ET.SubElement(chunk_root, 'meeting')
        
        # Use data from first race's meeting
        meeting_data = chunk_races[0]['meeting']
        ET.SubElement(chunk_meeting, 'date').text = meeting_data['date']
        ET.SubElement(chunk_meeting, 'track').text = meeting_data['track']
        ET.SubElement(chunk_meeting, 'country').text = meeting_data['country']
        
        races_elem = ET.SubElement(chunk_meeting, 'races')
        
        # Add races to chunk
        for race_data in chunk_races:
            races_elem.append(race_data['race'])
        
        # Create ZIP file for this chunk
        chunk_filename = f"chunk_{chunk_num:02d}_races_{i+1}-{min(i+races_per_chunk, len(races))}.zip"
        chunk_path = os.path.join(output_dir, chunk_filename)
        
        with zipfile.ZipFile(chunk_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            xml_str = ET.tostring(chunk_root, encoding='unicode')
            # Add XML declaration
            xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
            zf.writestr(f"races_{i+1}-{min(i+races_per_chunk, len(races))}.xml", xml_str)
        
        print(f"Created: {chunk_path} ({len(chunk_races)} races)")
        chunk_num += 1
    
    print(f"\nSplit complete! Files saved to: {output_dir}")
    print(f"Upload each file separately to avoid timeouts.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python split_xml.py <zip_file> [races_per_chunk]")
        print("Default races_per_chunk: 2")
        sys.exit(1)
    
    zip_file = sys.argv[1]
    races_per_chunk = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    split_xml_file(zip_file, races_per_chunk)