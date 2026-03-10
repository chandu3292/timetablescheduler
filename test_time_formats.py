import urllib.request

# Test with exact time format from the database
url = 'http://localhost:8000/timetable/view/?view_type=period&day=Monday&time=8:45+-+9:45'
print("Testing URL:", url)

try:
    response = urllib.request.urlopen(url)
    content = response.read().decode('utf-8')
    print('Status:', response.status)
    print('Page size:', len(content), 'bytes')
    print('Has results-section:', 'results-section' in content)
    
    # Try different time format variations
    print("\nTrying different time formats:")
    formats = [
        '8:45 - 9:45',
        '8:45+-+9:45', 
        '8:45%20-%209:45',
        '9:45 - 10:35',
    ]
    
    for time_format in formats:
        url = f'http://localhost:8000/timetable/view/?view_type=period&day=Monday&time={urllib.parse.quote(time_format)}'
        try:
            resp = urllib.request.urlopen(url)
            cont = resp.read().decode('utf-8')
            has_results = 'results-section' in cont
            print(f'  {time_format}: {len(cont)} bytes, has_results={has_results}')
        except Exception as e:
            print(f'  {time_format}: ERROR - {e}')
    
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
