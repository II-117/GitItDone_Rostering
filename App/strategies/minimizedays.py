from .scheduling_strategy import SchedulingStrategy


#this method was relocated here as it is only used by this strategy

def get_shift_day(shift):
    if shift is None:
        return None
    
    startTime = getattr(shift, "start_time", None)

    if startTime is not None:
        if hasattr(startTime, "date"):
            return startTime.date()
    return None


class MinimizeDaysStrategy(SchedulingStrategy):


    def distribute(self, staff_list, shifts, week_start=None):
        assignments = {}

        if not staff_list:
            return assignments
        
        staff_ids = [str(staffMember.id) for staffMember in staff_list]

        for staff_id in staff_ids:
            assignments[staff_id] = []
        
        days = {staff_id: set() for staff_id in staff_ids}

        for shift in shifts:
            shift_day = get_shift_day(shift)

            chosen = None

            for staff_id in staff_ids:
                if shift_day in days[staff_id]:
                    chosen = staff_id
                    break

            if chosen is None:
                chosen = min(staff_ids, key = lambda x: (len(days[x]), len(assignments[x])))
            
            assignments[chosen].append(shift)
            if shift_day is not None:
                days[chosen].add(shift_day)
                

        return assignments
    

"""
This strategy as the name suggests aims to reduce the number of distinct days that each staff members comes in to work.
When a new shift is to be assigned, it first checks if there is any staff member who is already scheduled to work on that day.
If such a staff member is found, the shift is assigned to them, so that they can work multiple shifts on the same day and thus minimize the total number of days they need to come in.
If no staff member is already scheduled for that day, the strategy selects the staff member who currently has the fewest distinct working days.
If there is a tie, it further breaks the tie by choosing the staff member with the fewest total assigned shifts.
This gives the staff more complete days off by goruping all their shifts into fewer days instead of spreading them out.
- VR.


"""
