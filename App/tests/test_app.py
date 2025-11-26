import os, tempfile, pytest, logging, unittest
from werkzeug.security import check_password_hash, generate_password_hash
from App.main import create_app
from App.database import db, create_db
from datetime import datetime, timedelta
from App.models import User, Schedule, Shift
from App.controllers import (
    create_user,
    get_all_users_json,
    loginCLI,
    get_user,
    update_user,
    create_schedule,
    schedule_shift, 
    get_shift_report,
    get_combined_roster,
    clock_in,
    clock_out,
    get_shift,
    auto_generate_schedule,
    create_unassigned_shift
)

from App.strategies import *
from App.strategies.balancedaynight import get_shift_type
from App.strategies.minimizedays import get_shift_day


LOGGER = logging.getLogger(__name__)

'''
   Unit Tests
'''


# User unit tests
@pytest.mark.unit
@pytest.mark.userunit
class UserUnitTests(unittest.TestCase):
    def test_new_user_admin(self):
        user = create_user("bot", "bobpass","admin")
        assert user.username == "bot"

    def test_new_user_staff(self):
        user = create_user("pam", "pampass","staff")
        assert user.username == "pam"

    def test_create_user_invalid_role(self):
        user = create_user("jim", "jimpass","ceo")
        assert user == None

    def test_get_json(self):
        user = User("bob", "bobpass", "admin")
        user_json = user.get_json()
        self.assertDictEqual(user_json, {"id":None, "username":"bob", "role":"admin"})
    
    def test_hashed_password(self):
        password = "mypass"
        user = User(username="tester", password=password)
        assert user.password != password
        assert user.check_password(password) is True

    def test_check_password(self):
        password = "mypass"
        user = User("bob", password)
        assert user.check_password(password)
    
    def test_get_user_by_username(self):
        user = create_user("alice", "alicepass", "staff")
        retrieved = User.query.filter_by(username="alice").first()
        assert retrieved.username == user.username

    def test_update_user(self):
        user = create_user("charlie", "charliepass", "staff")
        update_user(user.id, "charlie_updated")
        updated_user = get_user(user.id)
        assert updated_user.username == "charlie_updated"

