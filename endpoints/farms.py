from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.models import Farms, UserRoleFarm, AreaUnits, Roles, FarmStates, RolePermission, Permissions, UserRoleFarmStates
from utils.security import verify_session_token
from dataBase import get_db_session
import logging
from utils.response import session_token_invalid_response
from utils.response import create_response
from utils.state import get_state

logger = logging.getLogger(__name__)

router = APIRouter()

class CreateFarmRequest(BaseModel):
    """
    Modelo de datos para la creación de una finca.

    **Atributos**:
    - **name**: Nombre de la finca (cadena de texto). Debe ser un valor no vacío ni contener solo espacios.
    - **area**: Área de la finca (float). Debe ser un número positivo mayor que cero.
    - **areaUnit**: Unidad de medida del área (cadena de texto). Debe ser una unidad de medida válida como 'hectáreas' o 'metros cuadrados'.
    """
    name: str
    area: float
    areaUnit: str
    
class ListFarmResponse(BaseModel):
    """
    Modelo de datos para la respuesta al listar fincas.

    **Atributos**:
    - **farm_id**: ID único de la finca (entero).
    - **name**: Nombre de la finca (cadena de texto).
    - **area**: Área de la finca (float), representada en la unidad de medida especificada.
    - **area_unit**: Unidad de medida del área (cadena de texto).
    - **farm_state**: Estado actual de la finca (cadena de texto), por ejemplo, 'Activo' o 'Inactivo'.
    - **role**: Rol del usuario en relación a la finca (cadena de texto), como 'Propietario' o 'Administrador'.
    """
    farm_id: int
    name: str
    area: float
    area_unit: str
    farm_state: str
    role: str
    
class UpdateFarmRequest(BaseModel):
    """
    Modelo de datos para la actualización de una finca existente.

    **Atributos**:
    - **farm_id**: ID de la finca a actualizar (entero). Debe existir una finca con este ID.
    - **name**: Nuevo nombre de la finca (cadena de texto). No puede estar vacío ni contener solo espacios.
    - **area**: Nueva área de la finca (float). Debe ser un número positivo mayor que cero.
    - **areaUnit**: Nueva unidad de medida del área (cadena de texto). Debe ser una unidad de medida válida como 'hectáreas' o 'metros cuadrados'.
    """
    farm_id: int
    name: str
    area: float
    areaUnit: str

# Función auxiliar para crear una respuesta uniforme


