# app/routes.py
from flask import Blueprint, render_template, request, jsonify
from .query_executor import handle_question

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/api/query", methods=["POST"])
def api_query():
    """
    Accepts JSON: { "question": "<text>" }
    Returns JSON with keys:
      - answer_text (string)
      - chart (base64 image or null)
      - climate_table (list)
      - top_crops (dict)
      - provenance (list)
    This always returns a JSON object (and a 200 on success).
    """
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}

    question = payload.get("question") or payload.get("q") or ""
    if not isinstance(question, str):
        question = str(question)

    if not question.strip():
        return jsonify({
            "answer_text": "Please provide a question (e.g. 'list states' or 'Compare the average annual climate metric in StateA and StateB for the last 5 years').",
            "chart": None,
            "climate_table": [],
            "top_crops": {},
            "provenance": []
        }), 400

    try:
        result = handle_question(question)
        # Ensure we always return all expected keys so frontend doesn't break
        response = {
            "answer_text": result.get("answer_text") if isinstance(result, dict) else str(result),
            "chart": (result.get("chart") if isinstance(result, dict) else None),
            "climate_table": (result.get("climate_table") if isinstance(result, dict) else []),
            "top_crops": (result.get("top_crops") if isinstance(result, dict) else {}),
            "provenance": (result.get("provenance") if isinstance(result, dict) else []),
        }
        # include debug field if present (helpful while developing)
        if isinstance(result, dict) and "debug" in result:
            response["debug"] = result["debug"]
        return jsonify(response)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return jsonify({
            "answer_text": "Internal server error while processing your question.",
            "chart": None,
            "climate_table": [],
            "top_crops": {},
            "provenance": [],
            "error": str(e),
            "debug": tb
        }), 500