# Admin unit tests
@pytest.mark.unit
@pytest.mark.adminunit
class AdminUnitTests(unittest.TestCase):
    def test_schedule_shift_valid(self):
        admin = create_user("admin1", "adminpass", "admin")
        staff = create_user("staff1", "staffpass", "staff")
        
        schedule =  Schedule(weekStart=datetime(2025, 10, 20).date())

        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 22, 8, 0, 0)
        end = datetime(2025, 10, 22, 16, 0, 0)

        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        assert shift.staff_id == staff.id
        assert shift.schedule_id == schedule.id
        assert shift.start_time == start
        assert shift.end_time == end
        assert isinstance(shift, Shift)

    def test_schedule_shift_non_admin(self):
        non_admin = create_user("randomstaff", "randompass", "staff")
        staff = create_user("staff2", "staffpass", "staff")
        
        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 23, 8, 0, 0)
        end = datetime(2025, 10, 23, 16, 0, 0)

        try:
            schedule_shift(non_admin.id, staff.id, schedule.id, start, end)
            assert False, "Expected PermissionError for non-admin user"
        except PermissionError as e:
            assert str(e) == "Only admins can schedule shifts"

    def test_get_shift_report(self):
        admin = create_user("superadmin", "superpass", "admin")
        staff = create_user("worker1", "workerpass", "staff")
        db.session.add_all([admin, staff])
        db.session.commit()

        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        shift1 = schedule_shift(admin.id, staff.id, schedule.id,
                                datetime(2025, 10, 26, 8, 0, 0),
                                datetime(2025, 10, 26, 16, 0, 0))
        shift2 = schedule_shift(admin.id, staff.id, schedule.id,
                                datetime(2025, 10, 27, 8, 0, 0),
                                datetime(2025, 10, 27, 16, 0, 0))
        
        report = get_shift_report(admin.id)
        
        assert len(report) >= 2
        assert report[0]["staff_id"] == staff.id
        assert report[0]["schedule_id"] == schedule.id

    def test_get_shift_report_non_admin(self):
        non_admin = create_user("randomstaff", "randompass", "staff")

        try:
            get_shift_report(non_admin.id)
            assert False, "Expected PermissionError for non-admin user"
        except PermissionError as e:
            assert str(e) == "Only admins can view shift reports"

    def test_create_schedule(self):
        admin = create_user("admin_create", "adminpass", "admin")
        week_start = datetime(2025, 11, 3).date()
        schedule = create_schedule(admin.id, week_start)
        assert schedule.weekStart == week_start
        assert isinstance(schedule, Schedule)

    def test_create_schedule_non_admin(self):
        non_admin = create_user("staff_create", "staffpass", "staff")
        week_start = datetime(2025, 11, 3).date()
        try:
            create_schedule(non_admin.id, week_start)
            assert False, "Expected PermissionError for non-admin user"
        except PermissionError as e:
            assert str(e) == "Only admins can create schedules"

    def test_schedule_shift_invalid_staff(self):
        admin = create_user("admin_invalid_staff", "adminpass", "admin")
        
        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 24, 8, 0, 0)
        end = datetime(2025, 10, 24, 16, 0, 0)

        try:
            schedule_shift(admin.id, 9999, schedule.id, start, end)  # Invalid staff ID
            assert False, "Expected ValueError for invalid staff member"
        except ValueError as e:
            assert str(e) == "Invalid staff member"

    def test_schedule_shift_invalid_schedule(self):
        admin = create_user("admin_invalid_schedule", "adminpass", "admin") 
        staff = create_user("staff_invalid_schedule", "staffpass", "staff")

        start = datetime(2025, 10, 25, 8, 0, 0)
        end = datetime(2025, 10, 25, 16, 0, 0)

        try:
            schedule_shift(admin.id, staff.id, 9999, start, end)  # Invalid schedule ID
            assert False, "Expected ValueError for invalid schedule ID"
        except ValueError as e:
            assert str(e) == "Invalid schedule ID"

