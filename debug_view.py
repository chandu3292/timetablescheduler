import urllib.request
import urllib.parse

# Debug what the view is actually receiving and setting
url = 'http://localhost:8000/timetable/view/?view_type=period&day=Monday&time=8:45%20-%209:45'

# Save the response to a file
response = urllib.request.urlopen(url)
content = response.read().decode('utf-8')

# Save to file for inspection
with open('debug_response.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Saved response to debug_response.html ({len(content)} bytes)')

# Look for specific template variables
indicators = [
    'view_type',
    'selected_day',
    'selected_time',
    'results-section',
    'Period-wise',
]

print('\nSearching for indicators in HTML:')
for ind in indicators:
    count = content.count(ind)
    print(f'  {ind}: {count} occurrences')

# Check if the page is showing the login form instead
if 'password' in content.lower() and 'login' in content.lower():
    print('\n⚠️  WARNING: Page is showing LOGIN FORM!')
    print('   You need to be logged in to view this page.')
