from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.models import (
    Transactions, Plots, Users, Farms, UserRoleFarm, RolePermission, Permissions
)
from utils.security import verify_session_token
from dataBase import get_db_session
import logging
from typing import List, Optional
from utils.response import create_response, session_token_invalid_response
from utils.state import get_state
from pydantic import BaseModel, Field, conlist
from datetime import date
from fastapi.encoders import jsonable_encoder
from collections import defaultdict

router = APIRouter()

logger = logging.getLogger(__name__)

# Modelos de Pydantic

class FinancialReportRequest(BaseModel):
    plot_ids: conlist(int) = Field(..., description="Lista de IDs de lotes (puede ser un solo ID)")
    fechaInicio: date = Field(..., description="Fecha de inicio del periodo")
    fechaFin: date = Field(..., description="Fecha de fin del periodo")
    include_transaction_history: bool = Field(False, description="Indica si se debe incluir el historial de transacciones")


class FinancialCategoryBreakdown(BaseModel):
    category_name: str
    monto: float

class PlotFinancialData(BaseModel):
    plot_id: int
    plot_name: str
    ingresos: float
    gastos: float
    balance: float
    ingresos_por_categoria: List[FinancialCategoryBreakdown]
    gastos_por_categoria: List[FinancialCategoryBreakdown]

class FarmFinancialSummary(BaseModel):
    total_ingresos: float
    total_gastos: float
    balance_financiero: float
    ingresos_por_categoria: List[FinancialCategoryBreakdown]
    gastos_por_categoria: List[FinancialCategoryBreakdown]


class TransactionHistoryItem(BaseModel):
    date: date
    plot_name: str
    farm_name: str
    transaction_type: str
    transaction_category: str
    creator_name: str
    value: float
    
class FinancialReportResponse(BaseModel):
    finca_nombre: str
    lotes_incluidos: List[str]
    periodo: str
    plot_financials: List[PlotFinancialData]
    farm_summary: FarmFinancialSummary
    analysis: Optional[str] = None
    transaction_history: Optional[List[TransactionHistoryItem]] = None


class DetectionHistoryRequest(BaseModel):
    plot_ids: conlist(int) = Field(..., description="Lista de IDs de lotes (puede ser uno o varios)")
    fechaInicio: date = Field(..., description="Fecha de inicio del periodo")
    fechaFin: date = Field(..., description="Fecha de fin del periodo")

class DetectionHistoryResponse(BaseModel):
    detections: List[DetectionHistoryItem]

