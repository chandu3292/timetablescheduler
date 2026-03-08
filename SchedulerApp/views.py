"""
Timetable Scheduler – GA + Simulated Annealing hybrid
======================================================
Hard constraints (penalty 100 each):
  H1  Instructor clash          – same instructor, same day+time, any year
  H2  Section clash             – same (year,section), same meeting_time
  H3  Lab continuity            – lab hours not consecutive / crosses lunch
  H4  Elective not synced       – same (year,course), different time across sections
  H5  Lab not in correct room   – course.lab_rooms not respected
  H6  Lab room clash            – same lab_room, same day+time
  H7  hours_per_week not met    – 100 per missing hour

Soft constraints:
  S1  All theory on one day     – 80
  S2  Exceeds max_continuous    – 80 per run
  S3  Gap in morning/afternoon  – 20 per gap slot
  S4  Shortfall vs schedule     – 20 per missing hour
  S5  Same-course same-day dup  – 0.5 per extra occurrence
  S6  Special period not last   – 5 per hour not in last slots
"""

import math
import random
import logging
from collections import defaultdict

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .models import (
    Instructor, LabRoom, Course, Department, Year, MeetingTime,
    CourseInstructorAssignment, SpecialPeriod, GeneratedTimetable,
    TimetableEntry, LabBatchAssignment, TIME_SLOTS, DAYS_OF_WEEK,
)

logger = logging.getLogger(__name__)

# ── GA / SA constants ──────────────────────────────────────────────────────────
POPULATION_SIZE         = 50
NUMB_OF_ELITE_SCHEDULES = 3
TOURNAMENT_SIZE         = 5
MUTATION_RATE           = 0.08
RESTART_AFTER           = 15
MAX_GENERATIONS         = 1000
TARGET_FITNESS          = 0.90

SA_INITIAL_TEMP = 5.0
SA_COOLING_RATE = 0.95
SA_MIN_TEMP     = 0.01
SA_APPLY_EVERY  = 3

P_HARD             = 100
P_SOFT_A           = 80
P_SOFT_B           = 20
P_SOFT_C           = 0.5
P_SPECIAL_NOT_LAST = 5
PENALTY_NORM       = 500.0

VARS = {'generationNum': 0, 'terminateGens': False}

# ── Time-slot helpers ──────────────────────────────────────────────────────────
_TIME_SLOT_INDEX  = {t[0]: i for i, t in enumerate(TIME_SLOTS)}
_LUNCH_BOUNDARY   = {3}          # slot index 3 (11:25-12:15) → 4 (1:05-1:55) crosses lunch
_PREFER_SPECIAL_IDX = len(TIME_SLOTS) - 2   # prefer slots from index 5 (1:55-2:45) onwards


def _is_consecutive(indices):
    for i in range(len(indices) - 1):
        if indices[i + 1] != indices[i] + 1:
            return False
        if indices[i] in _LUNCH_BOUNDARY:
            return False
    return True


def _slot_idx(mt):
    return _TIME_SLOT_INDEX.get(mt.time, -1)


# ── Data container ─────────────────────────────────────────────────────────────
class Data:
    def __init__(self):
        self._instructors   = list(Instructor.objects.all())
        self._lab_rooms     = list(LabRoom.objects.all())
        self._courses       = list(Course.objects.prefetch_related('instructors', 'lab_rooms').all())
        self._years         = list(Year.objects.prefetch_related('courses').all())
        self._meeting_times = list(MeetingTime.objects.select_related('year').all())
        self._cias          = list(CourseInstructorAssignment.objects.prefetch_related(
            'instructors').select_related('course', 'year').all())
        self._specials      = list(SpecialPeriod.objects.select_related('year', 'instructor').all())

        # year_id → list[MeetingTime]
        self._mts_by_year = defaultdict(list)
        for mt in self._meeting_times:
            if mt.year_id:
                self._mts_by_year[mt.year_id].append(mt)

        # year_id → list[Course]
        self._courses_by_year = defaultdict(list)
        for year in self._years:
            self._courses_by_year[year.id] = list(year.courses.all())

        # year_id → list[CIA]
        self._cias_by_year = defaultdict(list)
        for cia in self._cias:
            self._cias_by_year[cia.year_id].append(cia)

        # (year_id, section_number, course_number) → CIA
        self._cia_lookup = {}
        for cia in self._cias:
            self._cia_lookup[(cia.year_id, cia.section_number, cia.course_id)] = cia

        # year_id → list[SpecialPeriod]
        self._specials_by_year = defaultdict(list)
        for sp in self._specials:
            self._specials_by_year[sp.year_id].append(sp)

        # year_id → {length: [[MeetingTime,…],…]}
        self._lab_blocks_by_year = {}
        for year in self._years:
            self._lab_blocks_by_year[year.id] = self._compute_lab_blocks(
                self._mts_by_year[year.id])

        # Build course_number → Course lookup (with prefetched M2M)
        self._course_lookup = {c.course_number: c for c in self._courses}

        # Pre-cache M2M on CIA objects; replace cia.course with the pre-fetched instance
        for cia in self._cias:
            cia._cached_insts = list(cia.instructors.all())
            # Replace the select_related course with the prefetched one so
            # _cached_lab_rooms is available
            prefetched = self._course_lookup.get(cia.course_id)
            if prefetched:
                cia.course = prefetched

        for c in self._courses:
            c._cached_lab_rooms = list(c.lab_rooms.all())

        # Also patch courses_by_year to use prefetched instances
        for year_id, courses in self._courses_by_year.items():
            self._courses_by_year[year_id] = [
                self._course_lookup.get(c.course_number, c) for c in courses
            ]

    def _compute_lab_blocks(self, mts):
        by_day = defaultdict(list)
        for mt in mts:
            idx = _slot_idx(mt)
            if idx >= 0:
                by_day[mt.day].append((idx, mt))
        for d in by_day:
            by_day[d].sort(key=lambda x: x[0])
        blocks = {2: [], 3: [], 4: []}
        for day, slots in by_day.items():
            for length in (2, 3, 4):
                for i in range(len(slots) - length + 1):
                    indices = [slots[i + j][0] for j in range(length)]
                    mts_    = [slots[i + j][1] for j in range(length)]
                    if _is_consecutive(indices):
                        blocks[length].append(mts_)
        return blocks

    def get_lab_blocks(self, year_id, length):
        return self._lab_blocks_by_year.get(year_id, {}).get(length, [])

    def years(self):              return self._years
    def lab_rooms(self):          return self._lab_rooms
    def mts_for_year(self, yid):  return self._mts_by_year.get(yid, [])
    def courses_for_year(self, yid): return self._courses_by_year.get(yid, [])
    def cias_for_year(self, yid): return self._cias_by_year.get(yid, [])
    def specials_for_year(self, yid): return self._specials_by_year.get(yid, [])


