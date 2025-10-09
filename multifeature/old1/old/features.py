# features.py

class FeatureSet:
    def __init__(self, features=None):
        self.features = set(features) if features else set()

    def add_feature(self, feature):
        self.features.add(feature)

    def has(self, feature):
        return feature in self.features

    def get_features(self):
        return list(self.features)

    def merge(self, other_set):
        self.features.update(other_set.get_features())

    def copy(self):
        return FeatureSet(self.features.copy())

    def __str__(self):
        return f"FeatureSet({self.features})"