from __future__ import annotations

from app.db import Base, engine, session_scope
from app.services import SyncService


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with session_scope() as db:
        sync = SyncService(db).sync_orders()
        print(sync.detail)


if __name__ == "__main__":
    main()
