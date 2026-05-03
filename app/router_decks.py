"""Endpoints for managing user decks and recommendations."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import User, Card, Deck, DeckCard, UserCard
from app.auth import get_current_user
from app import schemas
from app.recommendation import recommend_deck

router = APIRouter(prefix="/decks", tags=["decks"])


def validate_deck_composition(db: Session, cards_data: List[schemas.DeckCardEntry]):
    """
    Validate deck composition rules:
    - Exactly 30 cards total
    - Legendary cards: max 1 copy
    - Other cards: max 2 copies
    - All cards must exist in global pool
    """
    total = 0
    for entry in cards_data:
        total += entry.quantity
        
        if entry.quantity < 1:
            raise HTTPException(
                status_code=400, 
                detail="Card quantity must be at least 1"
            )
        
        card = db.query(Card).filter(Card.id == entry.card_id).first()
        if not card:
            raise HTTPException(
                status_code=404, 
                detail=f"Card ID {entry.card_id} not found in global pool"
            )
        
        if card.rarity == "legendary" and entry.quantity > 1:
            raise HTTPException(
                status_code=400, 
                detail="Legendary cards allow only 1 copy per deck"
            )
        if entry.quantity > 2:
            raise HTTPException(
                status_code=400, 
                detail="Non-legendary cards allow max 2 copies per deck"
            )
    
    if total != 30:
        raise HTTPException(
            status_code=400, 
            detail=f"A valid deck must consist of exactly 30 cards, got {total}"
        )


def check_deck_ownership(deck: Deck, current_user: User):
    """Check if current user owns the deck, raise 403 if not."""
    if deck.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only manage your own decks"
        )


@router.get("/", response_model=schemas.DeckListResponse)
def list_all_decks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=50),
    creator_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db)
):
    """
    List all decks with optional filtering by creator.
    
    Public endpoint - returns basic deck info without card details.
    """
    query = db.query(Deck)
    
    if creator_id:
        query = query.filter(Deck.creator_id == creator_id)
    
    total = query.count()
    decks = query.offset(skip).limit(limit).all()
    
    return schemas.DeckListResponse(
        decks=decks,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/me", response_model=List[schemas.DeckResponse])
def get_my_decks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all decks created by the current user."""
    decks = db.query(Deck).filter(Deck.creator_id == current_user.id).all()
    return decks


@router.get("/recommend", response_model=schemas.RecommendationResponse)
def get_recommended_deck(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Get a deck recommendation based on user's card collection.
    
    Algorithm matches available decks against user's owned cards
    and returns the best match with missing cards listed.
    """
    # Load user's collection
    user_cards = db.query(UserCard).filter(
        UserCard.user_id == current_user.id
    ).all()
    user_collection = {uc.card_id: uc.quantity for uc in user_cards}

    # Load all available decks
    decks = db.query(Deck).all()
    if not decks:
        return schemas.RecommendationResponse(
            deck_id=None, 
            deck_name="No decks available", 
            match_percentage=0.0, 
            missing_cards=[]
        )

    available_decks = []
    for deck in decks:
        deck_cards = db.query(DeckCard).filter(
            DeckCard.deck_id == deck.id
        ).all()
        cards_list = [
            {
                "card_id": dc.card_id,
                "name": dc.card.name,
                "quantity": dc.quantity,
                "mana_cost": dc.card.mana_cost
            }
            for dc in deck_cards
        ]
        available_decks.append({
            "id": deck.id, 
            "name": deck.name, 
            "cards": cards_list
        })

    # Run recommendation algorithm
    result = recommend_deck(user_collection, available_decks)
    return schemas.RecommendationResponse(**result)


@router.get("/{deck_id}", response_model=schemas.DeckDetailResponse)
def get_deck_by_id(
    deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific deck including its cards.
    
    Only accessible for decks owned by the current user.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    check_deck_ownership(deck, current_user)
    
    # Fetch deck cards with card details
    deck_cards = db.query(DeckCard).filter(DeckCard.deck_id == deck_id).all()
    cards_list = [
        schemas.DeckCardEntry(
            card_id=dc.card_id,
            quantity=dc.quantity
        )
        for dc in deck_cards
    ]
    
    return schemas.DeckDetailResponse(
        id=deck.id,
        name=deck.name,
        description=deck.description,
        creator_id=deck.creator_id,
        cards=cards_list
    )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.DeckResponse)
def create_deck(
    deck_data: schemas.DeckCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Create a new deck with validated composition.
    
    Requirements:
    - Exactly 30 cards total
    - Legendary cards: max 1 copy
    - Other cards: max 2 copies
    """
    validate_deck_composition(db, deck_data.cards)

    new_deck = Deck(
        name=deck_data.name, 
        description=deck_data.description, 
        creator_id=current_user.id
    )
    db.add(new_deck)
    db.flush()  # Generate ID for foreign key references

    for card_entry in deck_data.cards:
        db.add(DeckCard(
            deck_id=new_deck.id, 
            card_id=card_entry.card_id, 
            quantity=card_entry.quantity
        ))

    db.commit()
    db.refresh(new_deck)
    return new_deck


@router.put("/{deck_id}", response_model=schemas.DeckResponse)
def update_deck(
    deck_id: int,
    deck_update: schemas.DeckUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update deck metadata (name and/or description).
    
    Cannot modify deck composition via this endpoint - recreate deck instead.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    check_deck_ownership(deck, current_user)
    
    if deck_update.name is not None:
        deck.name = deck_update.name
    if deck_update.description is not None:
        deck.description = deck_update.description
    
    db.commit()
    db.refresh(deck)
    return deck


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(
    deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a deck and all its associated cards.
    
    This operation is irreversible. Returns 204 No Content on success.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    check_deck_ownership(deck, current_user)
    
    # Delete associated deck cards first (foreign key constraint)
    db.query(DeckCard).filter(DeckCard.deck_id == deck_id).delete()
    db.delete(deck)
    db.commit()
    
    return None