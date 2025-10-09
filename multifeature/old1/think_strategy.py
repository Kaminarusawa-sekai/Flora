from abc import ABC, abstractmethod
from multifeature.evolver import Evolver

# =================== 策略接口 ===================



class ThinkStrategy(ABC):
    def __init__(self, engine):
        self.engine = engine

    @abstractmethod
    def generate_rule(self, observed: list):
        pass

    @abstractmethod
    def set_goal(self, observed: list):
        pass

    @abstractmethod
    def optimize_operation(self, operation: str, observed: list):
        pass

    @abstractmethod
    def get_name(self):
        pass