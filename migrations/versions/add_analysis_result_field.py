"""add analysis_result field to StrengthAnalysisResult table

Revision ID: add_analysis_result_field
Revises: 0d845893a6e1
Create Date: 2025-01-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_analysis_result_field'
down_revision = '0d845893a6e1'
branch_labels = None
depends_on = None


def upgrade():
    # Add analysis_result column to strength_analysis_results table
    with op.batch_alter_table('strength_analysis_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('analysis_result', sa.JSON(), nullable=True))


def downgrade():
    # Remove analysis_result column from strength_analysis_results table
    with op.batch_alter_table('strength_analysis_results', schema=None) as batch_op:
        batch_op.drop_column('analysis_result')