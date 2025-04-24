from sqlalchemy.orm import Session
from models.models import (
    UserState, FarmState, PlotState, NotificationState, 
    UserFarmRoleState, TransactionState, InvitationState
)
import logging

logger = logging.getLogger(__name__)

def get_state(db: Session, status_name: str, entity_type: str):
    """
    Obtiene el estado para diferentes entidades.
    
    Args:
        db (Session): Sesión de la base de datos.
        status_name (str): Nombre del estado a obtener (e.g., "Activo", "Inactivo").
        entity_type (str): Tipo de entidad (e.g., "Farm", "User", "Plot").
        
    Returns:
        El objeto de estado si se encuentra, None en caso contrario.
    """
    try:
        if entity_type.lower() == "user":
            return db.query(UserState).filter(UserState.name == status_name).first()
        elif entity_type.lower() == "farm":
            return db.query(FarmState).filter(FarmState.name == status_name).first()
        elif entity_type.lower() == "plot":
            return db.query(PlotState).filter(PlotState.name == status_name).first()
        elif entity_type.lower() == "notification":
            return db.query(NotificationState).filter(NotificationState.name == status_name).first()
        elif entity_type.lower() == "user_role_farm" or entity_type.lower() == "user_farm_role":
            return db.query(UserFarmRoleState).filter(UserFarmRoleState.name == status_name).first()
        elif entity_type.lower() == "transaction":
            return db.query(TransactionState).filter(TransactionState.name == status_name).first()
        elif entity_type.lower() == "invitation":
            return db.query(InvitationState).filter(InvitationState.name == status_name).first()
        else:
            logger.error(f"Tipo de entidad desconocido: {entity_type}")
            return None
    except Exception as e:
        logger.error(f"Error al obtener el estado '{status_name}' para '{entity_type}': {str(e)}")
        return None
