from .scheduling_strategy import SchedulingStrategy



# again this function was moved to here as it is the only strategy that uses it.

def get_shift_type(shift):
    if shift is None:
        return "day"
    
    startTime = getattr(shift, "start_time", None)
    
    if startTime is not None:
        if hasattr(startTime, "hour"):
            hour = startTime.hour
            if hour >= 18 or hour < 6:
                return "night"
            else:
                return "day"
    
    return "day"  


class BalanceDayNightStrategy(SchedulingStrategy):


    def distribute(self, staff_list, shifts, week_start=None):
        assignments = {}

        if not staff_list:
            return assignments
        
        staff_ids = [str(staffMember.id) for staffMember in staff_list]

        for staff_id in staff_ids:
            assignments[staff_id] = []

        counts = {staff_id: {'day': 0, 'night': 0} for staff_id in staff_ids}

        for shift in shifts:
            shift_type = get_shift_type(shift)

            def score(staff_id):
                return (counts[staff_id].get(shift_type, 0), len(assignments[staff_id]))
            
            chosen_staff = min(staff_ids, key=score)
            assignments[chosen_staff].append(shift)
            counts[chosen_staff][shift_type] = counts[chosen_staff].get(shift_type, 0) + 1


        return assignments

"""
This strategy uses a greedy algorithm to balance the number of day and night shifts assigned to each staff member.
It first determins whether the shift is a day or night shift using the get_shift_type function.
It calculates a score for each staff member based on how many shifts of that type they already have assigned, as well as their total number of assigned shifts.
The staff member with the lowest score is chosen to receive the shift, helping to ensure an even distribution of day and night shifts among all staff members.

e.g if s1 has 2 day shifts and s2 has 1, the next day shift will go to s2 to balance it out.

- VR.
"""