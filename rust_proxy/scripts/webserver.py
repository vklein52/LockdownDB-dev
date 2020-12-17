# Just sends a few commands to the server for testing purposes
import json
import socket
import struct

HOST = 'localhost'
PORT = 7070

def receive_response(connection):
    size = int.from_bytes(connection.recv(4), "little")
    response_json = connection.recv(size).decode("utf-8")
    print(response_json)
    

def send_command(command_type, command, params=[]):
    command_json = json.dumps({"command_type": command_type, "command": command, "params": params})
    encoded_json = command_json.encode()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print("Connected to {}:{}".format(HOST, PORT))
        s.connect((HOST, PORT))
        header = len(encoded_json).to_bytes(4, 'little')
        message = header + encoded_json
        s.sendall(message)
        receive_response(s)

# send_command("EXECUTE",
#              """
#              create table if not exists cat_colors (
#              id integer primary key,
#              name text not null unique
#              )
#              """)
# send_command("EXECUTE",
#              """
#              create table if not exists cats (
#              id integer primary key,
#              name text not null,
#              color_id integer not null references cat_colors(id)
#              )
#              """)
# send_command("EXECUTE",
#              """
#              INSERT INTO cat_colors (name) values (?1)
#              """,
#              ["red"])
# send_command("EXECUTE",
#              """
#              INSERT INTO cats (name, color_id) values (?1, ?2)
#              """,
#              ["Tangerine", "1"])
# send_command("QUERY",
#              """
#              SELECT c.name, cc.name from cats c
#              INNER JOIN cat_colors cc
#              ON cc.id = c.color_id;
#              """,
#              )

send_command("QUERY",
             """
             SELECT name from cats
             """,
             )



# sample_command = "a sample command to 😂 run"
# send_command("QUERY", sample_command, ["yo", "yeet"])
# send_command("EXECUTE", sample_command)
# send_command("FAKE", sample_command)


