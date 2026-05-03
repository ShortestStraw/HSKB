from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    cards = relationship("UserCard", back_populates="user")
    decks = relationship("Deck", back_populates="creator")

class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    mana_cost = Column(Integer, nullable=False) # from 0 to 10
    rarity = Column(String, nullable=False)  # common, rare, epic, legendary

class UserCard(Base):
    __tablename__ = "user_cards"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity = Column(Integer, default=1)
    user = relationship("User", back_populates="cards")
    card = relationship("Card")

class Deck(Base):
    __tablename__ = "decks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    description = Column(String, nullable=True)
    creator = relationship("User", back_populates="decks")
    cards = relationship("DeckCard", back_populates="deck")

class DeckCard(Base):
    __tablename__ = "deck_cards"
    id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    deck = relationship("Deck", back_populates="cards")
    card = relationship("Card")