"""
データベース層テスト - 現在のSQLAlchemyモデルに合わせて修正済み
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import Base, ValuationCase, ValuationParameter, ValuationResult


# ────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────

@pytest.fixture(scope="function")
def engine():
    """テストごとにインメモリDBを作成"""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine):
    """テストごとにセッションを作成"""
    with Session(engine) as sess:
        yield sess


@pytest.fixture
def sample_case(session) -> ValuationCase:
    """共通テスト用ケース"""
    case = ValuationCase(
        name="テストケース",
        company_name="テスト株式会社",
        description="単体テスト用サンプル",
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


@pytest.fixture
def sample_parameter(session, sample_case) -> ValuationParameter:
    """共通テスト用パラメータ"""
    param = ValuationParameter(
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
    session.add(param)
    session.commit()
    session.refresh(param)
    return param


# ────────────────────────────────────────────────
# ValuationCase テスト
# ────────────────────────────────────────────────

class TestValuationCase:

    def test_create_case(self, session):
        """ケースの作成と主キー自動採番"""
        case = ValuationCase(
            name="ケース1",
            company_name="会社A",
            description="テスト",
        )
        session.add(case)
        session.commit()

        assert case.id is not None
        assert case.id >= 1

    def test_required_name(self, session):
        """name カラムは必須"""
        from sqlalchemy.exc import IntegrityError
        session.add(ValuationCase(company_name="会社B"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_read_case(self, session, sample_case):
        """保存したケースを読み込めること"""
        loaded = session.get(ValuationCase, sample_case.id)
        assert loaded is not None
        assert loaded.name == "テストケース"
        assert loaded.company_name == "テスト株式会社"

    def test_update_case(self, session, sample_case):
        """ケースの更新"""
        sample_case.name = "更新後ケース"
        session.commit()

        reloaded = session.get(ValuationCase, sample_case.id)
        assert reloaded.name == "更新後ケース"

    def test_delete_case(self, session, sample_case):
        """ケースの削除"""
        case_id = sample_case.id
        session.delete(sample_case)
        session.commit()

        assert session.get(ValuationCase, case_id) is None

    def test_created_at_auto(self, session, sample_case):
        """created_at が自動セットされること"""
        assert isinstance(sample_case.created_at, datetime)

    def test_optional_fields_nullable(self, session):
        """company_name / description は省略可能"""
        case = ValuationCase(name="最小ケース")
        session.add(case)
        session.commit()
        session.refresh(case)

        assert case.company_name is None
        assert case.description is None


# ────────────────────────────────────────────────
# ValuationParameter テスト
# ────────────────────────────────────────────────

class TestValuationParameter:

    def test_create_parameter(self, session, sample_case):
        """パラメータ作成と外部キー"""
        param = ValuationParameter(
            case_id=sample_case.id,
            stock_price=110.0,
            strike_price=100.0,
            risk_free_rate=0.03,
            volatility=0.25,
            time_to_expiry=0.5,
            dividend_yield=0.02,
            option_type="put",
            exercise_type="american",
        )
        session.add(param)
        session.commit()

        assert param.id is not None
        assert param.case_id == sample_case.id

    def test_parameter_columns(self, session, sample_parameter):
        """全カラムが正しく保存されること"""
        p = session.get(ValuationParameter, sample_parameter.id)
        assert p.stock_price    == 100.0
        assert p.strike_price   == 100.0
        assert p.risk_free_rate == 0.05
        assert p.volatility     == 0.20
        assert p.time_to_expiry == 1.0
        assert p.dividend_yield == 0.0
        assert p.option_type    == "call"
        assert p.exercise_type  == "european"

    def test_default_values(self, session, sample_case):
        """dividend_yield / option_type / exercise_type のデフォルト値"""
        param = ValuationParameter(
            case_id=sample_case.id,
            stock_price=100.0,
            strike_price=100.0,
            risk_free_rate=0.05,
            volatility=0.20,
            time_to_expiry=1.0,
        )
        session.add(param)
        session.commit()
        session.refresh(param)

        assert param.dividend_yield == 0.0
        assert param.option_type    == "call"
        assert param.exercise_type  == "european"

    def test_cascade_delete(self, session, sample_case, sample_parameter):
        """ケース削除でパラメータも連鎖削除"""
        param_id = sample_parameter.id
        session.delete(sample_case)
        session.commit()

        assert session.get(ValuationParameter, param_id) is None

    def test_relationship_from_case(self, session, sample_case, sample_parameter):
        """リレーションシップ経由でパラメータにアクセス"""
        session.refresh(sample_case)
        assert len(sample_case.parameters) == 1
        assert sample_case.parameters[0].id == sample_parameter.id


# ────────────────────────────────────────────────
# ValuationResult テスト
# ────────────────────────────────────────────────

class TestValuationResult:

    def test_create_result(self, session, sample_case, sample_parameter):
        """結果レコードの作成"""
        result = ValuationResult(
            case_id=sample_case.id,
            parameter_id=sample_parameter.id,
            model_name="BlackScholes",
            option_price=10.45,
            delta=0.637,
            gamma=0.019,
            vega=37.52,
            theta=-6.41,
            rho=53.23,
        )
        session.add(result)
        session.commit()

        assert result.id is not None

    def test_result_columns(self, session, sample_case, sample_parameter):
        """全ギリシャ文字カラムが保存・読み込みできること"""
        result = ValuationResult(
            case_id=sample_case.id,
            parameter_id=sample_parameter.id,
            model_name="MonteCarlo",
            option_price=10.50,
            standard_error=0.05,
            confidence_interval_lower=10.40,
            confidence_interval_upper=10.60,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        assert result.model_name                  == "MonteCarlo"
        assert result.option_price                == 10.50
        assert result.standard_error              == 0.05
        assert result.confidence_interval_lower   == 10.40
        assert result.confidence_interval_upper   == 10.60

    def test_extra_data_json(self, session, sample_case):
        """extra_data に任意のJSONを保存できること"""
        result = ValuationResult(
            case_id=sample_case.id,
            model_name="Binomial",
            option_price=10.48,
            extra_data={"steps": 200, "tree_type": "CRR", "tags": ["test"]},
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        assert result.extra_data["steps"]     == 200
        assert result.extra_data["tree_type"] == "CRR"
        assert "test" in result.extra_data["tags"]

    def test_nullable_greeks(self, session, sample_case):
        """ギリシャ文字カラムはNULL許容"""
        result = ValuationResult(
            case_id=sample_case.id,
            model_name="Binomial",
            option_price=10.48,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        assert result.delta is None
        assert result.gamma is None
        assert result.vega  is None
        assert result.theta is None
        assert result.rho   is None

    def test_parameter_id_optional(self, session, sample_case):
        """parameter_id は省略可能（NULLable）"""
        result = ValuationResult(
            case_id=sample_case.id,
            model_name="BlackScholes",
            option_price=10.45,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        assert result.parameter_id is None

    def test_cascade_delete_result(self, session, sample_case, sample_parameter):
        """ケース削除で結果も連鎖削除"""
        result = ValuationResult(
            case_id=sample_case.id,
            parameter_id=sample_parameter.id,
            model_name="BlackScholes",
            option_price=10.45,
        )
        session.add(result)
        session.commit()
        result_id = result.id

        session.delete(sample_case)
        session.commit()

        assert session.get(ValuationResult, result_id) is None

    def test_multiple_models_same_case(self, session, sample_case):
        """同一ケースに複数モデルの結果を保存"""
        models = [
            ("BlackScholes", 10.45),
            ("Binomial",     10.48),
            ("MonteCarlo",   10.51),
        ]
        for name, price in models:
            session.add(ValuationResult(
                case_id=sample_case.id,
                model_name=name,
                option_price=price,
            ))
        session.commit()
        session.refresh(sample_case)

        assert len(sample_case.results) == 3
        stored_names = {r.model_name for r in sample_case.results}
        assert stored_names == {"BlackScholes", "Binomial", "MonteCarlo"}


# ────────────────────────────────────────────────
# 統合テスト
# ────────────────────────────────────────────────

class TestIntegration:

    def test_full_workflow(self, session):
        """ケース → パラメータ → 結果の一連フロー"""
        # 1. ケース作成
        case = ValuationCase(
            name="統合テストケース",
            company_name="統合テスト会社",
        )
        session.add(case)
        session.commit()
        session.refresh(case)

        # 2. パラメータ登録
        param = ValuationParameter(
            case_id=case.id,
            stock_price=150.0,
            strike_price=140.0,
            risk_free_rate=0.03,
            volatility=0.30,
            time_to_expiry=0.5,
        )
        session.add(param)
        session.commit()
        session.refresh(param)

        # 3. 3モデルの結果を登録
        for model_name, price in [("BlackScholes", 15.0), ("Binomial", 15.1), ("MonteCarlo", 14.9)]:
            session.add(ValuationResult(
                case_id=case.id,
                parameter_id=param.id,
                model_name=model_name,
                option_price=price,
                extra_data={"note": f"{model_name} result"},
            ))
        session.commit()
        session.refresh(case)

        # 検証
        assert len(case.parameters) == 1
        assert len(case.results)    == 3
        assert case.parameters[0].stock_price == 150.0

        prices = {r.model_name: r.option_price for r in case.results}
        assert prices["BlackScholes"] == 15.0
        assert prices["Binomial"]     == 15.1
        assert prices["MonteCarlo"]   == 14.9

    def test_query_by_model_name(self, session, sample_case):
        """モデル名でフィルタリングできること"""
        from sqlalchemy import select

        for model_name, price in [("BlackScholes", 10.4), ("Binomial", 10.5)]:
            session.add(ValuationResult(
                case_id=sample_case.id,
                model_name=model_name,
                option_price=price,
            ))
        session.commit()

        stmt = select(ValuationResult).where(
            ValuationResult.case_id    == sample_case.id,
            ValuationResult.model_name == "BlackScholes",
        )
        results = session.scalars(stmt).all()
        assert len(results) == 1
        assert results[0].option_price == 10.4
