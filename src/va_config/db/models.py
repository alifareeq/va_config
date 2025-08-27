# models.py
from geoalchemy2 import Geometry
from sqlalchemy import (
    Column, BigInteger, Integer, Text, Float, TIMESTAMP, text
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.sql.schema import ForeignKeyConstraint, Index

Base = declarative_base()



class DetectionsGIS(Base):
    __tablename__ = "detections_gis"
    __table_args__ = (
        # Put time first in PK to help Timescale chunk pruning
        PrimaryKeyConstraint("timestamp", "object_id", name="detections_gis_pkey"),
        # Helpful indexes
        Index("ix_detections_gis_ts", "timestamp"),
        Index("ix_detections_gis_object_id", "object_id"),
        # Spatial index for ST_Intersects / ST_DWithin / &&:
        Index("idx_detections_gis_bbox_gist", "bbox", postgresql_using="gist"),
        {"schema": "public"},
    )

    object_id  = Column(BigInteger, nullable=False)
    timestamp  = Column(TIMESTAMP(timezone=True), nullable=False)
    frame_idx  = Column(Integer)
    # REQUIRED: polygon, SRID 0, NOT NULL
    bbox       = Column(Geometry(geometry_type="POLYGON", srid=0), nullable=False)
    confidence = Column(Float)


class ProjectTable(Base):
    __tablename__ = 'project_table'
    __table_args__ = {'schema': 'public'}
    project_id = Column(BigInteger, primary_key=True)
    case_title = Column(Text, nullable=True)
    progress = Column(Float, server_default=text('0'))
    objects_found = Column(Integer, server_default=text('0'))
    video_jobs_count = Column(Integer, server_default=text('0'))
    deletion_status = Column(Text, server_default=text("'-'"))
    status = Column(Text, server_default=text("'in_progress'"))
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text('CURRENT_TIMESTAMP')
    )
    expiration_time = Column(
        TIMESTAMP(timezone=True),
        server_default=text("(CURRENT_TIMESTAMP + '5 days'::interval)")
    )

    cameras = relationship(
        "ProjectCamera",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectCamera(Base):
    __tablename__ = 'project_camera'
    __table_args__ = (
        PrimaryKeyConstraint('project_id', 'camera_id',
                             name='project_camera_pkey'),
        ForeignKeyConstraint(
            ['project_id'],
            ['public.project_table.project_id']
        ),
        {'schema': 'public'}
    )

    project_id = Column(BigInteger, nullable=False)
    camera_id = Column(Integer, nullable=False)

    project = relationship("ProjectTable", back_populates="cameras")
    # multiple from/to entries per camera:
    timestamps = relationship(
        "ProjectCameraTimestamp",
        back_populates="camera",
        cascade="all, delete-orphan",
    )


class ProjectCameraTimestamp(Base):
    __tablename__ = 'project_camera_timestamps'
    __table_args__ = (
        PrimaryKeyConstraint(
            'project_id', 'camera_id', 'timestamp_from',
            name='pctime_pkey'
        ),
        ForeignKeyConstraint(
            ['project_id', 'camera_id'],
            ['public.project_camera.project_id',
             'public.project_camera.camera_id']
        ),
        {'schema': 'public'}
    )

    project_id = Column(BigInteger, nullable=False)
    camera_id = Column(Integer, nullable=False)
    timestamp_from = Column(TIMESTAMP(timezone=True), nullable=False)
    timestamp_to = Column(TIMESTAMP(timezone=True), nullable=False)
    camera = relationship("ProjectCamera", back_populates="timestamps")

class UniqueObjects(Base):
    __tablename__ = 'unique_objects'
    __table_args__ = (
        PrimaryKeyConstraint('object_id', 'project_id'),
        {'schema': 'public'}
    )
    object_id = Column(BigInteger)
    project_id = Column(Integer)
    camera_id = Column(Integer, nullable=True)
    job_id = Column(Text, nullable=True)
    class_name = Column(Text, nullable=True)
    image_uri = Column(Text,nullable=True)
    # TODO: MM tried to make it not nullable but the object need to be scanned before finding the best image, should be
    #       changed inside tracking.py before changing nullability of this field
    # TODO: HM/AF/MM If queries on unique_objects (by time ranges) start to slow down as row count grows:
    #   1. Add a btree index:  CREATE INDEX ON unique_objects (project_id, start_time);
    #   2. (Optional) Add a generated tstzrange(period) column with a GiST index
    #      for efficient "overlap" queries (start_time/end_time).
    #   3. Consider converting to a Timescale hypertable only if this table grows into millions+
    #      of rows and we need compression/retention policies.

    start_time = Column(TIMESTAMP(timezone=True), nullable=True)
    end_time = Column(TIMESTAMP(timezone=True), nullable=True)
    start_frame_idx = Column(Integer, nullable=True)
    end_frame_idx = Column(Integer, nullable=True)
    attributes = relationship(
        "UniqueObjectAttribute",
        back_populates="unique_object",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    
class UniqueObjectAttribute(Base):
    """
    One row = one name/value pair linked to a single UniqueObjects record.
    """
    __tablename__ = "unique_object_attributes"
    __table_args__ = (
        # FK to composite PK on unique_objects
        ForeignKeyConstraint(
            ["object_id", "project_id"],
            ["public.unique_objects.object_id", "public.unique_objects.project_id"],
            ondelete="CASCADE",
        ),
        Index("idx_uo_attr_object", "object_id", "project_id"),
        Index("idx_uo_attr_name", "name"),
        {"schema": "public"},
    )

    # surrogate PK
    attribute_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # composite reference back to UniqueObjects
    object_id = Column(BigInteger, nullable=False)
    project_id = Column(Integer, nullable=False)

    # payload
    name = Column(Text, nullable=False)
    value = Column(Text, nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    # back-ref
    unique_object = relationship(
        "UniqueObjects",
        back_populates="attributes",
        cascade_backrefs=False,
        passive_deletes=True,
    )

class VideoJobs(Base):
    __tablename__ = 'video_jobs'
    __table_args__ = (
        PrimaryKeyConstraint('project_id', 'job_id'),
        {'schema': 'public'}
    )
    project_id = Column(BigInteger)
    camera_id = Column(Text, nullable=True)
    job_id = Column(Text)
    timestamp_from_og = Column(TIMESTAMP(timezone=True), nullable=True)
    timestamp_to_og = Column(TIMESTAMP(timezone=True), nullable=True)
    timestamp_from_exact = Column(TIMESTAMP(timezone=True), nullable=True)
    timestamp_to_exact = Column(TIMESTAMP(timezone=True), nullable=True)
    status = Column(Text, server_default=text("'queued'"), nullable=True)
    objects_found = Column(Integer, server_default=text('0'))
    order_number = Column(Integer, server_default=text('0'))
