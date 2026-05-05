"""add search + nutrition indexes

Revision ID: 840ebd6a3ba3
Revises: b4c867333589
Create Date: 2026-05-05 23:54:14.085510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '840ebd6a3ba3'
down_revision: Union[str, Sequence[str], None] = 'b4c867333589'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("""CREATE EXTENSION IF NOT EXISTS pg_trgm;""")

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_generic_foods_search
    ON generic_foods USING GIN (search_vector);
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_products_search
    ON products USING GIN (search_vector);
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_generic_foods_name_trgm
    ON generic_foods USING GIN (name gin_trgm_ops);
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_products_name_trgm
    ON products USING GIN (name gin_trgm_ops);
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_generic_foods_search;")
    op.execute("DROP INDEX IF EXISTS idx_products_search;")
    op.execute("DROP INDEX IF EXISTS idx_generic_foods_name_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_products_name_trgm;")
