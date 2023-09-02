"""
This module contains the game logic for the blackjack game.
It contains the game state and functions to manipulate the game state.
"""
import random

# Initialize deck
deck = []

# Initialize suits and ranks
suits = ['hearts', 'diamonds', 'clubs', 'spades']
ranks = ['ace', 2, 3, 4, 5, 6, 7, 8, 9, 10, 'jack', 'queen', 'king']

for suit in suits:
    for rank in ranks:
        # add card to deck
        # with value 11 for ace, 10 for face cards, and rank for number cards
        # and image path
        card_ = {
            'suit': suit,
            'rank': rank,
            'value': rank if isinstance(rank, int) else 10 if rank in ['jack', 'queen', 'king'] else 11,
            'image': f'/static/img/{rank}_of_{suit}.png'
        }
        deck.append(card_)

# Initialize game state
game_state = {
    'players': [],
    'dealer': [
        {
            'name': 'dealer',
            'id': 'dealer',
            'hand': [],
            'score': 0,
            'bust': False,
        }],
    'deck': [],
    'status': 'waiting',
    'shuffled': False,
    'deck_id': None,
    'turn': 0,
    'winner': None,
    'about_to_start': False,
}


def shuffle_deck(seed=None):
    """
    Shuffles the deck of cards and updates the game state.
    :param seed:
    :return:
    """
    #  do random seed
    random.seed(seed)
    random.shuffle(deck)
    # update shuffled deck
    game_state['deck'] = deck
    # update shuffled status
    game_state['shuffled'] = True


def deal_card():
    """
    Deals a card from the deck and returns it.
    :return:
    """
    return deck.pop()


def calculate_score(hand):
    score = 0
    num_aces = 0
    for card in hand:
        if card['rank'] == 'ace':
            num_aces += 1
            score += card['value']
        elif card['rank'] in ['jack', 'queen', 'king']:
            score += card['value']
        else:
            score += card['value']

    while num_aces > 0 and score > 21:
        score -= 10
        num_aces -= 1
    return score


def form_string(winners: list):
    # form a string where there are commas between all the names except the
    # last two names which are separated by 'and'
    # if there is only one winner, return the name

    if len(winners) == 1:
        return winners[0]
    else:
        return ', '.join(winners[:-1]) + ' and ' + winners[-1]
