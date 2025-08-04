from fastapi import FastAPI, Header, HTTPException
from app.models import QueryRequest, QueryResponse
from app.parser import extract_question_intent
from app.vector_store import search_relevant_clauses
from app.response_builder import build_json_response

app = FastAPI()

@app.post("/api/v1/hackrx/run", response_model=QueryResponse)
async def run_query(request: QueryRequest, authorization: str = Header(...)):
    if authorization != "Bearer 581054ca933196fa7bf56dfedb2fda06fc38915f159c49f2f3a3cfb95a4a4759":
        raise HTTPException(status_code=403, detail="Invalid token")
    
    answers = []
    for question in request.questions:
        intent = extract_question_intent(question)
        clauses = search_relevant_clauses(intent)
        structured_answer = build_json_response(question, clauses)
        answers.append(structured_answer)

    return {"answers": answers}
