from sqlalchemy import Column, Integer, BigInteger, String, Numeric, ForeignKey, DateTime, Date, Sequence, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import pytz

Base = declarative_base()

class Farm(Base):
    __tablename__ = 'farms'

    farm_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    area = Column(Numeric(10, 2), nullable=False)
    area_unit_id = Column(Integer, ForeignKey('area_units.area_unit_id'), nullable=False)
    farm_state_id = Column(Integer, ForeignKey('farm_states.farm_state_id'), nullable=False)
    __table_args__ = (CheckConstraint('area > 0', name='check_area_positive'),)

    # Relaciones
    area_unit = relationship("AreaUnit")
    state = relationship("FarmState")
    invitations = relationship("Invitation", back_populates="farm")
    user_roles_farms = relationship('UserRoleFarm', back_populates='farm')
    plots = relationship("Plot", back_populates="farm")
    notifications = relationship("Notification", back_populates="farm")


# Modelo para UserRoleFarm (relación entre usuarios, roles y fincas)
class UserRoleFarm(Base):
    __tablename__ = 'user_role_farm'

    user_role_farm_id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.role_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.farm_id'), nullable=False)
    user_farm_role_state_id = Column(Integer, ForeignKey('user_farm_role_states.user_farm_role_state_id'), nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'role_id', 'farm_id'),)

    # Relaciones
    user = relationship('User', back_populates='user_roles_farms')
    farm = relationship('Farm', back_populates='user_roles_farms')
    role = relationship('Role', back_populates='user_roles_farms')
    state = relationship('UserFarmRoleState')


# Modelo para Role
class Role(Base):
    __tablename__ = 'roles'

    role_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relación con RolePermission
    permissions = relationship("RolePermission", back_populates="role")
    user_roles_farms = relationship('UserRoleFarm', back_populates='role')
    invitations = relationship("Invitation", back_populates="suggested_role")


# Modelo para AreaUnit
class AreaUnit(Base):
    __tablename__ = 'area_units'

    area_unit_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    abbreviation = Column(String(10), nullable=False, unique=True)


# Definición del modelo para diversos estados
class UserState(Base):
    __tablename__ = 'user_states'
    user_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    users = relationship("User", back_populates="state")


class FarmState(Base):
    __tablename__ = 'farm_states'
    farm_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    farms = relationship("Farm", back_populates="state")


class PlotState(Base):
    __tablename__ = 'plot_states'
    plot_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    plots = relationship("Plot", back_populates="state")


class NotificationState(Base):
    __tablename__ = 'notification_states'
    notification_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    notifications = relationship("Notification", back_populates="state")


class UserFarmRoleState(Base):
    __tablename__ = 'user_farm_role_states'
    user_farm_role_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)


class TransactionState(Base):
    __tablename__ = 'transaction_states'
    transaction_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    transactions = relationship("Transaction", back_populates="state")


class InvitationState(Base):
    __tablename__ = 'invitation_states'
    invitation_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    invitations = relationship("Invitation", back_populates="state")


# Definición del modelo User
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    verification_token = Column(String(255), nullable=True, unique=True)
    session_token = Column(String(255), nullable=True, unique=True)
    fcm_token = Column(String(255), nullable=True)
    user_state_id = Column(Integer, ForeignKey("user_states.user_state_id"), nullable=False)

    # Relaciones
    state = relationship("UserState", back_populates="users")
    user_roles_farms = relationship('UserRoleFarm', back_populates='user')
    notifications = relationship("Notification", back_populates="user")
    created_transactions = relationship("Transaction", back_populates="creator")
    created_invitations = relationship("Invitation", foreign_keys="[Invitation.inviter_user_id]", back_populates="inviter")


# Modelo para Permission
class Permission(Base):
    __tablename__ = 'permissions'

    permission_id = Column(Integer, primary_key=True, index=True)
    description = Column(String(200), nullable=False)
    name = Column(String(255), nullable=False, unique=True)

    # Relación con RolePermission
    roles = relationship("RolePermission", back_populates="permission")


