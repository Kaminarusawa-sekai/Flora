# neo4j_recorder.py

from neo4j import GraphDatabase
from typing import Dict, Any
from datetime import datetime

class Neo4jExecutionRecorder:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def record_execution(self, agent_id: str, capability: str, context: Dict, result: Any, timestamp: datetime):
        with self.driver.session() as session:
            session.write_transaction(self._record_execution_tx, agent_id, capability, context, result, timestamp)

    def record_optimization_trial(self, agent_id: str, task_id: str, trial_index: int, params: Dict, result: Any, timestamp: datetime):
        with self.driver.session() as session:
            session.write_transaction(self._record_trial_tx, agent_id, task_id, trial_index, params, result, timestamp)

    @staticmethod
    def _record_execution_tx(tx, agent_id, capability, context, result, timestamp):
        tx.run("""
            MATCH (a:Agent {agent_id: $agent_id})
            CREATE (e:Execution {
                capability: $capability,
                context: $context,
                result: $result,
                timestamp: $timestamp
            })
            CREATE (a)-[:EXECUTED]->(e)
        """, agent_id=agent_id, capability=capability, context=context, result=result, timestamp=timestamp.isoformat())

    @staticmethod
    def _record_trial_tx(tx, agent_id, task_id, trial_index, params, result, timestamp):
        tx.run("""
            MATCH (a:Agent {agent_id: $agent_id})
            CREATE (t:OptimizationTrial {
                task_id: $task_id,
                trial_index: $trial_index,
                params: $params,
                result: $result,
                timestamp: $timestamp
            })
            CREATE (a)-[:RAN_TRIAL]->(t)
        """, agent_id=agent_id, task_id=task_id, trial_index=trial_index, params=params, result=result, timestamp=timestamp.isoformat())