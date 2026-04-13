from app.core.database import SessionLocal
from app.models.models import Empresa
db = SessionLocal()
emp = db.query(Empresa).first()
if emp:
    print(f"Current auto: {emp.utilizar_agendamento_automatico}")
    print(f"Current pos: {emp.agendamento_opcoes_somente_apos_liberacao}")
    print(f"Current modo: {emp.agendamento_modo_padrao}")
    print(f"Current choice: {emp.agendamento_escolha_obrigatoria}")
else:
    print("No Empresa found")
