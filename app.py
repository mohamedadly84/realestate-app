import streamlit as st
import pandas as pd
import os
import io
import qrcode
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from database import (
    create_tables,
    authenticate_user, get_all_users, add_user, update_user, change_password, delete_user,
    add_unit, get_all_units, update_unit_status, update_unit, delete_unit,
    unit_has_contract, get_unit_by_id,
    add_customer, get_all_customers, update_customer, delete_customer,
    customer_has_contract, get_customer_by_id,
    add_contract, add_installment, get_all_contracts, get_installments_by_contract,
    get_contract_full_details,
    pay_installment, get_total_collected, get_total_due, get_overdue_installments,
    add_loan, add_loan_payment, get_all_loans, get_loan_payments,
    pay_loan_payment, get_total_debt, get_total_borrowed, get_total_repaid,
    get_upcoming_loan_payments,
    get_all_categories, add_expense, get_all_expenses,
    get_total_expenses, get_expenses_by_building, get_expenses_by_category,
    get_buildings_list,
    report_sales_summary, report_sales_by_building, report_units_status,
    report_cashflow, report_unit_profitability,
    report_monthly_collections, report_monthly_expenses,
    export_full_data
)
from pdf_utils import generate_contract_pdf, generate_receipt_pdf, generate_summary_pdf

create_tables()