_data = None   # refreshed each timetable request


# ── Gene ──────────────────────────────────────────────────────────────────────
class Gene:
    """One scheduled block: year+section+course → meeting_times+instructor+lab_room."""
    __slots__ = ('year_id', 'section', 'course', 'meeting_times',
                 'instructor', 'lab_room', 'batch', 'is_special')

    def __init__(self, year_id, section, course, meeting_times,
                 instructor=None, lab_room=None, batch='FULL', is_special=False):
        self.year_id       = year_id
        self.section       = section
        self.course        = course
        self.meeting_times = meeting_times   # list[MeetingTime]
        self.instructor    = instructor
        self.lab_room      = lab_room
        self.batch         = batch
        self.is_special    = is_special

    def copy(self):
        return Gene(self.year_id, self.section, self.course,
                    list(self.meeting_times), self.instructor,
                    self.lab_room, self.batch, self.is_special)


class _PseudoCourse:
    """Lightweight course-like wrapper for SpecialPeriod genes."""
    def __init__(self, sp):
        self.course_number        = f'SP_{sp.period_type}'
        self.course_name          = sp.period_type
        self.course_type          = 'THEORY'
        self.hours_per_week       = sp.hours_per_week
        self.max_continuous_hours = sp.continuous_hours
        self.split_into_batches   = False
        self._cached_lab_rooms    = []


