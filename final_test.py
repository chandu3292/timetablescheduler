import urllib.request
import urllib.parse

# Test the Period-wise view with parameters
url = 'http://localhost:8000/timetable/view/?view_type=period&day=Monday&time=' + urllib.parse.quote('8:45 - 9:45')
print("Testing:", url)
print("=" * 70)

try:
    response = urllib.request.urlopen(url)
    content = response.read().decode('utf-8')
    
    print('✓ Status:', response.status)
    print('✓ Page size:', len(content), 'bytes')
    print()
    
    # Check for debug box
    if '🔍 DEBUG INFO' in content:
        print('✓ DEBUG BOX FOUND!')
        # Extract debug info
        start = content.find('🔍 DEBUG INFO')
        end = content.find('END DEBUG INFO', start)
        if end > start:
            debug_section = content[start:end]
            print(debug_section[:500])
    else:
        print('✗ No debug box found')
    
    print()
    print('Checking for elements:')
    print('  results-section:', 'results-section' in content)
    print('  Faculty Availability:', 'Faculty Availability' in content)
    print('  Free Faculty:', 'Free Faculty' in content)
    print('  faculty-card:', content.count('faculty-card'), 'cards')
    
except Exception as e:
    print('✗ Error:', e)
    import traceback
    traceback.print_exc()
