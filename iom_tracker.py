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

c.execute("""CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    description TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    task_number TEXT NOT NULL,
    task_desc TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
)""")

c.execute("""CREATE TABLE IF NOT EXISTS pr_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_number TEXT UNIQUE NOT NULL,
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

c.execute("""CREATE TABLE IF NOT EXISTS pr_wbls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_number TEXT NOT NULL,
    task_id INTEGER NOT NULL,
    percentage INTEGER NOT NULL,
    FOREIGN KEY (pr_number) REFERENCES pr_tracking (pr_number) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
)""")

c.execute("""CREATE TABLE IF NOT EXISTS payment_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_number TEXT,
    category TEXT,
    po_number TEXT,
    invoice_number TEXT,
    wave_receipt TEXT,
    work_order_yesno TEXT,
    work_order_number TEXT,
    actual_usd REAL,
    actual_pkr REAL,
    payment_date TEXT,
    remarks TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pr_number) REFERENCES pr_tracking (pr_number) ON DELETE CASCADE
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

c.execute("""CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT,
    record_id TEXT,
    old_status TEXT,
    new_status TEXT,
    changed_by TEXT,
    changed_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

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
    "User Management",
    "Project & Task Management",
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
        all_prs = pd.read_sql("SELECT pr_number FROM pr_tracking", conn)
        pr_filter = st.selectbox(
            "Filter by PR Number", 
            ["All"] + all_prs["pr_number"].tolist() if not all_prs.empty else ["All"]
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
            update_pr = st.selectbox("Select PR to update status", prs["pr_number"])
            new_status = st.selectbox("New Status", ["Submitted","In Process","Completed"])
            if st.button("🔄 Update PR Status"):
                old_status = c.execute("SELECT status FROM pr_tracking WHERE pr_number=?", (update_pr,)).fetchone()[0]
                c.execute("UPDATE pr_tracking SET status=? WHERE pr_number=?", (new_status, update_pr))
                c.execute("""INSERT INTO status_history 
                             (record_type, record_id, old_status, new_status, changed_by) 
                             VALUES (?,?,?,?,?)""",
                          ("PR", update_pr, old_status, new_status, st.session_state["user"]))
                conn.commit()
                st.success(f"PR {update_pr} updated to {new_status}")
                st.rerun()

        with col2:
            delete_pr = st.selectbox("Select PR to delete", prs["pr_number"])
            if st.button("🗑️ Delete PR"):
                c.execute("DELETE FROM pr_tracking WHERE pr_number=?", (delete_pr,))
                conn.commit()
                st.success(f"PR {delete_pr} deleted")
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
            new_status = st.selectbox("New Status (Payment)", ["Pending","In Process","Completed"])
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
                    pr_num = c.execute("SELECT pr_number FROM payment_tracking WHERE id=?", (update_pay,)).fetchone()[0]
                    if pr_num:
                        old_pr_status = c.execute("SELECT status FROM pr_tracking WHERE pr_number=?", (pr_num,)).fetchone()[0]
                        c.execute("UPDATE pr_tracking SET status='Completed' WHERE pr_number=?", (pr_num,))
                        c.execute("""INSERT INTO status_history 
                                     (record_type, record_id, old_status, new_status, changed_by) 
                                     VALUES (?,?,?,?,?)""",
                                  ("PR", pr_num, old_pr_status, "Completed", st.session_state["user"]))
                        conn.commit()
                        st.info(f"Linked PR {pr_num} also marked Completed ✅")

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
            new_status = st.selectbox("New Status (DSA)", ["Pending","In Process","Completed","Paid"])
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

    # --- Operational Advances ---
    st.subheader("💼 Operational Advances")
    oas = pd.read_sql("SELECT * FROM operational_advances", conn)
    if oas.empty:
        st.info("No operational advances yet.")
    else:
        st.dataframe(oas, use_container_width=True, height=400)

        col1, col2 = st.columns(2)
        with col1:
            update_oa = st.selectbox("Select OA ID to update status", oas["id"])
            new_status = st.selectbox("New Status (OA)", ["Pending","In Process","Completed","Paid"])
            if st.button("🔄 Update OA Status"):
                old_status = c.execute("SELECT status FROM operational_advances WHERE id=?", (update_oa,)).fetchone()[0]
                c.execute("UPDATE operational_advances SET status=? WHERE id=?", (new_status, update_oa))
                c.execute("""INSERT INTO status_history 
                             (record_type, record_id, old_status, new_status, changed_by) 
                             VALUES (?,?,?,?,?)""",
                          ("OA", str(update_oa), old_status, new_status, st.session_state["user"]))
                conn.commit()
                st.success(f"Operational Advance {update_oa} updated to {new_status}")
                st.rerun()

        with col2:
            deloa = st.selectbox("Select OA ID to delete", oas["id"])
            if st.button("🗑️ Delete Operational Advance"):
                c.execute("DELETE FROM operational_advances WHERE id=?", (deloa,))
                conn.commit()
                st.success(f"Operational Advance {deloa} deleted ✅")
                st.rerun()

    # --- Reminders ---
    st.subheader("⏰ PR Reminders")
    reminders = pd.read_sql("""
        SELECT pr_number, staff_name, category, to_date, reminder_days
        FROM pr_tracking
        WHERE reminder_expiry='Yes'
    """, conn)
    if reminders.empty:
        st.success("✅ No reminders due.")
    else:
        today = datetime.today().date()
        reminders["Reminder Date"] = pd.to_datetime(reminders["to_date"]) - pd.to_timedelta(reminders["reminder_days"], unit="D")
        reminders["Reminder Date"] = reminders["Reminder Date"].dt.date
        reminders["Status"] = reminders["Reminder Date"].apply(lambda d: "⚠️ DUE" if d <= today else "📌 Upcoming")
        st.dataframe(reminders, use_container_width=True, height=300)
# ==============================
# Part 3: PR Tracking
# ==============================

elif page == "PR Tracking":
    st.title("📝 New Purchase Request")

    # --- PR Form ---
    st.subheader("➕ Create PR")

    col1, col2 = st.columns(2)
    with col1:
        pr_number = st.text_input("PR Number (unique)")
        date_request = st.date_input("Date of Request")
        staff_name = st.text_input("Created By", value=st.session_state["user"])
        programme_unit = st.selectbox(
            "Programme Unit", 
            ["CRLR","HEALTH","PROTECTION","SNFI and WASH","DTM","FCDO- BRAVE","MECC","Core Staff_ HRRD"]
        )
        type_services = st.selectbox("Type of Services", ["Goods","Services","Works"])
        category = st.selectbox("Category", [
            "Implementing Partners","Professional Services","Medical",
            "Private Sector Partners","Event management","ICT","WSNFI",
            "Miscellaneous","Rental Vehicle"
        ])
    with col2:
        description = st.text_area("Description")
        assigned_users = pd.read_sql("SELECT username FROM users", conn)
        assigned_to = st.selectbox(
            "Assign To", 
            assigned_users["username"].tolist() if not assigned_users.empty else ["admin"], 
            index=0
        )

    # --- Rental Vehicle Fields ---
    type_vehicle = traveller_name = traveller_phone = reminder_expiry = reminder_days = None
    if category == "Rental Vehicle":
        st.markdown("### 🚗 Rental Vehicle Details")
        col1, col2 = st.columns(2)
        with col1:
            type_vehicle = st.selectbox("Type of Vehicle", [
                "Sedan Car","Parado","Double Cabin Vigo/Hilux",
                "Armoured Vehicle","Equipped Ambulance","HiAce","Bus","Coaster"
            ])
            traveller_name = st.text_input("Traveller Name")
        with col2:
            traveller_phone = st.text_input("Traveller Phone #")
            reminder_expiry = st.radio("Reminder about expiry?", ["Yes","No"])
            if reminder_expiry == "Yes":
                reminder_days = st.number_input("Reminder days before", min_value=1)

    # --- Dates & Duration ---
    st.markdown("### 📅 Travel/Request Duration")
    col1, col2, col3 = st.columns(3)
    with col1:
        from_date = st.date_input("From")
    with col2:
        to_date = st.date_input("To")
    with col3:
        days = max((to_date - from_date).days, 0) if from_date and to_date else 0
        st.metric("Calculated Days", days)

    # --- Costs & Location ---
    st.markdown("### 💵 Cost & Location")
    col1, col2 = st.columns(2)
    with col1:
        location = st.text_input("Location")
        qty = st.number_input("Quantity", min_value=1)
        est_pkr = st.number_input("Estimated Cost (PKR)", min_value=0.0)
    with col2:
        est_usd = st.number_input("Estimated Cost (USD)", min_value=0.0)
        comments = st.text_area("Comments")

    # --- WBL Selection ---
    st.markdown("### 📂 WBL Allocation")
    projects_df = pd.read_sql("SELECT * FROM projects", conn)

    wbl_selections = []
    if projects_df.empty:
        st.warning("⚠️ Add projects and tasks in Project & Task Management first.")
    else:
        num_wbls = st.number_input("Number of allocations", min_value=1, max_value=5, value=1)
        for i in range(num_wbls):
            st.markdown(f"**WBL #{i+1}**")

            proj_choice = st.selectbox(
                f"Select Project for WBL {i+1}", 
                projects_df["code"], 
                key=f"proj_{i}"
            )

            proj_row = c.execute("SELECT id FROM projects WHERE code=?", (proj_choice.strip(),)).fetchone()
            proj_id = proj_row[0] if proj_row else None

            if not proj_id:
                st.error("⚠️ Project not found in DB.")
                continue

            proj_tasks = pd.read_sql("SELECT * FROM tasks WHERE project_id=?", conn, params=[proj_id])
            if proj_tasks.empty:
                st.warning("⚠️ This project has no tasks.")
            else:
                task_choice = st.selectbox(
                    f"Select Task for WBL {i+1}", 
                    proj_tasks["task_number"], 
                    key=f"task_{i}"
                )

                task_row = c.execute("SELECT id FROM tasks WHERE task_number=? AND project_id=?", 
                                    (task_choice.strip(), proj_id)).fetchone()
                task_id = task_row[0] if task_row else None

                perc = st.number_input(
                    f"Percentage for WBL {i+1}", 
                    min_value=0, max_value=100, 
                    value=100 if i==0 else 0, key=f"perc_{i}"
                )

                wbl_selections.append((task_id, perc))

    # --- Submit PR ---
    if st.button("✅ Submit PR"):
        if not pr_number.strip():
            st.error("⚠️ PR number is required.")
        elif sum([p for _, p in wbl_selections if p]) != 100:
            st.error("⚠️ WBL percentages must add up to 100!")
        else:
            try:
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
                    str(from_date), str(to_date), days, location, qty,
                    est_pkr, est_usd, reminder_expiry, reminder_days,
                    comments, "Submitted", datetime.now(), assigned_to
                ))

                for task_id, perc in wbl_selections:
                    if task_id:
                        c.execute("INSERT INTO pr_wbls (pr_number, task_id, percentage) VALUES (?,?,?)",
                                (pr_number, task_id, perc))

                c.execute("""INSERT INTO status_history 
                             (record_type, record_id, old_status, new_status, changed_by) 
                             VALUES (?,?,?,?,?)""",
                        ("PR", pr_number, None, "Submitted", st.session_state["user"]))

                conn.commit()
                st.success(f"✅ PR {pr_number} submitted successfully!")
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
        selected_pr = st.selectbox("Select a PR to view WBLs", prs["pr_number"])
        wbls = pd.read_sql("""
            SELECT pw.percentage, p.code AS project_code, t.task_number, t.task_desc
            FROM pr_wbls pw
            LEFT JOIN tasks t ON pw.task_id = t.id
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE pw.pr_number=?
        """, conn, params=[selected_pr])
        if wbls.empty:
            st.info("No WBLs found for this PR.")
        else:
            st.dataframe(
                wbls.rename(columns={
                    "percentage": "Percentage",
                    "project_code": "Project Code",
                    "task_number": "Task Number",
                    "task_desc": "Task Description"
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
            pr_choice = st.selectbox("Select PR Number", prs["pr_number"])
            pr_data = prs[prs["pr_number"] == pr_choice].iloc[0]

            # --- PR Details (pretty card style) ---
            st.markdown("### 📝 Purchase Request Details")
            st.markdown(f"""
            <div style="background:#f9f9f9; padding:10px; border-radius:8px;">
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

            work_order_yesno, work_order_number = None, None
            if category_choice != "Rental Vehicle":
                work_order_yesno = st.selectbox("Work Order in system?", ["No","Yes"])
                if work_order_yesno == "Yes":
                    work_order_number = st.text_input("Work Order Receipt #")

            col1, col2 = st.columns(2)
            with col1:
                actual_usd = st.number_input("Actual Amount (USD)", min_value=0.0)
                payment_date = st.date_input("Payment Submitted Date")
            with col2:
                actual_pkr = st.number_input("Actual Amount (PKR)", min_value=0.0)
                remarks = st.text_area("Remarks")

            status = st.selectbox("Payment Status", ["Pending","In Process","Completed"])

            if st.button("💾 Save Payment"):
                if not pr_choice:
                    st.error("⚠️ Please select a PR.")
                else:
                    c.execute("""INSERT INTO payment_tracking (
                        pr_number, category, po_number, invoice_number, wave_receipt,
                        work_order_yesno, work_order_number, actual_usd, actual_pkr,
                        payment_date, remarks, status
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
                        pr_choice, category_choice, po_number, invoice_number, wave_receipt,
                        work_order_yesno, work_order_number, actual_usd, actual_pkr,
                        str(payment_date), remarks, status
                    ))

                    # log payment status
                    c.execute("""INSERT INTO status_history 
                                 (record_type, record_id, old_status, new_status, changed_by) 
                                 VALUES (?,?,?,?,?)""",
                              ("Payment", pr_choice, None, status, st.session_state["user"]))

                    # workflow sync: mark PR as completed if payment completed
                    if status == "Completed":
                        old_pr_status = c.execute("SELECT status FROM pr_tracking WHERE pr_number=?", (pr_choice,)).fetchone()[0]
                        c.execute("UPDATE pr_tracking SET status='Completed' WHERE pr_number=?", (pr_choice,))
                        c.execute("""INSERT INTO status_history 
                                     (record_type, record_id, old_status, new_status, changed_by) 
                                     VALUES (?,?,?,?,?)""",
                                  ("PR", pr_choice, old_pr_status, "Completed", st.session_state["user"]))

                    conn.commit()
                    st.success(f"✅ Payment saved for PR {pr_choice}. Status: {status}")
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

        # days calc: last day = 0.3
        diff = (end_date - start_date).days
        days = 0 if diff <= 0 else 0.3 if diff == 1 else (diff - 1) + 0.3
        st.metric("Calculated Days", days)

        col1, col2 = st.columns(2)
        with col1:
            amount_pkr = st.number_input("Amount (PKR)", min_value=0.0)
            ist_number = st.text_input("IST Number")
        with col2:
            comments = st.text_area("Comments")
            status = st.selectbox("Status", ["Pending","In Process","Completed","Paid"])

        if st.button("💾 Save DSA Payment"):
            if not vendor_name.strip():
                st.error("⚠️ Vendor name is required.")
            else:
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

        col1, col2 = st.columns(2)
        with col1:
            location = st.text_input("Location")
        with col2:
            comments = st.text_area("Comments")
            status = st.selectbox("Status", ["Pending","In Process","Completed","Paid"])

        if st.button("💾 Save Operational Advance"):
            if not supplier_name.strip():
                st.error("⚠️ Supplier name is required.")
            else:
                c.execute("""INSERT INTO operational_advances (
                    date_request, staff_name, programme_unit, supplier_name, description,
                    invoice_type, invoice_no, total_amount, invoice_currency, payment_currency,
                    location, comments, status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    str(date_request), staff_name, programme_unit, supplier_name, description,
                    invoice_type, invoice_no, total_amount, invoice_currency, payment_currency,
                    location, comments, status
                ))
                c.execute("""INSERT INTO status_history 
                             (record_type, record_id, old_status, new_status, changed_by) 
                             VALUES (?,?,?,?,?)""",
                          ("OA", supplier_name, None, status, st.session_state["user"]))
                conn.commit()
                st.success("✅ Operational Advance saved.")
                st.rerun()
# ==============================
# Part 5: User Management, Project/Task Management, Reports
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
                if st.confirm("Are you sure you want to delete this user?"):
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

# --- Project & Task Management ---
elif page == "Project & Task Management":
    st.title("📂 Project & Task (WBL) Management")

    # Add Project
    st.subheader("➕ Add Project")
    with st.form("proj_form"):
        project_code = st.text_input("Project Code (e.g. DR0092)")
        project_desc = st.text_input("Project Description (optional)")
        if st.form_submit_button("Add Project"):
            try:
                c.execute("INSERT INTO projects (code, description) VALUES (?,?)",
                          (project_code.strip(), project_desc.strip()))
                conn.commit()
                st.success(f"✅ Project {project_code} added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    # Add Task
    st.subheader("➕ Add Task")
    projects = pd.read_sql("SELECT * FROM projects", conn)
    if projects.empty:
        st.warning("⚠️ Add a project first.")
    else:
        proj_choice = st.selectbox("Select Project", projects["code"])
        proj_row = c.execute("SELECT id FROM projects WHERE code=?", (proj_choice,)).fetchone()
        proj_id = proj_row[0] if proj_row else None

        with st.form("task_form"):
            task_number = st.text_input("Task Number (e.g. A:2:1:002)")
            task_desc = st.text_input("Task Description (optional)")
            if st.form_submit_button("Add Task"):
                try:
                    if not proj_id:
                        st.error("⚠️ Selected project not found in DB.")
                    else:
                        c.execute("INSERT INTO tasks (project_id, task_number, task_desc) VALUES (?,?,?)",
                                  (proj_id, task_number.strip(), task_desc.strip()))
                        conn.commit()
                        st.success("✅ Task added successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Existing Projects & Tasks
    st.subheader("📋 Existing Projects & Tasks")
    tasks = pd.read_sql("""
        SELECT t.id, p.code as project_code, t.task_number, 
               p.description as project_desc, t.task_desc
        FROM tasks t 
        JOIN projects p ON t.project_id = p.id
    """, conn)
    if tasks.empty:
        st.info("No tasks yet.")
    else:
        st.dataframe(tasks, use_container_width=True)

        del_task = st.selectbox("Select Task ID to delete", tasks["id"])
        if st.button("🗑️ Delete Task"):
            c.execute("DELETE FROM tasks WHERE id=?", (del_task,))
            conn.commit()
            st.success(f"✅ Task {del_task} deleted.")
            st.rerun()

    # Delete Project
    st.subheader("🗑️ Delete Project")
    if not projects.empty:
        del_proj = st.selectbox("Select Project ID to delete", projects["id"])
        if st.button("🗑️ Delete Project & Its Tasks"):
            c.execute("DELETE FROM tasks WHERE project_id=?", (del_proj,))
            c.execute("DELETE FROM projects WHERE id=?", (del_proj,))
            conn.commit()
            st.success(f"✅ Project {del_proj} and tasks deleted.")
            st.rerun()

# --- Reports ---
elif page == "Reports":
    st.title("📑 Reports & Exports")

    # Filters
    st.subheader("🔍 Filters")
    col1, col2, col3 = st.columns(3)
    with col1:
        all_prs = pd.read_sql("SELECT pr_number FROM pr_tracking", conn)
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
        if st.button("🔍 Generate Report"):
            pr_choice = pr_filter
            pr_data = pd.read_sql("SELECT * FROM pr_tracking WHERE pr_number=?", conn, params=[pr_choice])

            st.markdown("### 📝 PR Details")
            if not pr_data.empty:
                pr_row = pr_data.iloc[0]
                st.markdown(f"""
                <div style="background:#f9f9f9; padding:10px; border-radius:8px;">
                    <b>PR Number:</b> {pr_row['pr_number']}<br>
                    <b>Date of Request:</b> {pr_row['date_request']}<br>
                    <b>Staff:</b> {pr_row['staff_name']}<br>
                    <b>Programme Unit:</b> {pr_row['programme_unit']}<br>
                    <b>Category:</b> {pr_row['category']}<br>
                    <b>Status:</b> {pr_row['status']}
                </div>
                """, unsafe_allow_html=True)

            # WBL Allocations
            st.subheader("📂 WBL Allocations")
            wbls = pd.read_sql("""
                SELECT pw.percentage, p.code AS project_code, t.task_number, t.task_desc
                FROM pr_wbls pw
                LEFT JOIN tasks t ON pw.task_id = t.id
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE pw.pr_number=?
            """, conn, params=[pr_choice])
            st.dataframe(wbls if not wbls.empty else pd.DataFrame(columns=["No WBLs found"]), use_container_width=True)

            # Payments
            st.subheader("💰 Payments")
            payments = pd.read_sql("SELECT * FROM payment_tracking WHERE pr_number=?", conn, params=[pr_choice])
            st.dataframe(payments if not payments.empty else pd.DataFrame(columns=["No payments found"]), use_container_width=True)

            # Status Timeline
            st.subheader("📜 Status Timeline")
            timeline = pd.read_sql("SELECT * FROM status_history WHERE record_id=? ORDER BY changed_at", conn, params=[pr_choice])
            st.dataframe(timeline if not timeline.empty else pd.DataFrame(columns=["No status history"]), use_container_width=True)

            # Export PR-specific report
            file_name = f"PR_Report_{pr_choice}.xlsx"
            with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
                pr_data.to_excel(writer, index=False, sheet_name="PR")
                wbls.to_excel(writer, index=False, sheet_name="WBLs")
                payments.to_excel(writer, index=False, sheet_name="Payments")
                timeline.to_excel(writer, index=False, sheet_name="Timeline")
            with open(file_name, "rb") as f:
                st.download_button("⬇️ Download PR Report", f, file_name=file_name)

    # Export Full Database
    st.subheader("📊 Export All Data")
    if st.button("⬇️ Download Full Database"):
        pr_all = pd.read_sql("SELECT * FROM pr_tracking", conn)
        wbl_all = pd.read_sql("""
            SELECT pw.pr_number, pw.percentage, p.code AS project_code, t.task_number, t.task_desc
            FROM pr_wbls pw
            LEFT JOIN tasks t ON pw.task_id = t.id
            LEFT JOIN projects p ON t.project_id = p.id
        """, conn)
        pay_all = pd.read_sql("SELECT * FROM payment_tracking", conn)
        dsa_all = pd.read_sql("SELECT * FROM dsa_payments", conn)
        oa_all = pd.read_sql("SELECT * FROM operational_advances", conn)
        timeline_all = pd.read_sql("SELECT * FROM status_history", conn)

        file_name = "Full_Report.xlsx"
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            pr_all.to_excel(writer, index=False, sheet_name="PRs")
            wbl_all.to_excel(writer, index=False, sheet_name="WBLs")
            pay_all.to_excel(writer, index=False, sheet_name="Payments")
            dsa_all.to_excel(writer, index=False, sheet_name="DSA_Payments")
            oa_all.to_excel(writer, index=False, sheet_name="Operational_Advances")
            timeline_all.to_excel(writer, index=False, sheet_name="Timeline")
        with open(file_name, "rb") as f:
            st.download_button("⬇️ Download Full Report", f, file_name=file_name)