# ── Schedule ──────────────────────────────────────────────────────────────────
class Schedule:
    def __init__(self, genes=None):
        self._genes   = genes if genes is not None else []
        self._fitness = -1.0
        self._penalty = 0
        self._dirty   = True

    def genes(self):
        return self._genes

    def invalidate(self):
        self._dirty = True

    def getFitness(self):
        if self._dirty:
            self._penalty, self._fitness = self._calc()
            self._dirty = False
        return self._fitness

    def getNumbOfConflicts(self):
        self.getFitness()
        return self._penalty

    # ── random initialisation ─────────────────────────────────────────────────
    @classmethod
    def random(cls):
        genes = []
        d     = _data

        # Cross-year/cross-section tracking to prevent H1 and H6 at init time
        room_daytime_used: dict = {}   # (room_id, day, time) → True
        inst_daytime_used: dict = {}   # (inst_id, day, time)  → True

        for year in d.years():
            year_id  = year.id
            year_mts = d.mts_for_year(year_id)
            if not year_mts:
                continue

            # ── Elective: pre-assign ONE slot-set per (year, course) ──────────
            elec_slots  = {}          # course_number → [MeetingTime]
            global_used = set()       # pids committed to electives/specials

            elec_courses = [c for c in d.courses_for_year(year_id)
                            if c.course_type == 'ELECTIVE']
            for c in elec_courses:
                hrs  = max(c.hours_per_week, 1)
                free = [mt for mt in year_mts if mt.pid not in global_used]
                chosen = random.sample(free, min(hrs, len(free))) if free else []
                elec_slots[c.course_number] = chosen
                global_used.update(mt.pid for mt in chosen)

            # ── Special periods: prefer last slots ───────────────────────────
            special_slots = {}        # period_type → [MeetingTime]
            for sp in d.specials_for_year(year_id):
                hrs  = max(sp.hours_per_week, 1)
                pref = [mt for mt in year_mts
                        if _slot_idx(mt) >= _PREFER_SPECIAL_IDX
                        and mt.pid not in global_used]
                pool = pref or [mt for mt in year_mts if mt.pid not in global_used]
                chosen = random.sample(pool, min(hrs, len(pool))) if pool else []
                special_slots[sp.period_type] = chosen
                global_used.update(mt.pid for mt in chosen)

            for sec in (1, 2, 3):
                cias = [cia for cia in d.cias_for_year(year_id)
                        if cia.section_number == sec]
                if not cias:
                    continue

                # Pre-seed with globally reserved elective+special pids so
                # labs don't grab those slots
                used = set(global_used)   # pids used in this section

                # Priority 1 – LABs (longest first)
                lab_cias = sorted(
                    [cia for cia in cias if cia.course.course_type == 'LAB'],
                    key=lambda cia: (-cia.course.max_continuous_hours,
                                    -cia.course.hours_per_week)
                )
                for cia in lab_cias:
                    c = cia.course
                    if c.split_into_batches:
                        pass   # treat as regular lab; LabBatchAssignment is admin metadata
                    hrs     = max(c.hours_per_week, 1)
                    con_len = min(c.max_continuous_hours, hrs, 4)
                    inst    = random.choice(cia._cached_insts) if cia._cached_insts else None
                    lr_pool = c._cached_lab_rooms or d.lab_rooms()

                    placed = 0
                    while placed < hrs:
                        need      = min(con_len, hrs - placed)
                        inst_busy = {(dy, ti)
                                     for (iid, dy, ti) in inst_daytime_used
                                     if inst and iid == inst.id}

                        def _sec_free(b):
                            return (not any(mt.pid in used for mt in b)
                                    and not any((mt.day, mt.time) in inst_busy for mt in b))

                        def _has_free_room(b):
                            return any(
                                not any(room_daytime_used.get((r.id, mt.day, mt.time))
                                        for mt in b)
                                for r in lr_pool) if lr_pool else True

                        # Best: section-free AND has a free room
                        avail = [b for b in d.get_lab_blocks(year_id, need)
                                 if _sec_free(b) and _has_free_room(b)]
                        if not avail:
                            # Relax room constraint
                            avail = [b for b in d.get_lab_blocks(year_id, need)
                                     if _sec_free(b)]
                        if not avail:
                            # Relax instructor constraint too
                            avail = [b for b in d.get_lab_blocks(year_id, need)
                                     if not any(mt.pid in used for mt in b)
                                     and _has_free_room(b)]
                        if not avail:
                            avail = [b for b in d.get_lab_blocks(year_id, need)
                                     if not any(mt.pid in used for mt in b)]
                        if avail:
                            block = random.choice(avail)
                        else:
                            free = [mt for mt in year_mts if mt.pid not in used]
                            if not free:
                                break
                            block = [random.choice(free)]

                        # Pick a free room for this block
                        lr = None
                        if lr_pool:
                            free_rooms = [r for r in lr_pool
                                          if not any(room_daytime_used.get((r.id, mt.day, mt.time))
                                                     for mt in block)]
                            lr = random.choice(free_rooms) if free_rooms else random.choice(lr_pool)
                        if lr:
                            for mt in block:
                                room_daytime_used[(lr.id, mt.day, mt.time)] = True
                        if inst:
                            for mt in block:
                                inst_daytime_used[(inst.id, mt.day, mt.time)] = True
                        genes.append(Gene(year_id, sec, c, block, inst, lr))
                        used.update(mt.pid for mt in block)
                        placed += len(block)

                # Priority 2 – ELECTIVEs (synced)
                for cia in cias:
                    c = cia.course
                    if c.course_type != 'ELECTIVE':
                        continue
                    inst = random.choice(cia._cached_insts) if cia._cached_insts else None
                    mts  = elec_slots.get(c.course_number, [])
                    if mts:
                        if inst:
                            for mt in mts:
                                inst_daytime_used[(inst.id, mt.day, mt.time)] = True
                        genes.append(Gene(year_id, sec, c, list(mts), inst))
                        used.update(mt.pid for mt in mts)

                # Priority 3 – THEORY
                theo_cias = [cia for cia in cias if cia.course.course_type == 'THEORY']
                for cia in theo_cias:
                    c    = cia.course
                    hrs  = max(c.hours_per_week, 1)
                    inst = random.choice(cia._cached_insts) if cia._cached_insts else None
                    inst_busy = {(dy, ti)
                                 for (iid, dy, ti) in inst_daytime_used
                                 if inst and iid == inst.id}
                    for _ in range(hrs):
                        free = [mt for mt in year_mts
                                if mt.pid not in used
                                and (mt.day, mt.time) not in inst_busy]
                        if not free:
                            free = [mt for mt in year_mts if mt.pid not in used]
                        if not free:
                            break
                        mt = random.choice(free)
                        if inst:
                            inst_daytime_used[(inst.id, mt.day, mt.time)] = True
                            inst_busy.add((mt.day, mt.time))
                        genes.append(Gene(year_id, sec, c, [mt], inst))
                        used.add(mt.pid)

                # Priority 4 – SPECIAL PERIODS
                for sp in d.specials_for_year(year_id):
                    mts = special_slots.get(sp.period_type, [])
                    if mts:
                        pseudo = _PseudoCourse(sp)
                        inst   = sp.instructor
                        if inst:
                            for mt in mts:
                                inst_daytime_used[(inst.id, mt.day, mt.time)] = True
                        genes.append(Gene(year_id, sec, pseudo, list(mts),
                                          inst, is_special=True))

        return cls(genes)

    # ── fitness ───────────────────────────────────────────────────────────────
    def _calc(self):
        penalty = 0
        genes   = self._genes

        # Build lookup structures in one pass
        inst_dt   = defaultdict(list)   # (inst_id, day, time) → [Gene]
        sec_pid   = defaultdict(list)   # (year_id, sec, pid)  → [Gene]
        elec_pids = defaultdict(lambda: defaultdict(set))  # (year_id,cnum) → {sec→pids}
        room_dt   = defaultdict(list)   # (room_id, day, time) → [Gene]
        chours    = defaultdict(int)    # (year_id, sec, cnum) → hours placed

        for g in genes:
            for mt in g.meeting_times:
                if g.instructor and isinstance(g.instructor, Instructor):
                    inst_dt[(g.instructor.id, mt.day, mt.time)].append(g)
                sec_pid[(g.year_id, g.section, mt.pid)].append(g)
                if g.course.course_type == 'ELECTIVE':
                    elec_pids[(g.year_id, g.course.course_number)][g.section].add(mt.pid)
                if g.lab_room:
                    room_dt[(g.lab_room.id, mt.day, mt.time)].append(g)
            chours[(g.year_id, g.section, g.course.course_number)] += len(g.meeting_times)

        # H1 – instructor clash (cross-year)
        for occ in inst_dt.values():
            if len(occ) > 1:
                penalty += P_HARD * (len(occ) - 1)

        # H2 – section clash
        for occ in sec_pid.values():
            if len(occ) > 1:
                penalty += P_HARD * (len(occ) - 1)

        # H3 – lab continuity
        for g in genes:
            if g.course.course_type == 'LAB' and len(g.meeting_times) > 1:
                if not _is_consecutive([_slot_idx(mt) for mt in g.meeting_times]):
                    penalty += P_HARD

        # H4 – elective sync
        for (yid, cnum), sec_map in elec_pids.items():
            if len(sec_map) > 1:
                unique = set(frozenset(v) for v in sec_map.values())
                if len(unique) > 1:
                    penalty += P_HARD * (len(unique) - 1)

        # H5 – lab must use allowed lab rooms
        for g in genes:
            if g.course.course_type == 'LAB' and g.lab_room:
                allowed = g.course._cached_lab_rooms
                if allowed and g.lab_room not in allowed:
                    penalty += P_HARD

        # H6 – lab room clash (cross-year)
        for occ in room_dt.values():
            if len(occ) > 1:
                penalty += P_HARD * (len(occ) - 1)

        # H7 – hours_per_week completeness
        seen_hpw = set()
        for g in genes:
            key = (g.year_id, g.section, g.course.course_number)
            if key in seen_hpw:
                continue
            seen_hpw.add(key)
            req = g.course.hours_per_week
            if req > 0:
                actual = chours[key]
                if actual < req:
                    penalty += P_HARD * (req - actual)

        # ── soft constraints ──────────────────────────────────────────────────
        MORNING_SET   = set(range(4))
        AFTERNOON_SET = set(range(4, len(TIME_SLOTS)))

        by_sec = defaultdict(list)
        for g in genes:
            by_sec[(g.year_id, g.section)].append(g)

        for sec_genes in by_sec.values():
            theo_days  = set()
            theo_count = 0
            by_day     = defaultdict(list)
            cday_cnt   = defaultdict(int)

            for g in sec_genes:
                for mt in g.meeting_times:
                    idx = _slot_idx(mt)
                    if idx < 0:
                        continue
                    by_day[mt.day].append(idx)
                    cday_cnt[(g.course.course_number, mt.day)] += 1
                    if g.course.course_type == 'THEORY':
                        theo_days.add(mt.day)
                        theo_count += 1

            # S1 – all theory on one day
            if theo_count > 1 and len(theo_days) == 1:
                penalty += P_SOFT_A

            for day, idxs in by_day.items():
                idxs_s = sorted(idxs)

                # S2 – max_continuous_hours exceeded (check per-gene on this day)
                for g in sec_genes:
                    g_idxs = sorted(_slot_idx(mt)
                                    for mt in g.meeting_times if mt.day == day)
                    if not g_idxs:
                        continue
                    run = 1
                    for k in range(1, len(g_idxs)):
                        if (g_idxs[k] == g_idxs[k-1] + 1
                                and g_idxs[k-1] not in _LUNCH_BOUNDARY):
                            run += 1
                            if run > g.course.max_continuous_hours:
                                penalty += P_SOFT_A
                                break
                        else:
                            run = 1

                # S3 – gaps in morning / afternoon blocks
                for seg in (
                    sorted(i for i in idxs_s if i in MORNING_SET),
                    sorted(i for i in idxs_s if i in AFTERNOON_SET),
                ):
                    if len(seg) >= 2:
                        penalty += P_SOFT_B * (seg[-1] - seg[0] + 1 - len(seg))

            # S5 – same-course same-day repetition
            for cnt in cday_cnt.values():
                if cnt > 1:
                    penalty += P_SOFT_C * (cnt - 1)

        # S6 – special periods not in last slots
        for g in genes:
            if g.is_special:
                for mt in g.meeting_times:
                    if _slot_idx(mt) < _PREFER_SPECIAL_IDX:
                        penalty += P_SPECIAL_NOT_LAST

        fitness = 1.0 / (1.0 + penalty / PENALTY_NORM)
        return int(penalty), fitness

    # ── local search repair ───────────────────────────────────────────────────
    def local_search_repair(self, full=False):
        max_att = 50 if full else 20
        d = _data

        def _free(year_id, occupied):
            return [mt for mt in d.mts_for_year(year_id) if mt.pid not in occupied]

        def _reassign(g, occupied):
            if len(g.meeting_times) > 1:
                # Multi-hour lab: only allow same-length block reassignment.
                # Never reduce to fewer hours (would create H7 shortfall).
                length = len(g.meeting_times)
                avail  = [b for b in d.get_lab_blocks(g.year_id, length)
                          if not any(mt.pid in occupied for mt in b)]
                if avail:
                    g.meeting_times = list(random.choice(avail))
                    return True
                return False   # can't fix without breaking hours
            free = _free(g.year_id, occupied)
            if free:
                g.meeting_times = [random.choice(free)]
                return True
            return False

        for _ in range(max_att):
            # Phase 1 – section-internal clashes
            by_sec = defaultdict(list)
            for g in self._genes:
                by_sec[(g.year_id, g.section)].append(g)
            for sg in by_sec.values():
                used = {}
                for g in sg:
                    if any(mt.pid in used for mt in g.meeting_times):
                        _reassign(g, set(used.keys()))
                    for mt in g.meeting_times:
                        used.setdefault(mt.pid, g)

            # Phase 2 – instructor clashes (cross-year, day+time based)
            # Must use (day,time) keys – different years have different pids for same slot
            inst_dt = defaultdict(list)
            for g in self._genes:
                if g.instructor and isinstance(g.instructor, Instructor):
                    for mt in g.meeting_times:
                        inst_dt[(g.instructor.id, mt.day, mt.time)].append(g)
            for occ in inst_dt.values():
                if len(occ) <= 1:
                    continue
                for g in occ[1:]:
                    # Day+times the instructor is already teaching (excluding this gene)
                    inst_dts = {(mt.day, mt.time)
                                for gg in self._genes
                                if gg.instructor and isinstance(gg.instructor, Instructor)
                                and gg.instructor.id == g.instructor.id and gg is not g
                                for mt in gg.meeting_times}
                    sec_pids = {mt.pid for gg in self._genes
                                if gg.year_id == g.year_id
                                and gg.section == g.section and gg is not g
                                for mt in gg.meeting_times}
                    if len(g.meeting_times) > 1:
                        length = len(g.meeting_times)
                        avail  = [b for b in d.get_lab_blocks(g.year_id, length)
                                  if not any(mt.pid in sec_pids for mt in b)
                                  and not any((mt.day, mt.time) in inst_dts for mt in b)]
                        if avail:
                            g.meeting_times = list(random.choice(avail))
                    else:
                        free = [mt for mt in d.mts_for_year(g.year_id)
                                if mt.pid not in sec_pids
                                and (mt.day, mt.time) not in inst_dts]
                        if free:
                            g.meeting_times = [random.choice(free)]

            # Phase 3 – lab room clashes (greedy sequential, most-constrained first)
            # Clear and rebuild room assignments from scratch so fixes don't cascade.
            lab_genes = [g for g in self._genes if g.lab_room]
            # Sort: fewest allowed rooms first (hardest to place first)
            lab_genes.sort(key=lambda g: len(g.course._cached_lab_rooms or d.lab_rooms()))
            rb = {}   # (room_id, day, time) → True  (incrementally built)
            for g in lab_genes:
                allowed = g.course._cached_lab_rooms or d.lab_rooms()
                # Check if current assignment is conflict-free
                if not any(rb.get((g.lab_room.id, mt.day, mt.time)) for mt in g.meeting_times):
                    for mt in g.meeting_times:
                        rb[(g.lab_room.id, mt.day, mt.time)] = True
                    continue
                # Try a different room at the same time slots
                placed = False
                for r in random.sample(allowed, len(allowed)):
                    if not any(rb.get((r.id, mt.day, mt.time)) for mt in g.meeting_times):
                        g.lab_room = r
                        for mt in g.meeting_times:
                            rb[(r.id, mt.day, mt.time)] = True
                        placed = True
                        break
                if placed:
                    continue
                # Try different time slot + room (preserve hour count)
                sec_busy = {mt.pid for gg in self._genes
                            if gg.year_id == g.year_id and gg.section == g.section
                            and gg is not g for mt in gg.meeting_times}
                inst_dts = ({(mt.day, mt.time)
                             for gg in self._genes
                             if gg.instructor and isinstance(gg.instructor, Instructor)
                             and gg.instructor and g.instructor
                             and gg.instructor.id == g.instructor.id and gg is not g
                             for mt in gg.meeting_times}
                            if g.instructor and isinstance(g.instructor, Instructor) else set())
                length = len(g.meeting_times)
                for r in random.sample(allowed, len(allowed)):
                    avail = [b for b in d.get_lab_blocks(g.year_id, length)
                             if not any(mt.pid in sec_busy for mt in b)
                             and not any(rb.get((r.id, mt.day, mt.time)) for mt in b)
                             and not any((mt.day, mt.time) in inst_dts for mt in b)]
                    if avail:
                        g.meeting_times = list(random.choice(avail))
                        g.lab_room = r
                        for mt in g.meeting_times:
                            rb[(r.id, mt.day, mt.time)] = True
                        placed = True
                        break
                if not placed:
                    # Accept conflict but mark anyway to not block others
                    for mt in g.meeting_times:
                        rb[(g.lab_room.id, mt.day, mt.time)] = True

            # Phase 4 – elective synchronization
            elec_grp = defaultdict(list)
            for g in self._genes:
                if g.course.course_type == 'ELECTIVE':
                    elec_grp[(g.year_id, g.course.course_number)].append(g)
            for group in elec_grp.values():
                if len(group) <= 1:
                    continue
                pid_sets = [frozenset(mt.pid for mt in g.meeting_times) for g in group]
                winner   = max(set(pid_sets), key=pid_sets.count)
                ref_mts  = next(g.meeting_times for g in group
                                if frozenset(mt.pid for mt in g.meeting_times) == winner)
                for g in group:
                    if frozenset(mt.pid for mt in g.meeting_times) != winner:
                        g.meeting_times = list(ref_mts)

            self.invalidate()
            if self.getFitness() >= TARGET_FITNESS:
                break

        return self

    # ── SA improvement ────────────────────────────────────────────────────────
    def sa_improve(self, temperature):
        d    = _data
        best = self.getFitness()
        for _ in range(50):
            if not self._genes:
                break
            g       = random.choice(self._genes)
            old_mts = list(g.meeting_times)
            old_lr  = g.lab_room
            mts     = d.mts_for_year(g.year_id)
            if not mts:
                continue

            # Propose new assignment
            if g.course.course_type == 'LAB' and len(g.meeting_times) > 1:
                blocks = d.get_lab_blocks(g.year_id, len(g.meeting_times))
                g.meeting_times = list(random.choice(blocks)) if blocks else [random.choice(mts)]
            else:
                g.meeting_times = [random.choice(mts)]
            if g.course.course_type == 'LAB':
                pool = g.course._cached_lab_rooms or d.lab_rooms()
                if pool:
                    g.lab_room = random.choice(pool)

            self.invalidate()
            new_fit = self.getFitness()
            delta   = new_fit - best
            if delta >= 0:
                best = new_fit
            elif temperature > 1e-9 and random.random() < math.exp(delta / temperature):
                best = new_fit
            else:
                g.meeting_times = old_mts
                g.lab_room      = old_lr
                self.invalidate()
        return self


