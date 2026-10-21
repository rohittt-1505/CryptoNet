
import socket
import json
import struct

from crypto_service import encrypt_message
from key_service import load_or_create_key

HOST = "127.0.0.1"
PORT = 5001


def receive_exact(connection, size):
    data = b""

    while len(data) < size:
        chunk = connection.recv(size - len(data))

        if not chunk:
            raise ConnectionError("Server disconnected unexpectedly.")

        data += chunk

    return data


def main():
    key = load_or_create_key()

    message = input("Enter your secret message: ").strip()

    if not message:
        print("Message cannot be empty.")
        return

    encrypted_data = encrypt_message(message, key)
    payload = json.dumps(encrypted_data).encode("utf-8")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect((HOST, PORT))

            # Send the message length first, followed by encrypted data.
            client.sendall(struct.pack("!I", len(payload)))
            client.sendall(payload)

            print("\nEncrypted data sent to server.")
            print("Original message was not sent as plain text.")

            header = receive_exact(client, 4)
            response_length = struct.unpack("!I", header)[0]

            if response_length == 0 or response_length > 100_000:
                raise ValueError("Invalid server response size.")

            response_data = receive_exact(client, response_length)
            response = json.loads(response_data.decode("utf-8"))

            print("Server status:", response["status"])
            print("Server response:", response["message"])

    except ConnectionRefusedError:
        print("Could not connect. Start server.py first.")

    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("Communication error:", error)


if __name__ == "__main__":
    main()
