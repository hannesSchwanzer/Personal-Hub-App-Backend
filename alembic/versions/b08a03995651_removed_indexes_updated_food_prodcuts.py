"""removed indexes + updated food prodcuts

Revision ID: b08a03995651
Revises: d0775425bc11
Create Date: 2026-05-18 18:27:26.388062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b08a03995651'
down_revision: Union[str, Sequence[str], None] = 'd0775425bc11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    with op.batch_alter_table('food_product') as batch_op:
        batch_op.drop_column('search_vector')
        # Rename column 'completeness' to 'completeness_score'
        batch_op.alter_column('completeness', new_column_name='completeness_score')
        # Add new 'categories' column
        batch_op.add_column(sa.Column('categories', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))

    op.execute("DROP INDEX IF EXISTS idx_generic_foods_search;")
    op.execute("DROP INDEX IF EXISTS idx_products_search;")
    op.execute("DROP INDEX IF EXISTS idx_generic_foods_name_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_products_name_trgm;")

def downgrade() -> None:
    with op.batch_alter_table('food_product') as batch_op:
        # Re-add the 'search_vector' column
        batch_op.add_column(sa.Column(
            'search_vector', 
            sa.types.TEXT(),
            sa.Computed("to_tsvector('simple', name)", persisted=True)
        ))
        # Rename column 'completeness_score' back to 'completeness'
        batch_op.alter_column('completeness_score', new_column_name='completeness')
        # Drop the 'categories' column
        batch_op.drop_column('categories')


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
