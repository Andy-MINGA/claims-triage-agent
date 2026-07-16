import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

sample_policies = [
    {"policy_number": "POL-1001", "policyholder_name": "John Carter", "coverage_type": "Auto",
     "coverage_limit": 50000.00, "deductible": 500.00, "status": "active", "exclusions": "Racing, commercial use"},
    {"policy_number": "POL-1002", "policyholder_name": "Maria Chen", "coverage_type": "Home",
     "coverage_limit": 250000.00, "deductible": 1000.00, "status": "active", "exclusions": "Flood, earthquake"},
    {"policy_number": "POL-1003", "policyholder_name": "Robert Diaz", "coverage_type": "Auto",
     "coverage_limit": 30000.00, "deductible": 750.00, "status": "lapsed", "exclusions": "Racing, commercial use, DUI-related claims"},
    {"policy_number": "POL-1004", "policyholder_name": "Susan Lee", "coverage_type": "Home",
     "coverage_limit": 400000.00, "deductible": 2000.00, "status": "active", "exclusions": "Flood, wear and tear"},
    {"policy_number": "POL-1005", "policyholder_name": "David Kim", "coverage_type": "Auto",
     "coverage_limit": 100000.00, "deductible": 250.00, "status": "active", "exclusions": "Commercial use"},
]

for policy in sample_policies:
    doc_ref = db.collection("policies").document(policy["policy_number"])
    doc_ref.set(policy)
    print(f"Uploaded {policy['policy_number']}")

print("Firestore seeding complete.")