# ==============================
# Part 1: Setup, DB, Login & Navigation
# ==============================

import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import time
from datetime import datetime

# --- PAGE CONFIG (must be first Streamlit command) ---
st.set_page_config(
    page_title="PR & Payment Tracker",
    page_icon="📊",
    layout="wide"
)

from streamlit_cookies_manager import EncryptedCookieManager

# --- DB connection ---
conn = sqlite3.connect("pr_system.db", check_same_thread=False)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")   # ✅ enforce FKs

# --- Create tables ---
c.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Admin'
)""")

c.execute("""CREATE TABLE IF NOT EXISTS pr_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_number TEXT NOT NULL,   -- ✅ not unique anymore
    date_request TEXT,
    staff_name TEXT,
    programme_unit TEXT,
    type_services TEXT,
    category TEXT,
    description TEXT,
    type_vehicle TEXT,
    traveller_name TEXT,
    traveller_phone TEXT,
    from_date TEXT,
    to_date TEXT,
    days INTEGER,
    location TEXT,
    qty INTEGER,
    est_cost_pkr REAL,
    est_cost_usd REAL,
    reminder_expiry TEXT,
    reminder_days INTEGER,
    comments TEXT,
    status TEXT DEFAULT 'Submitted',
    created_at TEXT,
    assigned_to TEXT
)""")

# --- WBL allocations now store free-text project/task names ---
c.execute("""CREATE TABLE IF NOT EXISTS pr_wbls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_id INTEGER NOT NULL,             -- ✅ foreign key to PR ID
    project_name TEXT NOT NULL,
    task_name TEXT NOT NULL,
    percentage INTEGER NOT NULL,
    FOREIGN KEY (pr_id) REFERENCES pr_tracking (id) ON DELETE CASCADE
)""")

c.execute("""CREATE TABLE IF NOT EXISTS payment_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_id INTEGER,                      -- ✅ link to PR by ID
    pr_number TEXT,                     -- keep original PR number for reference
    category TEXT,
    po_number TEXT,
    invoice_number TEXT,
    wave_receipt TEXT,
    work_confirmation TEXT,             -- ✅ NEW field (Yes/No)
    work_order_yesno TEXT,
    work_order_number TEXT,
    actual_usd REAL,
    actual_pkr REAL,
    payment_date TEXT,
    remarks TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pr_id) REFERENCES pr_tracking (id) ON DELETE CASCADE
)""")


c.execute("""CREATE TABLE IF NOT EXISTS dsa_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_request TEXT,
    staff_name TEXT,
    programme_unit TEXT,
    type_services TEXT,
    dsa_type TEXT,
    vendor_name TEXT,
    description TEXT,
    location TEXT,
    start_date TEXT,
    end_date TEXT,
    days REAL,
    amount_pkr REAL,
    ist_number TEXT,
    comments TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")



c.execute("""CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT,
    record_id TEXT,
    old_status TEXT,
    new_status TEXT,
    changed_by TEXT,
    changed_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

# --- Operational Advances Table ---
c.execute("""CREATE TABLE IF NOT EXISTS operational_advances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_request TEXT,
    staff_name TEXT,
    programme_unit TEXT,
    supplier_name TEXT,
    description TEXT,
    invoice_type TEXT,
    invoice_no TEXT,
    total_amount REAL,
    invoice_currency TEXT,
    payment_currency TEXT,
    location TEXT,
    comments TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

# --- Operational Advance Liquidations Table ---
c.execute("""CREATE TABLE IF NOT EXISTS operational_liquidations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    oa_id INTEGER,  -- ✅ must reference a valid OA record
    date_request TEXT,
    staff_name TEXT,
    programme_unit TEXT,
    category TEXT,
    supplier_name TEXT,
    description TEXT,
    invoice_type TEXT,
    invoice_no TEXT,
    total_amount REAL,
    invoice_currency TEXT,
    payment_currency TEXT,
    liquidation_ist TEXT,
    liquidation_amount REAL,
    wbl_project_code TEXT,
    wbl_task_number TEXT,
    unspent_amount REAL,
    unspent_deposit_yesno TEXT,
    deposited_amount REAL,
    unspent_ist1 TEXT,
    unspent_ist2 TEXT,
    unspent_wbl_project_code TEXT,
    unspent_wbl_task_number TEXT,
    documents_submitted TEXT,
    location TEXT,
    comments TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (oa_id) REFERENCES operational_advances (id) ON DELETE CASCADE
)""")
conn.commit()


conn.commit()

# --- Helper: Password Hashing ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# --- Create default admin if none exists ---
if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    default_pwd = hash_password("admin")
    c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", 
              ("admin", default_pwd, "Admin"))
    conn.commit()

# --- Cookie Manager ---
cookies = EncryptedCookieManager(prefix="pr_app", password="super-secret-key")
if not cookies.ready():
    st.stop()

# --- Restore session from cookies ---
if "user" not in st.session_state:
    st.session_state["user"] = cookies.get("user")
if "role" not in st.session_state:
    st.session_state["role"] = cookies.get("role")
if "last_active" not in st.session_state:
    st.session_state["last_active"] = None

# --- Session timeout (optional) ---
SESSION_TIMEOUT = 60 * 30  # 30 minutes
if st.session_state["user"]:
    now = time.time()
    if st.session_state["last_active"] and (now - st.session_state["last_active"] > SESSION_TIMEOUT):
        st.warning("⏰ Session expired, please log in again.")
        st.session_state["user"] = None
        st.session_state["role"] = None
        cookies["user"] = ""
        cookies["role"] = ""
        cookies.save()
    else:
        st.session_state["last_active"] = now

# --- Login Page ---
if st.session_state["user"] is None:
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and verify_password(password, user[2]):
            st.session_state["user"] = user[1]
            st.session_state["role"] = user[3]
            st.session_state["last_active"] = time.time()

            # ✅ Save login in cookies
            cookies["user"] = user[1]
            cookies["role"] = user[3]
            cookies.save()

            st.success(f"Welcome {user[1]}! Role: {user[3]}")
            st.rerun()
        else:
            st.error("Invalid username or password")

    st.info("Default login → Username: admin | Password: admin")
    st.stop()  # stop execution if not logged in

