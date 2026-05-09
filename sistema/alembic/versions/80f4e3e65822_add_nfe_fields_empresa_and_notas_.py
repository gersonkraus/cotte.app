"""add_nfe_fields_empresa_and_notas_fiscais_table

Revision ID: 80f4e3e65822
Revises: z027_forma_pagamento_exibir_no_whatsapp
Create Date: 2026-05-08 16:32:16.291189

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '80f4e3e65822'
down_revision: Union[str, None] = 'z027_forma_pagamento_exibir_no_whatsapp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('empresas', sa.Column('cnpj', sa.String(length=18), nullable=True))
    op.add_column('empresas', sa.Column('inscricao_estadual', sa.String(length=30), nullable=True))
    op.add_column('empresas', sa.Column('inscricao_municipal', sa.String(length=30), nullable=True))
    op.add_column('empresas', sa.Column('regime_tributario', sa.String(length=20), nullable=True))
    op.add_column('empresas', sa.Column('crt', sa.Integer(), nullable=True))
    op.add_column('empresas', sa.Column('endereco_logradouro', sa.String(length=200), nullable=True))
    op.add_column('empresas', sa.Column('endereco_numero', sa.String(length=20), nullable=True))
    op.add_column('empresas', sa.Column('endereco_complemento', sa.String(length=100), nullable=True))
    op.add_column('empresas', sa.Column('endereco_bairro', sa.String(length=100), nullable=True))
    op.add_column('empresas', sa.Column('endereco_cidade', sa.String(length=100), nullable=True))
    op.add_column('empresas', sa.Column('endereco_uf', sa.String(length=2), nullable=True))
    op.add_column('empresas', sa.Column('endereco_cep', sa.String(length=9), nullable=True))
    op.add_column('empresas', sa.Column('endereco_codigo_municipio_ibge', sa.String(length=7), nullable=True))
    op.add_column('empresas', sa.Column('notaas_api_key', sa.String(length=200), nullable=True))
    op.add_column('empresas', sa.Column('notaas_ambiente', sa.String(length=20), nullable=True))
    op.add_column('empresas', sa.Column('notaas_webhook_secret', sa.String(length=200), nullable=True))
    op.alter_column('formas_pagamento_config', 'exibir_no_whatsapp',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('true'))

    conn = op.get_bind()
    has_notas = conn.dialect.has_table(conn, 'notas_fiscais')
    if not has_notas:
        op.create_table(
            'notas_fiscais',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('empresa_id', sa.Integer(), sa.ForeignKey('empresas.id'), nullable=False),
            sa.Column('orcamento_id', sa.Integer(), sa.ForeignKey('orcamentos.id'), nullable=True),
            sa.Column('tipo', sa.String(10), nullable=False),
            sa.Column('modelo', sa.Integer(), nullable=True),
            sa.Column('serie', sa.String(10), nullable=True),
            sa.Column('numero', sa.String(20), nullable=True),
            sa.Column('status', sa.String(30), server_default='pendente'),
            sa.Column('natureza_operacao', sa.String(200), nullable=True),
            sa.Column('notaas_invoice_id', sa.String(100), nullable=True),
            sa.Column('notaas_delivery_id', sa.String(100), nullable=True),
            sa.Column('chave_acesso', sa.String(44), nullable=True),
            sa.Column('protocolo', sa.String(20), nullable=True),
            sa.Column('xml_url', sa.String(500), nullable=True),
            sa.Column('danfe_url', sa.String(500), nullable=True),
            sa.Column('payload_enviado', sa.JSON(), nullable=True),
            sa.Column('erro_codigo', sa.String(50), nullable=True),
            sa.Column('erro_mensagem', sa.Text(), nullable=True),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('emitida_em', sa.DateTime(timezone=True), nullable=True),
            sa.Column('cancelada_em', sa.DateTime(timezone=True), nullable=True),
            sa.Column('cancelamento_motivo', sa.String(500), nullable=True),
            sa.Column('criado_por_id', sa.Integer(), sa.ForeignKey('usuarios.id'), nullable=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False),
        )
        op.create_index(op.f('ix_notas_fiscais_empresa_id'), 'notas_fiscais', ['empresa_id'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_orcamento_id'), 'notas_fiscais', ['orcamento_id'], unique=False)
    else:
        op.alter_column('notas_fiscais', 'criado_em',
                   existing_type=postgresql.TIMESTAMP(),
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=True)
        op.alter_column('notas_fiscais', 'emitida_em',
                   existing_type=postgresql.TIMESTAMP(),
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=True)
        op.alter_column('notas_fiscais', 'cancelada_em',
                   existing_type=postgresql.TIMESTAMP(),
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=True)
        op.create_index(op.f('ix_notas_fiscais_empresa_id'), 'notas_fiscais', ['empresa_id'], unique=False)
        op.create_index(op.f('ix_notas_fiscais_orcamento_id'), 'notas_fiscais', ['orcamento_id'], unique=False)

    op.execute("ALTER TABLE tenant_commercial_leads ALTER COLUMN lead_score DROP DEFAULT")
    op.execute("ALTER TABLE tenant_commercial_leads ALTER COLUMN lead_score TYPE leadscore USING lead_score::leadscore")
    op.execute("ALTER TABLE tenant_commercial_leads ALTER COLUMN lead_score SET DEFAULT 'FRIO'::leadscore")


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Reverter lead_score de Enum para VARCHAR
    op.execute("ALTER TABLE tenant_commercial_leads ALTER COLUMN lead_score DROP DEFAULT")
    op.execute("ALTER TABLE tenant_commercial_leads ALTER COLUMN lead_score TYPE VARCHAR(6) USING lead_score::VARCHAR")
    op.execute("ALTER TABLE tenant_commercial_leads ALTER COLUMN lead_score SET DEFAULT 'frio'")
    op.drop_index(op.f('ix_notas_fiscais_orcamento_id'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_empresa_id'), table_name='notas_fiscais')
    op.alter_column('notas_fiscais', 'cancelada_em',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('notas_fiscais', 'emitida_em',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('notas_fiscais', 'criado_em',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('formas_pagamento_config', 'exibir_no_whatsapp',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('true'))
    op.drop_column('empresas', 'notaas_webhook_secret')
    op.drop_column('empresas', 'notaas_ambiente')
    op.drop_column('empresas', 'notaas_api_key')
    op.drop_column('empresas', 'endereco_codigo_municipio_ibge')
    op.drop_column('empresas', 'endereco_cep')
    op.drop_column('empresas', 'endereco_uf')
    op.drop_column('empresas', 'endereco_cidade')
    op.drop_column('empresas', 'endereco_bairro')
    op.drop_column('empresas', 'endereco_complemento')
    op.drop_column('empresas', 'endereco_numero')
    op.drop_column('empresas', 'endereco_logradouro')
    op.drop_column('empresas', 'crt')
    op.drop_column('empresas', 'regime_tributario')
    op.drop_column('empresas', 'inscricao_municipal')
    op.drop_column('empresas', 'inscricao_estadual')
    op.drop_column('empresas', 'cnpj')
    # ### end Alembic commands ###
