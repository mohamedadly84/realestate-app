"""أدوات توليد PDF بالعربي"""
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import os

FONT_FILE = "arial.ttf"


def ar(text):
    if text is None:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except:
        return str(text)


class ArabicPDF(FPDF):
    def __init__(self):
        super().__init__()
        if not os.path.exists(FONT_FILE):
            raise FileNotFoundError(f"❌ ملف الخط '{FONT_FILE}' غير موجود!")
        self.add_font("ArabicFont", "", FONT_FILE, uni=True)
        self.set_font("ArabicFont", size=12)

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("ArabicFont", size=8)
        self.cell(0, 10, ar(f"صفحة {self.page_no()}"), align="C")


def generate_contract_pdf(contract_data, installments_data):
    pdf = ArabicPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("ArabicFont", size=18)
    pdf.cell(0, 12, ar("عقد بيع وحدة سكنية"), align="C", ln=True)
    pdf.ln(5)

    c = contract_data

    pdf.set_font("ArabicFont", size=13)
    pdf.cell(0, 8, ar("بيانات العقد"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"رقم العقد: {c[0]}"), ln=True)
    pdf.cell(0, 7, ar(f"تاريخ العقد: {c[3]}"), ln=True)
    pdf.ln(3)

    pdf.set_font("ArabicFont", size=13)
    pdf.cell(0, 8, ar("بيانات العميل"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"الاسم: {c[10]}"), ln=True)
    pdf.cell(0, 7, ar(f"الموبايل: {c[11] or '-'}"), ln=True)
    pdf.cell(0, 7, ar(f"الرقم القومي: {c[12] or '-'}"), ln=True)
    pdf.cell(0, 7, ar(f"العنوان: {c[13] or '-'}"), ln=True)
    pdf.ln(3)

    pdf.set_font("ArabicFont", size=13)
    pdf.cell(0, 8, ar("بيانات الوحدة"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"رقم الوحدة: {c[5]}"), ln=True)
    pdf.cell(0, 7, ar(f"العمارة: {c[6]}"), ln=True)
    pdf.cell(0, 7, ar(f"الدور: {c[7]}"), ln=True)
    pdf.cell(0, 7, ar(f"المساحة: {c[8]} م²"), ln=True)
    pdf.ln(3)

    pdf.set_font("ArabicFont", size=13)
    pdf.cell(0, 8, ar("الشروط المالية"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"إجمالي السعر: {c[1]:,.0f} ج.م"), ln=True)
    pdf.cell(0, 7, ar(f"المقدم: {c[2]:,.0f} ج.م"), ln=True)
    pdf.cell(0, 7, ar(f"المتبقي: {c[1]-c[2]:,.0f} ج.م"), ln=True)
    pdf.ln(3)

    if installments_data:
        pdf.set_font("ArabicFont", size=13)
        pdf.cell(0, 8, ar("جدول الأقساط"), ln=True)
        pdf.set_font("ArabicFont", size=10)
        pdf.cell(20, 8, ar("رقم"), border=1, align="C")
        pdf.cell(45, 8, ar("تاريخ الاستحقاق"), border=1, align="C")
        pdf.cell(45, 8, ar("المبلغ"), border=1, align="C")
        pdf.cell(45, 8, ar("الحالة"), border=1, align="C", ln=True)

        for inst in installments_data:
            pdf.cell(20, 7, ar(str(inst[1])), border=1, align="C")
            pdf.cell(45, 7, ar(inst[2]), border=1, align="C")
            pdf.cell(45, 7, ar(f"{inst[3]:,.0f}"), border=1, align="C")
            pdf.cell(45, 7, ar(inst[5]), border=1, align="C", ln=True)

    pdf.ln(10)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(90, 8, ar("توقيع البائع: ____________________"), align="C")
    pdf.cell(90, 8, ar("توقيع المشتري: ____________________"), align="C")

    return bytes(pdf.output())


def generate_receipt_pdf(contract_data, installment_data):
    pdf = ArabicPDF()
    pdf.add_page()

    c = contract_data
    inst = installment_data

    pdf.set_font("ArabicFont", size=20)
    pdf.cell(0, 15, ar("إيصال استلام"), align="C", ln=True)
    pdf.ln(10)

    pdf.set_font("ArabicFont", size=13)
    pdf.cell(0, 10, ar(f"رقم العقد: {c[0]}"), ln=True)
    pdf.cell(0, 10, ar(f"التاريخ: {inst[2]}"), ln=True)
    pdf.ln(5)

    pdf.set_font("ArabicFont", size=14)
    pdf.cell(0, 10, ar(f"استلمنا من السيد/ة: {c[10]}"), ln=True)
    pdf.ln(3)

    pdf.set_font("ArabicFont", size=13)
    pdf.cell(0, 10, ar(f"مبلغ وقدره: {inst[4]:,.0f} ج.م"), ln=True)
    pdf.cell(0, 10, ar(f"وذلك عن: القسط رقم {inst[1]}"), ln=True)
    pdf.cell(0, 10, ar(f"الوحدة رقم: {c[5]} - عمارة {c[6]}"), ln=True)
    pdf.ln(10)

    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 10, ar("التوقيع: ____________________"), ln=True, align="R")

    return bytes(pdf.output())


