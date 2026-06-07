"""
FULL HOUSE HACKATHON 2026
The Quant Bot

claudeimprovements.py
Description:
Multi-player tournament poker bot combining:
- Preflop hand-tier strategy
- Monte Carlo equity estimation
- Effective Hand Strength (EHS)
- Board texture analysis
- Opponent modelling
- Range-aware pressure decisions
- Dynamic bet sizing
- River nut-strength evaluation

Designed for long-run chip EV maximization in
multi-player tournament environments.
"""

import eval7
import random

BOT_NAME   = "The Quant Bot"
BOT_AVATAR = "robot_7"

# ─── Tunable parameters ────────────────────────────────────────────────────────

CHEAP_CALL_RATIO           = 0.33
MC_SIMULATIONS             = 300

# Range-based thinking
RANGE_ADVANTAGE_BONUS      = 0.04
RANGE_DISADVANTAGE_PENALTY = 0.03
RANGE_PRESSURE_EQUITY_MIN  = 0.35
RANGE_PRESSURE_PROB        = 0.18

# Board texture EHS adjustments
WET_BOARD_EHS_PENALTY       = 0.03
DRY_BOARD_EHS_BONUS         = 0.02
MULTIWAY_EHS_PENALTY        = 0.02

# Opponent modeling
MIN_OPPONENT_ACTIONS        = 8

# Post-flop EHS thresholds
EHS_MONSTER  = 0.85
EHS_STRONG   = 0.70
EHS_MEDIUM   = 0.50
EHS_DRAW     = 0.35

# Semi-bluff
POSTFLOP_SEMI_BLUFF_PROB       = 0.08

# Turn pressure
TURN_PRESSURE_PROB        = 0.12
TURN_PRESSURE_EQUITY_MIN  = 0.42
TURN_PRESSURE_EHS_MIN     = 0.52

# River thresholds
RIVER_NUT_SCORE_STRONG  = 0.92
RIVER_NUT_SCORE_MEDIUM  = 0.78
RIVER_BLUFF_PROB        = 0.10
RIVER_CALL_MARGIN       = 0.04
RIVER_SLOWPLAY_PROB     = 0.30

# Minimum equity to call on each street (fixes 0 turn/river fold bug)
TURN_MIN_EQUITY_TO_CALL  = 0.38
RIVER_MIN_EQUITY_TO_CALL = 0.35

# Preflop hand strength tiers
PREFLOP_VERY_STRONG  = 0.75
PREFLOP_STRONG       = 0.65
PREFLOP_MEDIUM       = 0.55
PREFLOP_PLAYABLE     = 0.35

# Preflop shove defence
PREFLOP_MEDIUM_SHOVE_LIMIT    = 0.50
PREFLOP_MASSIVE_DEFENSE_EQUITY = 0.70
PREFLOP_MONSTER_OVERBET_PROB  = 0.30

# Big pot
BIG_POT_RATIO                    = 0.35
BIG_POT_EHS_PENALTY              = 0.04
BIG_POT_FLOP_PRESSURE_REDUCTION  = 0.05
BIG_POT_TURN_PRESSURE_REDUCTION  = 0.05

# Overbet defence
FLOP_MASSIVE_DEFENSE_EHS  = 0.65
TURN_MASSIVE_DEFENSE_EHS  = 0.75
OVERBET_EHS_PENALTY       = 0.03
OVERBET_FLOP_PRESSURE_REDUCTION = 0.03
OVERBET_TURN_PRESSURE_REDUCTION = 0.03

# Medium hand value betting
MEDIUM_VALUE_EV_MARGIN    = 1.15

BOT_NAME   = "The Quant Bot"
BOT_AVATAR = "robot_2"

# ─── State ─────────────────────────────────────────────────────────────────────

OPPONENT_STATS    = {}
PROCESSED_ACTIONS = set()

# ─── Preflop equity table ──────────────────────────────────────────────────────

