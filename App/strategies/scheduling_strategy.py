from abc import ABC, abstractmethod

class SchedulingStrategy(ABC):
    @abstractmethod
    def distribute(self, staff, shifts, week_start=None):
        raise NotImplementedError("distribute must be implemented by subclasses")