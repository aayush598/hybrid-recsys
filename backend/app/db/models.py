from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(200), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ratings = relationship("Rating", back_populates="user", lazy="dynamic")
    interactions = relationship("UserInteraction", back_populates="user", lazy="dynamic")


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    genres = Column(String(500), nullable=True)
    year = Column(Integer, nullable=True)
    overview = Column(Text, nullable=True)
    poster_url = Column(String(1000), nullable=True)
    vote_average = Column(Float, nullable=True)
    vote_count = Column(Integer, nullable=True)
    popularity = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ratings = relationship("Rating", back_populates="movie", lazy="dynamic")
    tags = relationship("MovieTag", back_populates="movie", lazy="dynamic")
    features = relationship("MovieFeature", back_populates="movie", uselist=False)


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False, index=True)
    rating = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ratings")
    movie = relationship("Movie", back_populates="ratings")


class MovieTag(Base):
    __tablename__ = "movie_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False, index=True)
    tag = Column(String(200), nullable=False)
    relevance = Column(Float, default=1.0)

    movie = relationship("Movie", back_populates="tags")


class MovieFeature(Base):
    __tablename__ = "movie_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), unique=True, nullable=False)
    embedding = Column(Text, nullable=True)
    genre_vector = Column(Text, nullable=True)
    content_embedding = Column(Text, nullable=True)

    movie = relationship("Movie", back_populates="features")


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False)
    intensity = Column(Float, default=1.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interactions")


class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(100), nullable=True)
    algorithm = Column(String(50), nullable=False)
    recommended_movie_ids = Column(Text, nullable=False)
    latency_ms = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ABTestAssignment(Base):
    __tablename__ = "ab_test_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False, index=True)
    experiment_name = Column(String(100), nullable=False)
    variant = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
