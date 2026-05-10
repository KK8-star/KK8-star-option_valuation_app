"""
Pytest shared fixtures for option valuation app tests.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.pool import StaticPool
from src.database.models import Base
from src.database.manager import DatabaseManager
from src.database.repository import CaseRepository, ParameterRepository, ResultRepository


@pytest.fixture(scope="function")
def test_db():
    """
    Provide a fresh in-memory DatabaseManager for each test.
    Uses StaticPool so all connections share the same in-memory DB.
    """
    manager = DatabaseManager()
    # Reset singleton state for test isolation
    manager._engine = None
    manager._SessionFactory = None
    manager.initialize("sqlite:///:memory:")
    yield manager
    # Cleanup
    if manager._engine is not None:
        Base.metadata.drop_all(manager._engine)
        manager._engine = None
        manager._SessionFactory = None


@pytest.fixture(scope="function")
def db_session(test_db):
    """Provide a database session within a transaction for each test."""
    with test_db.get_session() as session:
        yield session


@pytest.fixture(scope="function")
def case_repo(db_session):
    """Provide a CaseRepository backed by the test session."""
    return CaseRepository(db_session)


@pytest.fixture(scope="function")
def param_repo(db_session):
    """Provide a ParameterRepository backed by the test session."""
    return ParameterRepository(db_session)


@pytest.fixture(scope="function")
def result_repo(db_session):
    """Provide a ResultRepository backed by the test session."""
    return ResultRepository(db_session)


@pytest.fixture(scope="function")
def sample_case(case_repo):
    """Create and return a sample ValuationCase for testing."""
    return case_repo.create(
        name="Test Case",
        company_name="Test Corp",
        description="Created by pytest fixture",
    )


@pytest.fixture(scope="function")
def sample_params(param_repo, sample_case):
    """Create and return sample ValuationParameters for testing."""
    return param_repo.create(
        case_id=sample_case.id,
        stock_price=100.0,
        strike_price=100.0,
        risk_free_rate=0.05,
        volatility=0.20,
        time_to_expiry=1.0,
        dividend_yield=0.0,
        option_type="call",
        exercise_type="european",
    )
