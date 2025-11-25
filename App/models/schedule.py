from datetime import datetime
from App.database import db

#updated to match UML class diagram

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    weekStart = db.Column(db.Date, nullable=True)
    shifts = db.relationship("Shift", backref="schedule", lazy=True)

    def get_all_shifts(self):
        return self.shifts
    
    def get_shifts_by_staff(self, staff):
        return [shift for shift in self.shifts if shift.staff_id == staff.id]
    

    def add_shift(self, shift):
        shift.schedule_id = self.id
        self.shifts.append(shift)

    def validate_schedule(self):
        if not self.shifts:
            return False
        for shift in self.shifts:
            if shift.staff_id is None:
                return False
        return True
    

    def get_json(self):

        return {
            "id": self.id,
            "weekStart": self.weekStart.strftime("%Y-%m-%d") if self.weekStart else None,
            "shifts": [shift.get_json() for shift in self.shifts]
        }


