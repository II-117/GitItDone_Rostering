import click, pytest, sys, os
from flask.cli import with_appcontext, AppGroup
from datetime import datetime
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from App.database import db, get_migrate
from App.models import User
from App.main import create_app 
from App.controllers import (
    create_user, get_all_users_json, get_all_users, initialize,
    schedule_shift, get_combined_roster, clock_in, clock_out, get_shift_report, login,loginCLI
)

app = create_app()
migrate = get_migrate(app)

@app.cli.command("init", help="Creates and initializes the database")
def init():
    initialize()
    print('database intialized')

auth_cli = AppGroup('auth', help='Authentication commands')

@auth_cli.command("login", help="Login and get JWT token")
@click.argument("username")
@click.argument("password")
def login_command(username, password):
    result = loginCLI(username, password)
    if result["message"] == "Login successful":
        token = result["token"]
        with open("active_token.txt", "w") as f:
            f.write(token)
        print(f"✅ {result['message']}! JWT token saved for CLI use.")
    else:
        print(f"⚠️ {result['message']}")

@auth_cli.command("logout", help="Logout a user by username")
@click.argument("username")
def logout_command(username):
    from App.controllers.auth import logout
    result = logout(username)
    if os.path.exists("active_token.txt"):
        os.remove("active_token.txt")
    print(result["message"])
    
app.cli.add_command(auth_cli)


user_cli = AppGroup('user', help='User object commands') 

@user_cli.command("create", help="Creates a user")
@click.argument("username", default="rob")
@click.argument("password", default="robpass")
@click.argument("role", default="staff")
def create_user_command(username, password, role):
    create_user(username, password, role)
    print(f'{username} created!')

@user_cli.command("list", help="Lists users in the database")
@click.argument("format", default="string")
def list_user_command(format):
    if format == 'string':
        print(get_all_users())
    else:
        print(get_all_users_json())

app.cli.add_command(user_cli)



shift_cli = AppGroup('shift', help='Shift management commands')

@shift_cli.command("schedule", help="Admin schedules a shift and assigns it to a schedule")
@click.argument("staff_id", type=int)
@click.argument("schedule_id", type=int)
@click.argument("start")
@click.argument("end")
def schedule_shift_command(staff_id, schedule_id, start, end):
    from datetime import datetime
    admin = require_admin_login()
    start_time = datetime.fromisoformat(start)
    end_time = datetime.fromisoformat(end)
    shift = schedule_shift(admin.id, staff_id, schedule_id, start_time, end_time)
    print(f"✅ Shift scheduled under Schedule {schedule_id} by {admin.username}:")
    print(shift.get_json())



@shift_cli.command("roster", help="Staff views combined roster")
def roster_command():
    staff = require_staff_login()
    roster = get_combined_roster(staff.id)
    print(f"📋 Roster for {staff.username}:")
    print(roster)


@shift_cli.command("clockin", help="Staff clocks in")
@click.argument("shift_id", type=int)
def clockin_command(shift_id):
    staff = require_staff_login()
    shift = clock_in(staff.id, shift_id)
    print(f"🕒 {staff.username} clocked in: {shift.get_json()}")



@shift_cli.command("clockout", help="Staff clocks out")
@click.argument("shift_id", type=int)
def clockout_command(shift_id):
    staff = require_staff_login()
    shift = clock_out(staff.id, shift_id)
    print(f"🕕 {staff.username} clocked out: {shift.get_json()}")


@shift_cli.command("report", help="Admin views shift report")
def report_command():
    admin = require_admin_login()
    report = get_shift_report(admin.id)
    print(f"📊 Shift report for {admin.username}:")
    print(report)

app.cli.add_command(shift_cli)


def require_admin_login():
    import os
    from flask_jwt_extended import decode_token
    from App.controllers import get_user

    if not os.path.exists("active_token.txt"):
        raise PermissionError("⚠️ No active session. Please login first.")

    with open("active_token.txt", "r") as f:
        token = f.read().strip()

    try:
        decoded = decode_token(token)
        user_id = decoded["sub"]
        user = get_user(user_id)
        if not user or user.role != "admin":
            raise PermissionError("🚫 Only an admin can use this command.")
        return user
    except Exception as e:
        raise PermissionError(f"Invalid or expired token. Please login again. ({e})")

