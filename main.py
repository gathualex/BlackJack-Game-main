"""
This is the main entry point for the application
it contains the main flask app and socketio instance
websockets are used to communicate with the client and
the game logic is handled in game_logic.py
"""
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, send, leave_room

from game_logic import shuffle_deck, deal_card, game_state, calculate_score, form_string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['transports'] = 'websocket'
socketio = SocketIO(app)

# initialize game state
clients = []


@app.route('/')
def index():
    """
    Render the index page
    this is the main project entry point
    :return:
    """
    return render_template('index.html')


@socketio.on('connect')
def on_connect():
    """
    Handle client connection
    ensure that the client is connected
    :return:
    """
    print('Client connected')
    pass


@socketio.on('join_game')
def on_join(name):
    """
    Handle client joining the game room
    Add the client to the clients list as well as the game state

    :param name:
    :return:
    """
    # join the room
    join_room('room')

    # get the key value of name in clients list
    names = [client['name'] for client in clients]

    # check if the name key is already taken
    if name in names:
        # send an error
        emit('error', {'message': 'Name already taken'})
        return

    # add the client to the list of clients
    clients.append(
        {
            'name': name,
            'id': request.sid,
            'hand': [],
            'score': 0,
            'stand': False,
            'hit': False,
            'bust': False,
            'win': False,
        })
    # check if the game state is waiting
    # if so, add the player to the game
    # if not, start a new game
    if game_state['status'] == 'waiting':
        if len(game_state['players']) < 2:
            print('joining existing game')
            game_state['players'] = clients

        # send the players in the game
        if len(clients) >= 2:
            print('Starting game')
            # to be used for new users joining the game
            # within the window of waiting the game to start
            game_state['about_to_start'] = True
            # start a countdown of 30 seconds to start the game
            send(
                {
                    'game_state': game_state,
                    'message': 'Starting game',
                    'waiting': True
                },
                to='room'
            )

        else:
            print('Waiting for players')
            # send a message to the client that they are waiting for players
            emit(
                'Wait_for_players',
                {
                    'players': game_state['players']
                },
                to='room'
            )
    else:
        print('game is full')
        emit('error', {'message': 'Game is full'})
        return

@socketio.on('disconnect')
def on_disconnect():
    """
    Handle client disconnect
    on disconnect, remove the client from the clients list
    and the game state
    :return:
    """
    # remove the client dict with the id from the clients list
    for item in clients.copy():
        if item.get('id') == request.sid:
            clients.remove(item)
            break
    for item in game_state['players'].copy():
        if item.get('id') == request.sid:
            game_state['players'].remove(item)
            break

    # remove the client from the room
    leave_room('room')
    # print(f'clients: {clients}')
    # print(f"game state clients {game_state['players']}")
    print('Client disconnected')

@socketio.on('start_game')
def on_start_game():
    """
    Handle client starting the game
    First, ensure that the game is in the waiting state
    Then, shuffle the deck
    Deal each player and dealer a card at a time and broadcast to all clients in the room
    :return:
    """
    # ensure that the game is in the waiting state
    if game_state['status'] == 'waiting':
        game_state['status'] = 'started'
        game_state['about_to_start'] = False
        # get seed id from an id in the clients list
        seed = clients[0]['id']
        # shuffle the deck
        shuffle_deck(seed=seed)

        # update game id
        game_state['deck_id'] = seed
        emit(
            'game_started',
            {
                'game_state': game_state
            },
            to='room'
        )
        # deal each player and dealer a card at a time and broadcast to all clients in the room
        for i in range(2):
            # deal dealer cards
            dealer_card = deal_card()
            game_state['dealer'][0]['hand'].append(dealer_card)

            # deal each player cards
            for player in game_state['players']:
                card = deal_card()
                player['hand'].append(card)

            # update score for each player
            for player in game_state['players']:
                score = calculate_score(player['hand'])
                # print(f'player : {player} score: {score}')
                player['score'] = score

            dealer = game_state['dealer'][0]
            # calculate dealers score
            dealer['score'] = calculate_score(dealer['hand'])

            emit(
                'card_dealt',
                {
                    'game_state': game_state
                },
                to='room'
            )
            socketio.sleep(2)

