# coordination/result_aggregator.py

class ResultAggregator:
    @staticmethod
    def aggregate_sequential(results: dict) -> any:
        """取最后一个结果（你的原逻辑）"""
        if not results:
            return None
        return list(results.values())[-1]

    @staticmethod
    def aggregate_vote(results: dict) -> any:
        # 可扩展：多数投票、加权平均等
        raise NotImplementedError