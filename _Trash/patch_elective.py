import re

with open('SchedulerApp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """    logger.info(f"Pre-allocating times for {len(elective_courses)} courses needing section alignment...")
    logger.info(f"  Aligned courses: {[c.course_number for c in elective_courses]}")

    if meeting_times:
        global_used_times = []
        for course in elective_courses:
            # Calculate how many hours need single periods vs continuous
            total_hours = course.hours_per_week
            continuous_hours = course.max_continuous_hours if course.max_continuous_hours > 1 else 0
            single_hours = total_hours - continuous_hours

            # Track times used for continuous blocks to avoid overlap
            used_times = []

            # FIRST: Pre-allocate continuous block(s) if needed
            if continuous_hours > 0:
                # Group meeting times by day and find valid continuous blocks
                day_groups = {}
                for mt in meeting_times:
                    if mt not in global_used_times:
                        day_groups.setdefault(mt.day, []).append(mt)

                for day in day_groups:
                    day_groups[day].sort(key=lambda x: TIME_SLOTS.index((x.time, x.time)))

                valid_blocks = []
                for day, times in day_groups.items():
                    for i in range(len(times) - course.max_continuous_hours + 1):
                        block = times[i:i + course.max_continuous_hours]
                        if not any(t.time == "12:15 - 1:05" for t in block):
                            is_contiguous = True
                            for j in range(len(block)-1):
                                idx1 = TIME_SLOTS.index((block[j].time, block[j].time))
                                idx2 = TIME_SLOTS.index((block[j+1].time, block[j+1].time))
                                if idx2 != idx1 + 1:
                                    is_contiguous = False
                                    break
                            if is_contiguous:
                                valid_blocks.append(block)

                if valid_blocks:
                    block_key = f"{course.course_number}_continuous"
                    import random
                    selected_block = random.choice(valid_blocks)
                    data.elective_time_tracker[block_key] = selected_block
                    logger.info(f"  {course.course_number} continuous: {selected_block[0].day} {[mt.time for mt in selected_block]}")
                    used_times.extend(selected_block)
                    global_used_times.extend(selected_block)

            # SECOND: Pre-allocate single period times from REMAINING times (exclude continuous block times)
            if single_hours > 0:
                available_times = [mt for mt in meeting_times if mt not in used_times and mt not in global_used_times]
                if len(available_times) >= single_hours:
                    single_key = f"{course.course_number}_single"
                    import random
                    def fragmentation_score(mt):
                        if mt.time in ['8:45 - 9:45', '11:25 - 12:15', '1:05 - 1:55', '2:45 - 3:35']: return random.randint(0,10)
                        if mt.time in ['9:45 - 10:35', '10:35 - 11:25', '1:55 - 2:45']: return 100 + random.randint(0,10)
                        return 50
                    available_times.sort(key=fragmentation_score)
                    selected_times = available_times[:single_hours]
                    data.elective_time_tracker[single_key] = selected_times  # Store as LIST
                    global_used_times.extend(selected_times)
                    logger.info(f"  {course.course_number} single ({single_hours} periods): {[(t.day, t.time) for t in selected_times]}")

                    # Also create index tracker for each section
                    index_key = f"{course.course_number}_single_index"
                    data.elective_time_tracker[index_key] = {}"""

pattern = re.compile(r'    logger\.info\(f"Pre-allocating times for \{len\(elective_courses\)\} courses needing section alignment\.\.\."\).*?data\.elective_time_tracker\[index_key\] = \{\}', re.DOTALL)

if pattern.search(content):
    content = pattern.sub(replacement, content)
    with open('SchedulerApp/views.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully!")
else:
    print("Could not find the block to replace!")