# Modelo para RolePermission
class RolePermission(Base):
    __tablename__ = 'role_permission'

    role_id = Column(Integer, ForeignKey('roles.role_id'), primary_key=True, nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.permission_id'), primary_key=True, nullable=False)

    # Relaciones con Role y Permission
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


# Modelo para Invitation
class Invitation(Base):
    __tablename__ = 'invitations'
    __table_args__ = (UniqueConstraint('email', 'farm_id'),)

    invitation_id = Column(Integer, primary_key=True)
    email = Column(String(150), nullable=False)
    suggested_role_id = Column(Integer, ForeignKey('roles.role_id'), nullable=False)
    invitation_state_id = Column(Integer, ForeignKey('invitation_states.invitation_state_id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.farm_id'), nullable=False)
    inviter_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    invitation_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relaciones
    farm = relationship("Farm", back_populates="invitations")
    state = relationship('InvitationState', back_populates="invitations")
    inviter = relationship("User", foreign_keys=[inviter_user_id], back_populates="created_invitations")
    notifications = relationship("Notification", back_populates="invitation")
    suggested_role = relationship('Role', back_populates="invitations")


# Modelo para NotificationType
class NotificationType(Base):
    __tablename__ = 'notification_types'

    notification_type_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relación con Notification
    notifications = relationship("Notification", back_populates="notification_type")


# Modelo para Notification
class Notification(Base):
    __tablename__ = 'notifications'

    notification_id = Column(Integer, primary_key=True)
    message = Column(String(255), nullable=True)
    notification_date = Column(DateTime(timezone=True), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    invitation_id = Column(Integer, ForeignKey('invitations.invitation_id'), nullable=True)
    notification_type_id = Column(Integer, ForeignKey('notification_types.notification_type_id'), nullable=False)
    notification_state_id = Column(Integer, ForeignKey('notification_states.notification_state_id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.farm_id'), nullable=True)

    # Relaciones
    user = relationship("User", back_populates="notifications")
    invitation = relationship("Invitation", back_populates="notifications")
    farm = relationship("Farm", back_populates="notifications")
    notification_type = relationship("NotificationType", back_populates="notifications")
    state = relationship("NotificationState", back_populates="notifications")


# Modelo para Plot
class Plot(Base):
    __tablename__ = 'plots'
    __table_args__ = (
        UniqueConstraint('name', 'farm_id'),
        CheckConstraint('area > 0', name='check_area_positive'),
        CheckConstraint('longitude BETWEEN -180 AND 180', name='check_longitude_range'),
        CheckConstraint('latitude BETWEEN -90 AND 90', name='check_latitude_range'),
        CheckConstraint('altitude >= 0 AND altitude <= 3000', name='check_altitude_range'),
    )

    plot_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=True)
    latitude = Column(Numeric(11, 8), nullable=True)
    altitude = Column(Numeric(10, 2), nullable=True)
    coffee_variety_id = Column(Integer, ForeignKey('coffee_varieties.coffee_variety_id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.farm_id'), nullable=False)
    area = Column(Numeric(10, 2), nullable=False)
    area_unit_id = Column(Integer, ForeignKey('area_units.area_unit_id'), nullable=False)
    plot_state_id = Column(Integer, ForeignKey('plot_states.plot_state_id'), nullable=False)

    # Relaciones
    farm = relationship("Farm", back_populates="plots")
    coffee_variety = relationship("CoffeeVariety", back_populates="plots")
    state = relationship("PlotState", back_populates="plots")
    area_unit = relationship("AreaUnit")
    transactions = relationship("Transaction", back_populates="plot")


# Modelo para CoffeeVariety
class CoffeeVariety(Base):
    __tablename__ = 'coffee_varieties'

    coffee_variety_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relaciones
    plots = relationship("Plot", back_populates="coffee_variety")


# Modelo para TransactionCategory
class TransactionCategory(Base):
    __tablename__ = 'transaction_categories'
    __table_args__ = (UniqueConstraint('name', 'transaction_type_id'),)

    transaction_category_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    transaction_type_id = Column(Integer, ForeignKey('transaction_types.transaction_type_id'), nullable=False)

    # Relaciones
    transaction_type = relationship("TransactionType", back_populates="categories")
    transactions = relationship("Transaction", back_populates="transaction_category")


# Modelo para TransactionType
class TransactionType(Base):
    __tablename__ = 'transaction_types'

    transaction_type_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relaciones
    categories = relationship("TransactionCategory", back_populates="transaction_type")


# Modelo para Transaction
class Transaction(Base):
    __tablename__ = 'transactions'

    transaction_id = Column(Integer, primary_key=True)
    plot_id = Column(Integer, ForeignKey('plots.plot_id'), nullable=False)
    description = Column(String(255), nullable=True)
    transaction_date = Column(Date, nullable=False)
    transaction_state_id = Column(Integer, ForeignKey('transaction_states.transaction_state_id'), nullable=False)
    value = Column(Numeric(15, 2), nullable=False)
    transaction_category_id = Column(Integer, ForeignKey('transaction_categories.transaction_category_id'), nullable=False)
    creator_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)

    # Relaciones
    plot = relationship("Plot", back_populates="transactions")
    transaction_category = relationship("TransactionCategory", back_populates="transactions")
    state = relationship("TransactionState", back_populates="transactions")
    creator = relationship("User", back_populates="created_transactions")
