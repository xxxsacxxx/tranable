from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    account_owner = Column(String(120))
    default_incoterm = Column(String(10))
    notes = Column(String(500))

    contacts = relationship("CustomerContact", back_populates="customer")
    products = relationship("Product", back_populates="customer")


class CustomerContact(Base, TimestampMixin):
    __tablename__ = "customer_contacts"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(150))
    phone = Column(String(40))

    customer = relationship("Customer", back_populates="contacts")


class User(Base, TimestampMixin):
    """Internal platform user (sales, ops, customs, admin) — RBAC role per PRD section on security."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(30), nullable=False, default="operations")  # sales|operations|customs|finance|admin
