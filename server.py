
import socket
import json
import struct

from crypto_service import decrypt_message
from key_service import load_or_create_key

HOST = "127.0.0.1"
PORT = 5001


def receive_exact(connection, size):
    data = b""

    while len(data) < size:
        chunk = connection.recv(size - len(data))

        if not chunk:
            raise ConnectionError("Client disconnected unexpectedly.")

        data += chunk

    return data


def start_server():
    key = load_or_create_key()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    print(f"CryptoNet Secure TCP Server running on {HOST}:{PORT}")
    print("Waiting for encrypted messages...")

    try:
        while True:
            connection, address = server.accept()

            with connection:
                print(f"\nClient connected: {address}")

                try:
                    header = receive_exact(connection, 4)
                    data_length = struct.unpack("!I", header)[0]

                    if data_length == 0 or data_length > 100_000:
                        raise ValueError("Invalid message size.")

                    payload = receive_exact(connection, data_length)
                    encrypted_data = json.loads(payload.decode("utf-8"))

                    original_message = decrypt_message(encrypted_data, key)

                    print("Encrypted message received successfully.")
                    print("Decrypted message:", original_message)

                    response = {
                        "status": "success",
                        "message": "Encrypted message received and verified."
                    }

                except Exception as error:
                    print("Message processing failed:", error)

                    response = {
                        "status": "error",
                        "message": "Message could not be verified or decrypted."
                    }

                response_bytes = json.dumps(response).encode("utf-8")
                connection.sendall(struct.pack("!I", len(response_bytes)))
                connection.sendall(response_bytes)

    except KeyboardInterrupt:
        print("\nServer stopped.")

    finally:
        server.close()


if __name__ == "__main__":
    start_server()
