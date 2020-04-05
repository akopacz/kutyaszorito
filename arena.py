import socket
import sys
import json
import numpy as np
import time

K = 3
SIZE = 512
TIMES = 4

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
    # get only valid moves
    moves = [(i, j) 
                for i in range(max(0, pos[0]-1), min(K, pos[0] + 2)) 
                for j in range(max(0, pos[1]-1), min(K, pos[1] + 2)) 
                    if board[i, j] == 0
            ]

    return len(moves) == 0

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = ('localhost', 10000)
print ( 'starting up on %s port %s' % server_address)
sock.bind(server_address)

# Listen for incoming connections
sock.listen(1)

players_connected = 0
clients = []
players = [1, 2]
won = [0, 0]

while players_connected < 2:
    print ( 'waiting for a connection')
    connection, client_address = sock.accept()
    clients.append((connection, client_address))
    print ( 'connection from', client_address)
    try:
        connection.sendall(json.dumps({
                "cmd": "init",
                "K": K, 
                "player": players[players_connected]
            }).encode())
        
        data = json.loads(connection.recv(SIZE).decode())
        if "status" not in data or data["status"] != "OK":
            print("Problem sending to client. Ignore connection attempt.")
        players_connected += 1
    except Exception:
        print("Problem sending to client. Ignore connection attempt.")


# Wait for a connection
try:
    for t in range(TIMES):
        # positions = [(0, K//2), (K-1, K//2)]
        positions = [(K-1, K//2), (0, K//2)]

        board = np.zeros((K, K), dtype=int)
        board[positions[0]] = players[0]
        board[positions[1]] = players[1]

        play = True
        if t * 2 < TIMES:
            player_indexes = (0, 1)
        else:
            player_indexes = (1, 0)
        for ind in player_indexes:
            clients[ind][0].sendall(json.dumps({
                "cmd": "start",
                "coords": positions[ind],
                "op_coords": positions[1 - ind]
                }).encode())

        time.sleep(0.5)
        move_to, excl = None, None

        print("Client", player_indexes[0], "starting")
        while play:
            for index in player_indexes:
                conn = clients[index][0]
                conn.sendall(json.dumps({
                        "cmd": "move",
                        "move": move_to,
                        "exclude": excl
                    }).encode())
            
                try:
                    data = json.loads(conn.recv(SIZE).decode())
                    print("Client", index, data)
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
                        "player": players[index]
                    }))

                if is_valid_position(board, move_to) and is_valid_move(positions[index], move_to):
                    board[positions[index]] = 0
                    positions[index] = move_to
                    board[move_to] = players[index]
                else:
                    raise CustomException(json.dumps({
                    "cmd": "error",
                    "msg": "invalid move",
                    "player": players[index]
                }))

                if is_valid_position(board, excl):
                    board[excl] = -1
                else:
                    raise CustomException(json.dumps({
                    "cmd": "error",
                    "msg": "invalid cell to exclude",
                    "player": players[index]
                }))
                print(board)

                opp_index = 1 - index
                if is_over(board, positions[opp_index]):
                    play = False
                    won[index] += 1
                    print("Client", index, "won")
                    break
                time.sleep(0.5)
    # Game over
    stats = [w/TIMES for w in won]
    print("Statistics:")
    print("Client 0:", stats[0])
    print("Client 1:", stats[1])

    if won[0] == won[1]:
        winner = None
    else:
        winner = 0 if won[0] > won[1] else 1
    print("Winner is: Client", winner)
    for conn, _ in clients:
        conn.sendall(json.dumps({
                        "cmd": "over",
                        "winner": players[winner] if winner else None
                    }).encode())
    time.sleep(0.5)
except CustomException as e:
    for conn, _ in clients:
        conn.sendall(e.args[0].encode())
finally:
    # Clean up the connection
    for conn, _ in clients:
        conn.close()
    
    sock.close()