@socketio.on('player_hit')
def on_player_hit():
    card = deal_card()
    for player in game_state['players']:
        if player['id'] == request.sid:
            player['hand'].append(card)
            player['hit'] = True
            player['stand'] = False
            player['score'] = calculate_score(player['hand'])

            # check if player has busted
            if player['score'] > 21:
                player['bust'] = True
            elif player['score'] == 21:
                # set game state to game over and set winner to player
                game_state['status'] = 'game_over'
                game_state['winner'] = player['name']
                player['win'] = True
                print(f'player {player["name"]} has won')
                emit(
                    'card_dealt',
                    {
                        'game_state': game_state
                    },
                    to='room'
                )
                emit(
                    'game_over',
                    {
                        'game_state': game_state,
                    },
                    to='room'
                )
                break

            emit(
                'card_dealt',
                {
                    'game_state': game_state
                },
                to='room'
            )

            # check if all players have busted
            if all(player['bust'] for player in game_state['players']):
                print('all players have busted')
                game_state['status'] = 'game_over'
                game_state['winner'] = 'dealer'
                emit(
                    'game_over',
                    {
                        'game_state': game_state,
                    },
                    to='room'
                )
                break

@socketio.on('player_stand')
def on_player_stand():
    # update player status to stand
    for player in game_state['players']:
        if player['id'] == request.sid:
            player['stand'] = True
            player['hit'] = False
            # notify the client that they have stood,
            # card dealt is used here necessarily to update the game state
            # but not to stand the player
            emit(
                'card_dealt',
                {
                    'game_state': game_state
                },
                to='room'
            )
            break

    # check if all players have stood  and if so, start dealer turn also if a player bust and all other players stand
    if all(player['stand'] or player['bust'] for player in game_state['players']):
        print('starting dealer turn')
        # set game state to dealer turn
        game_state['status'] = 'dealer_turn'

        # send the updated game state to the clients
        emit(
            'dealer_turn',
            {
                'game_state': game_state,
                'message': 'Dealer flips over their card'
            },
            to='room'
        )
        # sleep for 2 seconds
        socketio.sleep(2)
        # check if dealer has busted
        if game_state['dealer'][0]['score'] > 21:
            game_state['status'] = 'game_over'
            game_state['dealer'][0]['bust'] = True
            emit(
                'game_over',
                {
                    'game_state': game_state,
                },
                to='room'
            )
        # check if dealer has a score of between 17 and 21 and if so, compare scores with players
        # and if no players have a higher score, dealer wins
        elif 17 <= game_state['dealer'][0]['score'] <= 21:
            # check if any player has a higher score than the dealer and the dealer has not busted
            if all(player['score'] < game_state['dealer'][0]['score'] for player in game_state['players'] if
                   not player['bust']):
                game_state['status'] = 'game_over'
                game_state['winner'] = game_state['dealer'][0]['name']
                emit(
                    'game_over',
                    {
                        'game_state': game_state,
                    },
                    to='room'
                )
            else:
                # check if any player has a score of 21
                if any(player['score'] == 21 for player in game_state['players']):
                    # set game state to game over and set winner to player
                    game_state['status'] = 'game_over'
                    winners = []
                    for player in game_state['players']:
                        if player['score'] == 21:
                            winners.append(player['name'])

                    # if more than one player has a score of 21, set winner to 'tie'
                    if len(winners) > 1:
                        game_state['winner'] = form_string(winners)
                    else:
                        game_state['winner'] = winners[0]
                    # update  client game state
                    emit(
                        'game_over',
                        {
                            'game_state': game_state,
                        },
                        to='room'
                    )
                else:
                    winner = []
                    # check if any player has a score higher than the dealer
                    for player in game_state['players']:
                        if player['score'] > game_state['dealer'][0]['score']:
                            game_state['status'] = 'game_over'
                            winner.append(player['name'])

                    # if more than one player has a higher score than the dealer, set winner to 'tie'
                    if len(winner) > 1:
                        game_state['winner'] = form_string(winner)
                    else:
                        game_state['winner'] = winner[0]
                    # update  client game state
                    emit(
                        'game_over',
                        {
                            'game_state': game_state,
                        },
                        to='room'
                    )

        # if dealer has a score of less than 17, hit until score is 17 or more
        elif game_state['dealer'][0]['score'] < 17:
            while game_state['dealer'][0]['score'] < 17:
                print('dealer hits')
                card = deal_card()
                game_state['dealer'][0]['hand'].append(card)
                # print(f'dealer\'s hand is now {game_state["dealer"][0]["hand"]}')
                game_state['dealer'][0]['score'] = calculate_score(game_state['dealer'][0]['hand'])
                # send the updated game state to the clients
                emit(
                    'dealer_turn',
                    {
                        'game_state': game_state,
                        'message': 'Dealer hits'
                    },
                    to='room'
                )
                # send the updated game state to the clients
                emit(
                    'card_dealt',
                    {
                        'game_state': game_state
                    },
                    to='room'
                )
                # check if dealer has busted
                if game_state['dealer'][0]['score'] > 21:
                    print('dealer has busted')
                    game_state['status'] = 'game_over'
                    game_state['dealer'][0]['bust'] = True
                    # all players that have not busted win
                    winners = []
                    for player in game_state['players']:
                        if not player['bust']:
                            winners.append(player['name'])

                    # if more than one player has a score of 21, set winner to 'tie'
                    if len(winners) > 1:
                        game_state['winner'] = form_string(winners)
                    else:
                        game_state['winner'] = winners[0]

                    emit(
                        'game_over',
                        {
                            'game_state': game_state,
                        },
                        to='room'
                    )
                    break
                # check if dealer has a score of between 17 and 21 and if so, compare scores with players
                # and if no players have a higher score, dealer wins
                elif 17 <= game_state['dealer'][0]['score'] <= 21:
                    # check if any player has a higher score than the dealer
                    if all(player['score'] < game_state['dealer'][0]['score'] for player in game_state['players']):
                        game_state['status'] = 'game_over'
                        game_state['winner'] = game_state['dealer'][0]['name']

                        emit(
                            'game_over',
                            {
                                'game_state': game_state,
                            },
                            to='room'
                        )
                        break
                    else:
                        # check if any player has a score higher than the dealer
                        winners = []
                        for player in game_state['players']:
                            if player['score'] > game_state['dealer'][0]['score'] and not player['bust']:
                                game_state['status'] = 'game_over'
                                winners.append(player['name'])

                        # if more than one player has a higher score than the dealer, set winner to 'tie'
                        if len(winners) > 1:
                            game_state['winner'] = form_string(winners)
                        else:
                            game_state['winner'] = winners[0]
                        # update  client game state
                        emit(
                            'game_over',
                            {
                                'game_state': game_state,
                            },
                            to='room'
                        )

            socketio.sleep(2)

@socketio.on('reset_game')
def on_reset_game():
    # print('resetting game')
    # reset the game state
    game_state['status'] = 'waiting'
    game_state['winner'] = None
    game_state['deck_id'] = None
    game_state['dealer'][0]['hand'] = []
    game_state['dealer'][0]['score'] = 0
    game_state['dealer'][0]['bust'] = False
    # increment turn
    game_state['turn'] += 1
    for player in game_state['players']:
        player['hand'] = []
        player['score'] = 0
        player['bust'] = False
        player['stand'] = False
        player['win'] = False

    # send the updated game state to the clients
    emit(
        'reset-game',
        {
            'game_state': game_state
        },
        to='room'
    )

@socketio.on('about_start')
def on_about_start(message):

    send(
        {
            'game_state': game_state,
            'message': message,
            'waiting': True
        },
    )


#run the app
if __name__ == '__main__':
    socketio.run(app, debug=True)
