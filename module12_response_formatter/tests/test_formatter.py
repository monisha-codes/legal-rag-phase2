from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/formatter/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_format_success():
    payload = {
        "guardrail_passed_answer": (
            "Under Section 138 of the Negotiable Instruments Act, cheque dishonour "
            "may attract criminal liability if statutory conditions are met [1]. "
            "Procedural compliance also matters [2]. [[DEBUG: remove this]]"
        ),
        "guardrail_report": {
            "claims_checked": 2,
            "entailed_count": 2,
            "flagged_count": 0,
            "flagged_claims": []
        },
        "citation_verification_report": {
            "total_citations": 2,
            "verified_count": 2,
            "removed_count": 0,
            "flagged_markers": []
        },
        "source_chunk_metadata": [
            {
                "source_url": "https://example.org/ni-act/section-138",
                "act_name": "Negotiable Instruments Act, 1881",
                "section_number": "138",
                "year": 1881
            },
            {
                "source_url": "https://example.org/ni-act/proviso",
                "act_name": "Negotiable Instruments Act, 1881",
                "section_number": "138 proviso",
                "year": 1881
            }
        ],
        "user_tier": "free",
        "trace_id": "trace-success-001",
        "classification_metadata": {
            "jurisdiction": ["IN"],
            "act_name": "Negotiable Instruments Act, 1881"
        },
        "signal": None
    }

    response = client.post("/formatter/format", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["formatted_response"]["trace_id"] == "trace-success-001"
    assert len(data["formatted_response"]["citations"]) == 2
    assert "[[DEBUG" not in data["formatted_response"]["answer_text"]


def test_format_citation_fail():
    payload = {
        "guardrail_report": {
            "claims_checked": 0,
            "entailed_count": 0,
            "flagged_count": 0,
            "flagged_claims": []
        },
        "citation_verification_report": {
            "total_citations": 4,
            "verified_count": 1,
            "removed_count": 3,
            "flagged_markers": [2, 3, 4]
        },
        "source_chunk_metadata": [],
        "user_tier": "free",
        "trace_id": "trace-citation-fail-001",
        "classification_metadata": {
            "jurisdiction": ["IN"],
            "act_name": "Consumer Protection Act"
        },
        "signal": "citation_fail"
    }

    response = client.post("/formatter/format", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["formatted_response"]["citations"] == []
    assert "verify enough source citations" in data["formatted_response"]["answer_text"]