# ── Genetic Algorithm ─────────────────────────────────────────────────────────
class GeneticAlgorithm:
    def evolve(self, pop):
        return self._mutate(self._crossover(pop))

    def _crossover(self, pop):
        new_pop = list(pop[:NUMB_OF_ELITE_SCHEDULES])
        while len(new_pop) < POPULATION_SIZE:
            p1 = self._tournament(pop)
            p2 = self._tournament(pop)
            new_pop.append(self._cx_pair(p1, p2))
        return new_pop

    def _cx_pair(self, a, b):
        # Group genes by (year_id, section, course_number) and swap whole groups
        # so course structure is never corrupted by index-based slicing
        ga_grp = defaultdict(list)
        for g in a.genes():
            ga_grp[(g.year_id, g.section, g.course.course_number)].append(g)
        gb_grp = defaultdict(list)
        for g in b.genes():
            gb_grp[(g.year_id, g.section, g.course.course_number)].append(g)

        child = []
        for key, ga_group in ga_grp.items():
            if key in gb_grp and random.random() < 0.5:
                child.extend(g.copy() for g in gb_grp[key])
            else:
                child.extend(g.copy() for g in ga_group)
        return Schedule(child)

    def _mutate(self, pop):
        # Smart mutation: avoid H1, H2, H6 by tracking instructor/section/room usage
        d = _data
        for s in pop[NUMB_OF_ELITE_SCHEDULES:]:
            changed = False
            sec_used: dict  = defaultdict(set)   # (year_id, sec) → {pid}
            inst_busy: dict = defaultdict(set)   # inst_id → {(day, time)}
            room_busy: dict = {}                  # (room_id, day, time) → True
            for g in s.genes():
                for mt in g.meeting_times:
                    sec_used[(g.year_id, g.section)].add(mt.pid)
                if g.instructor and isinstance(g.instructor, Instructor):
                    for mt in g.meeting_times:
                        inst_busy[g.instructor.id].add((mt.day, mt.time))
                if g.lab_room:
                    for mt in g.meeting_times:
                        room_busy[(g.lab_room.id, mt.day, mt.time)] = True

            for g in s.genes():
                if random.random() >= MUTATION_RATE:
                    continue
                if g.is_special:
                    continue
                mts = d.mts_for_year(g.year_id)
                if not mts:
                    continue

                my_pids    = {mt.pid for mt in g.meeting_times}
                occupied   = sec_used[(g.year_id, g.section)] - my_pids
                inst        = g.instructor if isinstance(g.instructor, Instructor) else None
                my_dts     = {(mt.day, mt.time) for mt in g.meeting_times}
                i_busy     = (inst_busy[inst.id] - my_dts) if inst else set()

                if g.course.course_type == 'LAB' and len(g.meeting_times) > 1:
                    length = len(g.meeting_times)
                    avail  = [b for b in d.get_lab_blocks(g.year_id, length)
                              if not any(mt.pid in occupied for mt in b)
                              and not any((mt.day, mt.time) in i_busy for mt in b)]
                    if not avail:   # relax instructor constraint
                        avail = [b for b in d.get_lab_blocks(g.year_id, length)
                                 if not any(mt.pid in occupied for mt in b)]
                    new_mts = list(random.choice(avail)) if avail else None
                else:
                    free = [mt for mt in mts
                            if mt.pid not in occupied
                            and (mt.day, mt.time) not in i_busy]
                    if not free:    # relax instructor constraint
                        free = [mt for mt in mts if mt.pid not in occupied]
                    new_mts = [random.choice(free)] if free else None

                if new_mts:
                    # Remove old tracking
                    sec_used[(g.year_id, g.section)] -= my_pids
                    if inst:
                        inst_busy[inst.id] -= my_dts
                    if g.lab_room:
                        for mt in g.meeting_times:
                            room_busy.pop((g.lab_room.id, mt.day, mt.time), None)

                    g.meeting_times = new_mts

                    # Add new tracking
                    for mt in g.meeting_times:
                        sec_used[(g.year_id, g.section)].add(mt.pid)
                    if inst:
                        for mt in g.meeting_times:
                            inst_busy[inst.id].add((mt.day, mt.time))

                    if g.course.course_type == 'LAB':
                        pool = g.course._cached_lab_rooms or d.lab_rooms()
                        if pool:
                            free_rooms = [r for r in pool
                                          if not any(room_busy.get((r.id, mt.day, mt.time))
                                                     for mt in g.meeting_times)]
                            g.lab_room = random.choice(free_rooms) if free_rooms else random.choice(pool)
                        if g.lab_room:
                            for mt in g.meeting_times:
                                room_busy[(g.lab_room.id, mt.day, mt.time)] = True
                    changed = True
            if changed:
                s.invalidate()
        return pop

    def _tournament(self, pop):
        return max(random.sample(pop, min(TOURNAMENT_SIZE, len(pop))),
                   key=lambda s: s.getFitness())


