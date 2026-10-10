import streamlit as st
import sqlite3
from datetime import date
import hashlib
import pandas as pd
from sqlalchemy import text
def create_tables():
    """إنشاء الجداول لو مش موجودة"""
    conn = get_connection()
    with conn.session as session:
        # المستخدمين
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(200),
            role VARCHAR(50) NOT NULL DEFAULT 'sales',
            active INTEGER DEFAULT 1,
            created_at DATE
        )
        """))

        # الوحدات
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS units (
            id SERIAL PRIMARY KEY,
            unit_number VARCHAR(50) UNIQUE NOT NULL,
            building VARCHAR(100),
            floor INTEGER,
            area REAL,
            price REAL,
            status VARCHAR(50) DEFAULT 'متاحة'
        )
        """))

        # العملاء
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            phone VARCHAR(50),
            national_id VARCHAR(50),
            address VARCHAR(300),
            notes TEXT
        )
        """))

        # العقود
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS contracts (
            id SERIAL PRIMARY KEY,
            unit_id INTEGER REFERENCES units(id),
            customer_id INTEGER REFERENCES customers(id),
            total_price REAL NOT NULL,
            down_payment REAL DEFAULT 0,
            contract_date DATE,
            notes TEXT
        )
        """))

        # الأقساط
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS installments (
            id SERIAL PRIMARY KEY,
            contract_id INTEGER REFERENCES contracts(id),
            installment_number INTEGER,
            due_date DATE,
            amount REAL,
            paid_amount REAL DEFAULT 0,
            status VARCHAR(50) DEFAULT 'مستحق'
        )
        """))

        # القروض
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS loans (
            id SERIAL PRIMARY KEY,
            lender_name VARCHAR(200) NOT NULL,
            lender_type VARCHAR(50) DEFAULT 'فرد',
            amount REAL NOT NULL,
            interest_rate REAL DEFAULT 0,
            start_date DATE,
            notes TEXT,
            status VARCHAR(50) DEFAULT 'نشط'
        )
        """))

        # أقساط القروض
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS loan_payments (
            id SERIAL PRIMARY KEY,
            loan_id INTEGER REFERENCES loans(id),
            payment_number INTEGER,
            due_date DATE,
            amount REAL,
            paid_amount REAL DEFAULT 0,
            status VARCHAR(50) DEFAULT 'مستحق'
        )
        """))

        # بنود المصروفات
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS expense_categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL
        )
        """))

        # المصروفات
        session.execute(text("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            category_id INTEGER REFERENCES expense_categories(id),
            building VARCHAR(100),
            description VARCHAR(300),
            amount REAL NOT NULL,
            expense_date DATE,
            vendor VARCHAR(200),
            notes TEXT
        )
        """))

        # بنود افتراضية
        result = session.execute(text("SELECT COUNT(*) FROM expense_categories"))
        if result.scalar() == 0:
            for cat in ["مواد بناء", "مقاولون", "عمالة", "إشراف هندسي",
                        "تشطيبات", "كهرباء وسباكة", "رخصة وتراخيص",
                        "مصاريف إدارية", "أخرى"]:
                session.execute(text("INSERT INTO expense_categories (name) VALUES (:name)"), {"name": cat})

        # مستخدم admin افتراضي
        result = session.execute(text("SELECT COUNT(*) FROM users"))
        if result.scalar() == 0:
            session.execute(
                text("INSERT INTO users (username, password_hash, full_name, role, active, created_at) VALUES (:u, :p, :n, :r, 1, :d)"),
                {"u": "admin", "p": hash_password("admin123"), "n": "المدير", "r": "admin", "d": str(date.today())}
            )

        session.commit()

DB_NAME = "realestate.db"

# ========== Caching TTL ==========
CACHE_TTL = 60  # 60 ثانية


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def get_connection():
    return st.connection("postgresql", type="sql")


# ========== Auth (مش محتاجة cache) ==========
def authenticate_user(username, password):
    conn = get_connection()
    df = conn.query("""
        SELECT id, username, full_name, role, active FROM users
        WHERE username = :u AND password_hash = :p
    """, params={"u": username, "p": hash_password(password)}, ttl=0)
    if not df.empty and df.iloc[0]["active"] == 1:
        row = df.iloc[0]
        return {"id": int(row["id"]), "username": row["username"],
                "full_name": row["full_name"], "role": row["role"]}
    return None


def clear_all_cache():
    """امسح كل الكاش (يُستدعى بعد أي إضافة/تعديل/حذف)"""
    st.cache_data.clear()


# ========== الوحدات ==========
@st.cache_data(ttl=CACHE_TTL)
def get_all_units():
    conn = get_connection()
    df = conn.query("SELECT * FROM units ORDER BY unit_number", ttl=0)
    return df.values.tolist()


def get_unit_by_id(unit_id):
    conn = get_connection()
    df = conn.query("SELECT * FROM units WHERE id = :id", params={"id": unit_id}, ttl=0)
    return df.values.tolist()[0] if not df.empty else None


def add_unit(unit_number, building, floor, area, price, status="متاحة"):
    conn = get_connection()
    with conn.session as session:
        try:
            session.execute(text("""
                INSERT INTO units (unit_number, building, floor, area, price, status)
                VALUES (:un, :b, :f, :a, :p, :s)
            """), {"un": unit_number, "b": building, "f": floor,
                   "a": area, "p": price, "s": status})
            session.commit()
            clear_all_cache()
            return True
        except Exception:
            return False


def update_unit_status(unit_id, new_status):
    conn = get_connection()
    with conn.session as session:
        session.execute(text("UPDATE units SET status = :s WHERE id = :id"),
                        {"s": new_status, "id": unit_id})
        session.commit()
        clear_all_cache()


def update_unit(unit_id, unit_number, building, floor, area, price, status):
    conn = get_connection()
    with conn.session as session:
        try:
            session.execute(text("""
                UPDATE units SET unit_number=:un, building=:b, floor=:f,
                                area=:a, price=:p, status=:s
                WHERE id=:id
            """), {"un": unit_number, "b": building, "f": floor,
                   "a": area, "p": price, "s": status, "id": unit_id})
            session.commit()
            clear_all_cache()
            return True
        except Exception:
            return False


def delete_unit(unit_id):
    conn = get_connection()
    with conn.session as session:
        result = session.execute(text("SELECT COUNT(*) FROM contracts WHERE unit_id = :id"),
                                 {"id": unit_id})
        if result.scalar() > 0:
            return False
        session.execute(text("DELETE FROM units WHERE id = :id"), {"id": unit_id})
        session.commit()
        clear_all_cache()
        return True


def unit_has_contract(unit_id):
    conn = get_connection()
    df = conn.query("SELECT COUNT(*) as count FROM contracts WHERE unit_id = :id",
                    params={"id": unit_id}, ttl=0)
    return df.iloc[0]["count"] > 0


# ========== العملاء ==========
@st.cache_data(ttl=CACHE_TTL)
def get_all_customers():
    conn = get_connection()
    df = conn.query("SELECT * FROM customers ORDER BY id DESC", ttl=0)
    return df.values.tolist()


def get_customer_by_id(customer_id):
    conn = get_connection()
    df = conn.query("SELECT * FROM customers WHERE id = :id",
                    params={"id": customer_id}, ttl=0)
    return df.values.tolist()[0] if not df.empty else None


def add_customer(name, phone="", national_id="", address="", notes=""):
    conn = get_connection()
    with conn.session as session:
        result = session.execute(text("""
            INSERT INTO customers (name, phone, national_id, address, notes)
            VALUES (:n, :p, :nid, :a, :no) RETURNING id
        """), {"n": name, "p": phone, "nid": national_id, "a": address, "no": notes})
        session.commit()
        clear_all_cache()
        return result.scalar()


def update_customer(customer_id, name, phone, national_id, address, notes):
    conn = get_connection()
    with conn.session as session:
        session.execute(text("""
            UPDATE customers SET name=:n, phone=:p, national_id=:nid,
                                 address=:a, notes=:no
            WHERE id=:id
        """), {"n": name, "p": phone, "nid": national_id,
               "a": address, "no": notes, "id": customer_id})
        session.commit()
        clear_all_cache()


def delete_customer(customer_id):
    conn = get_connection()
    with conn.session as session:
        result = session.execute(text("SELECT COUNT(*) FROM contracts WHERE customer_id = :id"),
                                 {"id": customer_id})
        if result.scalar() > 0:
            return False
        session.execute(text("DELETE FROM customers WHERE id = :id"), {"id": customer_id})
        session.commit()
        clear_all_cache()
        return True


def customer_has_contract(customer_id):
    conn = get_connection()
    df = conn.query("SELECT COUNT(*) as count FROM contracts WHERE customer_id = :id",
                    params={"id": customer_id}, ttl=0)
    return df.iloc[0]["count"] > 0


# ========== العقود ==========
@st.cache_data(ttl=CACHE_TTL)
def get_all_contracts():
    conn = get_connection()
    df = conn.query("""
        SELECT c.id, u.unit_number, cu.name, c.total_price, c.down_payment, c.contract_date
        FROM contracts c
        JOIN units u ON c.unit_id = u.id
        JOIN customers cu ON c.customer_id = cu.id
        ORDER BY c.id DESC
    """, ttl=0)
    return df.values.tolist()


def get_contract_full_details(contract_id):
    conn = get_connection()
    df = conn.query("""
        SELECT c.id, c.total_price, c.down_payment, c.contract_date, c.notes,
               u.unit_number, u.building, u.floor, u.area, u.price,
               cu.name, cu.phone, cu.national_id, cu.address
        FROM contracts c
        JOIN units u ON c.unit_id = u.id
        JOIN customers cu ON c.customer_id = cu.id
        WHERE c.id = :id
    """, params={"id": contract_id}, ttl=0)
    return df.values.tolist()[0] if not df.empty else None


def get_installments_by_contract(contract_id):
    conn = get_connection()
    df = conn.query("""
        SELECT id, installment_number, due_date, amount, paid_amount, status
        FROM installments WHERE contract_id = :id ORDER BY installment_number
    """, params={"id": contract_id}, ttl=0)
    return df.values.tolist()


def add_contract(unit_id, customer_id, total_price, down_payment, contract_date, notes=""):
    conn = get_connection()
    with conn.session as session:
        result = session.execute(text("""
            INSERT INTO contracts (unit_id, customer_id, total_price, down_payment, contract_date, notes)
            VALUES (:ui, :ci, :tp, :dp, :cd, :n) RETURNING id
        """), {"ui": unit_id, "ci": customer_id, "tp": total_price,
               "dp": down_payment, "cd": contract_date, "n": notes})
        session.commit()
        clear_all_cache()
        return result.scalar()


def add_installment(contract_id, number, due_date, amount):
    conn = get_connection()
    with conn.session as session:
        session.execute(text("""
            INSERT INTO installments (contract_id, installment_number, due_date, amount, paid_amount, status)
            VALUES (:ci, :n, :dd, :a, 0, 'مستحق')
        """), {"ci": contract_id, "n": number, "dd": due_date, "a": amount})
        session.commit()
        clear_all_cache()


# ========== التحصيل ==========
def pay_installment(installment_id, amount):
    conn = get_connection()
    with conn.session as session:
        result = session.execute(text("SELECT amount, paid_amount FROM installments WHERE id = :id"),
                                 {"id": installment_id})
        row = result.fetchone()
        if not row:
            return False
        total_amount, paid_amount = row
        new_paid = min(paid_amount + amount, total_amount)
        status = "مدفوع" if new_paid >= total_amount else "مدفوع جزئيًا"
        session.execute(text("""
            UPDATE installments SET paid_amount = :p, status = :s WHERE id = :id
        """), {"p": new_paid, "s": status, "id": installment_id})
        session.commit()
        clear_all_cache()
        return True


@st.cache_data(ttl=CACHE_TTL)
def get_total_collected():
    conn = get_connection()
    df = conn.query("SELECT COALESCE(SUM(paid_amount), 0) as total FROM installments", ttl=0)
    return df.iloc[0]["total"]


@st.cache_data(ttl=CACHE_TTL)
def get_total_due():
    conn = get_connection()
    df = conn.query("SELECT COALESCE(SUM(amount - paid_amount), 0) as total FROM installments", ttl=0)
    return df.iloc[0]["total"]


@st.cache_data(ttl=CACHE_TTL)
def get_overdue_installments():
    conn = get_connection()
    df = conn.query("""
        SELECT i.id, u.unit_number, cu.name, i.due_date, i.amount, i.paid_amount, i.status
        FROM installments i
        JOIN contracts c ON i.contract_id = c.id
        JOIN units u ON c.unit_id = u.id
        JOIN customers cu ON c.customer_id = cu.id
        WHERE i.due_date < CURRENT_DATE AND i.status != 'مدفوع'
        ORDER BY i.due_date
    """, ttl=0)
    return df.values.tolist()


# ========== القروض ==========
@st.cache_data(ttl=CACHE_TTL)
def get_all_loans():
    conn = get_connection()
    df = conn.query("SELECT * FROM loans ORDER BY id DESC", ttl=0)
    return df.values.tolist()


def get_loan_payments(loan_id):
    conn = get_connection()
    df = conn.query("""
        SELECT id, payment_number, due_date, amount, paid_amount, status
        FROM loan_payments WHERE loan_id = :id ORDER BY payment_number
    """, params={"id": loan_id}, ttl=0)
    return df.values.tolist()


def add_loan(lender_name, lender_type, amount, interest_rate, start_date, notes=""):
    conn = get_connection()
    with conn.session as session:
        result = session.execute(text("""
            INSERT INTO loans (lender_name, lender_type, amount, interest_rate, start_date, notes)
            VALUES (:ln, :lt, :a, :ir, :sd, :n) RETURNING id
        """), {"ln": lender_name, "lt": lender_type, "a": amount,
               "ir": interest_rate, "sd": start_date, "n": notes})
        session.commit()
        clear_all_cache()
        return result.scalar()


def add_loan_payment(loan_id, number, due_date, amount):
    conn = get_connection()
    with conn.session as session:
        session.execute(text("""
            INSERT INTO loan_payments (loan_id, payment_number, due_date, amount, paid_amount, status)
            VALUES (:li, :n, :dd, :a, 0, 'مستحق')
        """), {"li": loan_id, "n": number, "dd": due_date, "a": amount})
        session.commit()
        clear_all_cache()


def pay_loan_payment(payment_id, amount):
    conn = get_connection()
    with conn.session as session:
        result = session.execute(text("SELECT amount, paid_amount FROM loan_payments WHERE id = :id"),
                                 {"id": payment_id})
        row = result.fetchone()
        if not row:
            return False
        total_amount, paid_amount = row
        new_paid = min(paid_amount + amount, total_amount)
        status = "مدفوع" if new_paid >= total_amount else "مدفوع جزئيًا"
        session.execute(text("UPDATE loan_payments SET paid_amount=:p, status=:s WHERE id=:id"),
                        {"p": new_paid, "s": status, "id": payment_id})

        result = session.execute(text("SELECT loan_id FROM loan_payments WHERE id = :id"),
                                 {"id": payment_id})
        loan_id = result.scalar()
        result = session.execute(text("SELECT COUNT(*) FROM loan_payments WHERE loan_id=:lid AND status != 'مدفوع'"),
                                 {"lid": loan_id})
        if result.scalar() == 0:
            session.execute(text("UPDATE loans SET status='مسدد' WHERE id=:id"), {"id": loan_id})
        session.commit()
        clear_all_cache()
        return True


@st.cache_data(ttl=CACHE_TTL)
def get_total_debt():
    conn = get_connection()
    df = conn.query("SELECT COALESCE(SUM(amount - paid_amount), 0) as total FROM loan_payments", ttl=0)
    return df.iloc[0]["total"]


@st.cache_data(ttl=CACHE_TTL)
def get_total_borrowed():
    conn = get_connection()
    df = conn.query("SELECT COALESCE(SUM(amount), 0) as total FROM loans", ttl=0)
    return df.iloc[0]["total"]


@st.cache_data(ttl=CACHE_TTL)
def get_total_repaid():
    conn = get_connection()
    df = conn.query("SELECT COALESCE(SUM(paid_amount), 0) as total FROM loan_payments", ttl=0)
    return df.iloc[0]["total"]


@st.cache_data(ttl=CACHE_TTL)
def get_upcoming_loan_payments(days=30):
    conn = get_connection()
    df = conn.query("""
        SELECT lp.id, l.lender_name, lp.due_date, lp.amount, lp.paid_amount, lp.status
        FROM loan_payments lp
        JOIN loans l ON lp.loan_id = l.id
        WHERE lp.due_date >= CURRENT_DATE AND lp.due_date <= CURRENT_DATE + :days
          AND lp.status != 'مدفوع'
        ORDER BY lp.due_date
    """, params={"days": days}, ttl=0)
    return df.values.tolist()


# ========== المصروفات ==========
@st.cache_data(ttl=CACHE_TTL)
def get_all_categories():
    conn = get_connection()
    df = conn.query("SELECT id, name FROM expense_categories ORDER BY id", ttl=0)
    return df.values.tolist()


@st.cache_data(ttl=CACHE_TTL)
def get_all_expenses():
    conn = get_connection()
    df = conn.query("""
        SELECT e.id, ec.name, e.building, e.description, e.amount, e.expense_date, e.vendor
        FROM expenses e
        LEFT JOIN expense_categories ec ON e.category_id = ec.id
        ORDER BY e.expense_date DESC, e.id DESC
    """, ttl=0)
    return df.values.tolist()


def add_expense(category_id, building, description, amount, expense_date, vendor="", notes=""):
    conn = get_connection()
    with conn.session as session:
        session.execute(text("""
            INSERT INTO expenses (category_id, building, description, amount, expense_date, vendor, notes)
            VALUES (:ci, :b, :d, :a, :ed, :v, :n)
        """), {"ci": category_id, "b": building, "d": description, "a": amount,
               "ed": expense_date, "v": vendor, "n": notes})
        session.commit()
        clear_all_cache()


@st.cache_data(ttl=CACHE_TTL)
def get_total_expenses():
    conn = get_connection()
    df = conn.query("SELECT COALESCE(SUM(amount), 0) as total FROM expenses", ttl=0)
    return df.iloc[0]["total"]


@st.cache_data(ttl=CACHE_TTL)
def get_expenses_by_building():
    conn = get_connection()
    df = conn.query("""
        SELECT building, SUM(amount), COUNT(*) FROM expenses
        WHERE building IS NOT NULL AND building != ''
        GROUP BY building ORDER BY building
    """, ttl=0)
    return df.values.tolist()


@st.cache_data(ttl=CACHE_TTL)
def get_expenses_by_category():
    conn = get_connection()
    df = conn.query("""
        SELECT ec.name, SUM(e.amount), COUNT(*) FROM expenses e
        LEFT JOIN expense_categories ec ON e.category_id = ec.id
        GROUP BY ec.name ORDER BY SUM(e.amount) DESC
    """, ttl=0)
    return df.values.tolist()


@st.cache_data(ttl=CACHE_TTL)
def get_buildings_list():
    conn = get_connection()
    df = conn.query("""
        SELECT DISTINCT building FROM (
            SELECT building FROM units WHERE building IS NOT NULL AND building != ''
            UNION
            SELECT building FROM expenses WHERE building IS NOT NULL AND building != ''
        ) ORDER BY building
    """, ttl=0)
    return df["building"].tolist()


# ========== التقارير ==========
@st.cache_data(ttl=CACHE_TTL)
def report_sales_summary():
    conn = get_connection()
    df = conn.query("""
        SELECT COUNT(*), COALESCE(SUM(total_price), 0), COALESCE(SUM(down_payment), 0)
        FROM contracts
    """, ttl=0)
    count, total, down = df.iloc[0]
    return {"count": int(count), "total": float(total), "down": float(down),
            "remaining": float(total - down)}


@st.cache_data(ttl=CACHE_TTL)
def report_sales_by_building():
    conn = get_connection()
    df = conn.query("""
        SELECT u.building, COUNT(c.id), COALESCE(SUM(c.total_price), 0)
        FROM contracts c
        JOIN units u ON c.unit_id = u.id
        GROUP BY u.building ORDER BY u.building
    """, ttl=0)
    return df.values.tolist()


@st.cache_data(ttl=CACHE_TTL)
def report_units_status():
    conn = get_connection()
    df = conn.query("SELECT status, COUNT(*) FROM units GROUP BY status", ttl=0)
    return df.values.tolist()


@st.cache_data(ttl=CACHE_TTL)
def report_cashflow():
    conn = get_connection()
    df_in = conn.query("SELECT COALESCE(SUM(paid_amount), 0) as total FROM installments", ttl=0)
    cash_in = float(df_in.iloc[0]["total"])

    df_exp = conn.query("SELECT COALESCE(SUM(amount), 0) as total FROM expenses", ttl=0)
    expenses = float(df_exp.iloc[0]["total"])

    df_rep = conn.query("SELECT COALESCE(SUM(paid_amount), 0) as total FROM loan_payments", ttl=0)
    loan_repaid = float(df_rep.iloc[0]["total"])

    cash_out = expenses + loan_repaid
    return {
        "cash_in": cash_in, "expenses": expenses,
        "loan_repaid": loan_repaid, "cash_out": cash_out,
        "net": cash_in - cash_out
    }


@st.cache_data(ttl=CACHE_TTL)
def report_unit_profitability():
    conn = get_connection()
    df = conn.query("""
        SELECT u.id, u.unit_number, u.building, u.area, u.price, u.status,
               c.total_price as sale_price,
               COALESCE((SELECT SUM(amount) FROM expenses WHERE building = u.building), 0) as building_cost,
               COALESCE((SELECT COUNT(*) FROM units u2 WHERE u2.building = u.building), 1) as units_in_building
        FROM units u
        LEFT JOIN contracts c ON c.unit_id = u.id
        ORDER BY u.building, u.unit_number
    """, ttl=0)

    result = []
    for _, row in df.iterrows():
        building_cost = float(row["building_cost"]) if row["building_cost"] else 0
        units_count = int(row["units_in_building"]) if row["units_in_building"] else 1
        unit_cost = building_cost / units_count if units_count > 0 else 0
        sale_price = float(row["sale_price"]) if row["sale_price"] else 0
        profit = sale_price - unit_cost if sale_price else -unit_cost

        result.append({
            "unit_number": row["unit_number"], "building": row["building"],
            "area": row["area"], "price": row["price"], "status": row["status"],
            "sale_price": sale_price, "unit_cost": unit_cost, "profit": profit
        })
    return result


@st.cache_data(ttl=CACHE_TTL)
def report_monthly_collections():
    conn = get_connection()
    df = conn.query("""
        SELECT TO_CHAR(due_date, 'YYYY-MM'), COALESCE(SUM(amount), 0), COALESCE(SUM(paid_amount), 0)
        FROM installments GROUP BY TO_CHAR(due_date, 'YYYY-MM') ORDER BY 1
    """, ttl=0)
    return df.values.tolist()


@st.cache_data(ttl=CACHE_TTL)
def report_monthly_expenses():
    conn = get_connection()
    df = conn.query("""
        SELECT TO_CHAR(expense_date, 'YYYY-MM'), COALESCE(SUM(amount), 0)
        FROM expenses GROUP BY TO_CHAR(expense_date, 'YYYY-MM') ORDER BY 1
    """, ttl=0)
    return df.values.tolist()


# ========== المستخدمين ==========
@st.cache_data(ttl=CACHE_TTL)
def get_all_users():
    conn = get_connection()
    df = conn.query("SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id", ttl=0)
    return df.values.tolist()


def add_user(username, password, full_name, role):
    conn = get_connection()
    with conn.session as session:
        try:
            session.execute(text("""
                INSERT INTO users (username, password_hash, full_name, role, active, created_at)
                VALUES (:u, :p, :n, :r, 1, :d)
            """), {"u": username, "p": hash_password(password),
                   "n": full_name, "r": role, "d": str(date.today())})
            session.commit()
            clear_all_cache()
            return True
        except Exception:
            return False


def update_user(user_id, full_name, role, active):
    conn = get_connection()
    with conn.session as session:
        session.execute(text("UPDATE users SET full_name=:n, role=:r, active=:a WHERE id=:id"),
                        {"n": full_name, "r": role, "a": active, "id": user_id})
        session.commit()
        clear_all_cache()


def change_password(user_id, new_password):
    conn = get_connection()
    with conn.session as session:
        session.execute(text("UPDATE users SET password_hash=:p WHERE id=:id"),
                        {"p": hash_password(new_password), "id": user_id})
        session.commit()
        clear_all_cache()


def delete_user(user_id):
    conn = get_connection()
    with conn.session as session:
        result = session.execute(text("SELECT username FROM users WHERE id = :id"),
                                 {"id": user_id})
        row = result.fetchone()
        if not row or row[0] == "admin":
            return False
        session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        session.commit()
        clear_all_cache()
        return True
  def export_full_data():
    """تصدير كل البيانات في dictionary"""
    conn = get_connection()
    data = {}
    tables = {
        "units": "SELECT * FROM units",
        "customers": "SELECT * FROM customers",
        "contracts": "SELECT * FROM contracts",
        "installments": "SELECT * FROM installments",
        "loans": "SELECT * FROM loans",
        "loan_payments": "SELECT * FROM loan_payments",
        "expenses": "SELECT * FROM expenses",
        "users": "SELECT id, username, full_name, role, active, created_at FROM users",
    }
    for name, query in tables.items():
        df = conn.query(query, ttl=0)
        data[name] = {"columns": df.columns.tolist(), "rows": df.values.tolist()}
    return data