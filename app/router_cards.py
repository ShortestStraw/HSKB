"""Endpoints for managing user card collections."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Card, UserCard
from app.auth import get_current_user
from app import schemas

router = APIRouter(prefix="/cards", tags=["cards"])

@router.get("/me", response_model=list[schemas.CardInCollection])
def get_my_cards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all cards in the current user's collection."""
    user_cards = (
        db.query(UserCard).join(Card)
        .filter(UserCard.user_id == current_user.id).all()
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

@router.post("/me", status_code=status.HTTP_201_CREATED)
def add_card_to_collection(
    card: schemas.CardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a card to the current user's collection or increment quantity."""
    db_card = db.query(Card).filter(Card.name == card.name).first()
    if not db_card:
        db_card = Card(name=card.name, mana_cost=card.mana_cost, rarity=card.rarity)
        db.add(db_card)
        db.flush()

    user_card = db.query(UserCard).filter(
        UserCard.user_id == current_user.id,
        UserCard.card_id == db_card.id,
    ).first()
    if user_card:
        user_card.quantity += 1
    else:
        user_card = UserCard(
            user_id=current_user.id, card_id=db_card.id, quantity=1
        )
        db.add(user_card)

    db.commit()
    db.refresh(user_card)
    return {
        "message": "Card added",
        "card_id": db_card.id,
        "new_quantity": user_card.quantity,
    }

@router.delete("/me/{card_id}", status_code=status.HTTP_200_OK)
def remove_card_from_collection(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove one copy of a card from the user's collection."""
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