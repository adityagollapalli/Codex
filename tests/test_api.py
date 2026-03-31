"""API-level tests for core DocuMind flows."""

from fastapi.testclient import TestClient


def test_upload_query_and_analysis_flow(client: TestClient) -> None:
    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "doc.txt",
                (
                    b"DocuMind helps analysts upload PDFs, CSVs, and text files. "
                    b"It cleans text, chunks documents, indexes embeddings, "
                    b"and answers questions with citations."
                ),
                "text/plain",
            )
        },
    )
    assert upload_response.status_code == 201
    payload = upload_response.json()
    document_id = payload["document"]["id"]
    assert payload["document"]["chunk_count"] >= 1

    list_response = client.get("/api/v1/documents")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = client.get(f"/api/v1/documents/{document_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["filename"] == "doc.txt"

    summary_response = client.post(f"/api/v1/documents/{document_id}/summarize")
    assert summary_response.status_code == 200
    assert summary_response.json()["summary_status"] == "completed"

    stats_response = client.get(f"/api/v1/documents/{document_id}/stats")
    assert stats_response.status_code == 200
    assert stats_response.json()["chunk_count"] >= 1

    query_response = client.post(
        "/api/v1/query",
        json={
            "question": "What can the system ingest?",
            "document_ids": [document_id],
            "top_k": 3,
        },
    )
    assert query_response.status_code == 200
    assert query_response.json()["retrieval_count"] >= 1
    assert len(query_response.json()["citations"]) >= 1
