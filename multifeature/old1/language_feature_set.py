import uuid

# =================== 特征集表示（语言化） ===================
class LanguageFeatureSet:
    def __init__(self, description: str, features: dict, fid: str = None):
        self.description = description
        self.features = features
        self.id = fid or str(uuid.uuid4())

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "features": self.features
        }

    @staticmethod
    def from_dict(data):
        return LanguageFeatureSet(
            description=data["description"],
            features=data["features"],
            fid=data["id"]
        )

    def __repr__(self):
        return f"[{self.id[:6]}] {self.description} | {self.features}"