# ── SA state ──────────────────────────────────────────────────────────────────
_sa_temp = SA_INITIAL_TEMP


def _sa_reset():
    global _sa_temp
    _sa_temp = SA_INITIAL_TEMP


def _sa_cool():
    global _sa_temp
    _sa_temp = max(SA_MIN_TEMP, _sa_temp * SA_COOLING_RATE)


# ── Persistence ───────────────────────────────────────────────────────────────
def _save_timetable(schedule, gen):
    d = _data
    for year in d.years():
        tt, _ = GeneratedTimetable.objects.update_or_create(
            year=year,
            defaults={'fitness_score': schedule.getFitness(),
                      'generation_count': gen}
        )
        TimetableEntry.objects.filter(timetable=tt).delete()
        for g in schedule.genes():
            if g.year_id != year.id:
                continue
            if g.is_special:
                continue   # _PseudoCourse has no DB row; skip saving
            inst = g.instructor if isinstance(g.instructor, Instructor) else None
            for mt in g.meeting_times:
                TimetableEntry.objects.create(
                    timetable=tt, year=year,
                    section_number=g.section,
                    course_id=g.course.course_number,
                    instructor=inst, lab_room=g.lab_room,
                    meeting_time=mt, batch=g.batch,
                )


def _log_penalty_breakdown(schedule):
    genes = schedule.genes()
    inst_dt   = defaultdict(list)
    sec_pid   = defaultdict(list)
    elec_pids = defaultdict(lambda: defaultdict(set))
    room_dt   = defaultdict(list)
    chours    = defaultdict(int)
    for g in genes:
        for mt in g.meeting_times:
            if g.instructor and isinstance(g.instructor, Instructor):
                inst_dt[(g.instructor.id, mt.day, mt.time)].append(g)
            sec_pid[(g.year_id, g.section, mt.pid)].append(g)
            if g.course.course_type == 'ELECTIVE':
                elec_pids[(g.year_id, g.course.course_number)][g.section].add(mt.pid)
            if g.lab_room:
                room_dt[(g.lab_room.id, mt.day, mt.time)].append(g)
        chours[(g.year_id, g.section, g.course.course_number)] += len(g.meeting_times)
    h1 = sum(P_HARD*(len(v)-1) for v in inst_dt.values() if len(v)>1)
    h2 = sum(P_HARD*(len(v)-1) for v in sec_pid.values() if len(v)>1)
    h3 = sum(P_HARD for g in genes if g.course.course_type=='LAB' and len(g.meeting_times)>1
             and not _is_consecutive([_slot_idx(mt) for mt in g.meeting_times]))
    h4 = sum(P_HARD*(len({frozenset(v) for v in sm.values()})-1)
             for sm in elec_pids.values() if len({frozenset(v) for v in sm.values()})>1)
    h5 = sum(P_HARD for g in genes if g.course.course_type=='LAB' and g.lab_room
             and g.course._cached_lab_rooms and g.lab_room not in g.course._cached_lab_rooms)
    h6 = sum(P_HARD*(len(v)-1) for v in room_dt.values() if len(v)>1)
    h7 = 0
    seen = set()
    for g in genes:
        key = (g.year_id, g.section, g.course.course_number)
        if key not in seen:
            seen.add(key)
            req = g.course.hours_per_week
            if req > 0:
                actual = chours[key]
                if actual < req:
                    h7 += P_HARD * (req - actual)
    logger.info("Penalty breakdown: H1=%d H2=%d H3=%d H4=%d H5=%d H6=%d H7=%d",
                h1, h2, h3, h4, h5, h6, h7)


