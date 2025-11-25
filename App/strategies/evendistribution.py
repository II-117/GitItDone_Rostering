from .scheduling_strategy import SchedulingStrategy



class EvenDistributionStrategy(SchedulingStrategy):

    def distribute(self, staff_list, shifts, week_start=None):
        assignments = {}

        if not staff_list:
            return assignments
        

        staff_ids = [str(staffMember.id) for staffMember in staff_list]

        for staff_id in staff_ids:
            assignments[staff_id] = []
        
        i = 0
        num_staff = len(staff_ids)
        
        for shift in shifts:
            staff_id = staff_ids[i % num_staff]
            assignments[staff_id].append(shift)
            i += 1
        
        return assignments
    
# This use an even distribution, a round robin approach, to assign shifts to staff members in order. - VR