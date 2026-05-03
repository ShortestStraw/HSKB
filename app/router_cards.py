"""Endpoints for managing user card collections."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import User, Card, UserCard
from app.auth import get_current_user
from app import schemas

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("/", response_model=schemas.CardListResponse)
def list_all_cards(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=200, description="Maximum records to return"),
    rarity: Optional[str] = Query(None, pattern="^(common|rare|epic|legendary)$"),
    db: Session = Depends(get_db)
):
    """
    List all cards in the global pool with optional filtering and pagination.
    
    - **skip**: Offset for pagination (default: 0)
    - **limit**: Max items to return, 1-200 (default: 100)
    - **rarity**: Filter by card rarity (optional)
    """
    query = db.query(Card)
    
    if rarity:
        query = query.filter(Card.rarity == rarity)
    
    total = query.count()
    cards = query.offset(skip).limit(limit).all()
    
    return schemas.CardListResponse(
        cards=cards,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/me", response_model=List[schemas.CardInCollection])
def get_my_cards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all cards in the current user's collection."""
    user_cards = (
        db.query(UserCard)
        .join(Card)
        .filter(UserCard.user_id == current_user.id)
        .all()
    )
    return [
        schemas.CardInCollection(
            card_id=uc.card_id,
            card_name=uc.card.name,
            mana_cost=uc.card.mana_cost,
            rarity=uc.card.rarity,
            quantity=uc.quantity,
        )
        for uc in user_cards
    ]


@router.get("/{card_id}", response_model=schemas.CardResponse)
def get_card_by_id(
    card_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific card from the global pool by its ID.
    
    Returns 404 if card not found.
    """
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found in global pool"
        )
    return card


@router.get("/me/{card_id}", response_model=schemas.CardInCollection)
def get_card_in_collection(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific card from the current user's collection.
    
    Returns 404 if card not in user's collection.
    """
    user_card = db.query(UserCard).join(Card).filter(
        UserCard.user_id == current_user.id,
        UserCard.card_id == card_id
    ).first()
    
    if not user_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found in your collection"
        )
    
    return schemas.CardInCollection(
        card_id=user_card.card_id,
        card_name=user_card.card.name,
        mana_cost=user_card.card.mana_cost,
        rarity=user_card.card.rarity,
        quantity=user_card.quantity,
    )


@router.post("/me", status_code=status.HTTP_201_CREATED)
def add_card_to_collection(
    card: schemas.CardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a card to the current user's collection or increment quantity.
    
    If card exists in global pool, it's linked. Otherwise, a new card is created.
    Maximum quantity per card is 2.
    """
    # Check if card exists in global pool
    db_card = db.query(Card).filter(Card.name == card.name).first()
    
    if not db_card:
        # Create new card in global pool
        db_card = Card(
            name=card.name, 
            mana_cost=card.mana_cost, 
            rarity=card.rarity
        )
        db.add(db_card)
        db.flush()  # Generate ID for foreign key reference

    # Check if user already has this card
    user_card = db.query(UserCard).filter(
        UserCard.user_id == current_user.id,
        UserCard.card_id == db_card.id,
    ).first()
    
    if user_card:
        if user_card.quantity >= 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum quantity (2) reached for this card"
            )
        user_card.quantity += 1
    else:
        user_card = UserCard(
            user_id=current_user.id, 
            card_id=db_card.id, 
            quantity=1
        )
        db.add(user_card)

    db.commit()
    db.refresh(user_card)
    
    return {
        "message": "Card added to collection",
        "card_id": db_card.id,
        "new_quantity": user_card.quantity,
    }


@router.put("/me/{card_id}", response_model=schemas.CardInCollection)
def update_card_quantity(
    card_id: int,
    quantity_update: schemas.CardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the quantity of a specific card in user's collection.
    
    - Quantity 0 removes the card from collection
    - Maximum quantity is 2 per card
    """
    user_card = db.query(UserCard).filter(
        UserCard.user_id == current_user.id,
        UserCard.card_id == card_id,
    ).first()
    
    if not user_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found in your collection"
        )
    
    if quantity_update.quantity == 0:
        # Remove card from collection
        db.delete(user_card)
        db.commit()
        return {
            "card_id": card_id,
            "card_name": "Removed",
            "mana_cost": 0,
            "rarity": "",
            "quantity": 0,
        }
    
    # Update quantity (max 2)
    user_card.quantity = min(quantity_update.quantity, 2)
    db.commit()
    db.refresh(user_card)
    
    card = db.query(Card).filter(Card.id == card_id).first()
    return schemas.CardInCollection(
        card_id=user_card.card_id,
        card_name=card.name,
        mana_cost=card.mana_cost,
        rarity=card.rarity,
        quantity=user_card.quantity,
    )


@router.delete("/me/{card_id}", status_code=status.HTTP_200_OK)
def remove_card_from_collection(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove one copy of a card from the user's collection.
    
    If quantity reaches 0, the card entry is deleted entirely.
    """
    user_card = db.query(UserCard).filter(
        UserCard.user_id == current_user.id,
        UserCard.card_id == card_id,
    ).first()

    if not user_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found in your collection",
        )

    if user_card.quantity > 1:
        user_card.quantity -= 1
        db.commit()
        db.refresh(user_card)
        card = db.query(Card).filter(Card.id == card_id).first()
        return {
            "message": "Card copy removed",
            "card_id": user_card.card_id,
            "new_quantity": user_card.quantity,
        }

    db.delete(user_card)
    db.commit()
    return {
        "message": "Card removed completely",
        "card_id": card_id,
        "new_quantity": 0,
    }