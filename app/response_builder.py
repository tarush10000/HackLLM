def build_json_response(question: str, clauses: list):
    # Combine clauses + decision logic (use LLM again here if needed)
    response = f"Answer based on: {', '.join(clauses[:2])}..."  # Placeholder
    return response