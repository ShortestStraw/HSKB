from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Card, Deck, DeckCard, UserCard
from app.auth import get_current_user
from app import schemas
from app.recommendation import recommend_deck

router = APIRouter(prefix="/decks", tags=["decks"])

def validate_deck_composition(db: Session, cards_data: list[schemas.DeckCardEntry]):
    total = 0
    for entry in cards_data:
        total += entry.quantity
        if entry.quantity < 1:
            raise HTTPException(status_code=400, detail="Card quantity must be at least 1")
        card = db.query(Card).filter(Card.id == entry.card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail=f"Card ID {entry.card_id} not found in global pool")
        if card.rarity == "legendary" and entry.quantity > 1:
            raise HTTPException(status_code=400, detail="Legendary cards allow only 1 copy per deck")
        if entry.quantity > 2:
            raise HTTPException(status_code=400, detail="Non-legendary cards allow max 2 copies per deck")
    if total != 30:
        raise HTTPException(status_code=400, detail="A valid deck must consist of exactly 30 cards")

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.DeckResponse)
def create_deck(deck_data: schemas.DeckCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    validate_deck_composition(db, deck_data.cards)

    new_deck = Deck(name=deck_data.name, description=deck_data.description, creator_id=current_user.id)
    db.add(new_deck)
    db.flush()  # Generates new_deck.id for the foreign keys

    for card_entry in deck_data.cards:
        db.add(DeckCard(deck_id=new_deck.id, card_id=card_entry.card_id, quantity=card_entry.quantity))

    db.commit()
    db.refresh(new_deck)
    return new_deck

@router.get("/recommend", response_model=schemas.RecommendationResponse)
def get_recommended_deck(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Load user's collection
    user_cards = db.query(UserCard).filter(UserCard.user_id == current_user.id).all()
    user_collection = {uc.card_id: uc.quantity for uc in user_cards}

    # 2. Load all available decks
    decks = db.query(Deck).all()
    if not decks:
        return schemas.RecommendationResponse(deck_id=None, deck_name="No decks available", match_percentage=0.0, missing_cards=[])

    available_decks = []
    for deck in decks:
        # Valid query: fetch DeckCard rows, then access related Card via lazy/eager loading
        deck_cards = db.query(DeckCard).filter(DeckCard.deck_id == deck.id).all()
        cards_list = []
        for dc in deck_cards:
            cards_list.append({
                "card_id": dc.card_id,
                "name": dc.card.name,
                "quantity": dc.quantity,
                "mana_cost": dc.card.mana_cost
            })
        available_decks.append({"id": deck.id, "name": deck.name, "cards": cards_list})

    # 3. Run recommendation algorithm
    return schemas.RecommendationResponse(**recommend_deck(user_collection, available_decks))