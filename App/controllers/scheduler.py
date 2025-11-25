from App.models import Staff, Shift

from App.strategies.schedule_generator import ScheduleGenerator
from App.strategies.evendistribution import EvenDistributionStrategy
from App.strategies.balancedaynight import BalanceDayNightStrategy
from App.strategies.minimizedays import MinimizeDaysStrategy




def auto_generate_schedule(strategy_name="even", week_start=None):
    staff_list = Staff.query.all()

    if not staff_list:
        raise ValueError("No staff members available for scheduling")
    
    generator = ScheduleGenerator()
    generator.setStaffList(staff_list)

    if strategy_name == "even":
        generator.setStrategy(EvenDistributionStrategy())
    elif strategy_name == "balance_day_night":
        generator.setStrategy(BalanceDayNightStrategy())
    elif strategy_name == "minimize_days":
        generator.setStrategy(MinimizeDaysStrategy())
    else:
        raise ValueError(f"Unknown strategy name: {strategy_name}")
    
    return generator.generateSchedule(week_start)
