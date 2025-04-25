from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from models.models import Notification
from utils.security import verify_session_token
from dataBase import get_db_session
from pydantic import BaseModel
import logging
from utils.response import create_response, session_token_invalid_response

# Configurar el logger
logging.basicConfig(level=logging.INFO)  # Cambia a DEBUG si necesitas más detalles
logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic model para la respuesta de notificación
class NotificationResponse(BaseModel):
    notifications_id: int  # ID de la notificación
    message: Optional[str]  # Mensaje de la notificación
    date: datetime  # Fecha de la notificación
    notification_type: Optional[str]  # Tipo de notificación
    invitation_id: Optional[int]  # ID de la invitación asociada (si aplica)
    farm_id: Optional[int]  # ID de la finca asociada (si aplica)
    notification_state: Optional[str]  # Estado de la notificación

    class Config:
        from_attributes = True  # Permitir que los atributos se usen como parámetros de entrada
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Serializar fechas en formato ISO
        }

@router.get("/get-notification")
def get_notifications(session_token: str, db: Session = Depends(get_db_session)):
    """
    Endpoint para obtener las notificaciones de un usuario autenticado.

    Parámetros:
    - session_token: Token de sesión del usuario.
    - db: Sesión de la base de datos (inyectada automáticamente).

    Retorna:
    - Respuesta con las notificaciones del usuario.
    """
    # Verificar el session_token y obtener el usuario autenticado
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning(f"Sesión inválida para el token: {session_token}")
        return session_token_invalid_response()

    logger.info(f"Usuario autenticado: {user.user_id} - {user.name}")

    # Consultar las notificaciones del usuario en la base de datos
    notifications = db.query(Notification).filter(Notification.user_id == user.user_id).all()

    logger.info(f"Notificaciones obtenidas: {len(notifications)}")

    if not notifications:
        logger.info("No hay notificaciones para este usuario.")
        return create_response("success", "No hay notificaciones para este usuario.", data=[])

    # Mostrar las notificaciones obtenidas antes de serializarlas
    for notification in notifications:
        logger.debug(f"Notificación obtenida: {notification}")
        logger.debug(f"Notificación ID: {notification.notifications_id}, State ID: {notification.notification_state_id}")

        # Verificar si la relación 'state' está cargada y no es None
        if notification.state is None:
            logger.warning(f"La notificación con ID {notification.notifications_id} no tiene 'state'.")
        else:
            logger.debug(f"State: {notification.state.name}")

    # Convertir las notificaciones a un formato que Pydantic pueda manejar
    try:
        notification_responses = [
            NotificationResponse(
                notifications_id=notification.notifications_id,
                message=notification.message,
                date=notification.date,
                notification_type=notification.notification_type.name if notification.notification_type else None,
                invitation_id=notification.invitation_id,
                farm_id=notification.farm_id,
                notification_state=notification.state.name if notification.state else None
            )
            for notification in notifications
        ]
        logger.info(f"Notificaciones serializadas correctamente: {len(notification_responses)}")
        
        # Convertir a dict usando Pydantic
        notification_responses_dict = [n.dict() for n in notification_responses]
    except Exception as e:
        # Loguear el error exacto de serialización
        logger.error(f"Error de serialización: {e}")
        return create_response("error", f"Error de serialización: {str(e)}", data=[])

    # Devolver la respuesta exitosa con las notificaciones encontradas
    return create_response("success", "Notificaciones obtenidas exitosamente.", data=notification_responses_dict)
