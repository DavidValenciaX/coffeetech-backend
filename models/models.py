from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Users

class UserStates(Base):
    __tablename__ = 'user_states'
    user_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    users = relationship("Users", back_populates="state")

class Users(Base):
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
    state = relationship("UserStates", back_populates="users")
    user_roles_farms = relationship('UserRoleFarm', back_populates='user')
    notifications = relationship("Notifications", back_populates="user")
    created_transactions = relationship("Transactions", back_populates="creator")
    created_invitations = relationship("Invitations", foreign_keys="[Invitations.inviter_user_id]", back_populates="inviter")
    
class Roles(Base):
    __tablename__ = 'roles'

    role_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relación con RolePermission
    permissions = relationship("RolePermission", back_populates="role")
    user_roles_farms = relationship('UserRoleFarm', back_populates='role')
    invitations = relationship("Invitations", back_populates="suggested_role")

class Permissions(Base):
    __tablename__ = 'permissions'

    permission_id = Column(Integer, primary_key=True, index=True)
    description = Column(String(200), nullable=False)
    name = Column(String(255), nullable=False, unique=True)

    # Relación con RolePermission
    roles = relationship("RolePermission", back_populates="permission")

class RolePermission(Base):
    __tablename__ = 'role_permission'

    role_id = Column(Integer, ForeignKey('roles.role_id'), primary_key=True, nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.permission_id'), primary_key=True, nullable=False)

    # Relaciones con Roles y Permissions
    role = relationship("Roles", back_populates="permissions")
    permission = relationship("Permissions", back_populates="roles")
    
# Farms

class FarmStates(Base):
    __tablename__ = 'farm_states'
    farm_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    farms = relationship("Farms", back_populates="state")

class Farms(Base):
    __tablename__ = 'farms'

    farm_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    area = Column(Numeric(10, 2), nullable=False)
    area_unit_id = Column(Integer, ForeignKey('area_units.area_unit_id'), nullable=False)
    farm_state_id = Column(Integer, ForeignKey('farm_states.farm_state_id'), nullable=False)
    __table_args__ = (CheckConstraint('area > 0', name='check_area_positive'),)

    # Relaciones
    area_unit = relationship("AreaUnits")
    state = relationship("FarmStates")
    invitations = relationship("Invitations", back_populates="farm")
    user_roles_farms = relationship('UserRoleFarm', back_populates='farm')
    plots = relationship("Plots", back_populates="farm")
    notifications = relationship("Notifications", back_populates="farm")
    
class PlotStates(Base):
    __tablename__ = 'plot_states'
    plot_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    plots = relationship("Plots", back_populates="state")

class Plots(Base):
    __tablename__ = 'plots'
    __table_args__ = (
        UniqueConstraint('name', 'farm_id'),
        CheckConstraint('area > 0'),
        CheckConstraint('longitude BETWEEN -180 AND 180'),
        CheckConstraint('latitude BETWEEN -90 AND 90'),
        CheckConstraint('altitude >= 0 AND altitude <= 3000'),
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
    farm = relationship("Farms", back_populates="plots")
    coffee_variety = relationship("CoffeeVarieties", back_populates="plots")
    state = relationship("PlotStates", back_populates="plots")
    area_unit = relationship("AreaUnits", back_populates="plots")
    transactions = relationship("Transactions", back_populates="plot")
    
class CoffeeVarieties(Base):
    __tablename__ = 'coffee_varieties'

    coffee_variety_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relaciones
    plots = relationship("Plots", back_populates="coffee_variety")
    
class AreaUnits(Base):
    __tablename__ = 'area_units'

    area_unit_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    abbreviation = Column(String(10), nullable=False, unique=True)
    farms = relationship("Farms", back_populates="area_unit")
    plots = relationship("Plots", back_populates="area_unit")
    
# Invitations

class InvitationStates(Base):
    __tablename__ = 'invitation_states'
    invitation_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    invitations = relationship("Invitations", back_populates="state")

class Invitations(Base):
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
    farm = relationship("Farms", back_populates="invitations")
    state = relationship('InvitationStates', back_populates="invitations")
    inviter = relationship("Users", foreign_keys=[inviter_user_id], back_populates="created_invitations")
    notifications = relationship("Notifications", back_populates="invitation")
    suggested_role = relationship('Roles', back_populates="invitations")
    
# Notifications

class NotificationStates(Base):
    __tablename__ = 'notification_states'
    notification_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    notifications = relationship("Notifications", back_populates="state")

class NotificationTypes(Base):
    __tablename__ = 'notification_types'

    notification_type_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relación con Notifications
    notifications = relationship("Notifications", back_populates="notification_type")

class Notifications(Base):
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
    user = relationship("Users", back_populates="notifications")
    invitation = relationship("Invitations", back_populates="notifications")
    farm = relationship("Farms", back_populates="notifications")
    notification_type = relationship("NotificationTypes", back_populates="notifications")
    state = relationship("NotificationStates", back_populates="notifications")
    
# Transactions

class TransactionStates(Base):
    __tablename__ = 'transaction_states'
    transaction_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    transactions = relationship("Transactions", back_populates="state")
    
class TransactionTypes(Base):
    __tablename__ = 'transaction_types'

    transaction_type_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relaciones
    categories = relationship("TransactionCategories", back_populates="transaction_type")

class TransactionCategories(Base):
    __tablename__ = 'transaction_categories'
    __table_args__ = (UniqueConstraint('name', 'transaction_type_id'),)

    transaction_category_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    transaction_type_id = Column(Integer, ForeignKey('transaction_types.transaction_type_id'), nullable=False)

    # Relaciones
    transaction_type = relationship("TransactionTypes", back_populates="categories")
    transactions = relationship("Transactions", back_populates="transaction_category")

class Transactions(Base):
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
    plot = relationship("Plots", back_populates="transactions")
    transaction_category = relationship("TransactionCategories", back_populates="transactions")
    state = relationship("TransactionStates", back_populates="transactions")
    creator = relationship("Users", back_populates="created_transactions")
    
# UserRoleFarm
    
class UserRoleFarmStates(Base):
    __tablename__ = 'user_role_farm_states'
    user_role_farm_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    user_role_farm = relationship("UserRoleFarm", back_populates="state")

class UserRoleFarm(Base):
    __tablename__ = 'user_role_farm'

    user_role_farm_id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.role_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.farm_id'), nullable=False)
    user_role_farm_state_id = Column(Integer, ForeignKey('user_role_farm_states.user_role_farm_state_id'), nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'role_id', 'farm_id'),)

    # Relaciones
    user = relationship('Users', back_populates='user_roles_farms')
    farm = relationship('Farms', back_populates='user_roles_farms')
    role = relationship('Roles', back_populates='user_roles_farms')
    state = relationship('UserRoleFarmStates', back_populates='user_role_farm')
