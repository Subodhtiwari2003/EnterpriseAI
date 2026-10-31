from sqlalchemy.ext.asyncio import AsyncEngine

class Database:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def close(self) -> None:
        await self.engine.dispose()