st.set_page_config(
    page_title="برنامج المحاسبة العقارية",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================== CSS للموبايل ==================
st.markdown("""
<style>
    /* تحسينات عامة */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }
    
    /* تبويبات أوضح */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        flex-wrap: wrap;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        padding: 0 12px;
        font-size: 14px;
    }
    
    /* متريكس أوضح */
    [data-testid="stMetricValue"] {
        font-size: 22px;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 13px;
    }
    
    /* أزرار */
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
    }
    
    /* للشاشات الصغيرة */
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab"] {
            font-size: 12px;
            padding: 0 8px;
            height: 40px;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 18px;
        }
        
        h1 {
            font-size: 22px !important;
        }
        
        h2 {
            font-size: 18px !important;
        }
        
        h3 {
            font-size: 16px !important;
        }
    }
    
    /* input boxes */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div {
        font-size: 15px;
    }
</style>
""", unsafe_allow_html=True)


# ================== تسجيل الدخول ==================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🔐 برنامج المحاسبة العقارية")
    st.write("من فضلك سجّل الدخول")

    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("اسم المستخدم", key="login_username")
    with col2:
        password = st.text_input("كلمة السر", type="password", key="login_pwd")

    if st.button("دخول", type="primary", use_container_width=True):
        user = authenticate_user(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("❌ اسم المستخدم أو كلمة السر غير صحيحة")
    st.stop()


user = st.session_state.user
role = user["role"]

PERMISSIONS = {
    "admin": {
        "view_units": True, "edit_units": True,
        "view_customers": True, "edit_customers": True,
        "view_sales": True, "edit_sales": True,
        "view_collection": True, "edit_collection": True,
        "view_loans": True, "edit_loans": True,
        "view_expenses": True, "edit_expenses": True,
        "view_reports": True, "view_settings": True, "view_users": True,
    },
    "accountant": {
        "view_units": True, "edit_units": False,
        "view_customers": True, "edit_customers": False,
        "view_sales": True, "edit_sales": False,
        "view_collection": True, "edit_collection": True,
        "view_loans": True, "edit_loans": True,
        "view_expenses": True, "edit_expenses": True,
        "view_reports": True, "view_settings": False, "view_users": False,
    },
    "sales": {
        "view_units": True, "edit_units": False,
        "view_customers": True, "edit_customers": True,
        "view_sales": True, "edit_sales": True,
        "view_collection": False, "edit_collection": False,
        "view_loans": False, "edit_loans": False,
        "view_expenses": False, "edit_expenses": False,
        "view_reports": False, "view_settings": False, "view_users": False,
    },
}

perm = PERMISSIONS.get(role, PERMISSIONS["sales"])


# ================== دوال مساعدة ==================
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="البيانات")
    return output.getvalue()


def to_excel_multi(data_dict):
    """تصدير كل البيانات في Excel بأوراق متعددة"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, data in data_dict.items():
            df = pd.DataFrame(data["rows"], columns=data["columns"])
            df.to_excel(writer, index=False, sheet_name=name[:31])  # Excel حد أقصى 31 حرف
    return output.getvalue()


def excel_download_button(df, filename, key):
    if not df.empty:
        st.download_button(
            label="📥 Excel",
            data=to_excel(df),
            file_name=f"{filename}_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=key
        )


def make_qr(data):
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ================== الهيدر ==================
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🏢 برنامج المحاسبة العقارية")
with col2:
    st.write("")
    role_names = {"admin": "🔴 مدير", "accountant": "🟡 محاسب", "sales": "🟢 مبيعات"}
    st.success(f"👤 {user['full_name'] or user['username']}")
    st.caption(role_names.get(role, role))
    if st.button("🚪 خروج", use_container_width=True):
        st.session_state.user = None
        st.rerun()


# ================== التبويبات ==================
tabs_list = []
if perm["view_units"]:
    tabs_list.append("🏠 الرئيسية")
    tabs_list.append("🏢 الوحدات")
if perm["view_customers"]:
    tabs_list.append("👥 العملاء")
if perm["view_sales"]:
    tabs_list.append("💰 البيع")
if perm["view_collection"]:
    tabs_list.append("💵 التحصيل")
if perm["view_loans"]:
    tabs_list.append("🏦 القروض")
if perm["view_expenses"]:
    tabs_list.append("🧾 المصروفات")
if perm["view_reports"]:
    tabs_list.append("📊 التقارير")
if perm["view_users"]:
    tabs_list.append("👤 المستخدمون")
if perm["view_settings"]:
    tabs_list.append("⚙️ الإعدادات")

tabs = st.tabs(tabs_list)
tab_dict = dict(zip(tabs_list, tabs))


# ================== الرئيسية ==================
if "🏠 الرئيسية" in tab_dict:
    with tab_dict["🏠 الرئيسية"]:
        st.header("🏠 لوحة المعلومات")

        cf = report_cashflow()
        sales = report_sales_summary()
        total_borrowed = get_total_borrowed()
        total_debt = get_total_debt()
        total_expenses = get_total_expenses()
        total_collected = get_total_collected()
        total_due = get_total_due()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💵 التدفق النقدي", f"{cf['net']:,.0f} ج.م")
        c2.metric("📈 المبيعات", f"{sales['total']:,.0f} ج.م")
        c3.metric("💰 المحصّل", f"{total_collected:,.0f} ج.م")
        c4.metric("🏦 المديونية", f"{total_debt:,.0f} ج.م")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏢 العقود", sales["count"])
        c2.metric("⏳ متبقي على العملاء", f"{sales['remaining']:,.0f} ج.م")
        c3.metric("🧾 المصروفات", f"{total_expenses:,.0f} ج.م")
        c4.metric("🏦 المقترض", f"{total_borrowed:,.0f} ج.م")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏢 حالة الوحدات")
            us = report_units_status()
            if us:
                df_us = pd.DataFrame(us, columns=["الحالة", "العدد"])
                st.dataframe(df_us, use_container_width=True, hide_index=True)
                st.bar_chart(df_us.set_index("الحالة")["العدد"])

        with col2:
            st.subheader("⚠️ أقساط متأخرة")
            overdue = get_overdue_installments()
            if overdue:
                df_over = pd.DataFrame(overdue, columns=[
                    "ID", "الوحدة", "العميل", "التاريخ", "المبلغ", "المدفوع", "الحالة"
                ])
                st.dataframe(df_over.head(10), use_container_width=True, hide_index=True)
                st.caption(f"إجمالي {len(overdue)} قسط متأخر")
            else:
                st.success("✅ لا توجد أقساط متأخرة")

        st.divider()
        st.subheader("📅 أقساط قروض مستحقة خلال 30 يوم")
        upcoming = get_upcoming_loan_payments(30)
        if upcoming:
            df_up = pd.DataFrame(upcoming, columns=[
                "ID", "المُقرض", "التاريخ", "المبلغ", "المدفوع", "الحالة"
            ])
            st.dataframe(df_up, use_container_width=True, hide_index=True)
            total_up = sum(u[3] - u[4] for u in upcoming)
            st.warning(f"⚠️ المطلوب سداده: **{total_up:,.0f} ج.م** خلال 30 يوم")
        else:
            st.success("✅ لا توجد أقساط قروض قريبة")


# ================== الوحدات ==================
if "🏢 الوحدات" in tab_dict:
    with tab_dict["🏢 الوحدات"]:
        st.header("إدارة الوحدات")

        if perm["edit_units"]:
            with st.expander("➕ إضافة وحدة جديدة"):
                col1, col2 = st.columns(2)
                with col1:
                    unit_number = st.text_input("رقم الوحدة", key="unit_number")
                    floor = st.number_input("الدور", min_value=0, step=1, key="unit_floor")
                    area = st.number_input("المساحة (م²)", min_value=0.0, step=1.0, key="unit_area")
                with col2:
                    building = st.text_input("العمارة", key="unit_building")
                    price = st.number_input("السعر", min_value=0.0, step=10000.0, key="unit_price")

                if st.button("حفظ الوحدة", use_container_width=True):
                    if unit_number and building:
                        ok = add_unit(unit_number, building, int(floor), area, price)
                        if ok:
                            st.success(f"✅ تمت إضافة الوحدة {unit_number}")
                            st.rerun()
                        else:
                            st.error(f"❌ رقم الوحدة {unit_number} موجود بالفعل")

        st.subheader("📋 قائمة الوحدات")
        units = get_all_units()
        if units:
            df = pd.DataFrame(units, columns=[
                "ID", "رقم الوحدة", "العمارة", "الدور", "المساحة", "السعر", "الحالة"
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.write(f"**إجمالي الوحدات**: {len(units)}")
            excel_download_button(df, "units", "dl_units")

            if perm["edit_units"]:
                with st.expander("✏️ تعديل أو حذف وحدة"):
                    unit_options = {f"{u[1]} - عمارة {u[2]} (ID: {u[0]})": u[0] for u in units}
                    selected = st.selectbox("اختر وحدة", list(unit_options.keys()), key="edit_unit_select")
                    unit_id = unit_options[selected]
                    unit_data = get_unit_by_id(unit_id)

                    if unit_data:
                        col1, col2 = st.columns(2)
                        with col1:
                            new_number = st.text_input("رقم الوحدة", value=unit_data[1], key="edit_u_num")
                            new_floor = st.number_input("الدور", value=int(unit_data[3]), min_value=0, key="edit_u_floor")
                            new_area = st.number_input("المساحة", value=float(unit_data[4]), min_value=0.0, key="edit_u_area")
                        with col2:
                            new_building = st.text_input("العمارة", value=unit_data[2], key="edit_u_building")
                            new_price = st.number_input("السعر", value=float(unit_data[5]), min_value=0.0, key="edit_u_price")
                            new_status = st.selectbox(
                                "الحالة",
                                ["متاحة", "محجوزة", "مباعة", "مسلّمة"],
                                index=["متاحة", "محجوزة", "مباعة", "مسلّمة"].index(unit_data[6]) if unit_data[6] in ["متاحة", "محجوزة", "مباعة", "مسلّمة"] else 0,
                                key="edit_u_status"
                            )

                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("💾 حفظ", use_container_width=True, key="btn_update_unit"):
                                ok = update_unit(unit_id, new_number, new_building, int(new_floor), new_area, new_price, new_status)
                                if ok:
                                    st.success("✅ تم تحديث الوحدة")
                                    st.rerun()

                        with col_b:
                            if unit_has_contract(unit_id):
                                st.warning("⚠️ لا يمكن الحذف")
                            else:
                                if st.button("🗑️ حذف", use_container_width=True, key="btn_delete_unit"):
                                    if delete_unit(unit_id):
                                        st.success("✅ تم الحذف")
                                        st.rerun()

            with st.expander("🖨️ عرض الباركود"):
                unit_options_qr = {f"{u[1]} - عمارة {u[2]}": u for u in units}
                selected_qr = st.selectbox("اختر وحدة", list(unit_options_qr.keys()), key="qr_unit_select")
                u = unit_options_qr[selected_qr]

                qr_data = f"وحدة: {u[1]}\nالعمارة: {u[2]}\nالدور: {u[3]}\nالمساحة: {u[4]} م²\nالسعر: {u[5]:,.0f} ج.م"
                qr_img = make_qr(qr_data)

                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.image(qr_img, caption=f"QR الوحدة {u[1]}", use_container_width=True)
                    st.download_button("📥 تنزيل", data=qr_img,
                                       file_name=f"qr_{u[1]}.png", mime="image/png",
                                       key="dl_qr", use_container_width=True)
                with col_b:
                    st.write(f"**رقم الوحدة**: {u[1]}")
                    st.write(f"**العمارة**: {u[2]}")
                    st.write(f"**الدور**: {u[3]}")
                    st.write(f"**المساحة**: {u[4]} م²")
                    st.write(f"**السعر**: {u[5]:,.0f} ج.م")
                    st.write(f"**الحالة**: {u[6]}")


# ================== العملاء ==================
if "👥 العملاء" in tab_dict:
    with tab_dict["👥 العملاء"]:
        st.header("إدارة العملاء")

        if perm["edit_customers"]:
            with st.expander("➕ إضافة عميل"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("الاسم *", key="cust_name")
                    phone = st.text_input("الموبايل", key="cust_phone")
                    national_id = st.text_input("الرقم القومي", key="cust_nid")
                with col2:
                    address = st.text_input("العنوان", key="cust_address")
                    notes = st.text_area("ملاحظات", key="cust_notes")

                if st.button("حفظ العميل", use_container_width=True):
                    if name:
                        add_customer(name, phone, national_id, address, notes)
                        st.success(f"✅ تمت إضافة {name}")
                        st.rerun()

        st.subheader("📋 قائمة العملاء")
        customers = get_all_customers()
        if customers:
            df = pd.DataFrame(customers, columns=[
                "ID", "الاسم", "الموبايل", "الرقم القومي", "العنوان", "ملاحظات"
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.write(f"**إجمالي العملاء**: {len(customers)}")
            excel_download_button(df, "customers", "dl_customers")

            if perm["edit_customers"]:
                with st.expander("✏️ تعديل أو حذف"):
                    cust_options = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
                    selected = st.selectbox("اختر عميل", list(cust_options.keys()), key="edit_cust_select")
                    cust_id = cust_options[selected]
                    cust_data = get_customer_by_id(cust_id)

                    if cust_data:
                        col1, col2 = st.columns(2)
                        with col1:
                            new_name = st.text_input("الاسم", value=cust_data[1], key="edit_c_name")
                            new_phone = st.text_input("الموبايل", value=cust_data[2] or "", key="edit_c_phone")
                            new_nid = st.text_input("الرقم القومي", value=cust_data[3] or "", key="edit_c_nid")
                        with col2:
                            new_address = st.text_input("العنوان", value=cust_data[4] or "", key="edit_c_address")
                            new_notes = st.text_area("ملاحظات", value=cust_data[5] or "", key="edit_c_notes")

                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("💾 حفظ", use_container_width=True, key="btn_update_cust"):
                                if new_name:
                                    update_customer(cust_id, new_name, new_phone, new_nid, new_address, new_notes)
                                    st.success("✅ تم التحديث")
                                    st.rerun()
                        with col_b:
                            if customer_has_contract(cust_id):
                                st.warning("⚠️ لا يمكن الحذف")
                            else:
                                if st.button("🗑️ حذف", use_container_width=True, key="btn_delete_cust"):
                                    if delete_customer(cust_id):
                                        st.success("✅ تم الحذف")
                                        st.rerun()


# ================== البيع ==================
if "💰 البيع" in tab_dict:
    with tab_dict["💰 البيع"]:
        st.header("إدارة البيع")

        if perm["edit_sales"]:
            with st.expander("➕ عقد بيع جديد", expanded=True):
                customers = get_all_customers()
                all_units = get_all_units()
                available_units = [u for u in all_units if u[6] == "متاحة"]

                if not customers:
                    st.warning("⚠️ أضف عميل أولاً")
                elif not available_units:
                    st.warning("⚠️ لا توجد وحدات متاحة")
                else:
                    col1, col2 = st.columns(2)

                    with col1:
                        customer_options = {f"{c[1]} (ID: {c[0]})": c[0] for c in customers}
                        selected_customer = st.selectbox("العميل", list(customer_options.keys()))
                        customer_id = customer_options[selected_customer]

                        unit_options = {f"{u[1]} - عمارة {u[2]} - {u[4]}م² - {u[5]:,.0f}": u[0] for u in available_units}
                        selected_unit = st.selectbox("الوحدة", list(unit_options.keys()))
                        unit_id = unit_options[selected_unit]

                        selected_unit_data = next(u for u in available_units if u[0] == unit_id)
                        total_price = st.number_input("إجمالي السعر", min_value=0.0,
                                                      value=float(selected_unit_data[5]),
                                                      step=10000.0, key="sale_total_price")

                    with col2:
                        down_payment = st.number_input("المقدم", min_value=0.0, step=10000.0, key="sale_down")
                        contract_date = st.date_input("تاريخ العقد", value=date.today(), key="sale_date")
                        notes = st.text_area("ملاحظات", key="sale_notes")

                    st.markdown("---")
                    st.subheader("📅 جدولة الأقساط")
                    schedule_method = st.radio(
                        "الطريقة:",
                        ["تلقائي - شهري", "يدوي - تواريخ مخصصة"],
                        key="schedule_method", horizontal=True
                    )

                    remaining = total_price - down_payment
                    num_installments = 0
                    first_due = None
                    manual_dates = []

                    if remaining > 0:
                        st.info(f"💡 المتبقي: **{remaining:,.0f} ج.م**")

                        if schedule_method == "تلقائي - شهري":
                            col_a, col_b = st.columns(2)
                            with col_a:
                                first_due = st.date_input("تاريخ أول قسط",
                                                          value=contract_date + relativedelta(months=1),
                                                          key="first_due_date")
                            with col_b:
                                num_installments = st.number_input("عدد الأقساط", min_value=1, max_value=120,
                                                                  value=12, step=1, key="num_inst_auto")
                            monthly_amount = remaining / num_installments
                            st.success(f"📌 {int(num_installments)} قسط × {monthly_amount:,.2f} ج.م")
                        else:
                            num_manual = st.number_input("عدد الأقساط", min_value=1, max_value=120,
                                                         value=4, step=1, key="num_inst_manual")
                            for i in range(int(num_manual)):
                                d = st.date_input(f"تاريخ القسط {i+1}",
                                                  value=contract_date + relativedelta(months=(i+1)),
                                                  key=f"manual_date_{i}")
                                manual_dates.append(d)
                            manual_amount = remaining / num_manual
                            st.success(f"📌 {int(num_manual)} قسط × {manual_amount:,.2f} ج.م")

                    if st.button("💾 حفظ العقد", type="primary", use_container_width=True):
                        if down_payment > total_price:
                            st.error("❌ المقدم أكبر من الإجمالي")
                        else:
                            contract_id = add_contract(unit_id, customer_id, total_price,
                                                       down_payment, str(contract_date), notes)
                            update_unit_status(unit_id, "مباعة")
                            remaining = total_price - down_payment
                            if remaining > 0:
                                if schedule_method == "تلقائي - شهري":
                                    monthly_amount = remaining / num_installments
                                    for i in range(int(num_installments)):
                                        due = first_due + relativedelta(months=i)
                                        add_installment(contract_id, i+1, str(due), monthly_amount)
                                else:
                                    manual_amount = remaining / len(manual_dates)
                                    for i, d in enumerate(manual_dates):
                                        add_installment(contract_id, i+1, str(d), manual_amount)
                            st.success(f"✅ عقد رقم {contract_id}")
                            st.rerun()

        st.subheader("📋 قائمة العقود")
        contracts = get_all_contracts()
        if contracts:
            df = pd.DataFrame(contracts, columns=["ID", "الوحدة", "العميل", "الإجمالي", "المقدم", "التاريخ"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            excel_download_button(df, "contracts", "dl_contracts")

            st.subheader("📄 طباعة عقد PDF")
            contract_options = {f"عقد {c[0]} - {c[2]} - وحدة {c[1]}": c[0] for c in contracts}
            selected_contract = st.selectbox("اختر عقد", list(contract_options.keys()), key="pdf_contract")
            pdf_contract_id = contract_options[selected_contract]

            contract_details = get_contract_full_details(pdf_contract_id)
            if contract_details:
                installments_data = get_installments_by_contract(pdf_contract_id)
                if st.button("📄 توليد العقد PDF", use_container_width=True):
                    try:
                        pdf_bytes = generate_contract_pdf(contract_details, installments_data)
                        st.download_button("📥 تنزيل PDF", data=pdf_bytes,
                                           file_name=f"contract_{pdf_contract_id}.pdf",
                                           mime="application/pdf",
                                           key="dl_contract_pdf", use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ خطأ: {str(e)}")


# ================== التحصيل ==================
if "💵 التحصيل" in tab_dict:
    with tab_dict["💵 التحصيل"]:
        st.header("التحصيل")

        col1, col2, col3 = st.columns(3)
        tc = get_total_collected()
        td = get_total_due()
        col1.metric("المتوقع", f"{tc+td:,.0f} ج.م")
        col2.metric("المحصّل", f"{tc:,.0f} ج.م")
        col3.metric("المتبقي", f"{td:,.0f} ج.م")

        st.divider()

        overdue = get_overdue_installments()
        if overdue:
            st.subheader("⚠️ أقساط متأخرة")
            df_over = pd.DataFrame(overdue, columns=["ID", "الوحدة", "العميل", "التاريخ", "المبلغ", "المدفوع", "الحالة"])
            st.dataframe(df_over, use_container_width=True, hide_index=True)

        st.subheader("💵 تسجيل دفعة")
        contracts = get_all_contracts()
        if contracts and perm["edit_collection"]:
            contract_options = {f"عقد {c[0]} - {c[2]} - وحدة {c[1]}": c[0] for c in contracts}
            selected_contract = st.selectbox("اختر العقد", list(contract_options.keys()), key="collect_contract")
            contract_id = contract_options[selected_contract]

            installments = get_installments_by_contract(contract_id)
            if installments:
                unpaid = [i for i in installments if i[5] != "مدفوع"]
                if unpaid:
                    installment_options = {}
                    for i in unpaid:
                        label = f"قسط {i[1]} - استحقاق {i[2]} - مطلوب: {i[3]:,.0f} - مدفوع: {i[4]:,.0f} - {i[5]}"
                        installment_options[label] = i

                    selected_inst = st.selectbox("اختر القسط", list(installment_options.keys()), key="collect_inst")
                    inst_data = installment_options[selected_inst]
                    inst_id = inst_data[0]
                    inst_remaining = inst_data[3] - inst_data[4]

                    col_a, col_b = st.columns(2)
                    with col_a:
                        pay_amount = st.number_input("المبلغ", min_value=0.0,
                                                     max_value=float(inst_remaining),
                                                     value=float(inst_remaining),
                                                     step=1000.0, key="collect_amount")
                    with col_b:
                        st.write("")
                        if st.button("✅ تسجيل الدفعة", use_container_width=True):
                            if pay_amount > 0:
                                pay_installment(inst_id, pay_amount)
                                st.success(f"✅ تم تسجيل {pay_amount:,.0f} ج.م")
                                st.rerun()

                    if st.button("📄 توليد إيصال PDF", use_container_width=True):
                        try:
                            contract_details = get_contract_full_details(contract_id)
                            installments_updated = get_installments_by_contract(contract_id)
                            current_inst = next((x for x in installments_updated if x[0] == inst_id), inst_data)
                            pdf_bytes = generate_receipt_pdf(contract_details, current_inst)
                            st.download_button("📥 تنزيل الإيصال", data=pdf_bytes,
                                               file_name=f"receipt_{contract_id}_{current_inst[1]}.pdf",
                                               mime="application/pdf",
                                               key="dl_receipt", use_container_width=True)
                        except Exception as e:
                            st.error(f"❌ خطأ: {str(e)}")
                else:
                    st.success("✅ كل الأقساط مدفوعة")


# ================== القروض ==================
if "🏦 القروض" in tab_dict:
    with tab_dict["🏦 القروض"]:
        st.header("إدارة القروض")

        c1, c2, c3 = st.columns(3)
        c1.metric("المقترض", f"{get_total_borrowed():,.0f} ج.م")
        c2.metric("المسدد", f"{get_total_repaid():,.0f} ج.م")
        c3.metric("المديونية", f"{get_total_debt():,.0f} ج.م")

        st.divider()

        if perm["edit_loans"]:
            with st.expander("➕ إضافة قرض جديد"):
                col1, col2 = st.columns(2)
                with col1:
                    lender_name = st.text_input("اسم المُقرض", key="loan_lender")
                    lender_type = st.selectbox("النوع", ["فرد", "بنك", "شركة", "أخرى"], key="loan_type")
                    amount = st.number_input("المبلغ", min_value=0.0, step=10000.0, key="loan_amount")
                with col2:
                    interest_rate = st.number_input("الفائدة %", min_value=0.0, max_value=100.0, key="loan_interest")
                    start_date = st.date_input("تاريخ القرض", value=date.today(), key="loan_date")
                    num_payments = st.number_input("عدد الأقساط", min_value=1, value=12, key="loan_num")

                notes = st.text_area("ملاحظات", key="loan_notes")

                if st.button("💾 حفظ القرض", use_container_width=True):
                    if lender_name and amount > 0:
                        loan_id = add_loan(lender_name, lender_type, amount,
                                           interest_rate, str(start_date), notes)
                        monthly = amount / num_payments
                        for i in range(int(num_payments)):
                            due = start_date + relativedelta(months=i+1)
                            add_loan_payment(loan_id, i+1, str(due), monthly)
                        st.success(f"✅ قرض رقم {loan_id}")
                        st.rerun()

        st.subheader("📋 قائمة القروض")
        loans = get_all_loans()
        if loans:
            df_loans = pd.DataFrame(loans, columns=["ID", "المُقرض", "النوع", "المبلغ", "الفائدة %", "التاريخ", "ملاحظات", "الحالة"])
            st.dataframe(df_loans, use_container_width=True, hide_index=True)

            if perm["edit_loans"]:
                st.subheader("💸 سداد قرض")
                loan_options = {f"قرض {l[0]} - {l[1]} - {l[3]:,.0f}": l[0] for l in loans}
                selected_loan = st.selectbox("اختر القرض", list(loan_options.keys()), key="pay_loan_select")
                loan_id = loan_options[selected_loan]

                payments = get_loan_payments(loan_id)
                if payments:
                    unpaid_payments = [p for p in payments if p[5] != "مدفوع"]
                    if unpaid_payments:
                        payment_options = {}
                        for p in unpaid_payments:
                            label = f"قسط {p[1]} - استحقاق {p[2]} - مطلوب: {p[3]:,.0f} - {p[5]}"
                            payment_options[label] = p

                        selected_pay = st.selectbox("اختر القسط", list(payment_options.keys()), key="pay_loan_inst")
                        pay_data = payment_options[selected_pay]
                        pay_id = pay_data[0]
                        pay_remaining = pay_data[3] - pay_data[4]

                        col_a, col_b = st.columns(2)
                        with col_a:
                            pay_amount = st.number_input("المبلغ", min_value=0.0,
                                                         max_value=float(pay_remaining),
                                                         value=float(pay_remaining),
                                                         key="pay_loan_amount")
                        with col_b:
                            st.write("")
                            if st.button("✅ تسجيل السداد", use_container_width=True):
                                if pay_amount > 0:
                                    pay_loan_payment(pay_id, pay_amount)
                                    st.success(f"✅ تم تسجيل {pay_amount:,.0f} ج.م")
                                    st.rerun()
                    else:
                        st.success("✅ القرض مسدد")


# ================== المصروفات ==================
if "🧾 المصروفات" in tab_dict:
    with tab_dict["🧾 المصروفات"]:
        st.header("المصروفات")
        st.metric("إجمالي المصروفات", f"{get_total_expenses():,.0f} ج.م")
        st.divider()

        if perm["edit_expenses"]:
            with st.expander("➕ إضافة مصروف"):
                categories = get_all_categories()
                buildings = get_buildings_list()

                col1, col2 = st.columns(2)
                with col1:
                    category_options = {c[1]: c[0] for c in categories}
                    selected_cat = st.selectbox("البند", list(category_options.keys()), key="exp_cat")
                    category_id = category_options[selected_cat]

                    if buildings:
                        building = st.selectbox("العمارة", buildings, key="exp_building")
                    else:
                        building = st.text_input("العمارة", key="exp_building_text")

                    description = st.text_input("الوصف", key="exp_desc")

                with col2:
                    amount = st.number_input("المبلغ", min_value=0.0, step=1000.0, key="exp_amount")
                    expense_date = st.date_input("التاريخ", value=date.today(), key="exp_date")
                    vendor = st.text_input("المورد", key="exp_vendor")

                notes = st.text_area("ملاحظات", key="exp_notes")

                if st.button("💾 حفظ المصروف", use_container_width=True):
                    if amount > 0 and description:
                        add_expense(category_id, building, description, amount, str(expense_date), vendor, notes)
                        st.success(f"✅ {amount:,.0f} ج.م")
                        st.rerun()

        st.subheader("📊 حسب العمارة")
        bb = get_expenses_by_building()
        if bb:
            df_b = pd.DataFrame(bb, columns=["العمارة", "الإجمالي", "عدد"])
            st.dataframe(df_b, use_container_width=True, hide_index=True)
            st.bar_chart(df_b.set_index("العمارة")["الإجمالي"])

        st.subheader("📋 كل المصروفات")
        expenses = get_all_expenses()
        if expenses:
            df_exp = pd.DataFrame(expenses, columns=["ID", "البند", "العمارة", "الوصف", "المبلغ", "التاريخ", "المورد"])
            st.dataframe(df_exp, use_container_width=True, hide_index=True)
            excel_download_button(df_exp, "expenses", "dl_expenses")


# ================== التقارير ==================
if "📊 التقارير" in tab_dict:
    with tab_dict["📊 التقارير"]:
        st.header("📊 التقارير")

        cf = report_cashflow()
        sales = report_sales_summary()
        total_expenses = get_total_expenses()
        total_collected = get_total_collected()
        total_due = get_total_due()
        total_borrowed = get_total_borrowed()
        total_debt = get_total_debt()
        units_status = report_units_status()
        overdue = get_overdue_installments()

        # زر التقرير الشامل
        if st.button("📄 توليد تقرير شامل PDF", type="primary", use_container_width=True):
            try:
                pdf_bytes = generate_summary_pdf(
                    cf, sales, total_expenses, total_collected,
                    total_due, total_borrowed, total_debt,
                    units_status, overdue
                )
                st.download_button(
                    "📥 تنزيل التقرير الشامل",
                    data=pdf_bytes,
                    file_name=f"summary_report_{date.today()}.pdf",
                    mime="application/pdf",
                    key="dl_summary_pdf",
                    use_container_width=True
                )
                st.success("✅ تم توليد التقرير!")
            except Exception as e:
                st.error(f"❌ خطأ: {str(e)}")

        st.divider()

        st.subheader("💵 التدفق النقدي")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("تدفق داخل", f"{cf['cash_in']:,.0f} ج.م")
        c2.metric("مصروفات", f"{cf['expenses']:,.0f} ج.م")
        c3.metric("سداد قروض", f"{cf['loan_repaid']:,.0f} ج.م")
        c4.metric("الصافي", f"{cf['net']:,.0f} ج.م")

        st.divider()
        st.subheader("💰 المبيعات")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("عدد العقود", sales["count"])
        c2.metric("الإجمالي", f"{sales['total']:,.0f} ج.م")
        c3.metric("المقدم", f"{sales['down']:,.0f} ج.م")
        c4.metric("المتبقي", f"{sales['remaining']:,.0f} ج.م")

        st.divider()
        st.subheader("🎯 ربحية الوحدة")
        profit_data = report_unit_profitability()
        if profit_data:
            df_p = pd.DataFrame(profit_data)
            df_p.columns = ["الوحدة", "العمارة", "المساحة", "المعروض", "الحالة", "سعر البيع", "التكلفة", "الربح"]
            st.dataframe(df_p, use_container_width=True, hide_index=True)
            excel_download_button(df_p, "unit_profitability", "dl_profit")


# ================== المستخدمون ==================
if "👤 المستخدمون" in tab_dict:
    with tab_dict["👤 المستخدمون"]:
        st.header("👤 إدارة المستخدمين")

        with st.expander("➕ إضافة مستخدم"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("اسم المستخدم", key="new_username")
                new_fullname = st.text_input("الاسم الكامل", key="new_fullname")
            with col2:
                new_password = st.text_input("كلمة السر", type="password", key="new_password")
                new_role = st.selectbox("الدور", ["sales", "accountant", "admin"], key="new_role")

            if st.button("💾 إضافة", use_container_width=True):
                if new_username and new_password:
                    if add_user(new_username, new_password, new_fullname, new_role):
                        st.success(f"✅ تم إضافة {new_username}")
                        st.rerun()
                    else:
                        st.error("❌ اسم المستخدم موجود")

        st.subheader("📋 المستخدمون")
        users = get_all_users()
        if users:
            role_names = {"admin": "🔴 مدير", "accountant": "🟡 محاسب", "sales": "🟢 مبيعات"}
            df_users = pd.DataFrame(users, columns=["ID", "اسم المستخدم", "الاسم الكامل", "الدور", "نشط", "تاريخ الإنشاء"])
            df_users["الدور"] = df_users["الدور"].map(role_names)
            df_users["نشط"] = df_users["نشط"].map({1: "✅", 0: "❌"})
            st.dataframe(df_users, use_container_width=True, hide_index=True)

            user_options = {f"{u[1]} ({u[2] or '-'})": u for u in users if u[1] != "admin"}
            if user_options:
                st.subheader("✏️ تعديل")
                selected_user = st.selectbox("اختر مستخدم", list(user_options.keys()), key="edit_user_select")
                u = user_options[selected_user]
                user_id = u[0]

                col1, col2 = st.columns(2)
                with col1:
                    edit_fullname = st.text_input("الاسم الكامل", value=u[2] or "", key="edit_user_fullname")
                    edit_role = st.selectbox("الدور", ["sales", "accountant", "admin"],
                                             index=["sales", "accountant", "admin"].index(u[3]) if u[3] in ["sales", "accountant", "admin"] else 0,
                                             key="edit_user_role")
                with col2:
                    edit_active = st.checkbox("نشط", value=(u[4] == 1), key="edit_user_active")
                    new_pass = st.text_input("كلمة سر جديدة", type="password", key="edit_user_pass")

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 حفظ", use_container_width=True):
                        update_user(user_id, edit_fullname, edit_role, 1 if edit_active else 0)
                        if new_pass:
                            change_password(user_id, new_pass)
                        st.success("✅ تم التحديث")
                        st.rerun()
                with col_b:
                    if st.button("🗑️ حذف", use_container_width=True):
                        if delete_user(user_id):
                            st.success("✅ تم الحذف")
                            st.rerun()


# ================== الإعدادات ==================
if "⚙️ الإعدادات" in tab_dict:
    with tab_dict["⚙️ الإعدادات"]:
        st.header("⚙️ الإعدادات")

        st.subheader("📊 تصدير كامل")
        st.write("تصدير كل البيانات في ملف Excel واحد بأوراق متعددة")
        if st.button("📥 توليد ملف Excel كامل", use_container_width=True):
            try:
                data = export_full_data()
                excel_bytes = to_excel_multi(data)
                st.download_button(
                    "📥 تنزيل الملف",
                    data=excel_bytes,
                    file_name=f"full_export_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_full_export",
                    use_container_width=True
                )
                st.success("✅ تم توليد الملف!")
            except Exception as e:
                st.error(f"❌ خطأ: {str(e)}")

        st.divider()

        st.subheader("💾 النسخ الاحتياطي")
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists("realestate.db"):
                with open("realestate.db", "rb") as f:
                    db_bytes = f.read()
                st.download_button(
                    "📥 تنزيل قاعدة البيانات",
                    data=db_bytes,
                    file_name=f"realestate_backup_{date.today()}.db",
                    mime="application/octet-stream",
                    use_container_width=True
                )
        with col2:
            uploaded = st.file_uploader("⬆️ استرجاع نسخة", type=["db"], key="backup_uploader")
            if uploaded is not None:
                if st.button("🔄 استرجاع", type="primary", use_container_width=True):
                    if os.path.exists("realestate.db"):
                        os.rename("realestate.db", f"realestate_before_restore_{date.today()}.db")
                    with open("realestate.db", "wb") as f:
                        f.write(uploaded.read())
                    st.success("✅ تم الاسترجاع! حدّث الصفحة")