from sqlalchemy.orm import Session
from app import models_db, schemas

def create_document(db: Session, document: schemas.DocumentCreate):
    db_doc = models_db.Document(**document.dict())
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

def get_document_by_id(db: Session, doc_id: str):
    return db.query(models_db.Document).filter(models_db.Document.id == doc_id).first()