# Endpoint para generar el reporte financiero
@router.post("/financial-report")
def financial_report(
    request: FinancialReportRequest,
    session_token: str,
    db: Session = Depends(get_db_session)
):
    """
    Genera un reporte financiero detallado de los lotes seleccionados en una finca específica.

    - **request**: Contiene los IDs de los lotes, el rango de fechas y si se debe incluir el historial de transacciones.
    - **session_token**: Token de sesión del usuario para validar su autenticación.
    - **db**: Sesión de base de datos proporcionada automáticamente por FastAPI.

    El reporte incluye ingresos, gastos y balance financiero de los lotes y la finca en general.
    """
    # 1. Verificar que el session_token esté presente
    if not session_token:
        logger.warning("No se proporcionó el token de sesión en la cabecera")
        return create_response("error", "Token de sesión faltante", status_code=401)
    
    # 2. Verificar el token de sesión
    user = verify_session_token(session_token, db)
    if not user:
        logger.warning("Token de sesión inválido o usuario no encontrado")
        return session_token_invalid_response()
    
    try:
        # 3. Obtener los lotes seleccionados
        plots = db.query(Plots).filter(Plots.plot_id.in_(request.plot_ids)).all()
        if not plots:
            logger.warning("No se encontraron lotes con los IDs proporcionados")
            return create_response("error", "No se encontraron lotes con los IDs proporcionados", status_code=404)
        
        # Asegurarse de que todos los lotes pertenezcan a la misma finca
        farm_ids = {plot.farm_id for plot in plots}
        if len(farm_ids) != 1:
            logger.warning("Los lotes seleccionados pertenecen a diferentes fincas")
            return create_response("error", "Los lotes seleccionados pertenecen a diferentes fincas", status_code=400)
        
        farm_id = farm_ids.pop()
        farm = db.query(Farms).filter(Farms.farm_id == farm_id).first()
        if not farm:
            logger.warning("La finca asociada a los lotes no existe")
            return create_response("error", "La finca asociada a los lotes no existe", status_code=404)
        
        # 4. Verificar que el usuario esté asociado con esta finca y tenga permisos
        active_urf_state = get_state(db, "Activo", "user_role_farm")
        if not active_urf_state:
            logger.error("Estado 'Activo' para user_role_farm no encontrado")
            return create_response("error", "Estado 'Activo' para user_role_farm no encontrado", status_code=500)
        
        user_role_farm = db.query(UserRoleFarm).filter(
            UserRoleFarm.user_id == user.user_id,
            UserRoleFarm.farm_id == farm_id,
            UserRoleFarm.user_role_farm_state_id == active_urf_state.user_role_farm_state_id
        ).first()
        
        if not user_role_farm:
            logger.warning(f"El usuario {user.user_id} no está asociado con la finca {farm_id}")
            return create_response("error", "No tienes permisos para ver reportes financieros de esta finca", status_code=403)
        
        # Verificar permiso 'read_financial_report'
        role_permission = db.query(RolePermission).join(Permissions).filter(
            RolePermission.role_id == user_role_farm.role_id,
            Permissions.name == "read_financial_report"
        ).first()
        
        if not role_permission:
            logger.warning(f"El rol {user_role_farm.role_id} del usuario no tiene permiso para ver reportes financieros")
            return create_response("error", "No tienes permiso para ver reportes financieros", status_code=403)
        
        # 5. Obtener el estado 'Activo' para Transactions
        active_transaction_state = get_state(db, "Activo", "Transactions")
        if not active_transaction_state:
            logger.error("Estado 'Activo' para Transactions no encontrado")
            return create_response("error", "Estado 'Activo' para Transactions no encontrado", status_code=500)
        
        # 6. Consultar las transacciones de los lotes seleccionados dentro del rango de fechas
        transactions = db.query(Transactions).filter(
            Transactions.plot_id.in_(request.plot_ids),
            Transactions.transaction_date >= request.fechaInicio,
            Transactions.transaction_date <= request.fechaFin,
            Transactions.transaction_state_id == active_transaction_state.transaction_state_id
        ).all()
        
        # 7. Procesar las transacciones para agregaciones
        plot_financials = {}
        farm_ingresos = 0.0
        farm_gastos = 0.0
        farm_ingresos_categorias = defaultdict(float)
        farm_gastos_categorias = defaultdict(float)
        
        for plot in plots:
            plot_financials[plot.plot_id] = {
                "plot_id": plot.plot_id,
                "plot_name": plot.name,
                "ingresos": 0.0,
                "gastos": 0.0,
                "balance": 0.0,
                "ingresos_por_categoria": defaultdict(float),
                "gastos_por_categoria": defaultdict(float)
            }
        
        for txn in transactions:
            plot_id = txn.plot_id
            txn_type = txn.transaction_type
            txn_category = txn.transaction_category
            
            if not txn_type or not txn_category:
                logger.warning(f"Transacción con ID {txn.transaction_id} tiene tipo o categoría inválidos")
                continue  # Omitir transacciones incompletas
            
            category = txn_category.name
            monto = float(txn.value)
            
            if txn_type.name.lower() in ["ingreso", "income", "revenue"]:
                plot_financials[plot_id]["ingresos"] += monto
                plot_financials[plot_id]["ingresos_por_categoria"][category] += monto
                farm_ingresos += monto
                farm_ingresos_categorias[category] += monto
            elif txn_type.name.lower() in ["gasto", "expense", "cost"]:
                plot_financials[plot_id]["gastos"] += monto
                plot_financials[plot_id]["gastos_por_categoria"][category] += monto
                farm_gastos += monto
                farm_gastos_categorias[category] += monto
            else:
                logger.warning(f"Transacción con ID {txn.transaction_id} tiene un tipo desconocido '{txn_type.name}'")
        
        # Calcular balances por lote
        plot_financials_list = []
        for plot_id, data in plot_financials.items():
            data["balance"] = data["ingresos"] - data["gastos"]
            # Convertir defaultdict a list de FinancialCategoryBreakdown
            data["ingresos_por_categoria"] = [
                FinancialCategoryBreakdown(category_name=k, monto=v) for k, v in data["ingresos_por_categoria"].items()
            ]
            data["gastos_por_categoria"] = [
                FinancialCategoryBreakdown(category_name=k, monto=v) for k, v in data["gastos_por_categoria"].items()
            ]
            plot_financials_list.append(PlotFinancialData(**data))
        
        # Resumen financiero de la finca
        farm_balance = farm_ingresos - farm_gastos
        farm_summary = FarmFinancialSummary(
            total_ingresos=farm_ingresos,
            total_gastos=farm_gastos,
            balance_financiero=farm_balance,
            ingresos_por_categoria=[
                FinancialCategoryBreakdown(category_name=k, monto=v) for k, v in farm_ingresos_categorias.items()
            ],
            gastos_por_categoria=[
                FinancialCategoryBreakdown(category_name=k, monto=v) for k, v in farm_gastos_categorias.items()
            ]
        )
        
        # Preparar la respuesta
        report_response = FinancialReportResponse(
            finca_nombre=farm.name,
            lotes_incluidos=[plot.name for plot in plots],
            periodo=f"{request.fechaInicio.isoformat()} a {request.fechaFin.isoformat()}",
            plot_financials=plot_financials_list,
            farm_summary=farm_summary,
            analysis=None  # Puedes agregar lógica para generar un análisis automático si lo deseas
        )
        
        # Agregar historial de transacciones si se solicita
        if request.include_transaction_history:
            transaction_history = []
            for txn in transactions:
                try:
                    # Obtener el nombre del creador consultando la tabla Users
                    creator = db.query(Users).filter(Users.user_id == txn.creador_id).first()
                    creator_name = creator.name if creator else "Desconocido"

                    history_item = TransactionHistoryItem(
                        date=txn.transaction_date,
                        plot_name=txn.plot.name,
                        farm_name=txn.plot.farm.name,
                        transaction_type=txn.transaction_type.name,
                        transaction_category=txn.transaction_category.name,
                        creator_name=creator_name,
                        value=float(txn.value)
                    )
                    transaction_history.append(history_item)
                except Exception as e:
                    logger.warning(f"Error al procesar la transacción ID {txn.transaction_id}: {str(e)}")
                    continue  # Omitir transacciones con errores
            report_response.transaction_history = transaction_history

        
        logger.info(f"Reporte financiero generado para el usuario {user.user_id} en la finca '{farm.name}'")
        
        return create_response("success", "Reporte financiero generado correctamente", data=jsonable_encoder(report_response))
    
    except Exception as e:
        logger.error(f"Error al generar el reporte financiero: {str(e)}")
        return create_response("error", f"Error al generar el reporte financiero: {str(e)}", status_code=500)