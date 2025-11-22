from App.models import Staff, Shift
from App.controllers.user import get_user
from App.strategies.evendistribution import EvenDistribution
from App.strategies.balancedaynight import BalanceDayNight
from App.strategies.minimizedays import MinimizeDays

STRATEGIES = { "even": EvenDistribution, "balance_day_night": BalanceDayNight, "minimize_days": MinimizeDays }

def auto_generate_schedule(admin_id, strategy_name="even"):
    admin = get_user(admin_id)
    if admin.role != "admin":
        raise PermissionError("Only admins can generate schedules")
    
    strategy_class = STRATEGIES.get(strategy_name)
    if not strategy_class:
        raise ValueError(f"Invalid strategy '{strategy_name}'. Valid strategies are: {list(STRATEGIES.keys())}")
    
    strategy = strategy_class()
    staff_list = Staff.query.all()
    shifts = Shift.query.all()

    return strategy.distribute_shifts(staff_list, shifts)
