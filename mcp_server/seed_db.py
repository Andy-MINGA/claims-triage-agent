import sqlite3

conn = sqlite3.connect("policies.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS policies (
    policy_number TEXT PRIMARY KEY,
    policyholder_name TEXT,
    coverage_type TEXT,
    coverage_limit REAL,
    deductible REAL,
    status TEXT,
    exclusions TEXT
)
""")

sample_policies = [
    ("POL-1001", "John Carter", "Auto", 50000.00, 500.00, "active", "Racing, commercial use"),
    ("POL-1002", "Maria Chen", "Home", 250000.00, 1000.00, "active", "Flood, earthquake"),
    ("POL-1003", "Robert Diaz", "Auto", 30000.00, 750.00, "lapsed", "Racing, commercial use, DUI-related claims"),
    ("POL-1004", "Susan Lee", "Home", 400000.00, 2000.00, "active", "Flood, wear and tear"),
    ("POL-1005", "David Kim", "Auto", 100000.00, 250.00, "active", "Commercial use"),
]

cursor.executemany(
    "INSERT OR REPLACE INTO policies VALUES (?, ?, ?, ?, ?, ?, ?)",
    sample_policies
)

conn.commit()
conn.close()
print("Database seeded successfully.")