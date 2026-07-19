"""SQLAlchemy ORM models for Aadhirai Mart SQL Server database."""

from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Product(Base):
    """Product model mapping to med_item_hdr in SQL Server."""
    __tablename__ = "med_item_hdr"

    id = Column("MIH_ITEM_CODE", Integer, primary_key=True)
    name = Column("MIH_ITEM_NAME", String(255), index=True)
    brand = Column("mih_item_name_short", String(255))
    category_id = Column("MIH_CATEGORY_1", Integer)
    category2_id = Column("MIH_CATEGORY_2", Integer)
    unit = Column("mih_unit", String(50))
    cost_price_fallback = Column("MIH_PUR_PRICE", Float)
    barcode_fallback = Column("MIH_EANCODE", String(100))
    hsn_code = Column("MIH_HSN_CODE", String(50))
    created_at = Column("MIH_CREATED_DATE", DateTime)
    availability = Column("MIH_AVAILABILITY", String(10))  # 'Y' or 'N'


class ProductBatch(Base):
    """ProductBatch model mapping to MED_ITEM_DTL in SQL Server."""
    __tablename__ = "MED_ITEM_DTL"

    row_id = Column("mid_row_id", Integer, primary_key=True)
    product_id = Column("MID_ITEM_CODE", Integer, index=True)
    stock = Column("MID_BAL_STOCK", Float)
    expiry_date = Column("MID_EXPIRY_DT", DateTime)
    batch_no = Column("MID_BATCH_NO", String(100))
    mrp = Column("MID_MRP", Float)
    purchase_price = Column("MID_PUR_PRICE", Float)
    barcode = Column("mid_unique_Barcode", String(100))
    tax_percent = Column("MID_SALE_TAX_PERC", Float)


class Category(Base):
    """Category model mapping to MED_CATEGORY_DTL in SQL Server."""
    __tablename__ = "MED_CATEGORY_DTL"

    id = Column("MCD_CAT_CODE", Integer, primary_key=True)
    name = Column("MCD_CAT_NAME", String(255))
    level_name = Column("MCD_CAT_ANAME", String(100))  # e.g., 'MIH_CATEGORY_1'
    is_active = Column("MCD_Active", String(10))  # 'Y' or 'N'


class Customer(Base):
    """Customer model mapping to MED_CUSTOMER_MAST in SQL Server."""
    __tablename__ = "MED_CUSTOMER_MAST"

    id = Column("MCM_CUST_CODE", Integer, primary_key=True)
    name = Column("MCM_CUST_NAME", String(255), index=True)
    phone = Column("mcm_phone2", String(50))
    phone_alt = Column("MCM_CUST_TEL", String(50))
    outstanding_balance = Column("MCM_CUST_CREDIT_BAL", Float)
    credit_limit = Column("MCM_CUST_CREDIT_LIMIT", Float)
    address = Column("MCM_CUST_ADDR1", String(255))
    loyalty_allowed = Column("mcm_loyalty_allowed", Integer)  # 1 or 0
    status = Column("MCM_CUST_STATUS", String(10))  # 'A' or similar
    created_at = Column("MCM_CREATED_DT_TIME", DateTime)


class BillHdr(Base):
    """Bill Header model mapping to MED_BILL_HDR in SQL Server."""
    __tablename__ = "MED_BILL_HDR"

    bill_no = Column("MBH_BILL_NO", Integer, primary_key=True)
    bill_date = Column("MBH_BILL_DATE", DateTime, index=True)
    bill_amount = Column("MBH_BILL_AMOUNT", Float)
    customer_code = Column("MBH_BILL_CUST_CODE", Integer)
    customer_name = Column("MBH_BILL_CUST_NAME", String(255))
    cash_amount = Column("MBH_CASH_AMT", Float)
    card_amount = Column("MBH_CARD_AMT", Float)
    credit_amount = Column("MBH_CREDIT_AMT", Float)
    wallet_amount = Column("mbh_wallet_amt", Float)
    profit = Column("MBH_PROFIT", Float)


class BillDtl(Base):
    """Bill Detail model mapping to MED_BILL_DTL in SQL Server."""
    __tablename__ = "MED_BILL_DTL"

    row_id = Column("mbd_item_rowid", Integer, primary_key=True)
    bill_no = Column("MBD_BILL_NO", Integer, index=True)
    product_id = Column("MBD_ITEM_CODE", Integer, index=True)
    quantity = Column("MBD_ITEM_QTY", Float)
    rate = Column("MBD_ITEM_RATE", Float)
    amount = Column("MBD_ITEM_AMOUNT", Float)
    purchase_rate = Column("MBD_PUR_RATE", Float)
    profit = Column("mbd_profit_amt", Float)
    barcode = Column("mbd_eancode", String(100))