PRE_FLOP_EQUITY = {
    # Pocket pairs
    "AA": 0.85, "KK": 0.82, "QQ": 0.80, "JJ": 0.77,
    "TT": 0.75, "99": 0.72, "88": 0.69, "77": 0.66,
    "66": 0.63, "55": 0.60, "44": 0.57, "33": 0.54, "22": 0.51,
    # Ace-high suited
    "AKs": 0.67, "AQs": 0.66, "AJs": 0.64, "ATs": 0.63,
    "A9s": 0.61, "A8s": 0.59, "A7s": 0.57, "A6s": 0.56,
    "A5s": 0.56, "A4s": 0.55, "A3s": 0.54, "A2s": 0.53,
    # Ace-high offsuit
    "AKo": 0.65, "AQo": 0.64, "AJo": 0.62, "ATo": 0.60,
    "A9o": 0.58, "A8o": 0.56, "A7o": 0.55, "A6o": 0.54,
    "A5o": 0.54, "A4o": 0.53, "A3o": 0.52, "A2o": 0.51,
    # King-high suited
    "KQs": 0.63, "KJs": 0.61, "KTs": 0.59, "K9s": 0.57,
    "K8s": 0.56, "K7s": 0.55, "K6s": 0.54, "K5s": 0.53,
    # King-high offsuit
    "KQo": 0.61, "KJo": 0.59, "KTo": 0.57, "K9o": 0.55,
    # Queen-high suited
    "QJs": 0.60, "QTs": 0.58, "Q9s": 0.56, "Q8s": 0.55,
    # Queen-high offsuit
    "QJo": 0.58, "QTo": 0.56, "Q9o": 0.54,
    # Jack-high suited / connected
    "JTs": 0.59, "J9s": 0.57, "J8s": 0.55,
    "JTo": 0.57,
    # Connected suited
    "T9s": 0.57, "T8s": 0.55, "98s": 0.56, "97s": 0.54,
    "87s": 0.54, "86s": 0.52, "76s": 0.53, "75s": 0.51,
    "65s": 0.52, "64s": 0.50, "54s": 0.51, "53s": 0.49,
    # Offsuit connectors
    "T9o": 0.55, "98o": 0.54, "87o": 0.52, "76o": 0.51, "65o": 0.50,
    # Garbage benchmark
    "72o": 0.35,
}

# ─── Opponent tracking ─────────────────────────────────────────────────────────

def update_opponent_stats(game_state):
    my_seat = game_state["seat_to_act"]
    for i, action in enumerate(game_state["action_log"]):
        action_id = (game_state["hand_id"], i)
        if action_id in PROCESSED_ACTIONS:
            continue
        PROCESSED_ACTIONS.add(action_id)
        seat = action.get("seat")
        act  = action.get("action")
        if seat is None or seat == my_seat:
            continue
        if seat not in OPPONENT_STATS:
            OPPONENT_STATS[seat] = {
                "raises": 0, "calls": 0, "folds": 0,
                "checks": 0, "all_ins": 0, "total": 0,
            }
        stats = OPPONENT_STATS[seat]
        if   act == "raise":  stats["raises"]  += 1
        elif act == "call":   stats["calls"]   += 1
        elif act == "fold":   stats["folds"]   += 1
        elif act == "check":  stats["checks"]  += 1
        elif act == "all_in": stats["all_ins"] += 1
        stats["total"] += 1


def classify_opponents():
    total  = sum(s["total"]  for s in OPPONENT_STATS.values())
    raises = sum(s["raises"] for s in OPPONENT_STATS.values())
    calls  = sum(s["calls"]  for s in OPPONENT_STATS.values())
    folds  = sum(s["folds"]  for s in OPPONENT_STATS.values())
    checks = sum(s["checks"] for s in OPPONENT_STATS.values())
    if total < MIN_OPPONENT_ACTIONS:
        return "unknown"
    if raises / total >= 0.25:              return "aggressive"
    if (calls + checks) / total >= 0.65:   return "passive"
    if calls / total >= 0.35 and folds / total <= 0.25: return "loose"
    if folds / total >= 0.45:              return "tight"
    return "unknown"

# ─── Hand / card helpers ────────────────────────────────────────────────────────

def get_hand_name(cards):
    rank_order = "23456789TJQKA"
    r1, r2 = cards[0][0], cards[1][0]
    s1, s2 = cards[0][1], cards[1][1]
    if r1 == r2:
        return r1 + r2
    sorted_ranks = sorted([r1, r2], key=lambda r: rank_order.index(r), reverse=True)
    return "".join(sorted_ranks) + ("s" if s1 == s2 else "o")

# ─── Street filtering ───────────────────────────────────────────────────────────

def get_street_actions(game_state):
    """Return only actions from the current betting street."""
    actions = game_state["action_log"]
    current = game_state["street"]
    if current == "preflop":
        return actions
    street_order   = ["preflop", "flop", "turn", "river"]
    target         = street_order.index(current)
    transitions    = 0
    for i, a in enumerate(actions):
        if a.get("action") == "check":
            transitions += 1
            if transitions == target:
                return actions[i + 1:]
    return actions

# ─── NEW: Relative sizing functions ────────────────────────────────────────────

def get_bb_size(game_state):
    """Extract the big blind amount from the action log."""
    for a in game_state["action_log"]:
        if a.get("action") == "big_blind":
            return max(1, a["amount"])
    return 100


def make_preflop_raise(game_state, raises, raise_type,
                       my_stack, my_bet_this_street):
    """
    Size preflop raises relative to the last aggressor's bet or the BB.

    open  → 2.5–3.0x BB depending on position
    3-bet → 3.0x their open raise amount
    4-bet → 2.3x their 3-bet amount
    5bet+ → shove (all-in)

    All results are capped at our remaining stack.
    """
    bb_size   = get_bb_size(game_state)
    min_raise = game_state["min_raise_to"]
    stack_cap = my_stack + my_bet_this_street

    if raise_type == "open":
        position   = get_position(game_state)
        multiplier = 2.5 if position in ("late", "blinds") else 3.0
        amount     = int(bb_size * multiplier)

    elif raise_type == "3bet":
        their_amount = raises[-1]["amount"] if raises else int(bb_size * 3)
        amount       = int(their_amount * 3.0)

    elif raise_type == "4bet":
        their_amount = raises[-1]["amount"] if raises else int(bb_size * 9)
        amount       = int(their_amount * 2.3)

    else:
        # 5-bet or deeper: shove
        return stack_cap

    return min(max(amount, min_raise), stack_cap)


