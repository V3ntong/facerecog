import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=FaceRecognitionDB;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes",
    timeout=5
)
cursor = conn.cursor()

cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
tables = cursor.fetchall()
print("=== TABLES ===")
for t in tables:
    print(t[0])

for t in tables:
    tn = t[0]
    print(f"\n=== {tn} columns ===")
    cursor.execute(
        "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE "
        "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=? ORDER BY ORDINAL_POSITION",
        tn
    )
    for col in cursor.fetchall():
        print(f"  {col[0]}: {col[1]}({col[2]}) nullable={col[3]}")
    cursor.execute(f"SELECT COUNT(*) FROM [{tn}]")
    count = cursor.fetchone()[0]
    print(f"  >> {count} rows")

# Check for FileTables
cursor.execute(
    "SELECT name FROM sys.tables WHERE is_filetable=1"
)
ft = cursor.fetchall()
if ft:
    print("\n=== FILETABLES ===")
    for f in ft:
        print(f"  {f[0]}")

# Check schemas
cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA")
schemas = [s[0] for s in cursor.fetchall()]
print(f"\n=== SCHEMAS: {schemas} ===")

conn.close()
print("Done.")
