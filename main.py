from fastapi import FastAPI
from endpoints import auth, utils, farm ,invitation, notification, collaborators, plots, transaction, reports
from dataBase import engine
from models.models import Base
import os
import logging

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


# Crear todas las tablas
Base.metadata.create_all(bind=engine)

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Incluir las rutas de auth con prefijo y etiqueta
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])

# Incluir las rutas de utilidades (roles y unidades de medida)
app.include_router(utils.router, prefix="/utils", tags=["Utilidades"])

# Incluir las rutas de gestión de fincas
app.include_router(farm.router, prefix="/farm", tags=["Fincas"])

# Incluir las rutas de invitaciones
app.include_router(invitation.router, prefix="/invitation", tags=["Invitaciones"])

# Incluir las rutas de gestión de lotes
app.include_router(plots.router, prefix="/plots", tags=["Lotes"])

# Incluir las rutas de notificaciones
app.include_router(notification.router, prefix="/notification", tags=["Notificaciones"])

# Incluir las rutas de colaboradores
app.include_router(collaborators.router, prefix="/collaborators", tags=["Collaborators"])

# Incluir las rutas de transacciones
app.include_router(transaction.router, prefix="/transaction", tags=["transaction"])

app.include_router(reports.router, prefix="/reports", tags=["Reports"])

# Incluir las rutas de farm con prefijo y etiqueta

@app.get("/")
def read_root():
    """
    Ruta raíz que retorna un mensaje de bienvenida.

    Returns:
        dict: Un diccionario con un mensaje de bienvenida.
    """
    return {"message": "Welcome to the FastAPI application CoffeeTech!"}