# storage.py

from features import FeatureSet

class UserProfiler:
    def __init__(self):
        self.user_profiles = {}  # {user_id: FeatureSet}
        self.type_catalog = {}   # {type_name: FeatureSet}
        self.user_counter = 0

    def create_user(self, user_id=None):
        if user_id is None:
            user_id = self.user_counter
            self.user_counter += 1
        self.user_profiles[user_id] = FeatureSet()
        return user_id

    def get_profile(self, user_id):
        return self.user_profiles.get(user_id)

    def update_profile(self, user_id, new_features):
        profile = self.get_profile(user_id)
        if not profile:
            profile = FeatureSet()
            self.user_profiles[user_id] = profile
        for feat in new_features:
            profile.add_feature(feat)

    def generate_user_type(self, type_name, example_user_ids):
        combined = FeatureSet()
        for uid in example_user_ids:
            profile = self.get_profile(uid)
            if profile:
                combined.merge(profile)
        self.type_catalog[type_name] = combined
        return combined

    def find_similar_users(self, user_id, threshold=0.5):
        target = self.get_profile(user_id)
        if not target:
            return []
        result = []
        for uid, profile in self.user_profiles.items():
            if uid == user_id:
                continue
            sim = len(target.features.intersection(profile.features)) / (
                    len(target.features.union(profile.features)) or 1
            )
            if sim >= threshold:
                result.append((uid, sim))
        return sorted(result, key=lambda x: x[1], reverse=True)

    def get_all_user_ids(self):
        return list(self.user_profiles.keys())