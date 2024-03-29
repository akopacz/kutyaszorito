#!/usr/bin/python3
import socket
import json
import numpy as np
import time

K = 7
SIZE = 512
TIMES = 2
GLOBAL_GAME_TIME = 10
RESPONSE_TIME = 1
PORT = 10000

class CustomException(Exception):
    pass

def is_valid_position(board, pos):
    return (len(pos) == 2 
        and all(isinstance(p, int) for p in pos)
        and 0 <= pos[0] < board.shape[0] 
        and 0 <= pos[1] < board.shape[1] 
        and board[pos] == 0)

def is_valid_move(old_pos, new_pos):
    return abs(old_pos[0] - new_pos[0]) <= 1 and abs(old_pos[1] - new_pos[1]) <= 1

def is_over(board, pos):
    return not any(
        (
            (board[i, j] == 0) 
            for i in range(max(0, pos[0]-1), min(K, pos[0] + 2)) 
            for j in range(max(0, pos[1]-1), min(K, pos[1] + 2)) 
        )
    )

def main():
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = ('localhost', PORT)
    print ( 'starting up on %s port %s' % server_address)
    sock.bind(server_address)

    # Listen for incoming connections
    sock.listen(1)

    players_connected = 0
    clients = [None, None]
    players = [1, 2]
    won = [0, 0]

    while players_connected < 2:
        print ( 'waiting for a connection')
        connection, client_address = sock.accept()
        clients[players_connected] = connection
        print ( 'connection from', client_address)
        try:
            connection.sendall(json.dumps({
                    "cmd": "init",
                    "K": K, 
                    "id": players[players_connected]
                }).encode())
            
            data = json.loads(connection.recv(SIZE).decode())
            if "status" not in data or data["status"] != "OK":
                print("Problem sending to client. Ignore connection attempt.")
                continue

            players_connected += 1
        except Exception:
            print("Problem sending to client. Ignore connection attempt.")


    # Wait for a connection
    try:
        for t in range(TIMES):
            positions = [(0, K//2), (K-1, K//2)]
            remaining_times = {
                0: GLOBAL_GAME_TIME,
                1: GLOBAL_GAME_TIME
            }
            board = np.zeros((K, K), dtype=int)
            board[positions[0]] = players[0]
            board[positions[1]] = players[1]

            play = True
            if t * 2 < TIMES:
                player_indexes = (0, 1)
            else:
                player_indexes = (1, 0)
            for ind in player_indexes:
                clients[ind].sendall(json.dumps({
                    "cmd": "start",
                    "coords": positions[ind],
                    "op_coords": positions[1 - ind]
                }).encode())
            for ind in player_indexes:
                data = json.loads(clients[ind].recv(SIZE).decode())
                if "status" not in data or data["status"] != "OK":
                    raise CustomException(json.dumps({
                            "cmd": "error",
                            "msg": "initialization of the game not confirmed",
                            "id": players[ind]
                        }))

            move_to, excl = None, None

            print("Player", players[player_indexes[0]], "starting")
            while play:
                for index in player_indexes:
                    if is_over(board, positions[index]):
                        # current player lost
                        play = False
                        won[1 - index] += 1
                        print("Player", players[1 - index], "won")
                        break
                    if is_over(board, positions[1 - index]):
                        # current player won
                        play = False
                        won[index] += 1
                        print("Player", players[index], "won")
                        break

                    conn = clients[index]

                    # start timer
                    start = time.time()
                    conn.sendall(json.dumps({
                            "cmd": "move",
                            "move": move_to,
                            "exclude": excl
                        }).encode())
                
                    try:
                        data = json.loads(conn.recv(SIZE).decode())
                        print("Player", players[index], data)
                        if "client_error" in data:
                            play = False
                            winner = players[1 - index]
                            break
                        else:
                            move_to = tuple(data["move"])
                            excl = tuple(data["exclude"])

                    except Exception:
                        raise CustomException(json.dumps({
                            "cmd": "error",
                            "msg": "invalid input",
                            "id": players[index]
                        }))

                    # stop timer
                    end = time.time()
                    time_elapsed = end - start
                    print("Player", players[index], "responded in", time_elapsed, "seconds")
                    if time_elapsed > RESPONSE_TIME:
                        remaining_times[index] -= (time_elapsed - RESPONSE_TIME)
                        if remaining_times[index] < 0:
                            # current player lost
                            play = False
                            won[1 - index] += 1
                            print("Player", players[index], "exceeded time limit. Client", 1 - index, "won")
                            break

                    if is_valid_position(board, move_to) and is_valid_move(positions[index], move_to):
                        board[positions[index]] = 0
                        positions[index] = move_to
                        board[move_to] = players[index]
                    else:
                        raise CustomException(json.dumps({
                            "cmd": "error",
                            "msg": "invalid move",
                            "id": players[index]
                        }))

                    if is_valid_position(board, excl):
                        board[excl] = -1
                    else:
                        raise CustomException(json.dumps({
                            "cmd": "error",
                            "msg": "cell can not be excluded",
                            "id": players[index]
                        }))
                    print(board)
            print("Game finished")
            print("remaining time (in seconds) - Player 1 (Client 0):", remaining_times[0], "Player 2 (Client 1) :", remaining_times[1])

        # Game over
        stats = [w/TIMES for w in won]
        print("Statistics:")
        print("Player {} (Client 0): {}".format(players[0], stats[0]))
        print("Player {} (Client 1): {}".format(players[1], stats[1]))

        if won[0] == won[1]:
            winner = None
        else:
            winner = 0 if won[0] > won[1] else 1
        if winner is not None:
            print("Winner is: Player {} (Client {})".format(players[winner], winner))
        else:
            print("Game outcome: Draw")
        
        for conn in clients:
            conn.sendall(json.dumps({
                            "cmd": "over",
                            "winner": players[winner] if winner is not None else None
                        }).encode())
        time.sleep(RESPONSE_TIME)
    except CustomException as e:
        for conn in clients:
            conn.sendall(e.args[0].encode())
    finally:
        # Clean up the connection
        for conn in clients:
            conn.close()

        sock.close()

if __name__ == "__main__":
    main()