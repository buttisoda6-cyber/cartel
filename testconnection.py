import pyodbc
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Connection credentials
server = r"100.107.143.8\GFT"
database = "Medishopdb"
username = "readonly_sanjay"
password = "readonly@123"
driver = "{ODBC Driver 17 for SQL Server}"

conn_str = (
    f"DRIVER={driver};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    f"TrustServerCertificate=yes;"
    f"Connection Timeout=30;"
)

tables = [
    "MED_CATEGORY_HDR",
    "MED_CATEGORY_DTL",
    "MED_ITEM_HDR",
    "MED_ITEM_DTL",
    "MED_CUSTOMER_MAST",
    "MED_BILL_HDR",
    "MED_BILL_DTL"
]

pdf_file = "Medishop_Sample_Data.pdf"
doc = SimpleDocTemplate(pdf_file)
styles = getSampleStyleSheet()
content = []

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    content.append(Paragraph("Medishop Database Sample Data", styles['Title']))
    content.append(Spacer(1, 12))

    for table in tables:
        content.append(PageBreak())
        content.append(Paragraph(f"Table: {table}", styles['Heading1']))

        cursor.execute(f"SELECT TOP 5 * FROM {table}")

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

        if not rows:
            content.append(Paragraph("No rows found.", styles['Normal']))
            continue

        for idx, row in enumerate(rows, start=1):
            content.append(Paragraph(f"<b>Row {idx}</b>", styles['Heading3']))

            for col, val in zip(columns, row):
                content.append(
                    Paragraph(
                        f"<b>{col}</b>: {str(val).replace('&', '&amp;')}",
                        styles['Normal']
                    )
                )

            content.append(Spacer(1, 8))

    cursor.close()
    conn.close()

    doc.build(content)

    print(f"✅ PDF generated successfully: {pdf_file}")

except Exception as e:
    print("❌ Error:")
    print(e)