def generate_summary_pdf(cashflow, sales, total_expenses, total_collected,
                          total_due, total_borrowed, total_debt,
                          units_status, top_overdue):
    """تقرير ملخص شامل"""
    pdf = ArabicPDF()
    pdf.add_page()

    pdf.set_font("ArabicFont", size=20)
    pdf.cell(0, 15, ar("التقرير المالي الشامل"), align="C", ln=True)
    pdf.ln(5)

    from datetime import date as dt
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 8, ar(f"تاريخ التقرير: {dt.today()}"), align="C", ln=True)
    pdf.ln(8)

    # التدفق النقدي
    pdf.set_font("ArabicFont", size=14)
    pdf.cell(0, 10, ar("💵 التدفق النقدي"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"التدفق الداخل (تحصيلات): {cashflow['cash_in']:,.0f} ج.م"), ln=True)
    pdf.cell(0, 7, ar(f"المصروفات: {cashflow['expenses']:,.0f} ج.م"), ln=True)
    pdf.cell(0, 7, ar(f"سداد القروض: {cashflow['loan_repaid']:,.0f} ج.م"), ln=True)
    pdf.set_font("ArabicFont", size=12)
    pdf.cell(0, 8, ar(f"الصافي: {cashflow['net']:,.0f} ج.م"), ln=True)
    pdf.ln(5)

    # المبيعات
    pdf.set_font("ArabicFont", size=14)
    pdf.cell(0, 10, ar("💰 المبيعات"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"عدد العقود: {sales['count']}"), ln=True)
    pdf.cell(0, 7, ar(f"إجمالي المبيعات: {sales['total']:,.0f} ج.م"), ln=True)
    pdf.cell(0, 7, ar(f"إجمالي المقدم: {sales['down']:,.0f} ج.م"), ln=True)
    pdf.cell(0, 7, ar(f"المتبقي على العملاء: {sales['remaining']:,.0f} ج.م"), ln=True)
    pdf.ln(5)

    # التحصيلات
    pdf.set_font("ArabicFont", size=14)
    pdf.cell(0, 10, ar("💵 التحصيلات"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"إجمالي المحصّل: {total_collected:,.0f} ج.م"), ln=True)
    pdf.cell(0, 7, ar(f"إجمالي المتبقي: {total_due:,.0f} ج.م"), ln=True)
    pdf.ln(5)

    # القروض
    pdf.set_font("ArabicFont", size=14)
    pdf.cell(0, 10, ar("🏦 القروض"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"إجمالي المقترض: {total_borrowed:,.0f} ج.م"), ln=True)
    pdf.cell(0, 7, ar(f"المديونية المتبقية: {total_debt:,.0f} ج.م"), ln=True)
    pdf.ln(5)

    # المصروفات
    pdf.set_font("ArabicFont", size=14)
    pdf.cell(0, 10, ar("🧾 المصروفات"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    pdf.cell(0, 7, ar(f"إجمالي المصروفات: {total_expenses:,.0f} ج.م"), ln=True)
    pdf.ln(5)

    # حالة الوحدات
    pdf.set_font("ArabicFont", size=14)
    pdf.cell(0, 10, ar("🏢 حالة الوحدات"), ln=True)
    pdf.set_font("ArabicFont", size=11)
    for status, count in units_status:
        pdf.cell(0, 7, ar(f"{status}: {count}"), ln=True)
    pdf.ln(5)

    # أقساط متأخرة
    if top_overdue:
        pdf.add_page()
        pdf.set_font("ArabicFont", size=14)
        pdf.cell(0, 10, ar(f"⚠️ أقساط متأخرة ({len(top_overdue)})"), ln=True)
        pdf.set_font("ArabicFont", size=9)
        pdf.cell(15, 8, ar("ID"), border=1, align="C")
        pdf.cell(30, 8, ar("الوحدة"), border=1, align="C")
        pdf.cell(50, 8, ar("العميل"), border=1, align="C")
        pdf.cell(35, 8, ar("التاريخ"), border=1, align="C")
        pdf.cell(35, 8, ar("المبلغ"), border=1, align="C", ln=True)

        for o in top_overdue[:50]:  # أول 50 بس
            pdf.cell(15, 7, ar(str(o[0])), border=1, align="C")
            pdf.cell(30, 7, ar(o[1]), border=1, align="C")
            pdf.cell(50, 7, ar(o[2][:25]), border=1, align="C")
            pdf.cell(35, 7, ar(o[3]), border=1, align="C")
            pdf.cell(35, 7, ar(f"{o[4]:,.0f}"), border=1, align="C", ln=True)

    return bytes(pdf.output())