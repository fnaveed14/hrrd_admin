import win32com.client

# === CONFIGURATION ===
db_path = r"C:\Users\fnaveed\Documents\IOM_Database.accdb"

# DAO engine (for database, tables, relationships)
dao = win32com.client.Dispatch("DAO.DBEngine.120")

# Create new database (delete file manually if re-running)
db = dao.CreateDatabase(db_path, ";LANGID=0x0409;CP=1252;COUNTRY=0")
print(f"Database created at {db_path}")

# === TABLE CREATION ===
tables_sql = [
    """CREATE TABLE Lookup_ProgrammeUnit (
        UnitID AUTOINCREMENT PRIMARY KEY,
        UnitName TEXT(100)
    )""",
    """CREATE TABLE Lookup_ServiceType (
        ServiceTypeID AUTOINCREMENT PRIMARY KEY,
        ServiceTypeName TEXT(100)
    )""",
    """CREATE TABLE Lookup_VehicleType (
        VehicleTypeID AUTOINCREMENT PRIMARY KEY,
        VehicleTypeName TEXT(100)
    )""",
    """CREATE TABLE Lookup_PaymentCategory (
        CategoryID AUTOINCREMENT PRIMARY KEY,
        CategoryName TEXT(100)
    )""",
    """CREATE TABLE Lookup_StaffPaymentType (
        StaffPaymentTypeID AUTOINCREMENT PRIMARY KEY,
        PaymentTypeName TEXT(100)
    )""",
    """CREATE TABLE Lookup_Status (
        StatusID AUTOINCREMENT PRIMARY KEY,
        StatusName TEXT(50)
    )""",
    """CREATE TABLE PR_Tracking (
        PR_ID AUTOINCREMENT PRIMARY KEY,
        Date_Request DATETIME,
        Staff_Name TEXT(150),
        ProgrammeUnit INT,
        ServiceType INT,
        Category INT,
        VehicleType INT,
        Notes MEMO
    )""",
    """CREATE TABLE Payment_Tracking (
        Payment_ID AUTOINCREMENT PRIMARY KEY,
        PR_ID INT,
        Date_Request DATETIME,
        Staff_Name TEXT(150),
        ProgrammeUnit INT,
        Category INT,
        Amount CURRENCY,
        Status INT
    )""",
    """CREATE TABLE StaffPayments (
        StaffPayment_ID AUTOINCREMENT PRIMARY KEY,
        Date_Request DATETIME,
        Staff_Name TEXT(150),
        ProgrammeUnit INT,
        Payment_Type INT,
        Amount CURRENCY,
        Status INT
    )"""
]

for sql in tables_sql:
    db.Execute(sql)

print("Tables created successfully!")

# === RELATIONSHIPS ===
relations = [
    ("PR_Tracking", "ProgrammeUnit", "Lookup_ProgrammeUnit", "UnitID"),
    ("PR_Tracking", "ServiceType", "Lookup_ServiceType", "ServiceTypeID"),
    ("PR_Tracking", "Category", "Lookup_PaymentCategory", "CategoryID"),
    ("PR_Tracking", "VehicleType", "Lookup_VehicleType", "VehicleTypeID"),
    ("Payment_Tracking", "PR_ID", "PR_Tracking", "PR_ID"),
    ("Payment_Tracking", "ProgrammeUnit", "Lookup_ProgrammeUnit", "UnitID"),
    ("Payment_Tracking", "Category", "Lookup_PaymentCategory", "CategoryID"),
    ("Payment_Tracking", "Status", "Lookup_Status", "StatusID"),
    ("StaffPayments", "ProgrammeUnit", "Lookup_ProgrammeUnit", "UnitID"),
    ("StaffPayments", "Payment_Type", "Lookup_StaffPaymentType", "StaffPaymentTypeID"),
    ("StaffPayments", "Status", "Lookup_Status", "StatusID")
]

for child, child_field, parent, parent_field in relations:
    rel = db.CreateRelation(f"FK_{child}_{child_field}", parent, child)
    fld = rel.CreateField(parent_field)   # parent key field
    fld.ForeignName = child_field         # child foreign key field
    rel.Fields.Append(fld)
    db.Relations.Append(rel)

print("Relationships created!")

# === POPULATE LOOKUP VALUES ===
lookup_values = {
    "Lookup_ProgrammeUnit": [
        "CRLR","HEALTH","PROTECTION","SNFI and WASH",
        "DTM","FCDO- BRAVE","MECC","Core Staff_ HRRD"
    ],
    "Lookup_ServiceType": ["Goods","Services","Works"],
    "Lookup_VehicleType": [
        "Sedan Car","Parado","Double Cabin Vigo/Hilux",
        "Armoured Vehicle","Equipped Ambulance",
        "HiAce","Bus","Coaster"
    ],
    "Lookup_PaymentCategory": [
        "Implementing Partners","Professional Services",
        "Medical","Private Sector Partners",
        "Event management","ICT","WSNFI","Miscellaneous"
    ],
    "Lookup_StaffPaymentType": ["DSA payment","Operational Advance"],
    "Lookup_Status": ["Pending","Cleared","Approved","Rejected"]
}

lookup_fields = {
    "Lookup_ProgrammeUnit": "UnitName",
    "Lookup_ServiceType": "ServiceTypeName",
    "Lookup_VehicleType": "VehicleTypeName",
    "Lookup_PaymentCategory": "CategoryName",
    "Lookup_StaffPaymentType": "PaymentTypeName",
    "Lookup_Status": "StatusName"
}

for table, values in lookup_values.items():
    field = lookup_fields[table]
    for v in values:
        db.Execute(f"INSERT INTO {table} ({field}) VALUES ('{v}')")

print("Lookup values inserted!")

# Finish
db.Close()
print("Database build complete ")