# ── Main timetable view ───────────────────────────────────────────────────────
@login_required
def timetable(request):
    global _data, _sa_temp
    _data    = Data()
    _sa_temp = SA_INITIAL_TEMP
    VARS['generationNum'] = 0
    VARS['terminateGens'] = False

    population = [Schedule.random() for _ in range(POPULATION_SIZE)]
    population.sort(key=lambda s: s.getFitness(), reverse=True)
    ga           = GeneticAlgorithm()
    best         = population[0]
    best_fitness = best.getFitness()
    no_improve   = 0

    logger.info("Gen 0 | fitness %.4f | penalty %d",
                best_fitness, best.getNumbOfConflicts())

    while best_fitness < TARGET_FITNESS and VARS['generationNum'] < MAX_GENERATIONS:
        if VARS['terminateGens']:
            break

        population = ga.evolve(population)
        population.sort(key=lambda s: s.getFitness(), reverse=True)
        best = population[0]

        best.local_search_repair(full=False)
        population[0] = best
        population.sort(key=lambda s: s.getFitness(), reverse=True)
        best = population[0]

        if VARS['generationNum'] % SA_APPLY_EVERY == 0:
            best.sa_improve(_sa_temp)
            _sa_cool()
            population.sort(key=lambda s: s.getFitness(), reverse=True)
            best = population[0]

        VARS['generationNum'] += 1
        new_fit = best.getFitness()

        if new_fit > best_fitness:
            best_fitness = new_fit
            no_improve   = 0
        else:
            no_improve += 1

        if no_improve >= RESTART_AFTER:
            for i in range(NUMB_OF_ELITE_SCHEDULES, POPULATION_SIZE):
                population[i] = Schedule.random()
            no_improve = 0
            _sa_reset()
            logger.info("Gen %d | RESTART | fitness %.4f",
                        VARS['generationNum'], best_fitness)

        if VARS['generationNum'] % 10 == 0:
            logger.info("Gen %d | fitness %.4f | penalty %d",
                        VARS['generationNum'], best_fitness,
                        best.getNumbOfConflicts())

    best.local_search_repair(full=True)
    logger.info("DONE Gen %d | fitness %.4f | penalty %d",
                VARS['generationNum'], best.getFitness(), best.getNumbOfConflicts())
    _log_penalty_breakdown(best)

    _save_timetable(best, VARS['generationNum'])

    return render(request, 'timetable.html', {
        'years_data':  _build_context(best),
        'sections':    [1, 2, 3],
        'timeSlots':   TIME_SLOTS,
        'weekDays':    DAYS_OF_WEEK,
        'fitness':     round(best.getFitness(), 4),
        'generations': VARS['generationNum'],
    })


