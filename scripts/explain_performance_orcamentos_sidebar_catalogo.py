#!/usr/bin/env python3
"""
EXPLAIN ANALYZE alinhado às queries reais de:
- GET /orcamentos/ (listagem resumida + padrão selectinload de itens)
- GET /empresa/resumo-sidebar (empresa + 3 COUNTs)
- GET /catalogo/ (serviços com joinedload de categoria)

Uso em staging (Railway/psql):
  cd sistema && source venv/bin/activate
  cd .. && python scripts/explain_performance_orcamentos_sidebar_catalogo.py --empresa-id 42

Variáveis: EMPRESA_ID opcional; se omitida, usa o primeiro id de empresas.

Índices esperados (migration f004_indexes_multitenancy):
  ix_orcamentos_empresa_criado   ON orcamentos (empresa_id, criado_em DESC)
  ix_notificacoes_empresa_lida   ON notificacoes (empresa_id, lida)
  ix_servicos_empresa_id         ON servicos (empresa_id)
  + PK/FK em itens_orcamento.orcamento_id
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="EXPLAIN ANALYZE — orçamentos, sidebar, catálogo")
    parser.add_argument(
        "--empresa-id",
        type=int,
        default=None,
        help="empresa_id para filtrar (default: primeiro registro em empresas)",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="usa só EXPLAIN (sem ANALYZE) — mais rápido, sem medir tempo real",
    )
    args = parser.parse_args()

    os.chdir(os.path.join(os.path.dirname(__file__), "..", "sistema"))
    sys.path.insert(0, os.getcwd())

    from sqlalchemy import text

    from app.core.database import SessionLocal, engine

    prefix = "EXPLAIN " if args.no_analyze else "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "

    session = SessionLocal()
    try:
        eid = args.empresa_id
        if eid is None:
            row = session.execute(text("SELECT id FROM empresas ORDER BY id LIMIT 1")).fetchone()
            if not row:
                print("Nenhuma empresa no banco; passe --empresa-id explicitamente.")
                return 1
            eid = int(row[0])
            print(f"Usando empresa_id={eid} (primeiro registro)\n")

        def run_block(title: str, sql_body: str) -> None:
            print("=" * 72)
            print(title)
            print("=" * 72)
            result = session.execute(text(prefix + sql_body), {"eid": eid})
            for line in result:
                print(line[0])
            print()

        # 1) Listagem orcamentos — núcleo (Index Scan em ix_orcamentos_empresa_criado esperado)
        run_block(
            "1a) Listagem orçamentos (JOIN cliente, ORDER criado_em DESC, LIMIT 200)",
            """
SELECT o.id
FROM orcamentos o
JOIN clientes c ON c.id = o.cliente_id
WHERE o.empresa_id = :eid
ORDER BY o.criado_em DESC NULLS LAST
LIMIT 200 OFFSET 0
""",
        )

        # 1b) Segunda query do selectinload (itens + servico)
        run_block(
            "1b) Itens dos 200 orçamentos (padrão IN + JOIN servicos)",
            """
SELECT i.id
FROM itens_orcamento i
LEFT JOIN servicos s ON s.id = i.servico_id
WHERE i.orcamento_id IN (
    SELECT o.id
    FROM orcamentos o
    WHERE o.empresa_id = :eid
    ORDER BY o.criado_em DESC NULLS LAST
    LIMIT 200
)
""",
        )

        # 2) Sidebar — mesma ordem lógica do router
        run_block("2a) COUNT orçamentos por empresa", """
SELECT count(*) AS n FROM orcamentos WHERE empresa_id = :eid
""")
        run_block("2b) COUNT usuários (exceto superadmin)", """
SELECT count(*) AS n FROM usuarios
WHERE empresa_id = :eid AND (is_superadmin IS NULL OR is_superadmin = false)
""")
        run_block("2c) COUNT notificações não lidas", """
SELECT count(*) AS n FROM notificacoes
WHERE empresa_id = :eid AND lida = false
""")
        run_block("2d) SELECT empresa (PK)", """
SELECT id FROM empresas WHERE id = :eid
""")

        # 3) Catálogo — joinedload categoria
        run_block(
            "3) Catálogo ativo (JOIN categoria, ORDER BY nome)",
            """
SELECT s.id
FROM servicos s
LEFT JOIN categorias_catalogo cc ON cc.id = s.categoria_id
WHERE s.empresa_id = :eid AND s.ativo = true
ORDER BY s.nome
""",
        )

        print("=" * 72)
        print("Índices em tabelas relevantes (pg_indexes)")
        print("=" * 72)
        idx_sql = text(
            """
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = ANY(:tables)
ORDER BY tablename, indexname
"""
        )
        tables = ["orcamentos", "notificacoes", "servicos", "itens_orcamento", "usuarios", "clientes"]
        seen_names: set[str] = set()
        for row in session.execute(idx_sql, {"tables": tables}).fetchall():
            seen_names.add(row[2])
            print(f"{row[1]}.{row[2]}")
            print(f"  {row[3]}")
            print()

        # Checagem explícita (alembic f004_indexes_multitenancy)
        esperados = (
            "ix_orcamentos_empresa_criado",
            "ix_notificacoes_empresa_lida",
            "ix_servicos_empresa_id",
            "ix_itens_orcamento_orcamento_id",
        )
        print("=" * 72)
        print("Checklist índices (performance multi-tenant / f004)")
        print("=" * 72)
        for nome in esperados:
            ok = nome in seen_names
            print(f"  [{'OK' if ok else 'FALTA'}] {nome}")
        print()
        print(
            "Em bases pequenas o planner pode preferir Seq Scan mesmo com índice; "
            "em staging/produção com volume, espere Index Scan nos filtros acima."
        )

    finally:
        session.close()

    print("Concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
