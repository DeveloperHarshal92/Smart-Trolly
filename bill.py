import pandas as pd
from collections import Counter
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os
from xml.sax.saxutils import escape

# ── Products catalogue ────────────────────────────────────────────────────────
# The detector class remains the stable key shared with the YOLO model.
product_catalog = {
    'dairy_milk': {
        'name': 'Dairy Milk Chocolate', 'hsn': '1806', 'price': 5,
    },
    'colgate': {
        'name': 'Colgate MaxFresh', 'hsn': '3306', 'price': 115,
    },
    'good_day': {
        'name': 'Good Day Cookies', 'hsn': '1905', 'price': 30,
    },
    'parle_g': {
        'name': 'Parle-G Biscuit Packet', 'hsn': '1905', 'price': 10,
    },
    'parachute': {
        'name': 'Parachute Coconut Oil', 'hsn': '3305', 'price': 15,
    },
}

# Backwards-compatible price map used by the original bill table.
products = {key: value['price'] for key, value in product_catalog.items()}


def build_invoice_summary(
    items_list: list,
    invoice_number: str = "INV-2026-98742",
) -> dict:
    """Builds the checkout invoice from detector class names."""
    rows = []
    subtotal = 0.0

    for class_name, quantity in Counter(items_list).items():
        product = product_catalog.get(class_name)
        if product is None:
            continue
        line_total = float(product['price'] * quantity)
        subtotal += line_total
        rows.append({
            'class_name': class_name,
            'name': product['name'],
            'hsn': product['hsn'],
            'quantity': quantity,
            'rate': float(product['price']),
            'total': line_total,
        })

    cgst = round(subtotal * 0.09, 2)
    sgst = round(subtotal * 0.09, 2)
    grand_total = round(subtotal + cgst + sgst, 2)

    return {
        'invoice_number': invoice_number,
        'generated_at': datetime.now().strftime("%d %b %Y · %I:%M %p"),
        'items': rows,
        'subtotal': subtotal,
        'cgst': cgst,
        'sgst': sgst,
        'grand_total': grand_total,
        'barcode': '8904 2000 9874 2',
    }

# ── Bill generation ───────────────────────────────────────────────────────────
def generateBill(items_list: list) -> tuple[pd.DataFrame, int]:
    """
    Returns (bill_df, total_bill).
    Uses Counter so item order is deterministic (insertion order in Python 3.7+).
    Unknown items are skipped with a warning instead of crashing.
    """
    counts    = Counter(items_list)
    bill_data = []
    total_bill = 0

    for i, (item, quantity) in enumerate(counts.items(), start=1):
        unit_price = products.get(item)
        if unit_price is None:
            print(f"[WARN] Unknown item '{item}' skipped — add it to products dict.")
            continue
        total_price = quantity * unit_price
        total_bill  += total_price
        display_name = product_catalog[item]['name']
        bill_data.append([i, display_name, quantity, unit_price, total_price])

    bill_df = pd.DataFrame(bill_data, columns=["SN", "Item", "Quantity", "Unit Price (₹)", "Total (₹)"])
    bill_df.loc[len(bill_df)] = ["", "Total", "", "", total_bill]
    return bill_df, total_bill


