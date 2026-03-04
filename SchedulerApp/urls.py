from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('data-check/', data_check, name='data_check'),
    path('timetableGeneration/', timetable, name='timetable'),
    path('timetable/download/pdf/', download_timetable_pdf, name='download_timetable_pdf'),
    path('timetable/instructor/select/', instructor_timetable_select, name='instructor_timetable_select'),
    path('timetable/instructor/', instructor_timetable, name='instructor_timetable'),
    path('timetable/lab/', lab_timetable, name='lab_timetable'),

    path('instructorAdd/', instructorAdd, name='instructorAdd'),
    path('instructorEdit/', instructorEdit, name='instructorEdit'),
    path('instructorDelete/<int:pk>/', instructorDelete, name='deleteinstructor'),

    path('labRoomAdd/', labRoomAdd, name='labRoomAdd'),
    path('labRoomEdit/', labRoomEdit, name='labRoomEdit'),
    path('labRoomDelete/<int:pk>/', labRoomDelete, name='labRoomDelete'),


    path('meetingTimeAdd/', meetingTimeAdd, name='meetingTimeAdd'),
    path('meetingTimeEdit/', meetingTimeEdit, name='meetingTimeEdit'),
    path('meetingTimeDelete/<str:pk>/', meetingTimeDelete, name='deletemeetingtime'),

    path('courseAdd/', courseAdd, name='courseAdd'),
    path('courseEdit/', courseEdit, name='courseEdit'),
    path('courseDelete/<str:pk>/', courseDelete, name='deletecourse'),

    # path('departmentAdd/', departmentAdd, name='departmentAdd'),
    # path('departmentEdit/', departmentEdit, name='departmentEdit'),
    # path('departmentDelete/<int:pk>/', departmentDelete, name='deletedepartment'),
    path('yearAdd/', yearAdd, name='yearAdd'),
    path('yearEdit/', yearEdit, name='yearEdit'),
    path('yearDelete/<pk>/', yearDelete, name='yearDelete'),

    path('api/genNum/', apiGenNum, name='apiGenNum'),
    path('api/terminateGens/', apiterminateGens, name='apiterminateGens')
]
