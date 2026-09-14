"""Modelo relacional normalizado para los datos operativos del monitor."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampedModel, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    monitored_databases: Mapped[list["MonitoredDatabase"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    threshold_profiles: Mapped[list["ThresholdProfile"]] = relationship(back_populates="owner")


class DatabaseEngine(Base):
    """Catálogo extensible de motores que la plataforma puede monitorear."""

    __tablename__ = "database_engines"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    monitored_databases: Mapped[list["MonitoredDatabase"]] = relationship(back_populates="engine")
    metric_definitions: Mapped[list["MetricDefinition"]] = relationship(back_populates="engine")
    threshold_profiles: Mapped[list["ThresholdProfile"]] = relationship(back_populates="engine")


class MonitoredDatabase(TimestampedModel, Base):
    """Una instancia externa perteneciente a un usuario."""

    __tablename__ = "monitored_databases"
    __table_args__ = (
        UniqueConstraint("owner_id", "engine_id", "name", name="uq_monitored_database_owner_engine_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    engine_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("database_engines.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    connection_uri_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner: Mapped[User] = relationship(back_populates="monitored_databases")
    engine: Mapped[DatabaseEngine] = relationship(back_populates="monitored_databases")
    schedule: Mapped["MonitoringSchedule"] = relationship(
        back_populates="monitored_database", cascade="all, delete-orphan", uselist=False
    )
    threshold_assignment: Mapped["DatabaseThresholdProfile"] = relationship(
        back_populates="monitored_database", cascade="all, delete-orphan", uselist=False
    )
    samples: Mapped[list["MetricSample"]] = relationship(
        back_populates="monitored_database", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="monitored_database")


class MonitoringSchedule(TimestampedModel, Base):
    """Configuración de ejecución separada de la identidad de la instancia."""

    __tablename__ = "monitoring_schedules"
    __table_args__ = (
        CheckConstraint("interval_seconds >= 10", name="ck_monitoring_schedule_minimum_interval"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    monitored_database_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("monitored_databases.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    interval_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    monitored_database: Mapped[MonitoredDatabase] = relationship(back_populates="schedule")


class MetricDefinition(TimestampedModel, Base):
    """Catálogo: una métrica pertenece a un motor y tiene una unidad estable."""

    __tablename__ = "metric_definitions"
    __table_args__ = (
        UniqueConstraint("engine_id", "code", name="uq_metric_definition_engine_code"),
        CheckConstraint(
            "alert_direction IN ('above', 'below')", name="ck_metric_definition_alert_direction"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    engine_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("database_engines.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    alert_direction: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    engine: Mapped[DatabaseEngine] = relationship(back_populates="metric_definitions")
    values: Mapped[list["MetricValue"]] = relationship(back_populates="metric_definition")
    threshold_rules: Mapped[list["ThresholdRule"]] = relationship(back_populates="metric_definition")


class ThresholdProfile(TimestampedModel, Base):
    """Conjunto reutilizable de umbrales de un motor para un usuario."""

    __tablename__ = "threshold_profiles"
    __table_args__ = (
        UniqueConstraint("owner_id", "engine_id", "name", name="uq_threshold_profile_owner_engine_name"),
        Index(
            "uq_threshold_profiles_default_per_engine_owner",
            "owner_id",
            "engine_id",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    engine_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("database_engines.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    owner: Mapped[User] = relationship(back_populates="threshold_profiles")
    engine: Mapped[DatabaseEngine] = relationship(back_populates="threshold_profiles")
    rules: Mapped[list["ThresholdRule"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["DatabaseThresholdProfile"]] = relationship(back_populates="profile")


class ThresholdRule(TimestampedModel, Base):
    """Umbrales de una métrica dentro de un perfil, sin repetir el catálogo."""

    __tablename__ = "threshold_rules"
    __table_args__ = (
        UniqueConstraint("profile_id", "metric_definition_id", name="uq_threshold_rule_profile_metric"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("threshold_profiles.id", ondelete="CASCADE"), nullable=False
    )
    metric_definition_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("metric_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    warning_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    critical_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)

    profile: Mapped[ThresholdProfile] = relationship(back_populates="rules")
    metric_definition: Mapped[MetricDefinition] = relationship(back_populates="threshold_rules")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="threshold_rule")


class DatabaseThresholdProfile(TimestampedModel, Base):
    """Asignación de exactamente un perfil a cada instancia monitoreada."""

    __tablename__ = "database_threshold_profiles"

    monitored_database_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("monitored_databases.id", ondelete="CASCADE"),
        primary_key=True,
    )
    threshold_profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("threshold_profiles.id", ondelete="RESTRICT"), nullable=False
    )

    monitored_database: Mapped[MonitoredDatabase] = relationship(back_populates="threshold_assignment")
    profile: Mapped[ThresholdProfile] = relationship(back_populates="assignments")


class MetricSample(Base):
    """Cabecera de cada intento de recolección; no contiene métricas repetidas."""

    __tablename__ = "metric_samples"
    __table_args__ = (
        Index("ix_metric_samples_database_collected", "monitored_database_id", "collected_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    monitored_database_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("monitored_databases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collection_succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    monitored_database: Mapped[MonitoredDatabase] = relationship(back_populates="samples")
    values: Mapped[list["MetricValue"]] = relationship(
        back_populates="sample", cascade="all, delete-orphan"
    )
    health_assessment: Mapped["HealthAssessment"] = relationship(
        back_populates="sample", cascade="all, delete-orphan", uselist=False
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="sample")


class MetricValue(Base):
    """Un valor atómico por métrica y muestra: mantiene la primera forma normal."""

    __tablename__ = "metric_values"
    __table_args__ = (
        UniqueConstraint("sample_id", "metric_definition_id", name="uq_metric_value_sample_definition"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sample_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("metric_samples.id", ondelete="CASCADE"), nullable=False
    )
    metric_definition_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("metric_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    numeric_value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)

    sample: Mapped[MetricSample] = relationship(back_populates="values")
    metric_definition: Mapped[MetricDefinition] = relationship(back_populates="values")


class HealthAssessment(Base):
    __tablename__ = "health_assessments"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_health_assessment_score_range"),
        CheckConstraint(
            "status IN ('healthy', 'warning', 'critical', 'unknown')",
            name="ck_health_assessment_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sample_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("metric_samples.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sample: Mapped[MetricSample] = relationship(back_populates="health_assessment")


class Alert(TimestampedModel, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_database_status", "monitored_database_id", "status"),
        CheckConstraint("severity IN ('warning', 'critical')", name="ck_alert_severity"),
        CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="ck_alert_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    monitored_database_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("monitored_databases.id", ondelete="CASCADE"), nullable=False
    )
    sample_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("metric_samples.id", ondelete="SET NULL")
    )
    threshold_rule_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("threshold_rules.id", ondelete="SET NULL")
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    monitored_database: Mapped[MonitoredDatabase] = relationship(back_populates="alerts")
    sample: Mapped[MetricSample | None] = relationship(back_populates="alerts")
    threshold_rule: Mapped[ThresholdRule | None] = relationship(back_populates="alerts")
