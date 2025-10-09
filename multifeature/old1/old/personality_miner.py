# personality_miner.py

from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import CountVectorizer
import numpy as np

class PersonalityMiner:
    def __init__(self, user_profiler):
        self.user_profiler = user_profiler

    def build_feature_vectors(self):
        all_users = self.user_profiler.get_all_user_ids()
        all_features = set()
        for uid in all_users:
            fs = self.user_profiler.get_profile(uid)
            all_features.update(fs.get_features())

        feature_list = sorted(all_features)
        vectorizer = CountVectorizer(vocabulary=feature_list)
        docs = []
        for uid in all_users:
            feats = self.user_profiler.get_profile(uid).get_features()
            doc = " ".join(feats)
            docs.append(doc)

        X = vectorizer.transform(docs)
        return np.array(X.todense()), all_users, feature_list

    def cluster_users(self, eps=0.5, min_samples=2):
        X, uids, features = self.build_feature_vectors()
        clustering = DBSCAN(metric='cosine', eps=eps, min_samples=min_samples).fit(X)

        clusters = {}
        for i, label in enumerate(clustering.labels_):
            if label == -1:
                continue
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(uids[i])

        return clusters

    def generate_personality_type(self, cluster_label, cluster_uids):
        combined = FeatureSet()
        for uid in cluster_uids:
            combined.merge(self.user_profiler.get_profile(uid))

        type_name = f"type_{cluster_label}"
        self.user_profiler.generate_user_type(type_name, cluster_uids)
        return type_name, combined