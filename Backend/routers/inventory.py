# inventory.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from database import get_db
from models import Inventory, RestockRequest
from schemas import (
    InventoryItem,
    RestockRequestCreate,
    RestockRequestRead,
    RestockRequestUpdate,
)

router = APIRouter(prefix="/inventory", tags=["Inventory & Restock"])

class StockUpdate(BaseModel):
    item_name: str
    quantity_used: int

# 1️⃣ Get low-stock items for a PHC
@router.get("/low-stock", response_model=List[InventoryItem])
def get_low_stock_items(
    db: Session = Depends(get_db), 
    threshold_days: int = 5,
    phc_id: Optional[int] = None
):
    """
    Shows items that will run out within `threshold_days` based on daily consumption rate.
    """
    query = db.query(Inventory)
    if phc_id:
        query = query.filter(Inventory.phc_id == phc_id)
    
    items = query.all()
    low_stock = []

    for item in items:
        if item.daily_consumption_rate > 0:
            days_remaining = item.current_stock / item.daily_consumption_rate
            if days_remaining <= threshold_days:
                low_stock.append(
                    InventoryItem(
                        item_name=item.item_name,
                        item_type=item.item_type,
                        current_stock=item.current_stock,
                        daily_consumption_rate=item.daily_consumption_rate,
                        unit=item.unit,
                        days_remaining=round(days_remaining, 1),
                    )
                )
    return low_stock

@router.post("/auto-restock-check", status_code=status.HTTP_201_CREATED)
def auto_restock_check(db: Session = Depends(get_db)):
    """
    Automatically generate restock requests for all low-stock items (<= 5 days remaining)
    and assign priority based on days_remaining.
    """
    low_stock_items = db.query(Inventory).filter(Inventory.days_remaining <= 5).all()
    if not low_stock_items:
        raise HTTPException(status_code=404, detail="No low-stock items found")

    created_requests = []

    for item in low_stock_items:
        # Skip if an open request for this item already exists
        existing = db.query(RestockRequest).filter(
            RestockRequest.item_name == item.item_name,
            RestockRequest.phc_id == item.phc_id,  # Same PHC
            RestockRequest.status == "pending"
        ).first()
        if existing:
            continue

        # Determine priority
        days_remaining = item.days_remaining or 0
        if days_remaining <= 2:
            priority = "High"
        elif days_remaining <= 5:
            priority = "Medium"
        else:
            priority = "Low"

        # Create new request
        restock_request = RestockRequest(
            item_name=item.item_name,
            quantity_needed=max(0, int(item.daily_consumption_rate * 7)),  # Suggest 1 week supply
            phc_id=item.phc_id,
            phc_name=item.phc_name,
            days_remaining=days_remaining,
            priority_level=priority
        )
        db.add(restock_request)
        created_requests.append(restock_request)

    db.commit()
    return {"message": f"{len(created_requests)} restock requests created successfully."}

## LGA Admins

@router.post("/restock-requests", response_model=RestockRequestRead, status_code=status.HTTP_201_CREATED)
def create_restock_request(request: RestockRequestCreate, db: Session = Depends(get_db)):
    """
    Create a new restock request from PHC to LGA Admin,
    including priority level and days remaining.
    """
    # Fetch item details from inventory using item_name AND phc_id
    item = db.query(Inventory).filter(
        Inventory.item_name == request.item_name,
        Inventory.phc_id == request.phc_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in inventory for this PHC")

    # Determine priority based on days_remaining
    days_remaining = item.days_remaining or 0
    if days_remaining <= 2:
        priority = "High"
    elif days_remaining <= 5:
        priority = "Medium"
    else:
        priority = "Low"

    # Create restock request record
    restock_request = RestockRequest(
        item_name=request.item_name,
        quantity_needed=request.quantity_needed,
        phc_id=request.phc_id,
        phc_name=request.phc_name,
        days_remaining=days_remaining,
        priority_level=priority
    )

    db.add(restock_request)
    db.commit()
    db.refresh(restock_request)
    return restock_request

@router.get("/restock-requests", response_model=List[RestockRequestRead])
def get_restock_requests(
    db: Session = Depends(get_db),
    phc_id: Optional[int] = None,
    phc_name: Optional[str] = None,
    status: Optional[str] = None,
):
    """
    Allows LGA Admin to view all restock requests.
    Filterable by phc_id, phc_name, or status.
    """
    query = db.query(RestockRequest)
    
    if phc_id:
        query = query.filter(RestockRequest.phc_id == phc_id)
    
    if phc_name:
        query = query.filter(RestockRequest.phc_name.ilike(f"%{phc_name}%"))
    
    if status:
        query = query.filter(RestockRequest.status == status)
    
    requests = query.order_by(RestockRequest.request_date.desc()).all()
    return requests

# 5️⃣ Update (approve/decline) a restock request
@router.put("/restock-requests/{request_id}", response_model=RestockRequestRead)
def update_restock_request(
    request_id: int,
    update: RestockRequestUpdate,
    db: Session = Depends(get_db),
):
    """
    Allows LGA Admin to approve or decline a restock request.
    """
    request = db.query(RestockRequest).filter(RestockRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Restock request not found")

    request.status = update.status
    request.comments = update.comments
    db.commit()
    db.refresh(request)
    return request

@router.post("/update-stock", status_code=status.HTTP_200_OK)
def update_stock(
    updates: List[StockUpdate],
    db: Session = Depends(get_db),
    phc_id: int = 1 # Assuming a default PHC ID for now
):
    """
    Updates the stock level for a list of items based on daily usage.
    """
    for update in updates:
        item = db.query(Inventory).filter(
            Inventory.item_name.ilike(f"%{update.item_name}%"),
            Inventory.phc_id == phc_id
        ).first()

        if item:
            item.current_stock -= update.quantity_used
            if item.current_stock < 0:
                item.current_stock = 0
    
    db.commit()
    return {"message": "Stock levels updated successfully."}