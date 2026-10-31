import pytest
from fastapi.testclient import TestClient
from fastapi import Request

from app.domain.interfaces.application_error import ApplicationError
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_request_id_is_preserved(client: TestClient) -> None:
    request_id = "request-123"

    response = client.get("/health/", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_request_id_is_generated_when_missing(client: TestClient) -> None:
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


@app.get("/test/app-error", include_in_schema=False)
async def raise_app_error(request: Request) -> None:
    raise ApplicationError(
        "The requested operation is invalid.",
        code="invalid_operation",
        status_code=422,
    )


def test_app_error_includes_structured_details_and_request_id(
    client: TestClient,
) -> None:
    request_id = "request-error-123"

    response = client.get("/test/app-error", headers={"X-Request-ID": request_id})

    assert response.status_code == 422
    assert response.json() == {
        "error": "invalid_operation",
        "message": "The requested operation is invalid.",
        "request_id": request_id,
    }
    assert response.headers["X-Request-ID"] == request_id
