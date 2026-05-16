import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

from screener import prescreen
from retriever import retrieve, retrieve_multi
from prompts import SYSTEM_PROMPT, build_user_prompt

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

VALID_STATUSES = {"replied", "escalated"}
VALID_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}

RATE_LIMIT_DELAY = 10

# cosine distance thresholds for retrieval confidence
CONFIDENCE_HIGH = 0.5
CONFIDENCE_LOW = 0.8

MAX_RETRIES = 2


def _get_client() -> OpenAI:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def _call_llm(system: str, user: str) -> dict:
    client = _get_client()

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            return json.loads(text)
        except Exception as e:
            print(f"    LLM error (attempt {attempt + 1}/{MAX_RETRIES + 1}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RATE_LIMIT_DELAY)
            else:
                return {
                    "status": "escalated",
                    "product_area": "general_support",
                    "response": "We are unable to process this request automatically. A support agent will review your case.",
                    "justification": "LLM processing failed after retries — escalating for safety.",
                    "request_type": "product_issue",
                }


def _assess_retrieval_confidence(docs: list[dict]) -> str:
    if not docs:
        return "LOW"
    top_distance = docs[0]["distance"]
    if top_distance <= CONFIDENCE_HIGH:
        return "HIGH"
    elif top_distance <= CONFIDENCE_LOW:
        return "MEDIUM"
    return "LOW"


def _validate_output(result: dict) -> dict:
    if result.get("status") not in VALID_STATUSES:
        result["status"] = "escalated"

    if result.get("request_type") not in VALID_REQUEST_TYPES:
        result["request_type"] = "product_issue"

    result.setdefault("product_area", "general_support")
    result.setdefault("response", "")
    result.setdefault("justification", "")

    if not result["product_area"]:
        result["product_area"] = "general_support"

    return result


def process_ticket(issue: str, subject: str, company: str) -> dict:
    # pre-screen for adversarial/OOS/pleasantries
    screen_result = prescreen(issue, subject, company)
    if screen_result:
        return screen_result

    # retrieve relevant docs from corpus
    query = f"{issue} {subject}".strip()

    if company and company.strip().lower() not in ("none", ""):
        docs = retrieve(query, company=company, top_k=8)
    else:
        multi = retrieve_multi(query, top_k=5)
        all_docs = []
        for comp_docs in multi.values():
            all_docs.extend(comp_docs)
        all_docs.sort(key=lambda d: d["distance"])
        docs = all_docs[:8]

    confidence = _assess_retrieval_confidence(docs)

    # call LLM with retrieved context
    user_prompt = build_user_prompt(issue, subject, company, docs, retrieval_confidence=confidence)
    result = _call_llm(SYSTEM_PROMPT, user_prompt)
    time.sleep(RATE_LIMIT_DELAY)

    return _validate_output(result)
