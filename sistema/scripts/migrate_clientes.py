"""
Migração: adiciona campos individuais de endereço na tabela 'clientes'.

Execute uma única vez:
    python migrate_clientes.py
"""
import sys
sys.path.insert(0, '.')

from app.core.database import engine
from sqlalchemy import text

NOVAS_COLUNAS = [
    ("cep",         "VARCHAR(9)"),
    ("logradouro",  "VARCHAR(200)"),
    ("numero",      "VARCHAR(20)"),
    ("complemento", "VARCHAR(100)"),
    ("bairro",      "VARCHAR(100)"),
    ("cidade",      "VARCHAR(100)"),
    ("estado",      "VARCHAR(2)"),
]

def migrar():
    with engine.connect() as conn:
        for col_nome, col_tipo in NOVAS_COLUNAS:
            try:
                # PostgreSQL suporta IF NOT EXISTS no ALTER TABLE
                conn.execute(text(
                    f"ALTER TABLE clientes ADD COLUMN IF NOT EXISTS {col_nome} {col_tipo}"
                ))
                print(f"  ✅ Coluna '{col_nome}' adicionada")
            except Exception as e:
                print(f"  ⚠️  '{col_nome}': {e}")
        conn.commit()
    print("\n✅ Migração concluída! Reinicie o servidor.")

if __name__ == "__main__":
    print("🔄 Migrando tabela 'clientes'...\n")
    migrar()
