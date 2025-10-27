# dify_run_registry.py
import pickle
from typing import Optional, Tuple, Any
from threading import Lock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import Column, Text, LargeBinary, JSON, DateTime
Base = declarative_base()

class DifyRunRecord(Base):
    __tablename__ = "dify_runs"

    run_id = Column(Text, primary_key=True)
    task_id = Column(Text, nullable=False)
    original_sender = Column(LargeBinary, nullable=False)  # pickled ActorAddress
    status = Column(Text, default="pending")
    outputs = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DifyRunRegistry:
    _instance = None
    _lock = Lock()  # 用于线程安全初始化

    def __new__(cls, database_url: str):
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定（Double-checked locking）
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._init(database_url)
        return cls._instance

    def _init(self, database_url: str):
        if self._initialized:
            return
        self.engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=3600)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._initialized = True

    def register_run(
        self,
        run_id: str,
        task_id: str,
        original_sender: Any  # ActorAddress
    ) -> bool:
        try:
            with self.SessionLocal() as session:
                record = DifyRunRecord(
                    run_id=run_id,
                    task_id=task_id,
                    original_sender=pickle.dumps(original_sender),
                )
                session.merge(record)
                session.commit()
                return True
        except Exception as e:
            print(f"[DifyRunRegistry] register_run failed: {e}")
            return False

    def get_run(self, run_id: str) -> Optional[Tuple[str, Any, str]]:
        try:
            with self.SessionLocal() as session:
                record = session.query(DifyRunRecord).filter_by(run_id=run_id).first()
                if not record:
                    return None
                sender = pickle.loads(record.original_sender)
                return record.task_id, sender, record.status
        except Exception as e:
            print(f"[DifyRunRegistry] get_run failed: {e}")
            return None

    def complete_run(
        self,
        run_id: str,
        status: str,
        outputs: Optional[Any] = None,
        error: Optional[str] = None
    ) -> bool:
        try:
            with self.SessionLocal() as session:
                record = session.query(DifyRunRecord).filter_by(run_id=run_id).first()
                if not record:
                    return False
                record.status = status
                record.outputs = outputs
                record.error = error
                session.commit()
                return True
        except Exception as e:
            print(f"[DifyRunRegistry] complete_run failed: {e}")
            return False

    def cleanup_expired(self, max_age_hours: int = 24) -> int:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        try:
            with self.SessionLocal() as session:
                deleted = session.query(DifyRunRecord)\
                    .filter(DifyRunRecord.created_at < cutoff)\
                    .filter(DifyRunRecord.status.in_(["pending", "started"]))\
                    .delete(synchronize_session=False)
                session.commit()
                return deleted
        except Exception as e:
            print(f"[DifyRunRegistry] cleanup_expired failed: {e}")
            return 0


# === 全局单例访问函数 ===
# 用户应通过此函数获取实例，而不是直接实例化
def get_dify_registry(database_url: str = None) -> DifyRunRegistry:
    """
    获取 DifyRunRegistry 单例。
    第一次调用时必须提供 database_url。
    后续调用可省略 database_url。
    """
    if DifyRunRegistry._instance is None:
        if database_url is None:
            raise ValueError("First call to get_dify_registry() must provide 'database_url'")
        return DifyRunRegistry(database_url)
    else:
        if database_url is not None:
            # 可选：警告或忽略
            pass
        return DifyRunRegistry._instance