from src.data.models import ValuationParameter, ValuationCase, ValuationResult
print("=== ValuationCase columns ===")
for c in ValuationCase.__table__.columns:
    print(f"  {c.name}: {c.type}")
print()
print("=== ValuationParameter columns ===")
for c in ValuationParameter.__table__.columns:
    print(f"  {c.name}: {c.type}")
print()
print("=== ValuationResult columns ===")
for c in ValuationResult.__table__.columns:
    print(f"  {c.name}: {c.type}")