def _build_context(schedule):
    result = []
    d = _data
    for year in d.years():
        year_secs = []
        for sec in (1, 2, 3):
            entries = []
            for g in schedule.genes():
                if g.year_id != year.id or g.section != sec:
                    continue
                for mt in g.meeting_times:
                    inst_name = (g.instructor.name
                                 if isinstance(g.instructor, Instructor) else '')
                    entries.append({
                        'day':         mt.day,
                        'time':        mt.time,
                        'course_name': g.course.course_name,
                        'course_type': g.course.course_type,
                        'instructor':  inst_name,
                        'lab_room':    g.lab_room.lab_name if g.lab_room else '',
                        'batch':       g.batch,
                        'is_special':  g.is_special,
                    })
            year_secs.append({'section': sec, 'entries': entries})
        result.append({'year': year, 'sections': year_secs,
                       'mts': d.mts_for_year(year.id)})
    return result


@login_required
def instructor_timetable(request):
    all_entries = TimetableEntry.objects.select_related(
        'course', 'instructor', 'meeting_time', 'year', 'lab_room').all()

    # Build per-instructor data: list of {instructor, entries:[{day,time,course_name,...}]}
    inst_map = {}   # instructor.id → {instructor: obj, entries: [...]}
    for e in all_entries:
        if not e.instructor:
            continue
        inst = e.instructor
        if inst.id not in inst_map:
            inst_map[inst.id] = {'instructor': inst, 'entries': []}
        inst_map[inst.id]['entries'].append({
            'day':         e.meeting_time.day,
            'time':        e.meeting_time.time,
            'course_name': e.course.course_name,
            'course_type': e.course.course_type,
            'year':        e.year.year_name,
            'section':     e.section_number,
            'lab_room':    e.lab_room.lab_name if e.lab_room else '',
        })

    # Group entries by day for each instructor
    day_order = [d[0] for d in DAYS_OF_WEEK]
    for inst_id, data in inst_map.items():
        by_day = defaultdict(list)
        for e in data['entries']:
            by_day[e['day']].append(e)
        # Sort slots within each day by time slot order
        slot_order = {s[0]: i for i, s in enumerate(TIME_SLOTS)}
        days_list = []
        for day in day_order:
            if day in by_day:
                slots = sorted(by_day[day], key=lambda e: slot_order.get(e['time'], 99))
                days_list.append({'day': day, 'slots': slots})
        data['days'] = days_list

    instructors_data = sorted(inst_map.values(),
                               key=lambda x: x['instructor'].name)

    return render(request, 'instructor_timetable.html', {
        'instructors_data': instructors_data,
        'timeSlots':        TIME_SLOTS,
        'weekDays':         DAYS_OF_WEEK,
    })


