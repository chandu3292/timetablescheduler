import os
import sys
import django
import codecs

import logging
logging.getLogger().setLevel(logging.CRITICAL)

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Scheduler.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from SchedulerApp.models import Year, TIME_SLOTS
from SchedulerApp.views import ConstraintScheduler, Data

year = Year.objects.get(year_name='3rd Year')
scheduler = ConstraintScheduler()
year_data = Data(year)
year_data.elective_time_tracker = {}

schedule = scheduler.build_schedule(year_data, year)
classes = schedule.get_classes()

with open('dump_struct.txt', 'w') as f:
    f.write(str(dir(classes[0])) + "\n")
    for k in dir(classes[0]):
        if not k.startswith('_'):
            try:
                attr = getattr(classes[0], k)
                if callable(attr):
                    f.write(f"{k}(): {attr()}\n")
                else:
                    f.write(f"{k}: {attr}\n")
            except Exception as e:
                f.write(f"{k}: ERROR {e}\n")
