import urllib.request
import urllib.parse

print("=" * 70)
print("TESTING ALL VIEW TYPES")
print("=" * 70)

tests = [
    {
        'name': 'Section-wise View (Year 1, Section 1)',
        'url': 'http://localhost:8000/timetable/view/?view_type=section&year=11&section=1',
        'success_indicators': ['timetable-grid', '1st Year', 'Section 1']
    },
    {
        'name': 'Year-wise View (Year 1)',
        'url': 'http://localhost:8000/timetable/view/?view_type=year&year=11',
        'success_indicators': ['timetable-grid', '1st Year', 'All Sections']
    },
    {
        'name': 'Faculty-wise View (All Faculties)',
        'url': 'http://localhost:8000/timetable/view/?view_type=faculty&all_faculties=true',
        'success_indicators': ['timetable-grid', 'All Faculties']
    },
    {
        'name': 'Lab-wise View (All Labs)',
        'url': 'http://localhost:8000/timetable/view/?view_type=lab&all_labs=true',
        'success_indicators': ['timetable-grid', 'All Labs']
    },
    {
        'name': 'Period-wise View (Monday 8:45-9:45)',
        'url': 'http://localhost:8000/timetable/view/?view_type=period&day=Monday&time=' + urllib.parse.quote('8:45 - 9:45'),
        'success_indicators': ['Faculty Availability', 'Monday', '8:45']
    },
]

results = []
for test in tests:
    print(f"\n{test['name']}")
    print("-" * 70)
    try:
        response = urllib.request.urlopen(test['url'])
        content = response.read().decode('utf-8')
        
        if response.status == 200:
            # Check for success indicators
            found_indicators = []
            missing_indicators = []
            
            for indicator in test['success_indicators']:
                if indicator in content:
                    found_indicators.append(indicator)
                else:
                    missing_indicators.append(indicator)
            
            has_results = 'results-section' in content
            class_count = content.count('class-card')
            
            if has_results and len(found_indicators) >= 2:
                print(f"  ✓ PASS - Status: {response.status}")
                print(f"  ✓ Results section found")
                print(f"  ✓ Found indicators: {', '.join(found_indicators)}")
                if class_count > 0:
                    print(f"  ✓ Class cards: {class_count}")
                results.append({'test': test['name'], 'status': 'PASS'})
            else:
                print(f"  ⚠ PARTIAL - Status: {response.status}")
                print(f"  - Has results section: {has_results}")
                print(f"  - Found: {found_indicators}")
                print(f"  - Missing: {missing_indicators}")
                print(f"  - Page size: {len(content)} bytes")
                results.append({'test': test['name'], 'status': 'PARTIAL'})
        else:
            print(f"  ✗ FAIL - Status: {response.status}")
            results.append({'test': test['name'], 'status': 'FAIL'})
            
    except Exception as e:
        print(f"  ✗ ERROR - {str(e)[:100]}")
        results.append({'test': test['name'], 'status': 'ERROR'})

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
for result in results:
    status_symbol = '✓' if result['status'] == 'PASS' else ('⚠' if result['status'] == 'PARTIAL' else '✗')
    print(f"{status_symbol} {result['test']}: {result['status']}")

pass_count = sum(1 for r in results if r['status'] == 'PASS')
print(f"\nPassed: {pass_count}/{len(results)}")
