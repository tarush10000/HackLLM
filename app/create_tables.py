from app.models_db import Base
from app.database import engine

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
