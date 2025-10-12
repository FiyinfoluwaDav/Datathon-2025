# inventory.py
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from database import get_db
from models import Inventory, RestockRequest
from schemas import (
    InventoryItem,
    RestockRequestCreate,
    RestockRequestRead,
    RestockRequestUpdate,
)

router = APIRouter(prefix="/inventory", tags=["Inventory & Restock"])

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
        try:
            if item.daily_consumption_rate and item.daily_consumption_rate > 0:
                days_remaining = item.current_stock / item.daily_consumption_rate
                if days_remaining <= threshold_days:
                    low_stock.append(
                        InventoryItem(
                            item_name=item.item_name,
                            item_type=getattr(item, "item_type", None),
                            current_stock=item.current_stock,
                            daily_consumption_rate=item.daily_consumption_rate,
                            unit=getattr(item, "unit", None),
                            days_remaining=round(days_remaining, 1),
                        )
                    )
        except Exception:
            # skip malformed rows
            continue
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

# -------------------- NEW: paginated listing endpoint --------------------
@router.get("/items")
def list_inventory_items(
    db: Session = Depends(get_db),
    phc_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
):
    """
    Paginated listing of inventory items. Returns real total count and items for the page.
    """
    query = db.query(Inventory)
    if phc_id is not None:
        query = query.filter(Inventory.phc_id == phc_id)

    total = query.count()
    offset = (page - 1) * page_size
    rows = query.order_by(Inventory.item_name.asc()).offset(offset).limit(page_size).all()

    items = []
    for r in rows:
        days_remaining = None
        try:
            if r.daily_consumption_rate and r.daily_consumption_rate > 0:
                days_remaining = round((r.current_stock or 0) / r.daily_consumption_rate, 1)
        except Exception:
            days_remaining = None

        items.append({
            "id": getattr(r, "id", None),
            "item_name": getattr(r, "item_name", None),
            "item_type": getattr(r, "item_type", None),
            "current_stock": getattr(r, "current_stock", 0),
            "daily_consumption_rate": getattr(r, "daily_consumption_rate", 0),
            "unit": getattr(r, "unit", None),
            "phc_id": getattr(r, "phc_id", None),
            "phc_name": getattr(r, "phc_name", None),
            "days_remaining": days_remaining,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}

# -------------------- NEW: add-item (manual add/update) --------------------
@router.post("/add-item", status_code=status.HTTP_201_CREATED)
def add_or_update_item(payload: Dict = Body(...), db: Session = Depends(get_db)):
    """
    Manually add a new inventory item or add quantity to an existing item.
    Expected body keys: item_name (str), add_quantity (int), phc_id (int), optional: item_type, daily_consumption_rate, unit, phc_name
    """
    item_name = payload.get("item_name")
    add_quantity = int(payload.get("add_quantity", 0) or 0)
    phc_id = payload.get("phc_id")

    if not item_name or phc_id is None:
        raise HTTPException(status_code=400, detail="item_name and phc_id are required")

    item = db.query(Inventory).filter(
        Inventory.item_name == item_name,
        Inventory.phc_id == phc_id
    ).first()

    if item:
        # update existing
        item.current_stock = (item.current_stock or 0) + add_quantity
        if "daily_consumption_rate" in payload and payload["daily_consumption_rate"] is not None:
            item.daily_consumption_rate = payload["daily_consumption_rate"]
        if "item_type" in payload:
            item.item_type = payload.get("item_type")
        if "unit" in payload:
            item.unit = payload.get("unit")
        if "phc_name" in payload:
            item.phc_name = payload.get("phc_name")
        db.commit()
        db.refresh(item)
        return {"message": "Item updated", "item_id": getattr(item, "id", None)}
    else:
        # create new
        new_item = Inventory(
            item_name=item_name,
            item_type=payload.get("item_type"),
            current_stock=add_quantity,
            daily_consumption_rate=payload.get("daily_consumption_rate", 0),
            unit=payload.get("unit"),
            phc_id=phc_id,
            phc_name=payload.get("phc_name"),
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return {"message": "Item created", "item_id": getattr(new_item, "id", None)}

# -------------------- NEW: bulk create restock requests by threshold --------------------
@router.post("/create-restock-for-threshold", status_code=status.HTTP_201_CREATED)
def create_restock_for_threshold(
    db: Session = Depends(get_db),
    threshold_days: int = Query(5, ge=0),
    phc_id: Optional[int] = Query(None),
):
    """
    Create restock requests for inventory items whose days_remaining <= threshold_days.
    """
    query = db.query(Inventory)
    if phc_id is not None:
        query = query.filter(Inventory.phc_id == phc_id)

    rows = query.all()
    candidates = []
    for r in rows:
        try:
            if r.daily_consumption_rate and r.daily_consumption_rate > 0:
                days_remaining = (r.current_stock or 0) / r.daily_consumption_rate
                if days_remaining <= threshold_days:
                    candidates.append((r, round(days_remaining, 1)))
        except Exception:
            continue

    if not candidates:
        return {"created": 0, "requests": []}

    created = []
    for r, days in candidates:
        exists = db.query(RestockRequest).filter(
            RestockRequest.item_name == r.item_name,
            RestockRequest.phc_id == r.phc_id,
            RestockRequest.status == "pending"
        ).first()
        if exists:
            continue

        if days <= 2:
            priority = "High"
        elif days <= threshold_days:
            priority = "Medium"
        else:
            priority = "Low"

        rr = RestockRequest(
            item_name=r.item_name,
            quantity_needed=max(1, int((r.daily_consumption_rate or 0) * 7)),
            phc_id=r.phc_id,
            phc_name=r.phc_name,
            days_remaining=days,
            priority_level=priority
        )
        db.add(rr)
        created.append({"item_name": r.item_name, "phc_id": r.phc_id, "days_remaining": days, "priority": priority})

    db.commit()
    return {"created": len(created), "requests": created}