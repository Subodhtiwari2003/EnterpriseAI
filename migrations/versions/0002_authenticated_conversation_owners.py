from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_authenticated_conversation_owners"
down_revision: Union[str, Sequence[str], None] = "0001_conversation_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "chat_conversations",
        "user_id",
        new_column_name="owner_id",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
    op.drop_index(
        "ix_chat_conversations_user_id",
        table_name="chat_conversations",
    )
    op.create_index(
        "ix_chat_conversations_owner_id",
        "chat_conversations",
        ["owner_id"],
        unique=False,
    )
    op.alter_column(
        "chat_messages",
        "user_id",
        new_column_name="owner_id",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "chat_messages",
        "owner_id",
        new_column_name="user_id",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
    op.drop_index(
        "ix_chat_conversations_owner_id",
        table_name="chat_conversations",
    )
    op.alter_column(
        "chat_conversations",
        "owner_id",
        new_column_name="user_id",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
    op.create_index(
        "ix_chat_conversations_user_id",
        "chat_conversations",
        ["user_id"],
        unique=False,
    )