# ── API endpoints ─────────────────────────────────────────────────────────────
def apiGenNum(request):
    return JsonResponse({'genNum': VARS['generationNum']})


def apiterminateGens(request):
    VARS['terminateGens'] = True
    return redirect('home')


# ── Page views ────────────────────────────────────────────────────────────────
def home(request):
    return render(request, 'index.html', {})


@login_required
def instructorAdd(request):
    from .forms import InstructorForm
    form = InstructorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('instructorAdd')
    return render(request, 'instructorAdd.html', {'form': form})


@login_required
def instructorEdit(request):
    return render(request, 'instructorEdit.html',
                  {'instructors': Instructor.objects.all()})


@login_required
def instructorUpdate(request, pk):
    from .forms import InstructorForm
    inst = Instructor.objects.get(pk=pk)
    form = InstructorForm(request.POST or None, instance=inst)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('instructorEdit')
    return render(request, 'instructorUpdate.html', {'form': form, 'inst': inst})


@login_required
def instructorDelete(request, pk):
    if request.method == 'POST':
        Instructor.objects.filter(pk=pk).delete()
    return redirect('instructorEdit')


@login_required
def roomAdd(request):
    from .forms import LabRoomForm
    form = LabRoomForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('roomAdd')
    return render(request, 'roomAdd.html', {'form': form})


@login_required
def roomEdit(request):
    return render(request, 'roomEdit.html', {'rooms': LabRoom.objects.all()})


@login_required
def roomDelete(request, pk):
    if request.method == 'POST':
        LabRoom.objects.filter(pk=pk).delete()
    return redirect('roomEdit')


@login_required
def meetingTimeAdd(request):
    from .forms import MeetingTimeForm
    form = MeetingTimeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('meetingTimeAdd')
    return render(request, 'meetingTimeAdd.html', {'form': form})


@login_required
def meetingTimeEdit(request):
    return render(request, 'meetingTimeEdit.html',
                  {'meeting_times': MeetingTime.objects.all()})


@login_required
def meetingTimeDelete(request, pk):
    if request.method == 'POST':
        MeetingTime.objects.filter(pk=pk).delete()
    return redirect('meetingTimeEdit')


@login_required
def courseAdd(request):
    from .forms import CourseForm
    form = CourseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('courseAdd')
    return render(request, 'courseAdd.html', {'form': form})


@login_required
def courseEdit(request):
    return render(request, 'courseEdit.html', {'courses': Course.objects.all()})


@login_required
def courseDelete(request, pk):
    if request.method == 'POST':
        Course.objects.filter(pk=pk).delete()
    return redirect('courseEdit')


@login_required
def departmentAdd(request):
    from .forms import DepartmentForm
    form = DepartmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('departmentAdd')
    return render(request, 'departmentAdd.html', {'form': form})


@login_required
def departmentEdit(request):
    return render(request, 'departmentEdit.html',
                  {'departments': Department.objects.all()})


@login_required
def departmentDelete(request, pk):
    if request.method == 'POST':
        Department.objects.filter(pk=pk).delete()
    return redirect('departmentEdit')


@login_required
def sectionAdd(request):
    from .forms import CourseInstructorAssignmentForm
    form = CourseInstructorAssignmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('sectionAdd')
    return render(request, 'sectionAdd.html', {'form': form})


@login_required
def sectionEdit(request):
    cias = CourseInstructorAssignment.objects.select_related(
        'year', 'course').prefetch_related('instructors').all()
    return render(request, 'sectionEdit.html', {'sections': cias})


@login_required
def sectionDelete(request, pk):
    if request.method == 'POST':
        CourseInstructorAssignment.objects.filter(pk=pk).delete()
    return redirect('sectionEdit')


# ── Error pages ───────────────────────────────────────────────────────────────
def error_404(request, exception):
    return render(request, 'errors/404.html', {})


def error_500(request, *args, **kwargs):
    return render(request, 'errors/500.html', {})
