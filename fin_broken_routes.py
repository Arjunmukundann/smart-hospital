#!/usr/bin/env python3
"""
Script to find all broken url_for references in Flask templates
"""

import os
import re
from collections import defaultdict

def find_broken_routes(template_dir="app/templates"):
    """Find all url_for references in templates"""
    
    url_for_pattern = re.compile(r"url_for\(['\"]([^'\"]+)['\"]")
    results = defaultdict(list)
    
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            matches = url_for_pattern.findall(line)
                            for match in matches:
                                results[match].append({
                                    'file': filepath,
                                    'line': line_num,
                                    'content': line.strip()
                                })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return results

def main():
    print("=" * 80)
    print("FINDING ALL url_for REFERENCES IN TEMPLATES")
    print("=" * 80)
    
    results = find_broken_routes()
    
    # Group by blueprint
    blueprints = defaultdict(list)
    for route in sorted(results.keys()):
        blueprint = route.split('.')[0] if '.' in route else 'main'
        blueprints[blueprint].append(route)
    
    print("\n📋 ALL ROUTES FOUND IN TEMPLATES:\n")
    for blueprint in sorted(blueprints.keys()):
        print(f"\n[{blueprint.upper()}]")
        for route in sorted(blueprints[blueprint]):
            count = len(results[route])
            print(f"  ✓ {route:<40} ({count} usage{'s' if count > 1 else ''})")
    
    # Known broken routes
    print("\n" + "=" * 80)
    print("⚠️  LIKELY BROKEN ROUTES (based on error messages):")
    print("=" * 80)
    
    broken = [
        'doctor.patient_survey',
        'doctor.patient',
        'doctor.report_upload',
        'patient.reminder_settings'
    ]
    
    for route in broken:
        if route in results:
            print(f"\n❌ {route}")
            for occurrence in results[route]:
                rel_path = occurrence['file'].replace('app/templates/', '')
                print(f"   📄 {rel_path}:{occurrence['line']}")
                print(f"      {occurrence['content'][:80]}...")
    
    print("\n" + "=" * 80)
    print("💡 SUGGESTED FIXES:")
    print("=" * 80)
    print("""
1. doctor.patient_survey → doctor.search_patient (or remove if not needed)
2. doctor.report_upload → doctor.upload_report (or create the route)
3. patient.reminder_settings → admin.reminder_settings (or create patient version)
    """)

if __name__ == '__main__':
    main()