"""Change source to string

Revision ID: 5d68931b7bf1
Revises: 
Create Date: 2025-02-09 13:25:44.726974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d68931b7bf1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('snapchat_account', 'account_source',
                    existing_type=sa.Enum('WEB', 'IOS', 'MANUAL', 'EXTERNAL', 'WOLF', 'CHARLES', 'TURKEY',
                                          'VILLAIN_MIND', 'SANDWICH_CLUB', 'THRAWN', 'ZACKARY',
                                          name='account_status_enum'),
                    type_=sa.String(50),  # Change to string
                    existing_nullable=False)
    op.alter_column('jobs', 'sources',
                    existing_type=sa.ARRAY(
                        sa.Enum('WEB', 'IOS', 'MANUAL', 'EXTERNAL', 'WOLF', 'CHARLES', 'TURKEY', 'VILLAIN_MIND',
                                'SANDWICH_CLUB', 'THRAWN', 'ZACKARY', name='account_source_enum')),
                    type_=sa.ARRAY(sa.String),  # Change to array of strings
                    existing_nullable=True)


def downgrade() -> None:
    pass
