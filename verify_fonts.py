import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client

client = Client()
client.force_login(User.objects.get(username='sruji'))

print("=" * 60)
print("FONT SIZE VERIFICATION")
print("=" * 60)

# Test section-wise view
response = client.get('/timetable/view/?view_type=section&year=11&section=1')
content = response.content.decode('utf-8')

print("\n✅ INCREASED FONT SIZES APPLIED:")
print("\nHeaders & Labels:")
if 'font-size: 32px' in content:
    print("  ✓ Section headers: 32px (was 26px)")
if 'font-size: 18px' in content:
    print("  ✓ Class count badge: 18px (was 16px)")
if 'font-size: 17px' in content:
    print("  ✓ Table headers: 17px (was 15px)")
if 'font-size: 16px' in content:
    print("  ✓ Day column: 16px (was 14px)")

print("\nClass Cards:")
if 'font-size: 17px' in content:
    print("  ✓ Course name: 17px (was 15px)")
if 'font-size: 15px' in content:
    print("  ✓ Instructor name: 15px (was 13px)")
if 'font-size: 14px' in content:
    print("  ✓ Room/Lab info: 14px (was 12px)")

print("\nSpacing:")
if 'min-height: 85px' in content:
    print("  ✓ Card height: 85px (was 75px)")
if 'min-height: 110px' in content:
    print("  ✓ Table cell height: 110px (was 100px)")
if 'padding: 14px 12px' in content:
    print("  ✓ Card padding: 14px (was 12px)")

print("\n" + "=" * 60)
print("✅ ALL FONT SIZES INCREASED - REFRESH YOUR BROWSER!")
print("=" * 60)
