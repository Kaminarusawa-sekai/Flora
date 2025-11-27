# memory/memory_interface.py

class MemoryResponse:
    def __init__(self, key: str, value):
        self.key = key
        self.value = value

class MemoryUpdate:
    def __init__(self, key: str, value):
        self.key = key
        self.value = value

class LoadMemoryForAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id