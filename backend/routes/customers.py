"""Customer API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from schemas import CustomerResponse
from database import get_db

router = APIRouter(prefix="/api/customers", tags=["customers"])


CUSTOMER_QUERY = """
    SELECT
        c.MCM_CUST_CODE       AS id,
        UPPER(c.MCM_CUST_NAME)       AS name,
        c.MCM_CUST_TEL        AS phone,
        MAX(b.MBH_BILL_DATE)  AS last_purchase_date
    FROM MED_CUSTOMER_MAST c
    LEFT JOIN MED_BILL_HDR b
        ON c.MCM_CUST_CODE = b.MBH_BILL_CUST_CODE
    WHERE
        c.MCM_CUST_TEL IS NOT NULL
        AND LTRIM(RTRIM(c.MCM_CUST_TEL)) <> ''
        AND c.MCM_CUST_TEL <> '.'
        AND c.MCM_CUST_NAME IS NOT NULL
        AND LTRIM(RTRIM(c.MCM_CUST_NAME)) <> ''
        AND LTRIM(RTRIM(c.MCM_CUST_NAME)) NOT LIKE '[0-9]%'
        AND LTRIM(RTRIM(c.MCM_CUST_NAME)) LIKE '%[A-Za-z]%'
    GROUP BY
        c.MCM_CUST_CODE,
        c.MCM_CUST_NAME,
        c.MCM_CUST_TEL
    ORDER BY
        last_purchase_date DESC
"""

@router.get("", response_model=List[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    """List all customers with a valid phone number, from SQL Server."""
    rows = db.execute(text(CUSTOMER_QUERY)).fetchall()

    response = []
    for r in rows:
        response.append(
            CustomerResponse(
                id=r.id,
                name=r.name or "Unknown Customer",
                phone=r.phone.strip(),
                address=None,
                creditLimit=0.0,
                outstandingBalance=0.0,
                loyaltyPoints=0,
                isActive=True,
                createdAt=None,
                lastPurchase=r.last_purchase_date,
            )
        )
    return response


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get a single customer by ID from SQL Server."""
    from models import Customer
    c = db.query(Customer).filter(Customer.id == customer_id).first()

    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    phone_val = c.phone or c.phone_alt or ""
    if phone_val.strip() in [".", ""]:
        raise HTTPException(status_code=404, detail="Customer has no contact number")

    return CustomerResponse(
        id=c.id,
        name=c.name or "Unknown Customer",
        phone=phone_val,
        address=c.address if c.address != "." else None,
        creditLimit=float(c.credit_limit or 0.0),
        outstandingBalance=float(c.outstanding_balance or 0.0),
        loyaltyPoints=100 if (c.loyalty_allowed == 1) else 0,
        isActive=True,
        createdAt=c.created_at,
    )