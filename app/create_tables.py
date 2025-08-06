from models_db import Base
from database import engine

Base.metadata.create_all(bind=engine)