def make_postflop_raise(amount_owed, pot, street,
                        my_stack, my_bet_this_street,
                        min_raise, texture=None):
    """
    Size postflop raises relative to what we're facing.

    Facing a bet  → raise to N× their bet:
                    flop  2.8x, turn 2.3x, river 2.0x
                    Wet boards bump multiplier +0.3; dry boards -0.2
    No bet (we lead) → pot fraction:
                    flop 0.55, turn 0.65, river 0.65
                    Wet +0.10, dry -0.05

    All capped at our stack.
    """
    stack_cap = my_stack + my_bet_this_street

    # Board wetness modifier
    wet_adj = 0.0
    if texture:
        if texture.get("board_type") == "wet":  wet_adj =  0.10
        elif texture.get("board_type") == "dry": wet_adj = -0.05

    if amount_owed > 0:
        # Raise relative to their bet
        base = {"flop": 2.8, "turn": 2.3, "river": 2.0}.get(street, 2.5)
        multiplier = base + wet_adj * 0.3   # scale wet adj down for multipliers
        amount = int(amount_owed * multiplier)
    else:
        # Lead bet — pot fraction
        base = {"flop": 0.55, "turn": 0.65, "river": 0.65}.get(street, 0.60)
        fraction = base + wet_adj
        amount = int(pot * fraction)

    return min(max(amount, min_raise), stack_cap)

# ─── Monte Carlo equity estimation ─────────────────────────────────────────────

def estimate_postflop_equity(game_state, my_cards, board_cards,
                              opponent_range_type="wide"):
    hero  = [eval7.Card(c) for c in my_cards]
    board = [eval7.Card(c) for c in board_cards]
    active_opponents = 0
    folded_players   = 0
    for player in game_state["players"]:
        if player["seat"] == game_state["seat_to_act"]:
            continue
        if player.get("is_folded"):
            folded_players += 1
        elif player.get("is_active"):
            active_opponents += 1
    if active_opponents < 1:
        active_opponents = 1
    deck = eval7.Deck()
    for card in hero + board:
        deck.cards.remove(card)
    wins = 0
    ties = 0.0
    for _ in range(MC_SIMULATIONS):
        deck.shuffle()
        cursor = folded_players * 2
        opponents = []
        for _ in range(active_opponents):
            opponents.append(deck.cards[cursor:cursor + 2])
            cursor += 2
        cards_needed = 5 - len(board)
        full_board   = board + deck.cards[cursor:cursor + cards_needed]
        hero_value   = eval7.evaluate(hero + full_board)
        hero_wins    = True
        tie_count    = 0
        for opp_hand in opponents:
            opp_value = eval7.evaluate(opp_hand + full_board)
            if opp_value > hero_value:
                hero_wins = False
                break
            elif opp_value == hero_value:
                tie_count += 1
        if hero_wins:
            if tie_count == 0: wins += 1
            else:              ties += 1.0 / (tie_count + 1)
    equity = (wins + ties) / MC_SIMULATIONS
    range_discount = {"strong": 0.86, "medium": 0.93, "wide": 1.0, "unknown": 0.96}
    equity *= range_discount.get(opponent_range_type, 0.96)
    return max(0.0, min(1.0, equity))


def estimate_hand_potential(game_state, my_cards, board_cards):
    hero  = [eval7.Card(c) for c in my_cards]
    board = [eval7.Card(c) for c in board_cards]
    deck  = eval7.Deck()
    for card in hero + board:
        deck.cards.remove(card)
    active_opponents = max(1, sum(
        1 for p in game_state["players"]
        if p["seat"] != game_state["seat_to_act"]
        and not p.get("is_folded")
        and not p.get("is_all_in")
    ))
    ahead_now = behind_now = improve_later = get_outdrawn = 0
    for _ in range(MC_SIMULATIONS):
        deck.shuffle()
        cursor    = 0
        opponents = []
        for _ in range(active_opponents):
            opponents.append(deck.cards[cursor:cursor + 2])
            cursor += 2
        current_hero   = eval7.evaluate(hero + board)
        currently_ahead = all(eval7.evaluate(o + board) <= current_hero for o in opponents)
        cards_needed   = 5 - len(board)
        final_board    = board + deck.cards[cursor:cursor + cards_needed]
        final_hero     = eval7.evaluate(hero + final_board)
        finally_ahead  = all(eval7.evaluate(o + final_board) <= final_hero for o in opponents)
        if currently_ahead:
            ahead_now += 1
            if not finally_ahead: get_outdrawn += 1
        else:
            behind_now += 1
            if finally_ahead: improve_later += 1
    ppot = improve_later / behind_now if behind_now > 0 else 0.0
    npot = get_outdrawn  / ahead_now  if ahead_now  > 0 else 0.0
    return ppot, npot