def require_staff_login():
    import os
    from flask_jwt_extended import decode_token
    from App.controllers import get_user

    if not os.path.exists("active_token.txt"):
        raise PermissionError("⚠️ No active session. Please login first.")

    with open("active_token.txt", "r") as f:
        token = f.read().strip()

    try:
        decoded = decode_token(token)
        user_id = decoded["sub"]
        user = get_user(user_id)
        if not user or user.role != "staff":
            raise PermissionError("🚫 Only staff can use this command.")
        return user
    except Exception as e:
        raise PermissionError(f"Invalid or expired token. Please login again. ({e})")

schedule_cli = AppGroup('schedule', help='Schedule management commands')

@schedule_cli.command("create", help="Create a schedule")
@click.argument("name")
def create_schedule_command(name):
    from App.models import Schedule
    admin = require_admin_login()
    schedule = Schedule(name=name, created_by=admin.id)
    db.session.add(schedule)
    db.session.commit()
    print(f"✅ Schedule created: {schedule.get_json()}")


@schedule_cli.command("list", help="List all schedules")
def list_schedules_command():
    from App.models import Schedule
    admin = require_admin_login()
    schedules = Schedule.query.all()
    print(f"✅ Found {len(schedules)} schedule(s):")
    for s in schedules:
        print(s.get_json())


@schedule_cli.command("view", help="View a schedule and its shifts")
@click.argument("schedule_id", type=int)
def view_schedule_command(schedule_id):
    from App.models import Schedule
    admin = require_admin_login()
    schedule = db.session.get(Schedule, schedule_id)
    if not schedule:
        print("⚠️ Schedule not found.")
    else:
        print(f"✅ Viewing schedule {schedule_id}:")
        print(schedule.get_json())

@schedule_cli.command("auto-schedule", help="Auto-schedule shifts using a strategy")
@click.argument("schedule_id", type=int)
@click.argument("strategy", type=str)
@click.argument("staff_ids", type=str)
def auto_schedule_command(schedule_id, strategy, staff_ids):
    """Auto-schedule shifts for a schedule using a strategy (even, minimize, daynight)"""
    from App.models import Schedule, Staff
    from App.strategies.evendistribution import EvenDistributionStrategy
    from App.strategies.minimizedays import MinimizeDaysStrategy
    from App.strategies.balancedaynight import BalanceDayNightStrategy
    from App.strategies.schedule_generator import ScheduleGenerator
    
    require_admin_login()
    
    raw_id_list = [x.strip() for x in staff_ids.split(',') if x.strip()]
    
    if not all(x.isdigit() for x in raw_id_list):
        print("❌ Invalid staff IDs. Use format: 1,2,3 (numbers only)")
        return

    staff_id_list = [int(x) for x in raw_id_list]
    
    schedule = db.session.get(Schedule, schedule_id)
    if not schedule:
        print(f"❌ Schedule {schedule_id} not found")
        return
    
    staff_members = Staff.query.filter(Staff.id.in_(staff_id_list)).all()
    if not staff_members:
        print("❌ No staff members found")
        return
    
    strategies = {
        "even": EvenDistributionStrategy,
        "minimize": MinimizeDaysStrategy,
        "daynight": BalanceDayNightStrategy
    }
    
    strategy_key = strategy.lower()
    if strategy_key not in strategies:
        print(f"❌ Unknown strategy: {strategy}")
        print("Use: even, minimize, or daynight")
        return

    chosen_strategy = strategies[strategy_key]()
    
    generator = ScheduleGenerator()
    generator.setStrategy(chosen_strategy)
    generator.setStaffList(staff_members)
    new_schedule = generator.generateSchedule(week_start=schedule.weekStart)
    
    print(f"✅ Schedule created successfully!")
    print(f"Strategy: {strategy}")
    print(f"Staff count: {len(staff_members)}")
    print(f"Shifts assigned: {len(new_schedule.shifts)}")




app.cli.add_command(schedule_cli)
'''
Test Commands
'''
test = AppGroup('test', help='Testing commands') 

@test.command("user", help="Run User tests")
@click.argument("type", default="all")
def user_tests_command(type):
    if type == "unit":
        sys.exit(pytest.main(["-k", "UserUnitTests"]))
    elif type == "int":
        sys.exit(pytest.main(["-k", "UserIntegrationTests"]))
    else:
        sys.exit(pytest.main(["-k", "App"]))
    
app.cli.add_command(test)
