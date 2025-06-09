#!/usr/bin/env python3
"""
Create a small test XML file to verify upload functionality
"""

import zipfile
import os

# Create a minimal valid XML file
test_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<data>
    <meeting>
        <date>2025-06-11</date>
        <track>Test Track</track>
        <country>USA</country>
        <races>
            <race>
                <race_number>1</race_number>
                <post_time>12:00</post_time>
                <distance>6</distance>
                <dist_unit>F</dist_unit>
                <surface>D</surface>
                <race_type>Claiming</race_type>
                <purse>10000</purse>
                <entries>
                    <entry>
                        <program_number>1</program_number>
                        <horse_name>Test Horse</horse_name>
                        <jockey>Test Jockey</jockey>
                        <trainer>Test Trainer</trainer>
                        <morning_line_odds>5-2</morning_line_odds>
                    </entry>
                </entries>
            </race>
        </races>
    </meeting>
</data>"""

# Write XML file
xml_path = "/Users/alecrichmond/STALL10N/test_upload.xml"
with open(xml_path, 'w') as f:
    f.write(test_xml_content)
print(f"Created test XML: {xml_path}")

# Create ZIP file
zip_path = "/Users/alecrichmond/STALL10N/test_upload.zip"
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("test_race.xml", test_xml_content)
print(f"Created test ZIP: {zip_path}")

print("\nTest files created. Try uploading these smaller files to verify the upload works.")