# --- Sidebar ---
st.sidebar.title(f"👋 Welcome, {st.session_state['user']} ({st.session_state['role']})")
if st.sidebar.button("🚪 Logout"):
    st.session_state["user"] = None
    st.session_state["role"] = None
    st.session_state["last_active"] = None

    cookies["user"] = ""
    cookies["role"] = ""
    cookies.save()
    st.rerun()

page = st.sidebar.radio("📂 Navigation", [
    "Dashboard",
    "PR Tracking",
    "Payment Tracking",
    "Operational Advance Liquidation",   # 🆕 new option
    "User Management",
    "Reports"
])


# ==============================
# Part 2: Dashboard
# ==============================

if page == "Dashboard":
    st.title("📊 Main Dashboard")

    # --- Filters ---
    st.subheader("🔍 Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        all_prs = pd.read_sql("SELECT DISTINCT pr_number FROM pr_tracking", conn)
        pr_filter = st.selectbox(
            "Filter by PR Number",
            ["All"] + all_prs["pr_number"].dropna().tolist() if not all_prs.empty else ["All"]
        )
    with col2:
        all_categories = pd.read_sql("SELECT DISTINCT category FROM pr_tracking", conn)
        cat_filter = st.selectbox(
            "Filter by Category",
            ["All"] + all_categories["category"].dropna().tolist() if not all_categories.empty else ["All"]
        )
    with col3:
        all_staff = pd.read_sql("SELECT DISTINCT staff_name FROM pr_tracking", conn)
        staff_filter = st.selectbox(
            "Filter by Staff/User",
            ["All"] + all_staff["staff_name"].dropna().tolist() if not all_staff.empty else ["All"]
        )

    # --- Apply filters ---
    query = "SELECT * FROM pr_tracking WHERE 1=1"
    params = []
    if pr_filter != "All":
        query += " AND pr_number=?"
        params.append(pr_filter)
    if cat_filter != "All":
        query += " AND category=?"
        params.append(cat_filter)
    if staff_filter != "All":
        query += " AND staff_name=?"
        params.append(staff_filter)

    prs = pd.read_sql(query, conn, params=params)

    # --- Metrics ---
    st.markdown("### 📈 Key Metrics")
    total = prs.shape[0]
    submitted = prs[prs["status"] == "Submitted"].shape[0]
    in_process = prs[prs["status"] == "In Process"].shape[0]
    completed = prs[prs["status"] == "Completed"].shape[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 Total PRs", total)
    col2.metric("🕒 Submitted", submitted)
    col3.metric("⚙️ In Process", in_process)
    col4.metric("✅ Completed", completed)

    # --- PR Table ---
    st.subheader("📑 Purchase Requests")
    if prs.empty:
        st.info("No PRs available.")
    else:
        st.dataframe(prs, use_container_width=True, height=400)

        col1, col2 = st.columns(2)
        with col1:
            update_pr = st.selectbox("Select PR (by ID) to update status", prs["id"])
            new_status = st.selectbox("New Status", ["Submitted", "In Process", "Completed"])
            if st.button("🔄 Update PR Status"):
                old_status = c.execute("SELECT status FROM pr_tracking WHERE id=?", (update_pr,)).fetchone()[0]
                c.execute("UPDATE pr_tracking SET status=? WHERE id=?", (new_status, update_pr))
                c.execute("""INSERT INTO status_history 
                             (record_type, record_id, old_status, new_status, changed_by) 
                             VALUES (?,?,?,?,?)""",
                          ("PR", str(update_pr), old_status, new_status, st.session_state["user"]))
                conn.commit()
                st.success(f"PR ID {update_pr} updated to {new_status}")
                st.rerun()

        with col2:
            delete_pr = st.selectbox("Select PR (by ID) to delete", prs["id"])
            if st.button("🗑️ Delete PR"):
                c.execute("DELETE FROM pr_tracking WHERE id=?", (delete_pr,))
                conn.commit()
                st.success(f"PR ID {delete_pr} deleted")
                st.rerun()

    # --- Payment Records ---
    st.subheader("💰 Payment Records")
    payments = pd.read_sql("SELECT * FROM payment_tracking", conn)
    if payments.empty:
        st.info("No payments yet.")
    else:
        st.dataframe(payments, use_container_width=True, height=400)

        col1, col2 = st.columns(2)
        with col1:
            update_pay = st.selectbox("Select Payment ID to update status", payments["id"])
            new_status = st.selectbox("New Status (Payment)", ["Pending", "In Process", "Completed"])
            if st.button("🔄 Update Payment Status"):
                old_status = c.execute("SELECT status FROM payment_tracking WHERE id=?", (update_pay,)).fetchone()[0]
                c.execute("UPDATE payment_tracking SET status=? WHERE id=?", (new_status, update_pay))
                c.execute("""INSERT INTO status_history 
                             (record_type, record_id, old_status, new_status, changed_by) 
                             VALUES (?,?,?,?,?)""",
                          ("Payment", str(update_pay), old_status, new_status, st.session_state["user"]))
                conn.commit()

                # --- Cascade update: if payment completed, mark PR completed too
                if new_status == "Completed":
                    pr_id = c.execute("SELECT pr_id FROM payment_tracking WHERE id=?", (update_pay,)).fetchone()[0]
                    if pr_id:
                        old_pr_status = c.execute("SELECT status FROM pr_tracking WHERE id=?", (pr_id,)).fetchone()[0]
                        c.execute("UPDATE pr_tracking SET status='Completed' WHERE id=?", (pr_id,))
                        c.execute("""INSERT INTO status_history 
                                     (record_type, record_id, old_status, new_status, changed_by) 
                                     VALUES (?,?,?,?,?)""",
                                  ("PR", str(pr_id), old_pr_status, "Completed", st.session_state["user"]))
                        conn.commit()
                        st.info(f"Linked PR ID {pr_id} also marked Completed ✅")

                st.success(f"Payment {update_pay} updated to {new_status}")
                st.rerun()

        with col2:
            delpay = st.selectbox("Select Payment ID to delete", payments["id"])
            if st.button("🗑️ Delete Payment"):
                c.execute("DELETE FROM payment_tracking WHERE id=?", (delpay,))
                conn.commit()
                st.success(f"Payment {delpay} deleted ✅")
                st.rerun()

    # --- DSA Payments ---
    st.subheader("✈️ DSA Payments")
    dsas = pd.read_sql("SELECT * FROM dsa_payments", conn)
    if dsas.empty:
        st.info("No DSA payments yet.")
    else:
        st.dataframe(dsas, use_container_width=True, height=400)

        col1, col2 = st.columns(2)
        with col1:
            update_dsa = st.selectbox("Select DSA ID to update status", dsas["id"])
            new_status = st.selectbox("New Status (DSA)", ["Pending", "In Process", "Completed", "Paid"])
            if st.button("🔄 Update DSA Status"):
                old_status = c.execute("SELECT status FROM dsa_payments WHERE id=?", (update_dsa,)).fetchone()[0]
                c.execute("UPDATE dsa_payments SET status=? WHERE id=?", (new_status, update_dsa))
                c.execute("""INSERT INTO status_history 
                             (record_type, record_id, old_status, new_status, changed_by) 
                             VALUES (?,?,?,?,?)""",
                          ("DSA", str(update_dsa), old_status, new_status, st.session_state["user"]))
                conn.commit()
                st.success(f"DSA Payment {update_dsa} updated to {new_status}")
                st.rerun()

        with col2:
            deldsa = st.selectbox("Select DSA ID to delete", dsas["id"])
            if st.button("🗑️ Delete DSA Payment"):
                c.execute("DELETE FROM dsa_payments WHERE id=?", (deldsa,))
                conn.commit()
                st.success(f"DSA Payment {deldsa} deleted ✅")
                st.rerun()

        # --- Operational Advances + Liquidations ---
    st.subheader("💼 Operational Advances & Liquidations")

    # Merge OA + Liquidation info
    oa_query = """
    SELECT 
        oa.id AS id,
        oa.date_request AS date_request,
        oa.staff_name AS staff_name,
        oa.programme_unit AS programme_unit,
        oa.supplier_name AS supplier_name,
        oa.total_amount AS total_amount,
        oa.status AS oa_status,
        li.id AS liquidation_id,
        li.status AS liquidation_status,
        li.liquidation_amount AS liquidation_amount,
        li.date_request AS liquidation_date
    FROM operational_advances oa
    LEFT JOIN operational_liquidations li ON oa.id = li.oa_id
    ORDER BY oa.id DESC
    """
    oas = pd.read_sql(oa_query, conn)

    if oas.empty:
        st.info("No operational advances or liquidations yet.")
    else:
        # Show table with both OA and liquidation info
        display_df = oas.copy()
        display_df.rename(columns={
            "id": "OA ID",
            "date_request": "OA Date",
            "staff_name": "Staff",
            "programme_unit": "Programme Unit",
            "supplier_name": "Supplier",
            "total_amount": "Total Amount",
            "oa_status": "OA Status",
            "liquidation_id": "Liquidation ID",
            "liquidation_status": "Liquidation Status",
            "liquidation_amount": "Liquidation Amount",
            "liquidation_date": "Liquidation Date"
        }, inplace=True)

        st.dataframe(display_df, use_container_width=True, height=400)

        col1, col2 = st.columns(2)

        # --- Update OA Status ---
        with col1:
            st.markdown("### 🔄 Update OA Status")
            update_oa = st.selectbox("Select OA ID to update status", oas["id"])
            new_status = st.selectbox("New OA Status", ["Pending", "In Process", "Completed", "Paid"])
            if st.button("💾 Update OA Status"):
                old_status = c.execute("SELECT status FROM operational_advances WHERE id=?", (update_oa,)).fetchone()[0]
                c.execute("UPDATE operational_advances SET status=? WHERE id=?", (new_status, update_oa))
                c.execute("""INSERT INTO status_history 
                            (record_type, record_id, old_status, new_status, changed_by)
                            VALUES (?,?,?,?,?)""",
                        ("OA", str(update_oa), old_status, new_status, st.session_state["user"]))
                conn.commit()
                st.success(f"✅ Operational Advance {update_oa} updated to {new_status}")
                st.rerun()

        # --- Update Liquidation Status ---
        with col2:
            st.markdown("### 🧾 Update Liquidation Status")
            # Filter to OAs that have a liquidation record
            li_opts = oas.dropna(subset=["liquidation_id"])
            if li_opts.empty:
                st.info("No liquidation records found yet.")
            else:
                selected_liq = st.selectbox(
                    "Select Liquidation Record (OA ID | Supplier)",
                    li_opts.apply(lambda r: f"{r['id']} | {r['supplier_name']}", axis=1)
                )

                selected_oa_id = int(selected_liq.split(" | ")[0])
                old_liq_status = c.execute(
                    "SELECT status FROM operational_liquidations WHERE oa_id=?",
                    (selected_oa_id,)
                ).fetchone()

                new_liq_status = st.selectbox("New Liquidation Status", ["Pending", "In Process", "Completed", "Paid"])

                if st.button("💾 Update Liquidation Status"):
                    try:
                        # Update liquidation record
                        c.execute("UPDATE operational_liquidations SET status=? WHERE oa_id=?", (new_liq_status, selected_oa_id))
                        # Cascade update OA
                        c.execute("UPDATE operational_advances SET status=? WHERE id=?", (new_liq_status, selected_oa_id))
                        # Log both changes
                        c.execute("""INSERT INTO status_history
                                    (record_type, record_id, old_status, new_status, changed_by)
                                    VALUES (?,?,?,?,?)""",
                                ("Liquidation", str(selected_oa_id), old_liq_status[0] if old_liq_status else None, new_liq_status, st.session_state["user"]))
                        c.execute("""INSERT INTO status_history
                                    (record_type, record_id, old_status, new_status, changed_by)
                                    VALUES (?,?,?,?,?)""",
                                ("OA", str(selected_oa_id), old_liq_status[0] if old_liq_status else None, new_liq_status, st.session_state["user"]))
                        conn.commit()
                        st.success(f"✅ Liquidation status updated to {new_liq_status} for OA ID {selected_oa_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating liquidation: {e}")


    # --- Reminders ---

    st.subheader("⏰ PR Reminders")
    reminders = pd.read_sql("""
        SELECT id, pr_number, staff_name, category, from_date, reminder_days
        FROM pr_tracking
        WHERE reminder_expiry='Yes'
    """, conn)

    if reminders.empty:
        st.success("✅ No reminders due.")
    else:
        reminders["from_date"] = pd.to_datetime(reminders["from_date"], errors="coerce")
        reminders["reminder_days"] = pd.to_numeric(reminders["reminder_days"], errors="coerce")

        reminders["Reminder Date"] = reminders.apply(
            lambda r: (r["from_date"] - pd.to_timedelta(int(r["reminder_days"]), unit="D")).date()
            if pd.notnull(r["from_date"]) and pd.notnull(r["reminder_days"]) else pd.NaT,
            axis=1
        )

        today = datetime.today().date()
        def status_label(d):
            if pd.isna(d):
                return "—"
            if d < today:
                return "⏰ Overdue"
            if d == today:
                return "⚠️ Due Today"
            return "📌 Upcoming"

        reminders["Status"] = reminders["Reminder Date"].apply(status_label)

        view_cols = ["id","pr_number","staff_name","category","from_date","reminder_days","Reminder Date","Status"]
        st.dataframe(reminders[view_cols].rename(columns={
            "id": "PR ID",
            "pr_number": "PR Number",
            "staff_name": "Staff",
            "category": "Category",
            "from_date": "From Date",
            "reminder_days": "Days Before"
        }), use_container_width=True, height=300)

# ==============================
# Part 3: PR Tracking (Multi-Line, Shared WBL, Validation)
# ==============================

elif page == "PR Tracking":
    st.title("📝 New Purchase Request")

    # --- PR Header ---
    st.subheader("➕ Create PR Header")

    col1, col2 = st.columns(2)
    with col1:
        pr_number = st.text_input("PR Number *")
        date_request = st.date_input("Date of Request *")
        staff_name = st.text_input("Created By *", value=st.session_state["user"])
        programme_unit = st.selectbox(
            "Programme Unit *",
            ["", "CRLR", "HEALTH", "PROTECTION", "SNFI and WASH", "DTM", "FCDO- BRAVE", "MECC", "Core Staff_ HRRD"],
            index=0
        )
        type_services = st.selectbox("Type of Services *", ["", "Goods", "Services", "Works"], index=0)
        category = st.selectbox("Category *", [
            "", "Implementing Partners", "Professional Services", "Medical",
            "Private Sector Partners", "Event management", "ICT", "WSNFI",
            "Miscellaneous", "Rental Vehicle"
        ], index=0)
    with col2:
        description = st.text_area("Description (Optional)")
        assigned_users = pd.read_sql("SELECT username FROM users", conn)
        assigned_to = st.selectbox(
            "Assign To *",
            assigned_users["username"].tolist() if not assigned_users.empty else ["admin"],
            index=0
        )

    # --- Rental Vehicle Fields ---
    type_vehicle = traveller_name = traveller_phone = None
    if category == "Rental Vehicle":
        st.markdown("### 🚗 Rental Vehicle Details")
        col1, col2 = st.columns(2)
        with col1:
            type_vehicle = st.selectbox("Type of Vehicle *", [
                "", "Sedan Car", "Parado", "Double Cabin Vigo/Hilux",
                "Armoured Vehicle", "Equipped Ambulance", "HiAce", "Bus", "Coaster"
            ], index=0)
            traveller_name = st.text_input("Traveller Name (Optional)")
        with col2:
            traveller_phone = st.text_input("Traveller Phone # (Optional)")

    # --- Multi-Line Support ---
    st.markdown("### 🧾 Multi-Line Entry")
    num_lines = st.number_input("Number of PR Lines", min_value=1, max_value=10, value=1)

    # --- Shared WBL Option ---
    st.markdown("### 📂 WBL Allocation Options")
    same_wbl_for_all = st.checkbox("✅ Use the same WBL allocation for all PR lines")

    shared_wbls = []
    if same_wbl_for_all:
        st.info("You selected: Same WBL(s) for all lines.")
        num_shared_wbls = st.number_input("Number of WBL allocations (shared)", min_value=1, max_value=5, value=1, key="shared_num_wbls")
        for j in range(num_shared_wbls):
            st.markdown(f"**Shared WBL #{j+1}**")
            col1, col2, col3 = st.columns(3)
            with col1:
                proj = st.text_input(f"Project Name (Shared WBL {j+1}) *", key=f"shared_proj_{j}")
            with col2:
                task = st.text_input(f"Task Name (Shared WBL {j+1}) *", key=f"shared_task_{j}")
            with col3:
                perc = st.number_input(f"Percentage (Shared WBL {j+1}) *",
                                        min_value=0, max_value=100,
                                        value=100 if j == 0 else 0, key=f"shared_perc_{j}")
            if proj.strip() and task.strip():
                shared_wbls.append((proj.strip(), task.strip(), perc))

    pr_lines = []

    # --- PR Lines Loop ---
    for i in range(int(num_lines)):
        st.markdown(f"---\n### 🧩 PR Line #{i+1}")

        # --- Dates & Duration ---
        st.markdown("#### 📅 Travel/Request Duration")
        col1, col2, col3 = st.columns(3)
        with col1:
            from_date = st.date_input(f"From (Line {i+1}) *", key=f"from_{i}")
        with col2:
            to_date = st.date_input(f"To (Line {i+1}) *", key=f"to_{i}")
        with col3:
            days = max((to_date - from_date).days + 1, 0) if from_date and to_date else 0
            st.metric(f"Calculated Days (Line {i+1})", days)

        # --- Costs & Location ---
        st.markdown("#### 💵 Cost & Location")
        col1, col2 = st.columns(2)
        with col1:
            location = st.text_input(f"Location (Line {i+1}) *", key=f"loc_{i}")
            qty = st.number_input(f"Quantity (Line {i+1}) *", min_value=1, key=f"qty_{i}")
            est_pkr = st.number_input(f"Estimated Cost (PKR) (Line {i+1}) *", min_value=1.0, key=f"pkr_{i}")
        with col2:
            est_usd = st.number_input(f"Estimated Cost (USD) (Line {i+1}) (optional) ", key=f"usd_{i}")
            comments = st.text_area(f"Comments (Line {i+1}) (Optional)", key=f"comm_{i}")

        # --- Reminder ---
        st.markdown("#### ⏰ Reminder")
        reminder_expiry = st.radio(f"Set reminder before start date? (Line {i+1}) *", ["Yes", "No"], key=f"rem_{i}")
        reminder_days = None
        if reminder_expiry == "Yes":
            reminder_days = st.number_input(
                f"Remind me this many days before From date (Line {i+1}) *", min_value=1, key=f"remd_{i}"
            )

        # --- WBL Allocation ---
        if not same_wbl_for_all:
            st.markdown("#### 📂 WBL Allocation (Individual)")
            wbls = []
            num_wbls = st.number_input(f"Number of WBL allocations (Line {i+1})", min_value=1, max_value=5, value=1, key=f"numwbl_{i}")
            for j in range(num_wbls):
                st.markdown(f"**WBL #{j+1} (Line {i+1})**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    proj_name = st.text_input(f"Project Name (Line {i+1} WBL {j+1}) *", key=f"proj_{i}_{j}")
                with col2:
                    task_name = st.text_input(f"Task Name (Line {i+1} WBL {j+1}) *", key=f"task_{i}_{j}")
                with col3:
                    perc = st.number_input(f"Percentage (Line {i+1} WBL {j+1}) *",
                                            min_value=0, max_value=100,
                                            value=100 if j == 0 else 0,
                                            key=f"perc_{i}_{j}")
                if proj_name.strip() and task_name.strip():
                    wbls.append((proj_name.strip(), task_name.strip(), perc))
        else:
            wbls = shared_wbls

        pr_lines.append({
            "from_date": from_date,
            "to_date": to_date,
            "days": days,
            "location": location,
            "qty": qty,
            "est_pkr": est_pkr,
            "est_usd": est_usd,
            "comments": comments,
            "reminder_expiry": reminder_expiry,
            "reminder_days": reminder_days,
            "wbls": wbls
        })

    # --- Submit PR ---
    if st.button("✅ Submit PR"):
        missing_fields = []
        if not pr_number.strip():
            missing_fields.append("PR Number")
        if programme_unit == "":
            missing_fields.append("Programme Unit")
        if type_services == "":
            missing_fields.append("Type of Services")
        if category == "":
            missing_fields.append("Category")
        if category == "Rental Vehicle" and type_vehicle == "":
            missing_fields.append("Type of Vehicle")
        if not assigned_to.strip():
            missing_fields.append("Assigned To")

        if missing_fields:
            st.error("⚠️ Missing required fields: " + ", ".join(missing_fields))
        elif same_wbl_for_all and sum([p for _, _, p in shared_wbls if p]) != 100:
            st.error("⚠️ Shared WBL percentages must add up to 100!")
        else:
            try:
                for idx, line in enumerate(pr_lines, start=1):
                    # Validate per-line required fields
                    if not line["location"].strip() or not line["from_date"] or not line["to_date"]:
                        st.error(f"⚠️ Missing required fields in PR Line #{idx}")
                        st.stop()

                    c.execute("""INSERT INTO pr_tracking (
                        pr_number, date_request, staff_name, programme_unit, type_services, category,
                        description, type_vehicle, traveller_name, traveller_phone,
                        from_date, to_date, days, location, qty,
                        est_cost_pkr, est_cost_usd, reminder_expiry, reminder_days,
                        comments, status, created_at, assigned_to
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        pr_number, str(date_request), staff_name, programme_unit, type_services, category,
                        description, type_vehicle, traveller_name, traveller_phone,
                        str(line["from_date"]), str(line["to_date"]), line["days"], line["location"], line["qty"],
                        line["est_pkr"], line["est_usd"], line["reminder_expiry"], line["reminder_days"],
                        line["comments"], "Submitted", datetime.now(), assigned_to
                    ))
                    pr_id = c.lastrowid

                    # --- Insert WBLs ---
                    for proj_name, task_name, perc in line["wbls"]:
                        c.execute("INSERT INTO pr_wbls (pr_id, project_name, task_name, percentage) VALUES (?,?,?,?)",
                                  (pr_id, proj_name, task_name, perc))

                    # --- Log creation ---
                    c.execute("""INSERT INTO status_history 
                                 (record_type, record_id, old_status, new_status, changed_by) 
                                 VALUES (?,?,?,?,?)""",
                              ("PR", pr_id, None, "Submitted", st.session_state["user"]))

                conn.commit()
                st.success(f"✅ {num_lines} PR line(s) saved under PR {pr_number}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # --- View PRs with WBL Preview ---
    st.subheader("📋 My PRs")
    if st.session_state["role"] == "Admin":
        prs = pd.read_sql("SELECT * FROM pr_tracking", conn)
    else:
        prs = pd.read_sql(
            "SELECT * FROM pr_tracking WHERE staff_name=? OR assigned_to=?",
            conn, params=[st.session_state["user"], st.session_state["user"]]
        )

    if not prs.empty:
        st.dataframe(prs, use_container_width=True, height=400)

        st.markdown("### 📂 WBL Preview")
        selected_pr = st.selectbox("Select a PR to view WBLs", prs["id"])
        wbls = pd.read_sql("""
            SELECT project_name, task_name, percentage
            FROM pr_wbls
            WHERE pr_id=?
        """, conn, params=[selected_pr])
        if wbls.empty:
            st.info("No WBLs found for this PR.")
        else:
            st.dataframe(
                wbls.rename(columns={
                    "project_name": "Project",
                    "task_name": "Task",
                    "percentage": "Percentage"
                }),
                use_container_width=True, height=300
            )

# ==============================
# Part 4: Payment Tracking
# ==============================

elif page == "Payment Tracking":
    st.title("💰 Payment Tracking")

    category_choice = st.selectbox("Select Payment Category", [
        "Rental Vehicle","Implementing Partners","Professional Services","Medical",
        "Private Sector Partners","Event management","ICT","WSNFI","Miscellaneous",
        "DSA Payment","Operational Advance"
    ])

    # --- Case 1: Categories linked to PRs ---
    if category_choice in [
        "Rental Vehicle","Implementing Partners","Professional Services","Medical",
        "Private Sector Partners","Event management","ICT","WSNFI","Miscellaneous"
    ]:
        prs = pd.read_sql("SELECT * FROM pr_tracking WHERE category=?", conn, params=[category_choice])
        if prs.empty:
            st.warning("⚠️ No PRs available for this category.")
        else:
            pr_number_choice = st.selectbox("Select PR Number", prs["pr_number"].unique().tolist())
            pr_subset = prs[prs["pr_number"] == pr_number_choice]

            pr_options = {
                row["id"]: f"ID {row['id']} | {row['pr_number']} | {row['description']} | {row['staff_name']}"
                for _, row in pr_subset.iterrows()
            }

            pr_id_choice = st.selectbox(
                "Select PR Line",
                options=list(pr_options.keys()),
                format_func=lambda x: pr_options[x]
            )

            pr_data = pr_subset[pr_subset["id"] == pr_id_choice].iloc[0]

            st.markdown("### 📝 Purchase Request Details")
            st.markdown(f"""
            <div style="background:#f9f9f9; padding:10px; border-radius:8px;">
                <b>PR Number:</b> {pr_data['pr_number']}<br>
                <b>ID:</b> {pr_data['id']}<br>
                <b>Date of Request:</b> {pr_data['date_request']}<br>
                <b>Created By:</b> {pr_data['staff_name']}<br>
                <b>Programme Unit:</b> {pr_data['programme_unit']}<br>
                <b>Type of Services:</b> {pr_data['type_services']}<br>
                <b>Category:</b> {pr_data['category']}<br>
                <b>Location:</b> {pr_data['location']}<br>
                <b>Quantity:</b> {pr_data['qty']}<br>
                <b>Estimated Cost (PKR):</b> {pr_data['est_cost_pkr']}<br>
                <b>Estimated Cost (USD):</b> {pr_data['est_cost_usd']}<br>
                <b>Status:</b> {pr_data['status']}
            </div>
            """, unsafe_allow_html=True)

            # --- Payment Details ---
            st.markdown("### 💳 Payment Details")
            po_number = st.text_input("PO Number")
            invoice_number = st.text_input("Invoice Number")
            wave_receipt = st.text_input("Wave Receipt Number")
            work_confirmation = st.selectbox("Work Confirmation", ["No", "Yes"])

            work_order_yesno, work_order_number = None, None
            if category_choice != "Rental Vehicle":
                work_order_yesno = st.selectbox("Work Order in system?", ["No","Yes"])
                if work_order_yesno == "Yes":
                    work_order_number = st.text_input("Work Order Receipt #")

            col1, col2 = st.columns(2)
            with col1:
                actual_usd = st.number_input("Actual Amount (USD) (optional)",)
                payment_date = st.date_input("Payment Submitted Date")
            with col2:
                actual_pkr = st.number_input("Actual Amount (PKR)", min_value=0.0)
                remarks = st.text_area("Remarks")

            status = st.selectbox("Payment Status", ["Pending","In Process","Completed"])

            if st.button("💾 Save Payment"):
                existing_payment = c.execute(
                    "SELECT id FROM payment_tracking WHERE pr_id=?", (pr_id_choice,)
                ).fetchone()

                if existing_payment:
                    c.execute("""UPDATE payment_tracking
                                SET pr_number=?, category=?, po_number=?, invoice_number=?, wave_receipt=?, 
                                    work_confirmation=?, work_order_yesno=?, work_order_number=?, actual_usd=?, actual_pkr=?,
                                    payment_date=?, remarks=?, status=?
                                WHERE pr_id=?""",
                            (pr_number_choice, category_choice, po_number, invoice_number, wave_receipt,
                            work_confirmation, work_order_yesno, work_order_number, actual_usd, actual_pkr,
                            str(payment_date), remarks, status, pr_id_choice))
                    st.success(f"✅ Updated payment for PR {pr_number_choice} (ID {pr_id_choice}). Status: {status}")

                else:
                    c.execute("""INSERT INTO payment_tracking (
                        pr_id, pr_number, category, po_number, invoice_number, wave_receipt,
                        work_confirmation, work_order_yesno, work_order_number, actual_usd, actual_pkr,
                        payment_date, remarks, status
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                        pr_id_choice, pr_number_choice, category_choice, po_number, invoice_number, wave_receipt,
                        work_confirmation, work_order_yesno, work_order_number, actual_usd, actual_pkr,
                        str(payment_date), remarks, status
                    ))
                    st.success(f"✅ New payment saved for PR {pr_number_choice} (ID {pr_id_choice}). Status: {status}")

                c.execute("""INSERT INTO status_history 
                            (record_type, record_id, old_status, new_status, changed_by) 
                            VALUES (?,?,?,?,?)""",
                        ("Payment", str(pr_id_choice), None, status, st.session_state["user"]))

                if status == "Completed":
                    old_pr_status = pr_data["status"]
                    c.execute("UPDATE pr_tracking SET status='Completed' WHERE id=?", (pr_id_choice,))
                    c.execute("""INSERT INTO status_history 
                                (record_type, record_id, old_status, new_status, changed_by) 
                                VALUES (?,?,?,?,?)""",
                            ("PR", str(pr_id_choice), old_pr_status, "Completed", st.session_state["user"]))

                conn.commit()
                time.sleep(2)
                st.rerun()

    # --- Case 2: DSA Payment ---
    elif category_choice == "DSA Payment":
        st.subheader("✈️ DSA Payment Form")
        col1, col2 = st.columns(2)
        with col1:
            dsa_type = st.selectbox("DSA Type", ["TPC Staff","Gop Officials","Other Participants"])
            date_request = st.date_input("Date of Request")
            staff_name = st.text_input("Created By", value=st.session_state["user"])
            programme_unit = st.selectbox("Programme Unit", 
                ["CRLR","HEALTH","PROTECTION","SNFI and WASH","DTM","FCDO- BRAVE","MECC","Core Staff_ HRRD"])
            type_services = st.selectbox("Type of Services", ["Goods","Services","Works"])
        with col2:
            vendor_name = st.text_input("Vendor Name")
            description = st.text_area("Description")
            location = st.text_input("Location")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")

        diff = (end_date - start_date).days
        days = 0 if diff < 0 else diff + 0.3
        st.metric("Calculated Days", days)

        col1, col2 = st.columns(2)
        with col1:
            amount_pkr = st.number_input("Amount (PKR)", min_value=0.0)
            ist_number = st.text_input("IST Number")
        with col2:
            comments = st.text_area("Comments")
            status = st.selectbox("Status", ["Pending","In Process","Completed","Paid"])

        if st.button("💾 Save DSA Payment"):
            c.execute("""INSERT INTO dsa_payments (
                date_request, staff_name, programme_unit, type_services, dsa_type,
                vendor_name, description, location, start_date, end_date,
                days, amount_pkr, ist_number, comments, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                str(date_request), staff_name, programme_unit, type_services, dsa_type,
                vendor_name, description, location, str(start_date), str(end_date),
                days, amount_pkr, ist_number, comments, status
            ))
            c.execute("""INSERT INTO status_history 
                         (record_type, record_id, old_status, new_status, changed_by) 
                         VALUES (?,?,?,?,?)""",
                      ("DSA", vendor_name, None, status, st.session_state["user"]))
            conn.commit()
            st.success("✅ DSA Payment saved.")
            st.rerun()

    # --- Case 3: Operational Advance ---
    elif category_choice == "Operational Advance":
        st.subheader("💼 Operational Advance Form")

        col1, col2 = st.columns(2)
        with col1:
            date_request = st.date_input("Date of Request")
            staff_name = st.text_input("Created By", value=st.session_state["user"])
            programme_unit = st.selectbox("Programme Unit", 
                ["CRLR","HEALTH","PROTECTION","SNFI and WASH","DTM","FCDO- BRAVE","MECC","Core Staff_ HRRD"])
            supplier_name = st.text_input("Supplier Name")
            description = st.text_area("Description")
        with col2:
            invoice_type = st.selectbox("Invoice Type", ["Proforma","Final","Other"])
            invoice_no = st.text_input("Invoice Number")
            total_amount = st.number_input("Total Amount", min_value=0.0)
            invoice_currency = st.text_input("Invoice Currency")
            payment_currency = st.text_input("Payment Currency")
            location = st.text_input("Location")
            comments = st.text_area("Comments")
            status = st.selectbox("Status", ["Pending","In Process","Completed","Paid"])

        if st.button("💾 Save Operational Advance"):
            try:
                c.execute("""INSERT INTO operational_advances (
                    date_request, staff_name, programme_unit, supplier_name, description,
                    invoice_type, invoice_no, total_amount, invoice_currency, payment_currency,
                    location, comments, status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    str(date_request), staff_name, programme_unit, supplier_name, description,
                    invoice_type, invoice_no, total_amount, invoice_currency, payment_currency,
                    location, comments, status
                ))
                conn.commit()
                c.execute("""INSERT INTO status_history 
                             (record_type, record_id, old_status, new_status, changed_by) 
                             VALUES (?,?,?,?,?)""",
                          ("OA", str(c.lastrowid), None, status, st.session_state["user"]))
                conn.commit()
                st.success("✅ Operational Advance saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving OA: {e}")

# ==============================
# Operational Advance Liquidation
# ==============================

elif page == "Operational Advance Liquidation":
    st.title("💼 Operational Advance Liquidation")

    oas = pd.read_sql("SELECT * FROM operational_advances", conn)
    if oas.empty:
        st.warning("⚠️ No operational advances found.")
        st.stop()

    selected_oa_id = st.selectbox(
        "Select Operational Advance to Liquidate",
        oas["id"],
        format_func=lambda x: f"ID {x} | {oas.loc[oas['id']==x, 'supplier_name'].values[0]} | {oas.loc[oas['id']==x, 'description'].values[0]}"
    )

    oa_data = oas[oas["id"] == selected_oa_id].iloc[0]

    st.markdown("### 🔹 Operational Advance Details")
    st.write(f"""
    **Programme Unit:** {oa_data['programme_unit']}  
    **Category:** {oa_data['invoice_type']}  
    **Supplier:** {oa_data['supplier_name']}  
    **Description:** {oa_data['description']}  
    **Invoice No:** {oa_data['invoice_no']}  
    **Total Amount:** {oa_data['total_amount']}  
    **Location:** {oa_data['location']}  
    """)

    st.markdown("### 🧾 Liquidation Information")
    date_request = st.date_input("Date of Request")
    staff_name = st.text_input("Staff Name/Admin", value=st.session_state["user"])
    liquidation_ist = st.text_input("Liquidation IST#")
    liquidation_amount = st.number_input("Liquidation Amount", min_value=0.0)

    st.markdown("#### WBL 1")
    col1, col2 = st.columns(2)
    with col1:
        wbl_project_code = st.text_input("Project Code (WBL 1)")
    with col2:
        wbl_task_number = st.text_input("Task Number (WBL 1)")

    unspent_amount = st.number_input("Unspent Amount", min_value=0.0)
    unspent_deposit_yesno = st.selectbox("Unspent amount deposited in IOM account?", ["No", "Yes"])
    deposited_amount = None
    if unspent_deposit_yesno == "Yes":
        deposited_amount = st.number_input("Deposited Amount", min_value=0.0)

    unspent_ist1 = st.text_input("Unspent Amount IST#1")
    unspent_ist2 = st.text_input("Unspent Amount IST#2")

    col1, col2 = st.columns(2)
    with col1:
        unspent_wbl_project_code = st.text_input("Project Code (Unspent)")
    with col2:
        unspent_wbl_task_number = st.text_input("Task Number (Unspent)")

    documents_submitted = st.selectbox("Documents/Reports Submitted?", ["No", "Yes"])
    status = st.selectbox("Liquidation Status", ["Pending", "In Process", "Completed", "Paid"])
    comments = st.text_area("Comments", value=oa_data["comments"] or "")

    if st.button("💾 Save Liquidation Record"):
        try:
            c.execute("""INSERT INTO operational_liquidations (
                oa_id, date_request, staff_name, programme_unit, category, supplier_name, description,
                invoice_type, invoice_no, total_amount, invoice_currency, payment_currency,
                liquidation_ist, liquidation_amount, wbl_project_code, wbl_task_number,
                unspent_amount, unspent_deposit_yesno, deposited_amount,
                unspent_ist1, unspent_ist2, unspent_wbl_project_code, unspent_wbl_task_number,
                documents_submitted, location, comments, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                int(oa_data["id"]), str(date_request), staff_name, oa_data["programme_unit"], oa_data["invoice_type"],
                oa_data["supplier_name"], oa_data["description"], oa_data["invoice_type"], oa_data["invoice_no"],
                oa_data["total_amount"], oa_data["invoice_currency"], oa_data["payment_currency"],
                liquidation_ist, liquidation_amount, wbl_project_code, wbl_task_number,
                unspent_amount, unspent_deposit_yesno, deposited_amount,
                unspent_ist1, unspent_ist2, unspent_wbl_project_code, unspent_wbl_task_number,
                documents_submitted, oa_data["location"], comments, status
            ))

            if status in ["Completed", "Paid"]:
                c.execute("UPDATE operational_advances SET status=? WHERE id=?", (status, int(oa_data["id"])))
                c.execute("""INSERT INTO status_history
                             (record_type, record_id, old_status, new_status, changed_by)
                             VALUES (?,?,?,?,?)""",
                          ("OA", str(oa_data["id"]), oa_data["status"], status, st.session_state["user"]))
                st.info("Operational Advance marked as closed ✅")

            conn.commit()
            st.success(f"✅ Liquidation record saved for OA ID {oa_data['id']}")
            st.rerun()

        except Exception as e:
            st.error(f"Error saving liquidation: {e}")


# ==============================
# Part 5: User Management & Reports
# ==============================

# --- User Management ---
elif page == "User Management":
    st.title("👤 User Management")

    if st.session_state["role"] != "Admin":
        st.error("You do not have permission to manage users.")
        st.stop()

    # Add User
    st.subheader("➕ Add User")
    with st.form("user_form"):
        uname = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Admin", "Staff", "Finance"])
        if st.form_submit_button("Add User"):
            if not uname.strip() or not pwd.strip():
                st.error("⚠️ Username and Password are required.")
            else:
                try:
                    hashed_pwd = hash_password(pwd.strip())
                    c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", 
                              (uname.strip(), hashed_pwd, role))
                    conn.commit()
                    st.success(f"✅ User {uname} added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Existing Users
    st.subheader("👥 Existing Users")
    users = pd.read_sql("SELECT id, username, role FROM users", conn)
    if not users.empty:
        st.dataframe(users, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            del_user = st.selectbox("Select User ID to delete", users["id"])
            if st.button("🗑️ Delete User"):
                c.execute("DELETE FROM users WHERE id=?", (del_user,))
                conn.commit()
                st.success(f"✅ User {del_user} deleted.")
                st.rerun()

        with col2:
            reset_user = st.selectbox("Reset password for", users["username"])
            new_pwd = st.text_input("New Password", type="password")
            if st.button("🔄 Reset Password"):
                if not new_pwd.strip():
                    st.error("⚠️ Enter a new password.")
                else:
                    hashed_pwd = hash_password(new_pwd.strip())
                    c.execute("UPDATE users SET password=? WHERE username=?", (hashed_pwd, reset_user))
                    conn.commit()
                    st.success(f"✅ Password reset for {reset_user}")

# --- Reports ---
elif page == "Reports":
    st.title("📑 Reports & Exports")

    # Filters
    st.subheader("🔍 Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        all_prs = pd.read_sql("SELECT DISTINCT pr_number FROM pr_tracking", conn)
        pr_filter = st.selectbox("Filter by PR Number", ["All"] + all_prs["pr_number"].tolist() if not all_prs.empty else ["All"])
    with col2:
        all_categories = pd.read_sql("SELECT DISTINCT category FROM pr_tracking", conn)
        cat_filter = st.selectbox("Filter by Category", ["All"] + all_categories["category"].dropna().tolist() if not all_categories.empty else ["All"])
    with col3:
        all_staff = pd.read_sql("SELECT DISTINCT staff_name FROM pr_tracking", conn)
        staff_filter = st.selectbox("Filter by Staff/User", ["All"] + all_staff["staff_name"].dropna().tolist() if not all_staff.empty else ["All"])

    # Single PR Report
    st.subheader("📄 Single PR Report")
    if pr_filter != "All":
        prs = pd.read_sql("SELECT * FROM pr_tracking WHERE pr_number=?", conn, params=[pr_filter])
        if prs.empty:
            st.warning("⚠️ No PRs found with that number.")
        else:
            pr_id_choice = st.selectbox("Select specific PR ID", prs["id"])
            pr_data = prs[prs["id"] == pr_id_choice]

            st.markdown("### 📝 PR Details")
            pr_row = pr_data.iloc[0]
            st.markdown(f"""
            <div style="background:#f9f9f9; padding:10px; border-radius:8px;">
                <b>PR ID:</b> {pr_row['id']}<br>
                <b>PR Number:</b> {pr_row['pr_number']}<br>
                <b>Date of Request:</b> {pr_row['date_request']}<br>
                <b>Staff:</b> {pr_row['staff_name']}<br>
                <b>Programme Unit:</b> {pr_row['programme_unit']}<br>
                <b>Category:</b> {pr_row['category']}<br>
                <b>Status:</b> {pr_row['status']}
            </div>
            """, unsafe_allow_html=True)

            # Payments linked to PR
            st.subheader("💰 Payments")
            payments = pd.read_sql("SELECT * FROM payment_tracking WHERE pr_id=?", conn, params=[pr_id_choice])
            st.dataframe(payments if not payments.empty else pd.DataFrame(columns=["No payments found"]), use_container_width=True)

            # Status Timeline
            st.subheader("📜 Status Timeline")
            timeline = pd.read_sql("SELECT * FROM status_history WHERE record_id=? ORDER BY changed_at", conn, params=[pr_id_choice])
            st.dataframe(timeline if not timeline.empty else pd.DataFrame(columns=["No status history"]), use_container_width=True)

            # Export PR-specific report
            file_name = f"PR_Report_{pr_row['pr_number']}_ID{pr_id_choice}.xlsx"
            with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
                pr_data.to_excel(writer, index=False, sheet_name="PR")
                payments.to_excel(writer, index=False, sheet_name="Payments")
                timeline.to_excel(writer, index=False, sheet_name="Timeline")
            with open(file_name, "rb") as f:
                st.download_button("⬇️ Download PR Report", f, file_name=file_name)

    # Export Full Database
    st.subheader("📊 Export All Data")
    if st.button("⬇️ Download Full Database"):
        pr_all = pd.read_sql("SELECT * FROM pr_tracking", conn)
        pay_all = pd.read_sql("SELECT * FROM payment_tracking", conn)
        dsa_all = pd.read_sql("SELECT * FROM dsa_payments", conn)
        oa_all = pd.read_sql("SELECT * FROM operational_advances", conn)
        timeline_all = pd.read_sql("SELECT * FROM status_history", conn)

        file_name = "Full_Report.xlsx"
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            pr_all.to_excel(writer, index=False, sheet_name="PRs")
            pay_all.to_excel(writer, index=False, sheet_name="Payments")
            dsa_all.to_excel(writer, index=False, sheet_name="DSA_Payments")
            oa_all.to_excel(writer, index=False, sheet_name="Operational_Advances")
            timeline_all.to_excel(writer, index=False, sheet_name="Timeline")
        with open(file_name, "rb") as f:
            st.download_button("⬇️ Download Full Report", f, file_name=file_name)