# ─── Board texture ─────────────────────────────────────────────────────────────

def analyze_board_texture(board_cards):
    if len(board_cards) < 3:
        return {"flush_draw_possible": False, "straight_draw_possible": False,
                "paired_board": False, "high_card_board": False,
                "wetness_score": 0, "board_type": "unknown"}
    rank_order = "23456789TJQKA"
    ranks      = [c[0] for c in board_cards]
    suits      = [c[1] for c in board_cards]
    suit_counts = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    flush_draw_possible    = max(suit_counts.values()) >= 2
    paired_board           = len(set(ranks)) < len(ranks)
    high_card_board        = any(r in "AKQ" for r in ranks)
    rank_values            = sorted(set(rank_order.index(r) for r in ranks))
    connectedness          = sum(
        1 for i in range(len(rank_values) - 1)
        if rank_values[i+1] - rank_values[i] <= 2
    )
    straight_draw_possible = connectedness >= 2
    wetness_score = (
        (1 if flush_draw_possible    else 0) +
        (1 if straight_draw_possible else 0) +
        (1 if paired_board           else 0) +
        (0.5 if high_card_board      else 0)
    )
    board_type = "wet" if wetness_score >= 2 else "dry" if wetness_score <= 0.5 else "medium"
    return {"flush_draw_possible": flush_draw_possible,
            "straight_draw_possible": straight_draw_possible,
            "paired_board": paired_board, "high_card_board": high_card_board,
            "wetness_score": wetness_score, "board_type": board_type}

# ─── Range / opponent analysis ──────────────────────────────────────────────────

def estimate_current_action_range_type(game_state):
    current_actions = get_street_actions(game_state)
    saw_raise = any(a.get("action") in ("raise", "bet", "all_in") for a in current_actions)
    saw_call  = any(a.get("action") == "call"                      for a in current_actions)
    if saw_raise: return "strong"
    if saw_call:  return "medium"
    return "wide"


def estimate_board_range_advantage(texture, opponent_range_type):
    board_type = texture["board_type"]
    if texture["high_card_board"] and board_type in ("dry", "medium"):
        if opponent_range_type == "wide":   return "hero_advantage"
        if opponent_range_type == "medium": return "slight_hero_advantage"
        return "neutral"
    if texture["straight_draw_possible"] and board_type == "wet":
        if opponent_range_type in ("medium", "wide"):
            return "opponent_advantage"
    if board_type == "wet":  return "slight_opponent_advantage"
    if board_type == "dry":  return "slight_hero_advantage"
    return "neutral"


def estimate_nut_advantage(texture, range_advantage, opponent_range_type):
    board_type = texture["board_type"]
    if texture["high_card_board"] and board_type in ("dry", "medium"):
        if range_advantage in ("hero_advantage", "slight_hero_advantage"):
            return "hero_nut_advantage"
    if texture["straight_draw_possible"] and board_type == "wet":
        if opponent_range_type in ("medium", "wide"):
            return "opponent_nut_advantage"
    if texture["flush_draw_possible"] and board_type == "wet":
        if range_advantage == "hero_advantage": return "hero_nut_advantage"
        return "opponent_nut_advantage"
    if texture["paired_board"]: return "neutral"
    return "neutral"


def opponent_range_is_capped(game_state):
    current_actions = get_street_actions(game_state)
    checks = calls = raises = 0
    for a in current_actions:
        act = a.get("action")
        if act == "check":                      checks  += 1
        elif act == "call":                     calls   += 1
        elif act in ("raise","bet","all_in"):   raises  += 1
    if raises > 0:           return False
    if checks + calls >= 2:  return True
    return False


def estimate_fold_equity(game_state, texture, active_opponents):
    fold_equity = 0.28
    if texture["board_type"] == "dry":   fold_equity += 0.08
    elif texture["board_type"] == "wet": fold_equity -= 0.06
    if active_opponents >= 2:
        fold_equity -= 0.07 * (active_opponents - 1)
    current_actions = get_street_actions(game_state)
    for a in current_actions[-8:]:
        act = a.get("action")
        if act == "fold":                       fold_equity += 0.04
        elif act == "call":                     fold_equity -= 0.05
        elif act in ("raise","bet","all_in"):   fold_equity -= 0.06
    return max(0.05, min(0.70, fold_equity))

# ─── EV helpers ────────────────────────────────────────────────────────────────

def calculate_raise_ev(equity, fold_equity, pot, raise_cost):
    return (
        fold_equity * pot
        + (1 - fold_equity) * (equity * (pot + raise_cost) - (1 - equity) * raise_cost)
    )


def pot_safe_fraction(EV_call, pressure_ev, fraction):
    base = max(1, abs(EV_call), abs(pressure_ev))
    return base * fraction

# ─── Classify helpers ──────────────────────────────────────────────────────────

