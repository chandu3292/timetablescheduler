import urllib.request
import time

print("Waiting for server to start...")
time.sleep(3)

try:
    response = urllib.request.urlopen('http://localhost:8000')
    print('✓ Server is running!')
    print('Status:', response.status)
except Exception as e:
    print('✗ Server not responding:', str(e))
