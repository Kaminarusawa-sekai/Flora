# utils/data_scope.py

def matches_data_scope(data_scope: dict, context: dict) -> bool:
    return all(context.get(k) == v for k, v in data_scope.items())