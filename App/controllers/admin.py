#from App.models import Shift
#from App.database import db
#from datetime import datetime
#from App.controllers.user import get_user
#all of the above were duplicated imports

from App.models import Shift, Schedule
from App.database import db
from datetime import datetime
from App.controllers.user import get_user

def create_schedule(admin_id, week_start): #Not sure why this was missing
    admin = get_user(admin_id)
    if not admin or admin.role != "admin":
        raise PermissionError("Only admins can create schedules")

    new_schedule = Schedule(
        weekStart=week_start
    )

    db.session.add(new_schedule)
    db.session.commit()

    return new_schedule

def create_unassigned_shift(start_time, end_time):
    new_shift = Shift(
        staff_id=None,
        schedule_id=None,
        start_time=start_time,
        end_time=end_time
    )

    db.session.add(new_shift)
    db.session.commit()

    return new_shift


def schedule_shift(admin_id, staff_id, schedule_id, start_time, end_time):
    admin = get_user(admin_id)
    staff = get_user(staff_id)

    schedule = db.session.get(Schedule, schedule_id)

    if not admin or admin.role != "admin":
        raise PermissionError("Only admins can schedule shifts")
    if not staff or staff.role != "staff":
        raise ValueError("Invalid staff member")
    if not schedule:
        raise ValueError("Invalid schedule ID")

    new_shift = Shift(
        staff_id=staff_id,
        schedule_id=schedule_id,
        start_time=start_time,
        end_time=end_time
    )

    db.session.add(new_shift)
    db.session.commit()

    return new_shift


def get_shift_report(admin_id):
    admin = get_user(admin_id)
    if not admin or admin.role != "admin":
        raise PermissionError("Only admins can view shift reports")

    return [shift.get_json() for shift in Shift.query.order_by(Shift.start_time).all()]