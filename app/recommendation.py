from typing import Dict, List

def recommend_deck(
    user_collection: Dict[int, int],
    available_decks: List[Dict]
) -> Dict:
    """
    Deck recommendation strategy:
    1. Calculate match % for users collection.
    2. Take into account copies of card.
    3. TIe breaker strategy: choose deck with least manacost.
    4. Return best deck and cards, that should be crafted
    """
    if not available_decks:
        return {"deck_id": None, "deck_name": "No decks in database", "match_percentage": 0.0, "missing_cards": []}

    best_deck = None
    best_score = -1.0
    best_missing = []
    best_avg_mana = float('inf')

    for deck in available_decks:
        matched = 0
        missing = []
        deck_mana_sum = 0

        for dc in deck["cards"]:
            cid, cname, qty_req, mana = dc["card_id"], dc["name"], dc["quantity"], dc["mana_cost"]
            owned = user_collection.get(cid, 0)
            matched += min(owned, qty_req)
            if owned < qty_req:
                missing.append(f"{qty_req - owned}x {cname}")
            deck_mana_sum += mana * qty_req

        score = (matched / 30.0) * 100.0
        avg_mana = deck_mana_sum / 30.0

        if (score > best_score) or (score == best_score and avg_mana < best_avg_mana):
            best_score = score
            best_avg_mana = avg_mana
            best_deck = {"id": deck["id"], "name": deck["name"]}
            best_missing = missing

    return {
        "deck_id": best_deck["id"],
        "deck_name": best_deck["name"],
        "match_percentage": round(best_score, 2),
        "missing_cards": best_missing
    }