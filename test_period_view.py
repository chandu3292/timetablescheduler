import urllib.request

# Test the Period-wise view directly
url = 'http://localhost:8000/timetable/view/?view_type=period&day=Monday&time=8:45%20-%209:45'
print("Testing URL:", url)
print("=" * 70)

try:
    response = urllib.request.urlopen(url)
    content = response.read().decode('utf-8')
    print('✓ Status:', response.status)
    print('✓ Page size:', len(content), 'bytes')
    print()
    
    # Check for key elements
    checks = [
        ('results-section', 'Results section'),
        ('Free Faculty', 'Free Faculty header'),
        ('Busy Faculty', 'Busy Faculty header'),
        ('Faculty Availability', 'Availability header'),
        ('faculty-card', 'Faculty cards'),
        ('Timetable loaded successfully', 'Success banner'),
    ]
    
    for search_term, description in checks:
        found = search_term in content
        status = '✓' if found else '✗'
        print(f'{status} {description}: {found}')
        if found and search_term == 'faculty-card':
            count = content.count(search_term)
            print(f'   → Found {count} faculty cards')
    
    print()
    print("=" * 70)
    
    # Extract a snippet showing the results section
    if 'results-section' in content:
        idx = content.find('results-section')
        snippet = content[idx:idx+500]
        print("Results section preview:")
        print(snippet[:300])
    else:
        print("✗ No results section found!")
        
except Exception as e:
    print('✗ Error:', e)
    import traceback
    traceback.print_exc()