# Staff unit tests
@pytest.mark.unit
@pytest.mark.staffunit
class StaffUnitTests(unittest.TestCase):
    def test_get_combined_roster(self):
        staff = create_user("staff3", "pass123", "staff")
        admin = create_user("admin3", "adminpass", "admin")
        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        # create a shift
        shift = schedule_shift(admin.id, staff.id, schedule.id,
                               datetime(2025, 10, 23, 8, 0, 0),
                               datetime(2025, 10, 23, 16, 0, 0))

        roster = get_combined_roster(staff.id)
        assert len(roster) >= 1
        assert roster[0]["staff_id"] == staff.id
        assert roster[0]["schedule_id"] == schedule.id

    def test_get_combined_roster_invalid(self):
        non_staff = create_user("admin4", "adminpass", "admin")
        try:
            get_combined_roster(non_staff.id)
            assert False, "Expected PermissionError for non-staff"
        except PermissionError as e:
            assert str(e) == "Only staff can view roster"

    def test_clock_in(self):
        admin = create_user("admin_clock", "adminpass", "admin")
        staff = create_user("staff_clock", "staffpass", "staff")

        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 25, 8, 0, 0)
        end = datetime(2025, 10, 25, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        clocked_in_shift = clock_in(staff.id, shift.id)
        assert clocked_in_shift.clock_in is not None
        assert isinstance(clocked_in_shift.clock_in, datetime)

    def test_clock_in_invalid_user(self):
        admin = create_user("admin_clockin", "adminpass", "admin")
        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        staff = create_user("staff_invalid", "staffpass", "staff")
        start = datetime(2025, 10, 26, 8, 0, 0)
        end = datetime(2025, 10, 26, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        with pytest.raises(PermissionError) as e:
            clock_in(admin.id, shift.id)
        assert str(e.value) == "Only staff can clock in"

    def test_clock_in_invalid_shift(self):
        staff = create_user("clockstaff_invalid", "clockpass", "staff")
        with pytest.raises(ValueError) as e:
            clock_in(staff.id, 999)
        assert str(e.value) == "Invalid shift for staff"

    def test_clock_out(self):
        admin = create_user("admin_clockout", "adminpass", "admin")
        staff = create_user("staff_clockout", "staffpass", "staff")

        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 27, 8, 0, 0)
        end = datetime(2025, 10, 27, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        clocked_out_shift = clock_out(staff.id, shift.id)
        assert clocked_out_shift.clock_out is not None
        assert isinstance(clocked_out_shift.clock_out, datetime)

    def test_clock_out_invalid_user(self):
        admin = create_user("admin_invalid_out", "adminpass", "admin")
        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        staff = create_user("staff_invalid_out", "staffpass", "staff")
        start = datetime(2025, 10, 28, 8, 0, 0)
        end = datetime(2025, 10, 28, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        with pytest.raises(PermissionError) as e:
            clock_out(admin.id, shift.id)
        assert str(e.value) == "Only staff can clock out"

    def test_clock_out_invalid_shift(self):
        staff = create_user("staff_invalid_shift_out", "staffpass", "staff")
        with pytest.raises(ValueError) as e:
            clock_out(staff.id, 999)  
        assert str(e.value) == "Invalid shift for staff"

    def test_get_shift(self):
        admin = create_user("admin_getshift", "adminpass", "admin")
        staff = create_user("staff_getshift", "staffpass", "staff")

        schedule = Schedule(weekStart=datetime(2025, 10, 20).date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 29, 8, 0, 0)
        end = datetime(2025, 10, 29, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        retrieved_shift = get_shift(shift.id)
        assert retrieved_shift.id == shift.id
        assert retrieved_shift.staff_id == staff.id
        assert retrieved_shift.schedule_id == schedule.id

#schedule Unit tests
@pytest.mark.unit
@pytest.mark.scheduleunit
class ScheduleUnitTests(unittest.TestCase):
    def test_schedule_get_all_shifts(self):
        admin = create_user("admin_schedule", "adminpass", "admin")
        staff = create_user("staff_schedule", "staffpass", "staff")

        schedule = Schedule(weekStart=datetime(2025, 11, 1).date())
        db.session.add(schedule)
        db.session.commit()

        start1 = datetime(2025, 11, 3, 8, 0, 0)
        end1 = datetime(2025, 11, 3, 16, 0, 0)
        shift1 = schedule_shift(admin.id, staff.id, schedule.id, start1, end1)

        start2 = datetime(2025, 11, 4, 8, 0, 0)
        end2 = datetime(2025, 11, 4, 16, 0, 0)
        shift2 = schedule_shift(admin.id, staff.id, schedule.id, start2, end2)

        shifts = schedule.get_all_shifts()
        self.assertIn(shift1, shifts)
        self.assertIn(shift2, shifts)

    def test_schedule_validate_empty(self):
        schedule = Schedule(weekStart=datetime(2025, 11, 10).date())
        self.assertTrue(schedule.validate_schedule() == False)

    def test_schedule_validate_valid(self):
        admin = create_user("admin_valid", "adminpass", "admin")
        staff = create_user("staff_valid", "staffpass", "staff")

        schedule = Schedule(weekStart=datetime(2025, 11, 10).date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 11, 12, 8, 0, 0)
        end = datetime(2025, 11, 12, 16, 0, 0)
        schedule_shift(admin.id, staff.id, schedule.id, start, end)

        self.assertTrue(schedule.validate_schedule() == True)

#Strategy Unit Tests
@pytest.mark.unit
@pytest.mark.strategyunit
class StrategyUnitTests(unittest.TestCase):
    def test_even_distribution_strategy(self):
        staff1 = create_user("staff1", "pass1", "staff")
        staff2 = create_user("staff2", "pass2", "staff")
        staff3 = create_user("staff3", "pass3", "staff")
        staff_list = [staff1, staff2, staff3]

        shifts = [
            Shift(start_time=datetime(2025, 11, 10, 8, 0, 0), end_time=datetime(2025, 11, 10, 16, 0, 0)),
            Shift(start_time=datetime(2025, 11, 11, 8, 0, 0), end_time=datetime(2025, 11, 11, 16, 0, 0)),
            Shift(start_time=datetime(2025, 11, 12, 8, 0, 0), end_time=datetime(2025, 11, 12, 16, 0, 0)),
            Shift(start_time=datetime(2025, 11, 13, 8, 0, 0), end_time=datetime(2025, 11, 13, 16, 0, 0)),
            Shift(start_time=datetime(2025, 11, 14, 8, 0, 0), end_time=datetime(2025, 11, 14, 16, 0, 0)),
            Shift(start_time=datetime(2025, 11, 15, 8, 0, 0), end_time=datetime(2025, 11, 15, 16, 0, 0)),
        ]

        strategy = EvenDistributionStrategy()
        assignments = strategy.distribute(staff_list, shifts)

        self.assertEqual(assignments[str(staff1.id)][0], shifts[0])
        self.assertEqual(assignments[str(staff1.id)][1], shifts[3])
        self.assertEqual(assignments[str(staff2.id)][0], shifts[1])
        self.assertEqual(assignments[str(staff2.id)][1], shifts[4])
        self.assertEqual(assignments[str(staff3.id)][0], shifts[2])
        self.assertEqual(assignments[str(staff3.id)][1], shifts[5])

    def test_balance_day_night_stategy(self):
        staff1 = create_user("staffA", "passA", "staff")
        staff2 = create_user("staffB", "passB", "staff")
        staff_list = [staff1, staff2]

        shifts = [
            Shift(start_time=datetime(2025, 11, 10, 8, 0, 0), end_time=datetime(2025, 11, 10, 16, 0, 0)),  # Day
            Shift(start_time=datetime(2025, 11, 10, 20, 0, 0), end_time=datetime(2025, 11, 11, 4, 0, 0)), # Night
            Shift(start_time=datetime(2025, 11, 11, 8, 0, 0), end_time=datetime(2025, 11, 11, 16, 0, 0)), # Day
            Shift(start_time=datetime(2025, 11, 11, 20, 0, 0), end_time=datetime(2025, 11, 12, 4, 0, 0)), # Night
        ]

        strategy = BalanceDayNightStrategy()
        assignments = strategy.distribute(staff_list, shifts)

        self.assertEqual(assignments[str(staff1.id)][0], shifts[0])  # Day
        self.assertEqual(assignments[str(staff1.id)][1], shifts[3])  # Night
        self.assertEqual(assignments[str(staff2.id)][0], shifts[1])  # Night
        self.assertEqual(assignments[str(staff2.id)][1], shifts[2])  # Day

    def test_minimize_days_strategy(self):
        staff1 = create_user("staffA", "passA", "staff")
        staff2 = create_user("staffB", "passB", "staff")
        staff_list = [staff1, staff2]

        shifts = [
            Shift(start_time=datetime(2025, 11, 10, 8, 0, 0), end_time=datetime(2025, 11, 10, 16, 0, 0)),  # Day 1
            Shift(start_time=datetime(2025, 11, 10, 20, 0, 0), end_time=datetime(2025, 11, 11, 4, 0, 0)), # Night 1
            Shift(start_time=datetime(2025, 11, 11, 8, 0, 0), end_time=datetime(2025, 11, 11, 16, 0, 0)), # Day 2
            Shift(start_time=datetime(2025, 11, 11, 20, 0, 0), end_time=datetime(2025, 11, 12, 4, 0, 0)), # Night 2
        ]

        strategy = MinimizeDaysStrategy()
        assignments = strategy.distribute(staff_list, shifts)

        staff1_shifts = assignments[str(staff1.id)]
        staff2_shifts = assignments[str(staff2.id)]

        staff1_days = set(shift.start_time.date() for shift in staff1_shifts)
        staff2_days = set(shift.start_time.date() for shift in staff2_shifts)

        self.assertEqual(len(staff1_days), 1)  # Staff1 works only 1 day
        self.assertEqual(len(staff2_days), 1)  # Staff2 works only 1 day

        staff1_works_nov10 = any(shift.start_time.date() == datetime(2025, 11, 10).date() for shift in staff1_shifts)
        staff1_works_nov11 = any(shift.start_time.date() == datetime(2025, 11, 11).date() for shift in staff1_shifts)
        staff2_works_nov10 = any(shift.start_time.date() == datetime(2025, 11, 10).date() for shift in staff2_shifts)
        staff2_works_nov11 = any(shift.start_time.date() == datetime(2025, 11, 11).date() for shift in staff2_shifts)


        self.assertNotEqual(staff1_works_nov10, staff1_works_nov11)  # XOR - works one day but not both
        self.assertNotEqual(staff2_works_nov10, staff2_works_nov11)  # XOR - works one day but not both

    def test_get_shift_type_day(self):
        # Test various day shifts (6 AM to 6 PM)
        day_shifts = [
            Shift(start_time=datetime(2025, 11, 10, 6, 0, 0), end_time=datetime(2025, 11, 10, 14, 0, 0)),   # 6 AM
            Shift(start_time=datetime(2025, 11, 10, 8, 0, 0), end_time=datetime(2025, 11, 10, 16, 0, 0)),   # 8 AM
            Shift(start_time=datetime(2025, 11, 10, 12, 0, 0), end_time=datetime(2025, 11, 10, 20, 0, 0)),  # 12 PM
            Shift(start_time=datetime(2025, 11, 10, 14, 0, 0), end_time=datetime(2025, 11, 10, 22, 0, 0)),  # 2 PM
        ]
    
        for shift in day_shifts:
            result = get_shift_type(shift)
            self.assertEqual(result, "day", f"Shift starting at {shift.start_time.hour}:00 should be day shift")

    def test_get_shift_type_night(self):
        # Test various night shifts (6 PM to 6 AM)
        night_shifts = [
            Shift(start_time=datetime(2025, 11, 10, 18, 0, 0), end_time=datetime(2025, 11, 11, 2, 0, 0)),   # 6 PM
            Shift(start_time=datetime(2025, 11, 10, 20, 0, 0), end_time=datetime(2025, 11, 11, 4, 0, 0)),   # 8 PM
            Shift(start_time=datetime(2025, 11, 10, 23, 0, 0), end_time=datetime(2025, 11, 11, 7, 0, 0)),   # 11 PM
            Shift(start_time=datetime(2025, 11, 11, 2, 0, 0), end_time=datetime(2025, 11, 11, 10, 0, 0)),   # 2 AM
        ]
    
        for shift in night_shifts:
            result = get_shift_type(shift)
            self.assertEqual(result, "night", f"Shift starting at {shift.start_time.hour}:00 should be night shift")

    def test_get_shift_day(self):
        test_date = datetime(2025, 11, 10, 8, 0, 0)
        shift = Shift(start_time=test_date, end_time=datetime(2025, 11, 10, 16, 0, 0))

        result = get_shift_day(shift)
        expected_date = test_date.date()  

        self.assertEqual(result, expected_date)
        self.assertIsInstance(result, type(expected_date))

'''
    Integration Tests
'''
@pytest.fixture(autouse=True)
def clean_db():
    db.drop_all()
    create_db()
    db.session.remove()
    yield
# This fixture creates an empty database for the test and deletes it after the test
# scope="class" would execute the fixture once and resued for all methods in the class
@pytest.fixture(autouse=True, scope="module")
def empty_db():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.db'})
    create_db()
    db.session.remove()
    yield app.test_client()
    db.drop_all()


def test_authenticate():
    user = User("bob", "bobpass","user")
    assert loginCLI("bob", "bobpass") != None


# User integration tests
@pytest.mark.integration
@pytest.mark.userintegration
class UsersIntegrationTests(unittest.TestCase):
    def test_get_all_users_json(self):
        user = create_user("bot", "bobpass","admin")
        user = create_user("pam", "pampass","staff")
        users_json = get_all_users_json()
        self.assertListEqual([{"id":1, "username":"bot", "role":"admin"}, {"id":2, "username":"pam","role":"staff"}], users_json)

    def test_update_user(self):
        user = create_user("bot", "bobpass","admin")
        update_user(1, "ronnie")
        user = get_user(1)
        assert user.username == "ronnie"

    def test_create_and_get_user(self):
        user = create_user("alex", "alexpass", "staff")
        retrieved = get_user(user.id)
        self.assertEqual(retrieved.username, "alex")
        self.assertEqual(retrieved.role, "staff")
        
    
    # Admin integration tests
@pytest.mark.integration
@pytest.mark.adminintegration
class AdminIntegrationTests(unittest.TestCase):
    def test_admin_schedule_shift_for_staff(self):
        admin = create_user("admin1", "adminpass", "admin")
        staff = create_user("staff1", "staffpass", "staff")

        schedule = schedule = Schedule(weekStart=datetime.now().date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)
        retrieved = get_user(staff.id)

        self.assertIn(shift.id, [s.id for s in retrieved.shifts])
        self.assertEqual(shift.staff_id, staff.id)
        self.assertEqual(shift.schedule_id, schedule.id)

    def test_admin_generate_shift_report(self):
        admin = create_user("boss", "boss123", "admin")
        staff = create_user("sam", "sampass", "staff")

        schedule = Schedule(weekStart=datetime.now().date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        schedule_shift(admin.id, staff.id, schedule.id, start, end)
        report = get_shift_report(admin.id)

        self.assertTrue(any("sam" in r["staff_name"] for r in report))
        self.assertTrue(all("start_time" in r and "end_time" in r for r in report))

    def test_create_schedule(self):
        admin = create_user("admin_create", "adminpass", "admin")
        week_start = datetime.now().date()
        schedule = create_schedule(admin.id, week_start)
        self.assertEqual(schedule.weekStart, week_start)
        self.assertIsInstance(schedule, Schedule)


# Staff integration tests
@pytest.mark.integration
@pytest.mark.staffintegration
class StaffIntegrationTests(unittest.TestCase):
    def test_staff_view_combined_roster(self):
        admin = create_user("admin", "adminpass", "admin")
        staff = create_user("jane", "janepass", "staff")
        other_staff = create_user("mark", "markpass", "staff")

        schedule = Schedule(weekStart=datetime.now().date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        schedule_shift(admin.id, staff.id, schedule.id, start, end)
        schedule_shift(admin.id, other_staff.id, schedule.id, start, end)

        roster = get_combined_roster(staff.id)
        self.assertTrue(any(s["staff_id"] == staff.id for s in roster))
        self.assertTrue(any(s["staff_id"] == other_staff.id for s in roster))

    def test_staff_clock_in_and_out(self):
        admin = create_user("admin", "adminpass", "admin")
        staff = create_user("lee", "leepass", "staff")

        schedule = Schedule(weekStart=datetime.now().date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        clock_in(staff.id, shift.id)
        clock_out(staff.id, shift.id)


        updated_shift = get_shift(shift.id)
        self.assertIsNotNone(updated_shift.clock_in)
        self.assertIsNotNone(updated_shift.clock_out)
        self.assertLess(updated_shift.clock_in, updated_shift.clock_out)

    def test_get_shift(self):
        admin = create_user("admin", "adminpass", "admin")
        staff = create_user("nina", "ninapass", "staff")

        schedule = Schedule(weekStart=datetime.now().date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)
        retrieved_shift = get_shift(shift.id)

        self.assertEqual(retrieved_shift.id, shift.id)
        self.assertEqual(retrieved_shift.staff_id, staff.id)
        self.assertEqual(retrieved_shift.schedule_id, schedule.id)
    
#Permission integration tests
@pytest.mark.integration
@pytest.mark.permissionintegration
class PermissionIntegrationTests(unittest.TestCase):
    def test_permission_restrictions(self):
        admin = create_user("admin", "adminpass", "admin")
        staff = create_user("worker", "workpass", "staff")

        # Create schedule
        schedule = Schedule(weekStart=datetime.now().date())
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        with self.assertRaises(PermissionError):
            schedule_shift(staff.id, staff.id, schedule.id, start, end)

        with self.assertRaises(PermissionError):
            get_combined_roster(admin.id)

        with self.assertRaises(PermissionError):
            get_shift_report(staff.id)

#Auto-Scheduling integration tests
@pytest.mark.integration
@pytest.mark.autoscheduleintegration
class AutoScheduleIntegrationTests(unittest.TestCase):
    def test_auto_generate_schedule(self):
        staff1 = create_user("staff_auto1", "staffpass1", "staff")
        staff2 = create_user("staff_auto2", "staffpass2", "staff")

        shifts = [
            create_unassigned_shift(
                start_time=datetime.now(), 
                end_time=datetime.now() + timedelta(hours=8)
            ),
            create_unassigned_shift(
                start_time=datetime.now() + timedelta(days=1), 
                end_time=datetime.now() + timedelta(days=1, hours=8)
            ),
        ]

        week_start = datetime.now().date()
        schedule = auto_generate_schedule(strategy_name="even", week_start=week_start)

        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.weekStart, week_start)

        all_shifts = schedule.get_all_shifts()
        self.assertEqual(len(all_shifts), len(shifts))

        staff1_shifts = [shift for shift in all_shifts if shift.staff_id == staff1.id]
        staff2_shifts = [shift for shift in all_shifts if shift.staff_id == staff2.id]

        shift_count_diff = abs(len(staff1_shifts) - len(staff2_shifts))
        self.assertLessEqual(shift_count_diff, 1)
    

    def test_auto_generate_schedule_invalid_strategy(self):
        # Create staff members so the function gets past the staff check
        create_user("staff1", "staffpass1", "staff")
        create_user("staff2", "staffpass2", "staff")
        
        # Create unassigned shifts so the function gets past the shifts check
        create_unassigned_shift(
            start_time=datetime.now(), 
            end_time=datetime.now() + timedelta(hours=8)
        )
        with pytest.raises(ValueError) as exc_info:
            auto_generate_schedule(strategy_name="invalid_strategy", week_start=datetime.now().date())

        expected_message = "Unknown strategy name: invalid_strategy"
        assert str(exc_info.value) == expected_message

    def test_auto_generate_schedule_no_staff(self):
        # Ensure no staff members exist
        db.session.query(User).filter_by(role="staff").delete()
        db.session.commit()

        # Create unassigned shifts so the function gets past the shifts check
        create_unassigned_shift(
            start_time=datetime.now(), 
            end_time=datetime.now() + timedelta(hours=8)
        )
        with pytest.raises(ValueError) as exc_info:
            auto_generate_schedule(strategy_name="even", week_start=datetime.now().date())

        expected_message = "No staff members available for scheduling"
        assert str(exc_info.value) == expected_message

    def test_auto_generate_schedule_no_shifts(self):
        # Ensure no unassigned shifts exist
        db.session.query(Shift).filter_by(staff_id=None).delete()
        db.session.commit()

        # Create staff members so the function gets past the staff check
        create_user("staff1", "staffpass1", "staff")
        with pytest.raises(ValueError) as exc_info:
            auto_generate_schedule(strategy_name="even", week_start=datetime.now().date())

        expected_message = "No unassigned shifts available for scheduling"
        assert str(exc_info.value) == expected_message