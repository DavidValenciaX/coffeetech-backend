import os
import firebase_admin
from firebase_admin import credentials, messaging
import logging

# Ruta al archivo de credenciales
service_account_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'serviceAccountKey.json')

# Inicializar Firebase con el archivo de credenciales
if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)

# Configurar logger
logger = logging.getLogger(__name__)

def send_fcm_notification(fcm_token: str, title: str, body: str):
    """
    Envía una notificación utilizando Firebase Cloud Messaging (FCM).

    Args:
        fcm_token (str): El token de registro FCM del dispositivo al que se enviará la notificación.
        title (str): El título de la notificación.
        body (str): El cuerpo del mensaje de la notificación.

    Raises:
        Exception: Si hay un error al enviar la notificación.
    """
    # Construir el mensaje
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=fcm_token,
    )

    # Enviar la notificación
    try:
        response = messaging.send(message)
        logger.info('Notificación enviada correctamente: %s', response)
    except Exception as e:
        logger.error('Error enviando la notificación: %s', str(e))
