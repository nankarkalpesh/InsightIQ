import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    preferred_llm_provider = Column(String(50), nullable=True)
    groq_api_key = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    datasets = relationship("DatasetModel", back_populates="owner", cascade="all, delete-orphan")


class DatasetModel(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    file_path = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="datasets")
    dashboards = relationship("DashboardConfigModel", back_populates="dataset", cascade="all, delete-orphan")
    training_runs = relationship("TrainingRunModel", back_populates="dataset", cascade="all, delete-orphan")
    conversations = relationship("ChatConversationModel", back_populates="dataset", cascade="all, delete-orphan")


class DashboardConfigModel(Base):
    __tablename__ = "dashboard_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    config_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dataset = relationship("DatasetModel", back_populates="dashboards")


class TrainingRunModel(Base):
    __tablename__ = "training_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    target_column = Column(String(255), nullable=False)
    features_json = Column(Text, nullable=False, default="[]")
    model_name = Column(String(255), nullable=False)
    metrics_json = Column(Text, nullable=False, default="{}")
    run_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("DatasetModel", back_populates="training_runs")


class ChatConversationModel(Base):
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False, index=True)
    messages_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dataset = relationship("DatasetModel", back_populates="conversations")