# ── PDF generation ────────────────────────────────────────────────────────────
def generateBillPDF(
    items_list: list,
    customer_name: str = "Customer",
    customer_email: str = "",
    save_dir: str = "static/bills",
) -> str:
    """Generate the formal A4 tax invoice attached to the customer email."""
    os.makedirs(save_dir, exist_ok=True)
    generated = datetime.now()
    timestamp = generated.strftime("%Y%m%d_%H%M%S")
    filename = f"invoice_{timestamp}.pdf"
    filepath = os.path.abspath(os.path.join(save_dir, filename))
    invoice_number = f"INV-{generated.strftime('%Y%m%d-%H%M%S')}"
    invoice = build_invoice_summary(items_list, invoice_number=invoice_number)

    page_width = A4[0] - 1.2 * cm
    half_width = page_width / 2
    brand_blue = colors.HexColor("#1D0BEE")
    ink = colors.HexColor("#111111")
    line = colors.HexColor("#252525")
    soft_line = colors.HexColor("#D9D9D9")
    pale_blue = colors.HexColor("#F4F5FF")

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=0.6 * cm,
        rightMargin=0.6 * cm,
        topMargin=0.55 * cm,
        bottomMargin=0.55 * cm,
        title=f"Tax Invoice {invoice_number}",
        author="SMART-MART RETAILS PVT LTD",
    )
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "InvoiceNormal", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, leading=11, textColor=ink, spaceAfter=0,
    )
    small = ParagraphStyle(
        "InvoiceSmall", parent=normal, fontSize=7.2, leading=9.5,
    )
    bold = ParagraphStyle(
        "InvoiceBold", parent=normal, fontName="Helvetica-Bold",
    )
    brand = ParagraphStyle(
        "InvoiceBrand", parent=bold, fontSize=19, leading=22,
        textColor=brand_blue, spaceAfter=6,
    )
    title = ParagraphStyle(
        "InvoiceTitle", parent=normal, fontSize=19, leading=22,
        alignment=TA_LEFT, spaceAfter=8,
    )
    right = ParagraphStyle(
        "InvoiceRight", parent=normal, alignment=TA_RIGHT,
    )
    right_bold = ParagraphStyle(
        "InvoiceRightBold", parent=bold, alignment=TA_RIGHT,
    )
    white_label = ParagraphStyle(
        "InvoiceWhiteLabel", parent=bold, fontSize=8.2, leading=10,
        textColor=colors.white,
    )
    center_small = ParagraphStyle(
        "InvoiceCenterSmall", parent=small, alignment=TA_CENTER,
    )

    def paragraph(text, style=normal):
        return Paragraph(str(text).replace("\n", "<br/>"), style)

    customer = escape(customer_name or "Customer")
    email = escape(customer_email or "Not provided")
    company_block = [
        Paragraph("SMART-MART RETAILS PVT LTD", brand),
        paragraph("Store #42, Tech Hub Galleria, Pune, Maharashtra 411038", small),
        paragraph("Phone: +91 98765 43210", small),
        paragraph("<b>GSTIN:</b> 27AAAAA1111A1Z1", small),
        paragraph("<b>PAN:</b> AAAAA1111A", small),
    ]
    invoice_block = [
        Paragraph("TAX INVOICE", title),
        paragraph(f"<b>Invoice No:</b> {invoice_number}", small),
        paragraph(f"<b>Invoice Date:</b> {generated.strftime('%d %B %Y')}", small),
        paragraph(f"<b>Invoice Time:</b> {generated.strftime('%I:%M %p')}", small),
        paragraph("<b>Place of Supply:</b> Maharashtra", small),
    ]

    story = []
    header = Table(
        [[company_block, invoice_block]],
        colWidths=[half_width, half_width],
        rowHeights=[4.15 * cm],
    )
    header.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, line),
        ("INNERGRID", (0, 0), (-1, -1), 0.8, line),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(header)

    section_bar = Table(
        [[Paragraph("BILL TO", white_label), Paragraph("SHIP TO", white_label)]],
        colWidths=[half_width, half_width], rowHeights=[0.72 * cm],
    )
    section_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), brand_blue),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, line),
        ("INNERGRID", (0, 0), (-1, -1), 0.8, line),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(section_bar)

    bill_to = [
        Paragraph(f"<b>{customer}</b>", bold),
        paragraph(f"Email: {email}", small),
        paragraph("Customer Type: Retail", small),
        paragraph("State: Maharashtra", small),
        paragraph("Place of Supply: Pune", small),
    ]
    ship_to = [
        Paragraph(f"<b>{customer}</b>", bold),
        paragraph("In-store collection", small),
        paragraph("Smart Trolley Lane POS-042", small),
        paragraph("Tech Hub Galleria, Pune", small),
        paragraph("State Code: 27", small),
    ]
    details = Table(
        [[bill_to, ship_to]], colWidths=[half_width, half_width],
        rowHeights=[3.65 * cm],
    )
    details.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, line),
        ("INNERGRID", (0, 0), (-1, -1), 0.8, line),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(details)

    item_widths = [1.05 * cm, 6.25 * cm, 2.0 * cm, 1.4 * cm, 3.45 * cm, page_width - 14.15 * cm]
    item_data = [[
        paragraph("Sr.", white_label),
        paragraph("Items", white_label),
        paragraph("HSN", white_label),
        paragraph("Qty", white_label),
        paragraph("Price per Unit", white_label),
        Paragraph("Amount", ParagraphStyle("AmountHead", parent=white_label, alignment=TA_RIGHT)),
    ]]
    total_quantity = 0
    for index, item in enumerate(invoice["items"], start=1):
        total_quantity += item["quantity"]
        item_data.append([
            paragraph(index, center_small),
            paragraph(item["name"], small),
            paragraph(item["hsn"], center_small),
            paragraph(item["quantity"], center_small),
            paragraph(f"Rs. {item['rate']:.2f}", right),
            paragraph(f"Rs. {item['total']:.2f}", right),
        ])
    while len(item_data) < 7:
        item_data.append(["", "", "", "", "", ""])

    item_rows = [0.72 * cm] + [0.68 * cm] * (len(item_data) - 1)
    items_table = Table(item_data, colWidths=item_widths, rowHeights=item_rows, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), brand_blue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, line),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, soft_line),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FCFCFC")]),
    ]))
    story.append(items_table)

    subtotal = Table(
        [[
            Paragraph("Sub Total", white_label), "", "",
            paragraph(total_quantity, white_label), "",
            Paragraph(f"Rs. {invoice['subtotal']:.2f}", ParagraphStyle("SubAmount", parent=white_label, alignment=TA_RIGHT)),
        ]],
        colWidths=item_widths, rowHeights=[0.72 * cm],
    )
    subtotal.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), brand_blue),
        ("SPAN", (0, 0), (2, 0)),
        ("BOX", (0, 0), (-1, -1), 0.8, line),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(subtotal)

    left_bottom = Table([
        [Paragraph("Payment Details", bold)],
        [[
            paragraph("Payment Mode: Razorpay Touchless Wallet", small),
            paragraph("Payment Status: PAID", small),
            paragraph("Transaction verified using Razorpay signature", small),
        ]],
        [Paragraph("Notes", bold)],
        [paragraph("1. Computer-vision generated retail invoice.<br/>2. Please retain this invoice for returns.", small)],
        [Paragraph("Terms &amp; Conditions", bold)],
        [paragraph("1. Goods once sold are subject to store return policy.<br/>2. Tax is calculated as per applicable GST rules.<br/>3. This is a digitally generated invoice.", small)],
        [Paragraph("Customer Signature", bold)],
    ], colWidths=[half_width - 0.2 * cm],
       rowHeights=[0.65*cm, 2.0*cm, 0.55*cm, 1.15*cm, 0.55*cm, 1.55*cm, 6.0*cm])
    left_bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, -1), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    tax_rows = [
        [paragraph("Taxable Amount", right), paragraph(f"Rs. {invoice['subtotal']:.2f}", right)],
        [paragraph("CGST @ 9.0%", right), paragraph(f"Rs. {invoice['cgst']:.2f}", right)],
        [paragraph("SGST @ 9.0%", right), paragraph(f"Rs. {invoice['sgst']:.2f}", right)],
        [paragraph("Discount", right), paragraph("Rs. 0.00", right)],
        [Paragraph("Total Amount", right_bold), Paragraph(f"Rs. {invoice['grand_total']:.2f}", right_bold)],
        [paragraph("Received Amount", right), paragraph(f"Rs. {invoice['grand_total']:.2f}", right)],
        [Paragraph("Due Balance", right_bold), Paragraph("Rs. 0.00", right_bold)],
        ["", ""],
        ["", Paragraph("Authorised Signatory For<br/><b>SMART-MART RETAILS PVT LTD</b>", right_bold)],
    ]
    right_bottom = Table(
        tax_rows,
        colWidths=[4.9 * cm, half_width - 5.1 * cm],
        rowHeights=[0.65*cm, 0.55*cm, 0.55*cm, 0.55*cm, 1.05*cm, 0.65*cm, 0.65*cm, 6.2*cm, 1.55*cm],
    )
    right_bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEABOVE", (0, 4), (-1, 4), 0.8, line),
        ("LINEBELOW", (0, 4), (-1, 4), 0.8, line),
        ("VALIGN", (0, -1), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    bottom = Table(
        [[left_bottom, right_bottom]],
        colWidths=[half_width, half_width],
        rowHeights=[12.8 * cm],
    )
    bottom.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, line),
        ("INNERGRID", (0, 0), (-1, -1), 0.8, line),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(bottom)

    doc.build(story)
    print(f"[INFO] Tax invoice saved -> {filepath}")
    return filepath
