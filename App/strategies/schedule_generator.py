from App.models import Schedule, Staff, Shift
from App.database import db



class ScheduleGenerator:
    def __init__(self):
        self.strategy = None
        self.staffList = []

    def setStrategy(self, strategy):
        self.strategy = strategy

    def setStaffList(self, staffList):
        self.staffList = staffList

    def generateSchedule(self, week_start=None):
        if self.strategy is None:
            raise ValueError("No scheduling strategy set")
        
        if not self.staffList:
            raise ValueError("Staff list is empty")
    
        unassigned_shifts = Shift.query.filter_by(staff_id = None).all()

        if not unassigned_shifts:
            raise ValueError("No unassigned shifts available for scheduling")
        
        assignments = self.strategy.distribute(self.staffList, unassigned_shifts, week_start)

        new_schedule = Schedule(weekStart=week_start)

        db.session.add(new_schedule)
        db.session.flush()

        for staff_id, shifts in assignments.items():
            for shift in shifts:
                shift.staff_id = int(staff_id)
                shift.schedule_id = new_schedule.id
                
        db.session.commit()

        return new_schedule
    