def estimate_aggression_strength(amount_owed, pot):
    ratio = amount_owed / max(1, pot)
    if ratio >= 1.0: return "huge"
    if ratio >= 0.6: return "large"
    if ratio >= 0.3: return "medium"
    return "small"


def classify_bet_pressure(amount_owed, pot):
    ratio = amount_owed / max(1, pot)
    if ratio >= 2.0: return "massive"
    if ratio >= 1.0: return "overbet"
    if ratio >= 0.5: return "large"
    return "normal"


def get_dynamic_pressure_size(street, texture, active_opponents, range_advantage,
                               ehs, equity, pressure_ev, EV_call):
    board_type = texture["board_type"]
    ev_gap     = pressure_ev - EV_call
    if street == "flop":
        size = {"dry": 0.50, "medium": 0.62, "wet": 0.78}.get(board_type, 0.62)
    elif street == "turn":
        size = {"dry": 0.60, "medium": 0.75, "wet": 0.90}.get(board_type, 0.75)
    else:
        size = 0.60
    if ev_gap > pot_safe_fraction(EV_call, pressure_ev, 0.35): size += 0.15
    elif ev_gap > pot_safe_fraction(EV_call, pressure_ev, 0.20): size += 0.08
    if ehs >= 0.62:            size += 0.07
    elif ehs <= 0.53:          size -= 0.05
    if active_opponents >= 3:  size += 0.10
    if range_advantage == "hero_advantage": size += 0.05
    return max(0.45, min(1.20, size))


def estimate_river_nut_strength(my_cards, board_cards):
    hero  = [eval7.Card(c) for c in my_cards]
    board = [eval7.Card(c) for c in board_cards]
    deck  = eval7.Deck()
    for card in hero + board:
        deck.cards.remove(card)
    hero_value = eval7.evaluate(hero + board)
    cards      = deck.cards
    better = tied = worse = 0
    for i in range(len(cards)):
        for j in range(i + 1, len(cards)):
            opp_value = eval7.evaluate([cards[i], cards[j]] + board)
            if opp_value > hero_value:    better += 1
            elif opp_value == hero_value: tied   += 1
            else:                         worse  += 1
    total = better + tied + worse
    if total == 0:
        return {"nut_score": 0.5, "better_combos": 0, "is_nuts": False, "near_nuts": False}
    nut_score = 1.0 - (better / total)
    return {"nut_score": nut_score, "better_combos": better,
            "is_nuts": better == 0, "near_nuts": nut_score >= RIVER_NUT_SCORE_STRONG}

# ─── Preflop helpers ───────────────────────────────────────────────────────────

def is_closing_preflop_action(game_state):
    bb_seat = next(
        (a.get("seat") for a in game_state["action_log"] if a.get("action") == "big_blind"),
        None
    )
    return game_state["seat_to_act"] == bb_seat


def nobody_raised_preflop(game_state):
    return not any(a.get("action") in ("raise", "bet") for a in game_state["action_log"])


def get_position(game_state):
    actions  = game_state["action_log"]
    my_seat  = game_state["seat_to_act"]
    sb_seat  = next((a["seat"] for a in actions if a["action"] == "small_blind"), None)
    bb_seat  = next((a["seat"] for a in actions if a["action"] == "big_blind"), None)
    if sb_seat is None or bb_seat is None:
        return "middle"
    all_seats = sorted(p["seat"] for p in game_state["players"])
    n = len(all_seats)
    if n == 0: return "middle"
    sb_idx     = all_seats.index(sb_seat)
    dealer_idx = (sb_idx - 1) % n
    if my_seat not in all_seats: return "middle"
    my_idx     = all_seats.index(my_seat)
    distance   = (my_idx - dealer_idx) % n
    if my_seat in (sb_seat, bb_seat): return "blinds"
    if distance <= 1:     return "late"
    if distance == n - 1: return "late"
    if distance <= 3:     return "middle"
    return "early"


def get_preflop_raises(game_state):
    """All raise/all_in actions in the preflop log (full history)."""
    result = []
    for a in game_state["action_log"]:
        if a.get("action") in ("raise", "all_in"):
            result.append(a)
    return result


def preflop_shove_cost(game_state):
    return game_state["amount_owed"] / max(
        1, game_state["your_stack"] + game_state["your_bet_this_street"]
    )


# ─── Main decision function ─────────────────────────────────────────────────────

