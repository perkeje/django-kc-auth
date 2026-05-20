import pytest


@pytest.fixture
def user_info():
    return {
        "sub": "550e8400-e29b-41d4-a716-446655440000",
        "username": "testuser",
        "email": "testuser@example.com",
        "firstName": "Test",
        "lastName": "User",
        "resource_access": {
            "test-client": {
                "roles": [],
            }
        },
    }


@pytest.fixture
def kc_tokens():
    return {
        "access_token": "fake-access-token",
        "id_token": "fake-id-token",
        "session_state": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    }