@router.post("/create-farm")
def create_farm(request: CreateFarmRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Crea una nueva finca y asigna al usuario como propietario.

    **Parámetros**:
    - **request**: Objeto que contiene los datos de la finca (nombre, área, y unidad de medida).
    - **session_token**: Token de sesión del usuario.
    - **db**: Sesión de base de datos, se obtiene automáticamente.

    **Respuestas**:
    - **200 OK**: Finca creada y usuario asignado correctamente.
    - **400 Bad Request**: Si los datos de la finca no son válidos o no se encuentra el estado requerido.
    - **401 Unauthorized**: Si el token de sesión es inválido o el usuario no tiene permisos.
    - **500 Internal Server Error**: Si ocurre un error al intentar crear la finca o asignar el usuario.
    
    """
    # Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    
    # Validación 1: El nombre de la finca no puede estar vacío ni contener solo espacios
    if not request.name or not request.name.strip():
        logger.warning("El nombre de la finca no puede estar vacío o solo contener espacios")
        return create_response("error", "El nombre de la finca no puede estar vacío")

    # Validación 2: El nombre no puede exceder los 100 caracteres
    if len(request.name) > 50:
        logger.warning("El nombre de la finca es demasiado largo")
        return create_response("error", "El nombre de la finca no puede tener más de 50 caracteres")

    # Validación 3: El área no puede ser negativa ni cero
    if request.area <= 0:
        logger.warning("El área de la finca debe ser mayor que cero")
        return create_response("error", "El área de la finca debe ser un número positivo mayor que cero")

    # Validación 4: Área no puede ser extremadamente grande (por ejemplo, no más de 10,000 hectáreas)
    if request.area > 10000:
        logger.warning("El área de la finca no puede exceder las 10,000 unidades de medida")
        return create_response("error", "El área de la finca no puede exceder las 10,000 unidades de medida")

    # Obtener el state "Activo" para el tipo "Farms"
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'Farms'", status_code=400)

    # Comprobar si el usuario ya tiene una finca activa con el mismo nombre
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'user_role_farm'", status_code=400)

    existing_farm = db.query(Farms).join(UserRoleFarm).filter(
        Farms.name == request.name,
        UserRoleFarm.user_id == user.user_id,
        Farms.farm_state_id == active_farm_state.farm_state_id,  # Filtrar solo por fincas activas
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id  # Check if association is active
    ).first()

    if existing_farm:
        logger.warning("El usuario ya tiene una finca activa con el nombre '%s'", request.name)
        return create_response("error", f"Ya existe una finca activa con el nombre '{request.name}' para el propietario")

    # Buscar la unidad de medida (areaUnit)
    area_unit = db.query(AreaUnits).filter(AreaUnits.name == request.areaUnit).first()
    if not area_unit:
        logger.warning("Unidad de medida no válida: %s", request.areaUnit)
        return create_response("error", "Unidad de medida no válida")

    # Obtener el state "Activo" para el tipo "Farms" utilizando get_state
    farm_state_record = get_state(db, "Activo", "Farms")
    if not farm_state_record:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "No se encontró el estado 'Activo' para el tipo 'Farms'", status_code=400)

    try:
        # Crear la nueva finca
        new_farm = Farms(
            name=request.name,
            area=request.area,
            area_unit_id=area_unit.area_unit_id,
            farm_state_id=farm_state_record.farm_state_id
        )
        db.add(new_farm)
        db.commit()
        db.refresh(new_farm)
        logger.info("Finca creada exitosamente con ID: %s", new_farm.farm_id)

        # Buscar el rol "Propietario"
        role = db.query(Roles).filter(Roles.name == "Propietario").first()
        if not role:
            logger.error("Rol 'Propietario' no encontrado")
            raise HTTPException(status_code=400, detail="Rol 'Propietario' no encontrado")

        # Get active state for UserRoleFarm
        active_urf_state = get_state(db, "Activo", "user_role_farm")
        if not active_urf_state:
             logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
             raise HTTPException(status_code=400, detail="No se encontró el estado 'Activo' para el tipo 'user_role_farm'")

        # Crear la relación UserRoleFarm
        user_role_farm = UserRoleFarm(
            user_id=user.user_id,
            farm_id=new_farm.farm_id,
            role_id=role.role_id,
            user_role_farm_state_id=active_urf_state.user_role_farm_state_id  # Use looked-up state ID
        )
        db.add(user_role_farm)
        db.commit()
        logger.info("Usuario asignado como 'Propietario' de la finca con ID: %s", new_farm.farm_id)

        return create_response("success", "Finca creada y usuario asignado correctamente", {
            "farm_id": new_farm.farm_id,
            "name": new_farm.name,
            "area": new_farm.area,
            "area_unit": request.areaUnit
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al crear la finca o asignar el usuario: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al crear la finca o asignar el usuario: {str(e)}")


@router.post("/list-farm")
def list_farm(session_token: str, db: Session = Depends(get_db_session)):
    """
    Endpoint para listar las fincas activas asociadas a un usuario autenticado mediante un token de sesión.

    **Parámetros**:
    - **session_token**: Token de sesión proporcionado por el usuario para autenticarse.
    - **db**: Sesión de base de datos proporcionada por FastAPI a través de la dependencia.

    **Descripción**:
    1. **Verificar sesión**: 
       Se verifica el token de sesión del usuario. Si no es válido, se devuelve una respuesta de token inválido.
    
    2. **Obtener estados activos**: 
       Se buscan los estados "Activo" tanto para las fincas como para la relación `user_role_farm` que define el rol del usuario en la finca.
    
    3. **Realizar la consulta**: 
       Se realiza una consulta a la base de datos para obtener las fincas activas asociadas al usuario autenticado, filtrando por estado "Activo" tanto en la finca como en la relación `user_role_farm`.
    
    4. **Construir la respuesta**: 
       Se construye una lista de las fincas obtenidas, incluyendo detalles como el nombre de la finca, área, unidad de medida, estado y el rol del usuario.

    **Respuestas**:
    - **200**: Lista de fincas obtenida exitosamente.
    - **400**: Error al obtener los estados activos para las fincas o la relación `user_role_farm`.
    - **500**: Error interno del servidor durante la consulta.
    """
    # Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()

    # Obtener el state "Activo" para el tipo "Farms"
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "Estado 'Activo' no encontrado para Farms", status_code=400)

    # Obtener el state "Activo" para el tipo "user_role_farm"
    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)

    try:
        # Realizar la consulta con los filtros adicionales de estado activo
        farms = db.query(Farms, AreaUnits, FarmStates, Roles).select_from(UserRoleFarm).join(
            Farms, UserRoleFarm.farm_id == Farms.farm_id
        ).join(
            AreaUnits, Farms.area_unit_id == AreaUnits.area_unit_id
        ).join(
            FarmStates, Farms.farm_state_id == FarmStates.farm_state_id
        ).join(
            Roles, UserRoleFarm.role_id == Roles.role_id
        ).filter(
            UserRoleFarm.user_id == user.user_id,
            UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
            Farms.farm_state_id == active_farm_state.farm_state_id
        ).all()

        farm_list = []
        for farm, area_unit, farm_state, role in farms:
            farm_list.append(ListFarmResponse(
                farm_id=farm.farm_id,
                name=farm.name,
                area=farm.area,
                area_unit=area_unit.name,
                farm_state=farm_state.name,
                role=role.name
            ))

        return create_response("success", "Lista de fincas obtenida exitosamente", {"farms": farm_list})

    except Exception as e:
        logger.error("Error al obtener la lista de fincas: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al obtener la lista de fincas: {str(e)}")

    
    
@router.post("/update-farm")
def update_farm(request: UpdateFarmRequest, session_token: str, db: Session = Depends(get_db_session)):
    """
    Endpoint para actualizar la información de una finca asociada a un usuario autenticado.

    **Parámetros**:
    - **request**: Objeto de tipo `UpdateFarmRequest` que contiene los datos a actualizar de la finca (nombre, área, unidad de medida).
    - **session_token**: Token de sesión proporcionado por el usuario para autenticarse.
    - **db**: Sesión de base de datos proporcionada por FastAPI a través de la dependencia.

    **Descripción**:
    1. **Verificar sesión**: 
       Se verifica el token de sesión del usuario. Si no es válido, se devuelve una respuesta de token inválido.
    
    2. **Verificar asociación de usuario**: 
       Se verifica si el usuario está asociado con la finca activa que desea actualizar y si tiene el rol adecuado para editar.
    
    3. **Verificar permisos de edición**: 
       Se comprueba si el rol del usuario tiene permisos para editar fincas.

    4. **Validaciones de nombre y área**: 
       Se valida que el nombre no esté vacío, que no exceda los 50 caracteres y que el área sea mayor que cero. También se valida la unidad de medida.

    5. **Verificar existencia de finca y nombre duplicado**: 
       Se busca la finca en la base de datos y se verifica si el nuevo nombre ya está en uso por otra finca del mismo usuario.

    6. **Actualizar finca**: 
       Si todas las validaciones son correctas, se actualizan los datos de la finca en la base de datos.

    **Respuestas**:
    - **200**: Finca actualizada correctamente.
    - **400**: Error en las validaciones de nombre, área o permisos de usuario.
    - **500**: Error interno del servidor durante la actualización.
    """
    # Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()

    # Obtener el state "Activo" para la finca y la relación user_role_farm
    active_farm_state = get_state(db, "Activo", "Farms")
    active_urf_state = get_state(db, "Activo", "user_role_farm")

    # Verificar si el usuario está asociado con la finca y si tanto la finca como la relación están activas
    user_role_farm = db.query(UserRoleFarm).join(Farms).filter(
        UserRoleFarm.farm_id == request.farm_id,
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
        Farms.farm_state_id == active_farm_state.farm_state_id
    ).first()

    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca activa que intenta editar")
        return create_response("error", "No tienes permiso para editar esta finca porque no estás asociado con una finca activa")

    # Verificar permisos para el rol del usuario
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "edit_farm"
    ).first()

    if not role_permission:
        logger.warning("El rol del usuario no tiene permiso para editar la finca")
        return create_response("error", "No tienes permiso para editar esta finca")

    # Validaciones del nombre y área
    if not request.name or not request.name.strip():
        logger.warning("El nombre de la finca no puede estar vacío o solo contener espacios")
        return create_response("error", "El nombre de la finca no puede estar vacío")
    
    if len(request.name) > 50:
        logger.warning("El nombre de la finca es demasiado largo")
        return create_response("error", "El nombre de la finca no puede tener más de 50 caracteres")
    
    if request.area <= 0:
        logger.warning("El área de la finca debe ser mayor que cero")
        return create_response("error", "El área de la finca debe ser un número positivo mayor que cero")

    # Buscar la unidad de medida (areaUnit)
    area_unit = db.query(AreaUnits).filter(AreaUnits.name == request.areaUnit).first()
    if not area_unit:
        logger.warning("Unidad de medida no válida: %s", request.areaUnit)
        return create_response("error", "Unidad de medida no válida")

    try:
        # Buscar la finca que se está intentando actualizar
        farm = db.query(Farms).filter(Farms.farm_id == request.farm_id).first()
        if not farm:
            logger.warning("Finca no encontrada")
            return create_response("error", "Finca no encontrada")

        # Verificar si el nuevo nombre ya está en uso por otra finca en la que el usuario es propietario
        if farm.name != request.name:  # Solo validar el nombre si se está intentando cambiar
            existing_farm = db.query(Farms).join(UserRoleFarm).join(Roles).filter(
                Farms.name == request.name,
                Farms.farm_id != request.farm_id,
                UserRoleFarm.user_id == user.user_id,
                Roles.name == "Propietario",  # Verificar que el usuario sea propietario
                Farms.farm_state_id == active_farm_state.farm_state_id,
                UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
            ).first()

            if existing_farm:
                logger.warning("El nombre de la finca ya está en uso por otra finca del usuario")
                return create_response("error", "El nombre de la finca ya está en uso por otra finca del propietario")

        # Actualizar la finca
        farm.name = request.name
        farm.area = request.area
        farm.area_unit_id = area_unit.area_unit_id

        db.commit()
        db.refresh(farm)
        logger.info("Finca actualizada exitosamente con ID: %s", farm.farm_id)

        return create_response("success", "Finca actualizada correctamente", {
            "farm_id": farm.farm_id,
            "name": farm.name,
            "area": farm.area,
            "area_unit": request.areaUnit
        })
    except Exception as e:
        db.rollback()
        logger.error("Error al actualizar la finca: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al actualizar la finca: {str(e)}")



@router.get("/get-farm/{farm_id}")
def get_farm(farm_id: int, session_token: str, db: Session = Depends(get_db_session)):
    """
    Obtiene los detalles de una finca específica en la que el usuario tiene permisos.
    
    **Parámetros:**
    - `farm_id` (int): ID de la finca a consultar.
    - `session_token` (str): Token de sesión del usuario que está haciendo la solicitud.

    **Respuesta exitosa (200):**
    - **Descripción**: Devuelve la información de la finca, incluyendo nombre, área, unidad de medida, estado y rol del usuario en relación a la finca.

    **Errores:**
    - **401 Unauthorized**: Si el token de sesión es inválido o el usuario no se encuentra.
    - **400 Bad Request**: Si no se encuentra el estado "Activo" para la finca o para la relación `user_role_farm`.
    - **404 Not Found**: Si la finca no se encuentra o no pertenece al usuario.

    ```
    """
    # Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()

    # Obtener el state "Activo" para la finca y user_role_farm
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "Estado 'Activo' no encontrado para Farms", status_code=400)

    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)

    try:
        # Verificar que la finca y la relación user_role_farm estén activas
        farm_data = db.query(Farms, AreaUnits, FarmStates, Roles).select_from(UserRoleFarm).join(
            Farms, UserRoleFarm.farm_id == Farms.farm_id
        ).join(
            AreaUnits, Farms.area_unit_id == AreaUnits.area_unit_id
        ).join(
            FarmStates, Farms.farm_state_id == FarmStates.farm_state_id
        ).join(
            Roles, UserRoleFarm.role_id == Roles.role_id
        ).filter(
            UserRoleFarm.user_id == user.user_id,
            UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
            Farms.farm_state_id == active_farm_state.farm_state_id,
            Farms.farm_id == farm_id
        ).first()

        # Validar si se encontró la finca
        if not farm_data:
            logger.warning("Finca no encontrada o no pertenece al usuario")
            return create_response("error", "Finca no encontrada o no pertenece al usuario")

        farm, area_unit, farm_state, role = farm_data

        # Crear la respuesta en el formato esperado
        farm_response = ListFarmResponse(
            farm_id=farm.farm_id,
            name=farm.name,
            area=farm.area,
            area_unit=area_unit.name,
            farm_state=farm_state.name,
            role=role.name
        )

        return create_response("success", "Finca obtenida exitosamente", {"farm": farm_response})

    except Exception as e:
        # Log detallado para administradores, pero respuesta genérica para el usuario
        logger.error("Error al obtener la finca: %s", str(e))
        return create_response("error", "Ocurrió un error al intentar obtener la finca. Por favor, inténtalo de nuevo más tarde.")


@router.post("/delete-farm/{farm_id}")
def delete_farm(farm_id: int, session_token: str, db: Session = Depends(get_db_session)):
    """
    Elimina (inactiva) una finca específica.

    **Parámetros:**
    - `farm_id` (int): ID de la finca a eliminar.
    - `session_token` (str): Token de sesión del usuario que está haciendo la solicitud.

    **Respuesta exitosa (200):**
    - **Descripción**: Indica que la finca ha sido desactivada correctamente.

    **Errores:**
    - **401 Unauthorized**: Si el token de sesión es inválido o el usuario no se encuentra.
    - **400 Bad Request**: Si no se encuentra el estado "Activo" para la finca o para la relación `user_role_farm`.
    - **403 Forbidden**: Si el usuario no tiene permiso para eliminar la finca.
    - **404 Not Found**: Si la finca no se encuentra.
    - **500 Internal Server Error**: Si ocurre un error al desactivar la finca.

    """
    # Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return create_response("error", "Token de sesión inválido o usuario no encontrado")

    # Obtener el state "Activo" para la finca y user_role_farm
    active_farm_state = get_state(db, "Activo", "Farms")
    if not active_farm_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'Farms'")
        return create_response("error", "Estado 'Activo' no encontrado para Farms", status_code=400)

    active_urf_state = get_state(db, "Activo", "user_role_farm")
    if not active_urf_state:
        logger.error("No se encontró el estado 'Activo' para el tipo 'user_role_farm'")
        return create_response("error", "Estado 'Activo' no encontrado para user_role_farm", status_code=400)

    # Verificar si el usuario está asociado con la finca activa
    user_role_farm = db.query(UserRoleFarm).join(Farms).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == farm_id,
        UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id,
        Farms.farm_state_id == active_farm_state.farm_state_id
    ).first()

    if not user_role_farm:
        logger.warning("El usuario no está asociado con la finca que intenta eliminar")
        return create_response("error", "No tienes permiso para eliminar esta finca")

    # Verificar permisos para eliminar la finca
    role_permission = db.query(RolePermission).join(Permissions).filter(
        RolePermission.role_id == user_role_farm.role_id,
        Permissions.name == "delete_farm"
    ).first()

    if not role_permission:
        logger.warning("El rol del usuario no tiene permiso para eliminar la finca")
        return create_response("error", "No tienes permiso para eliminar esta finca")

    try:
        farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()

        if not farm:
            logger.warning("Finca no encontrada")
            return create_response("error", "Finca no encontrada")

        # Cambiar el estado de la finca a "Inactiva"
        inactive_farm_state = get_state(db, "Inactiva", "Farms")

        if not inactive_farm_state:
            logger.error("No se encontró el estado 'Inactiva' para el tipo 'Farms'")
            raise HTTPException(status_code=400, detail="No se encontró el estado 'Inactiva' para el tipo 'Farms'.")

        farm.farm_state_id = inactive_farm_state.farm_state_id

        # Cambiar el estado de todas las relaciones en user_role_farm a "Inactiva"
        inactive_urf_state = get_state(db, "Inactiva", "user_role_farm")

        if not inactive_urf_state:
            logger.error("No se encontró el estado 'Inactiva' para el tipo 'user_role_farm'")
            raise HTTPException(status_code=400, detail="No se encontró el estado 'Inactiva' para el tipo 'user_role_farm'.")

        user_role_farms = db.query(UserRoleFarm).filter(UserRoleFarm.farm_id == farm_id).all()
        for urf in user_role_farms:
            urf.user_role_farm_state_id = inactive_urf_state.user_role_farm_state_id

        db.commit()
        logger.info("Finca y relaciones en user_role_farm puestas en estado 'Inactiva' para la finca con ID %s", farm_id)
        return create_response("success", "Finca puesta en estado 'Inactiva' correctamente")

    except Exception as e:
        db.rollback()
        logger.error("Error al desactivar la finca: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al desactivar la finca: {str(e)}")