def decide(game_state: dict) -> dict:
    update_opponent_stats(game_state)

    my_cards           = game_state["your_cards"]
    amount_owed        = game_state["amount_owed"]
    pot                = game_state["pot"]
    my_stack           = game_state["your_stack"]
    street             = game_state["street"]
    board_cards        = game_state["community_cards"]
    my_bet_this_street = game_state["your_bet_this_street"]
    can_check          = game_state["can_check"]
    min_raise          = game_state["min_raise_to"]
    stack_cap          = my_stack + my_bet_this_street

    # ── Preflop ────────────────────────────────────────────────────────────────

    if street == "preflop":
        hand           = get_hand_name(my_cards)
        equity         = PRE_FLOP_EQUITY.get(hand, 0.38)
        position       = get_position(game_state)
        raises         = get_preflop_raises(game_state)
        n_raises       = len(raises)
        shove_fraction = preflop_shove_cost(game_state)

        is_very_strong = equity >= PREFLOP_VERY_STRONG
        is_strong      = equity >= PREFLOP_STRONG
        is_medium      = equity >= PREFLOP_MEDIUM
        is_playable    = equity >= PREFLOP_PLAYABLE

        # Shorthand that calls make_preflop_raise with the right context
        def pfr(raise_type):
            return make_preflop_raise(
                game_state, raises, raise_type, my_stack, my_bet_this_street
            )

        # ── VERY STRONG (equity ≥ 0.75) ───────────────────────────────────────
        if is_very_strong:
            # Facing a shove: always call — gamble with the best hands
            if amount_owed > 0 and shove_fraction >= 0.50:
                return {"action": "call"}
            # 4-bet or deeper
            if n_raises >= 2:
                size = pfr("5bet+") if random.random() < PREFLOP_MONSTER_OVERBET_PROB else pfr("4bet")
                return {"action": "raise", "amount": size}
            # 3-bet
            if n_raises == 1:
                return {"action": "raise", "amount": pfr("3bet")}
            # Open — raise over any limp too
            if amount_owed > 0:
                return {"action": "raise", "amount": pfr("open")}
            return {"action": "raise", "amount": pfr("open")}

        # ── STRONG (equity 0.65 – 0.75) ───────────────────────────────────────
        if is_strong:
            if amount_owed > 0 and shove_fraction >= 0.50:
                if equity >= 0.72:
                    return {"action": "call"}
                return {"action": "fold"}
            if n_raises >= 2:
                # Top of tier (TT 99) → 4-bet; rest call
                if equity >= 0.72:
                    return {"action": "raise", "amount": pfr("4bet")}
                return {"action": "call"}
            if n_raises == 1:
                return {"action": "raise", "amount": pfr("3bet")}
            if amount_owed > 0:
                return {"action": "raise", "amount": pfr("3bet")}
            return {"action": "raise", "amount": pfr("open")}

        # ── MEDIUM (equity 0.55 – 0.65) ───────────────────────────────────────
        # Always see the flop; only fold to a shove > 50% of stack
        if is_medium:
            if amount_owed > 0 and shove_fraction > PREFLOP_MEDIUM_SHOVE_LIMIT:
                return {"action": "fold"}
            if n_raises >= 2:
                return {"action": "call"}
            if n_raises == 1:
                return {"action": "call"}
            if can_check:
                return {"action": "check"}
            if amount_owed > 0:
                return {"action": "call"}
            if position == "late":
                return {"action": "raise", "amount": pfr("open")}
            return {"action": "call"} if amount_owed > 0 else {"action": "check"}

        # ── PLAYABLE / SPECULATIVE (equity 0.35 – 0.55) ───────────────────────
        if is_playable:
            if amount_owed > 0 and shove_fraction > 0.20:
                return {"action": "fold"}
            if can_check:
                return {"action": "check"}
            bb_size = get_bb_size(game_state)
            if amount_owed <= bb_size * CHEAP_CALL_RATIO * 3:
                return {"action": "call"}
            return {"action": "fold"}

        # ── TRASH ─────────────────────────────────────────────────────────────
        if can_check:
            return {"action": "check"}
        return {"action": "fold"}

    # ── Post-flop equity and texture ──────────────────────────────────────────

    opponent_range_type = estimate_current_action_range_type(game_state)

    try:
        equity = estimate_postflop_equity(
            game_state, my_cards, board_cards, opponent_range_type
        )
    except Exception:
        equity = 0.45

    if street == "river":
        ppot = npot = 0.0
    else:
        try:
            ppot, npot = estimate_hand_potential(game_state, my_cards, board_cards)
        except Exception:
            ppot = npot = 0.1

    ehs = max(0.0, min(1.0, equity * (1 - npot) + (1 - equity) * ppot))

    texture         = analyze_board_texture(board_cards)
    range_advantage = estimate_board_range_advantage(texture, opponent_range_type)
    nut_advantage   = estimate_nut_advantage(texture, range_advantage, opponent_range_type)

    if   range_advantage == "hero_advantage":            ehs += RANGE_ADVANTAGE_BONUS
    elif range_advantage == "slight_hero_advantage":     ehs += RANGE_ADVANTAGE_BONUS / 2
    elif range_advantage == "opponent_advantage":        ehs -= RANGE_DISADVANTAGE_PENALTY
    elif range_advantage == "slight_opponent_advantage": ehs -= RANGE_DISADVANTAGE_PENALTY / 2

    active_opponents = sum(
        1 for p in game_state["players"]
        if p["seat"] != game_state["seat_to_act"]
        and not p.get("is_folded")
        and not p.get("is_all_in")
    )

    if texture["board_type"] == "wet":   ehs -= WET_BOARD_EHS_PENALTY
    elif texture["board_type"] == "dry": ehs += DRY_BOARD_EHS_BONUS
    if active_opponents >= 3:            ehs -= MULTIWAY_EHS_PENALTY

    stack_committed = pot / max(1, my_stack + pot)
    big_pot = stack_committed >= BIG_POT_RATIO
    if big_pot: ehs -= BIG_POT_EHS_PENALTY

    ehs = max(0.0, min(1.0, ehs))

    # ── Pot odds and EV ────────────────────────────────────────────────────────

    if amount_owed > 0:
        pot_odds = amount_owed / (pot + amount_owed)
        EV_call  = equity * pot - (1 - equity) * amount_owed
    else:
        pot_odds = 0.0
        EV_call  = equity * pot

    EV_fold = 0.0

    # Reference raise for EV_raise calculation (used in pressure logic)
    ref_raise_to   = make_postflop_raise(
        amount_owed, pot, street, my_stack, my_bet_this_street, min_raise, texture
    )
    ref_raise_cost = ref_raise_to - my_bet_this_street
    EV_raise       = equity * (pot + ref_raise_cost) - (1 - equity) * ref_raise_cost

    # ── Shared post-flop setup ─────────────────────────────────────────────────

    bet_pressure = classify_bet_pressure(amount_owed, pot)

    if bet_pressure == "overbet":
        ehs -= OVERBET_EHS_PENALTY
        ehs = max(0.0, min(1.0, ehs))

    fold_equity = estimate_fold_equity(game_state, texture, active_opponents)

    range_pressure_prob = RANGE_PRESSURE_PROB
    turn_pressure_prob  = TURN_PRESSURE_PROB
    if bet_pressure == "overbet":
        range_pressure_prob = max(0, range_pressure_prob - OVERBET_FLOP_PRESSURE_REDUCTION)
        turn_pressure_prob  = max(0, turn_pressure_prob  - OVERBET_TURN_PRESSURE_REDUCTION)
    if big_pot:
        range_pressure_prob = max(0, range_pressure_prob - BIG_POT_FLOP_PRESSURE_REDUCTION)
        turn_pressure_prob  = max(0, turn_pressure_prob  - BIG_POT_TURN_PRESSURE_REDUCTION)

    # ── Massive overbet defence (flop/turn) ───────────────────────────────────

    if amount_owed > 0 and bet_pressure == "massive":
        if street == "flop":
            return {"action": "call"} if ehs >= FLOP_MASSIVE_DEFENSE_EHS else {"action": "fold"}
        if street == "turn":
            return {"action": "call"} if ehs >= TURN_MASSIVE_DEFENSE_EHS else {"action": "fold"}

    # ── Turn / river minimum equity fold ─────────────────────────────────────

    if amount_owed > 0 and street == "turn"  and equity < TURN_MIN_EQUITY_TO_CALL:
        return {"action": "fold"}
    if amount_owed > 0 and street == "river" and equity < RIVER_MIN_EQUITY_TO_CALL:
        return {"action": "fold"}

    # ── Flop range pressure ───────────────────────────────────────────────────

    if street == "flop":
        pressure_size_frac = get_dynamic_pressure_size(
            "flop", texture, active_opponents, range_advantage,
            ehs, equity,
            calculate_raise_ev(equity, fold_equity, pot,
                make_postflop_raise(0, pot, "flop", my_stack, my_bet_this_street, min_raise, texture) - my_bet_this_street),
            EV_call,
        )
        # Use relative sizing but blend with dynamic pressure fraction
        pressure_raise_to = min(
            max(min_raise, int(pot * pressure_size_frac)),
            stack_cap
        )
        pressure_ev = calculate_raise_ev(equity, fold_equity, pot, pressure_raise_to - my_bet_this_street)

        if (
            can_check
            and range_advantage in ("hero_advantage", "slight_hero_advantage")
            and EHS_MEDIUM <= ehs < EHS_STRONG
            and equity >= RANGE_PRESSURE_EQUITY_MIN
            and pressure_ev > EV_call
            and random.random() < range_pressure_prob
        ):
            return {"action": "raise", "amount": pressure_raise_to}

    # ── Turn range pressure ───────────────────────────────────────────────────

    if street == "turn":
        turn_size_frac = get_dynamic_pressure_size(
            "turn", texture, active_opponents, range_advantage,
            ehs, equity,
            calculate_raise_ev(equity, fold_equity, pot,
                make_postflop_raise(0, pot, "turn", my_stack, my_bet_this_street, min_raise, texture) - my_bet_this_street),
            EV_call,
        )
        turn_raise_to = min(
            max(min_raise, int(pot * turn_size_frac)),
            stack_cap
        )
        turn_pressure_ev = calculate_raise_ev(equity, fold_equity, pot, turn_raise_to - my_bet_this_street)

        if (
            can_check
            and range_advantage in ("hero_advantage", "slight_hero_advantage")
            and TURN_PRESSURE_EHS_MIN <= ehs < EHS_STRONG
            and equity >= TURN_PRESSURE_EQUITY_MIN
            and turn_pressure_ev > EV_call
            and random.random() < turn_pressure_prob
        ):
            return {"action": "raise", "amount": turn_raise_to}

    # ── River strategy ─────────────────────────────────────────────────────────

    if street == "river":
        try:
            river_nut = estimate_river_nut_strength(my_cards, board_cards)
            nut_score = river_nut["nut_score"]
            is_nuts   = river_nut["is_nuts"]
            near_nuts = river_nut["near_nuts"]
        except Exception:
            nut_score = equity
            is_nuts   = equity >= 0.97
            near_nuts = equity >= 0.90

        if   nut_advantage == "hero_nut_advantage":     nut_score = min(1.0, nut_score + 0.03)
        elif nut_advantage == "opponent_nut_advantage": nut_score = max(0.0, nut_score - 0.04)

        near_nuts = nut_score >= RIVER_NUT_SCORE_STRONG

        # River raise — always relative sizing
        river_raise_to = make_postflop_raise(
            amount_owed, pot, "river", my_stack, my_bet_this_street, min_raise, texture
        )
        river_raise_cost = river_raise_to - my_bet_this_street
        river_fold_equity = estimate_fold_equity(game_state, texture, active_opponents)
        river_raise_ev = calculate_raise_ev(equity, river_fold_equity, pot, river_raise_cost)

        if is_nuts:
            return {"action": "raise", "amount": river_raise_to}

        if near_nuts:
            if can_check and random.random() < RIVER_SLOWPLAY_PROB:
                return {"action": "check"}
            if can_check:
                return {"action": "raise", "amount": river_raise_to}
            if river_raise_ev > EV_call:
                return {"action": "raise", "amount": river_raise_to}
            return {"action": "call"}

        if nut_score >= RIVER_NUT_SCORE_MEDIUM and equity >= 0.58:
            if can_check:
                return {"action": "raise", "amount": river_raise_to}
            if equity >= pot_odds + RIVER_CALL_MARGIN:
                return {"action": "call"}
            return {"action": "fold"}

        if equity >= pot_odds + RIVER_CALL_MARGIN:
            if can_check:
                return {"action": "check"}
            return {"action": "call"}

        if (
            can_check
            and range_advantage in ("hero_advantage", "slight_hero_advantage")
            and river_fold_equity >= 0.38
            and river_raise_ev > EV_call
            and random.random() < RIVER_BLUFF_PROB
        ):
            return {"action": "raise", "amount": river_raise_to}

        if can_check:
            return {"action": "check"}
        return {"action": "fold"}

    # ── Flop / Turn value and protection logic ────────────────────────────────

    # Compute raise size once using relative sizing
    raise_to   = make_postflop_raise(
        amount_owed, pot, street, my_stack, my_bet_this_street, min_raise, texture
    )
    raise_cost = raise_to - my_bet_this_street
    EV_raise   = calculate_raise_ev(equity, fold_equity, pot, raise_cost)

    # Monster hand: value raise
    if ehs >= EHS_MONSTER:
        if can_check:
            return {"action": "raise", "amount": raise_to}
        if EV_raise > EV_call:
            return {"action": "raise", "amount": raise_to}
        return {"action": "call"}

    # Strong hand: value / protection raise
    if ehs >= EHS_STRONG:
        if EV_raise > EV_call:
            return {"action": "raise", "amount": raise_to}
        if can_check:
            return {"action": "check"}
        return {"action": "call"}

    # Medium hand: thin value in good spots, otherwise pot control
    if ehs >= EHS_MEDIUM:
        medium_raise_to = make_postflop_raise(
            0, pot, street, my_stack, my_bet_this_street, min_raise, texture
        )
        medium_cost = medium_raise_to - my_bet_this_street
        medium_ev   = calculate_raise_ev(equity, fold_equity, pot, medium_cost)

        if (
            can_check
            and active_opponents == 1
            and range_advantage in ("hero_advantage", "slight_hero_advantage")
            and medium_ev > EV_call * MEDIUM_VALUE_EV_MARGIN
        ):
            return {"action": "raise", "amount": medium_raise_to}

        if can_check:
            return {"action": "check"}
        if EV_call > EV_fold and equity > pot_odds:
            return {"action": "call"}
        return {"action": "fold"}

    # Draw / speculative hand
    if ehs >= EHS_DRAW:
        if not can_check and amount_owed <= pot * CHEAP_CALL_RATIO:
            return {"action": "call"}

        if can_check and ppot > 0.30 and random.random() < POSTFLOP_SEMI_BLUFF_PROB:
            bluff_raise_to = make_postflop_raise(
                0, pot, street, my_stack, my_bet_this_street, min_raise, texture
            )
            return {"action": "raise", "amount": bluff_raise_to}

        if can_check:
            return {"action": "check"}
        return {"action": "fold"}

    # Weak hand
    if can_check:
        return {"action": "check"}
    return {"action": "fold"}