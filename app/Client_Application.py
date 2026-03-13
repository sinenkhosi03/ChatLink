# client
import os
from socket import *
import datetime
import time
import json
import threading
import queue
import csv


class client_application:
    def __init__(self, ip_addr="0.0.0.0", peer_port=8000):
        self.server_ip = "196.47.245.85"
        self.server_port = 12000
        self.username = None
        self.ip_addr = ip_addr
        self.peer_port = peer_port

        self.client_socket = None
        self.udp_socket = None
        self.peer_socket = None
        self.peer_listener_socket = None

        self.message_queue = queue.Queue()
        self.waiting_for_response = False

        self.peer_lock = threading.Lock()
        self.listener_started = False
        self.peer_connected_event = threading.Event()

    # TCP / UDP CONNECTIONS
    def tcp_connect(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        client_socket.connect((server_ip, server_port))
        self.client_socket = client_socket

        print("connected to server")

        threading.Thread(target=self.tcp_receive_thread, daemon=True).start()

    def udp_connect(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

        self.udp_socket = socket(AF_INET, SOCK_DGRAM)
        self.udp_socket.bind(("", 0))

    def tcp_connect_peer(self, peer_ip, peer_port):
        try:
            peer_socket = socket(AF_INET, SOCK_STREAM)
            peer_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            peer_socket.connect((peer_ip, peer_port))

            with self.peer_lock:
                if self.peer_socket is not None:
                    try:
                        self.peer_socket.close()
                    except:
                        pass
                self.peer_socket = peer_socket

            self.peer_connected_event.set()
            print(f"connected to target client at {peer_ip}:{peer_port}")

            threading.Thread(target=self.peer_receive_thread, daemon=True).start()
            return True

        except Exception as e:
            print(f"Could not connect to target client at {peer_ip}:{peer_port}")
            print(f"Reason: {e}")
            return False

    def start_peer_listener(self):
        if self.listener_started:
            return

        listener = socket(AF_INET, SOCK_STREAM)
        listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        # Bind to all interfaces so another machine can connect
        listener.bind(("", self.peer_port))
        listener.listen(5)

        self.peer_listener_socket = listener
        self.listener_started = True

        print(f"\nWaiting for peer connection on port {self.peer_port}...")

        while True:
            try:
                incoming_socket, addr = listener.accept()

                with self.peer_lock:
                    if self.peer_socket is not None:
                        try:
                            self.peer_socket.close()
                        except:
                            pass
                    self.peer_socket = incoming_socket

                self.peer_connected_event.set()
                print(f"Peer connected from {addr[0]}:{addr[1]}")

                threading.Thread(target=self.peer_receive_thread, daemon=True).start()

            except Exception as e:
                print(f"Peer listener stopped: {e}")
                break

    # MESSAGE BUILDERS
    def send_command(self, command, body):
        header = {
            "msgType": "COMMAND",
            "command": command,
            "senderId": self.username,
            "timestamp": datetime.datetime.now().isoformat(),
            "bodyLength": len(json.dumps(body).encode())
        }

        return {
            "header": header,
            "body": body
        }

    def send_data(self, command, body):
        header = {
            "msgType": "DATA",
            "command": command,
            "senderId": self.username,
            "timestamp": datetime.datetime.now().isoformat(),
            "bodyLength": len(json.dumps(body).encode())
        }

        return {
            "header": header,
            "body": body
        }
    # SOCKET SENDS
    def send_message_tcp(self, message):
        self.client_socket.send((json.dumps(message) + '\n').encode())

    def send_message_udp(self, message):
        self.udp_socket.sendto(json.dumps(message).encode(), (self.server_ip, self.server_port))

    def send_message_peer(self, message):
        with self.peer_lock:
            if self.peer_socket is None:
                print("No peer is connected.")
                return False

            try:
                self.peer_socket.send((json.dumps(message) + '\n').encode())
                return True
            except Exception as e:
                print(f"Failed to send to peer: {e}")
                try:
                    self.peer_socket.close()
                except:
                    pass
                self.peer_socket = None
                self.peer_connected_event.clear()
                return False

    # MESSAGE RECEIVE / PROCESS
    def _try_unpack_nested_control(self, message_dict):
        """
        Some server responses are malformed and put a JSON string inside header['command'].
        This tries to rescue that nonsense.
        """
        try:
            header = message_dict.get("header", {})
            weird_command = header.get("command")

            if isinstance(weird_command, str) and weird_command.strip().startswith("{"):
                nested = json.loads(weird_command)
                if isinstance(nested, dict) and "header" in nested:
                    return nested
        except:
            pass

        return message_dict

    def receive_message(self, message):
        try:
            message_dict = json.loads(message)
        except json.JSONDecodeError:
            print("Received invalid JSON message.")
            return

        message_dict = self._try_unpack_nested_control(message_dict)

        header = message_dict.get("header", {})
        body = message_dict.get("body", {})
        command = header.get("command")

        if command == "ACK":
            #print("Continue with the next step")
            pass

        elif command == "ERROR":
            print("Received ERROR message:", body)

        elif command == "PING":
            pong_message = self.send_command("PONG", "")
            self.send_message_udp(pong_message)

        elif command == "SEND_TEXT":
            display_message = body.get("message", "")
            print(f"\n{header.get('senderId', 'Unknown')}: {display_message}")
            self.offline_data_rec(message_dict)

        elif command == "FILE_TRANSFER":
            filename = body.get("fileName")
            filesize = body.get("fileSize")

            print(f"\nReceiving file: {filename} ({filesize} bytes)")

            with self.peer_lock:
                sock = self.peer_socket
            if sock:
                self.receive_file(sock, filename, filesize)

        elif command == "GTEXT_MESSAGE":
            display_message = body.get("message", "")
            group_name = body.get("group-name", "GROUP")
            print(f"{group_name}-{header.get('senderId', 'Unknown')}: {display_message}")
        
        elif command == "GFILE_TRANSFER":
            filename = body.get("fileName")
            filesize = body.get("fileSize")

            print(f"\nReceiving file: {filename} ({filesize} bytes)")

            sock = self.client_socket
            if sock:
                self.receive_file(sock, filename, filesize)

        elif command == "VIEW_ONLINE":
            online_users = body.get("users", [])
            print("Online Users: ", online_users)


        elif command == "VIEW_GROUP":
            groups = body.get("groups", [])
            print("Groups: ", groups)

        elif command == "EXIT_CHAT":
            print("The chat has ended by the other party.")
            with self.peer_lock:
                if self.peer_socket:
                    try:
                        self.peer_socket.close()
                    except:
                        pass
                    self.peer_socket = None
            self.peer_connected_event.clear()

        else:
            #print("Received:", message_dict)
            pass

    def peer_receive_thread(self):
        buffer = ""

        while True:
            try:
                with self.peer_lock:
                    current_peer_socket = self.peer_socket

                if current_peer_socket is None:
                    break

                msg = current_peer_socket.recv(2048).decode()

                if not msg:
                    print("Peer disconnected.")
                    with self.peer_lock:
                        try:
                            current_peer_socket.close()
                        except:
                            pass
                        if self.peer_socket is current_peer_socket:
                            self.peer_socket = None
                    self.peer_connected_event.clear()
                    break

                buffer += msg

                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    if message.strip():
                        self.receive_message(message)

            except Exception:
                print("Peer disconnected.")
                with self.peer_lock:
                    try:
                        if self.peer_socket:
                            self.peer_socket.close()
                    except:
                        pass
                    self.peer_socket = None
                self.peer_connected_event.clear()
                break

    def tcp_receive_thread(self):
        buffer = ""

        while True:
            try:
                msg = self.client_socket.recv(2048).decode()
              #  print(f"\n[Debug] Received raw message: {msg.strip()}")

                if not msg:
                    print("Server disconnected.")
                    break

                buffer += msg

                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)

                    if not message.strip():
                        continue

                    if self.waiting_for_response:
                        self.message_queue.put(message)
                    else:
                        self.receive_message(message)

            except Exception:
                print("Server disconnected.")
                break

    # CONNECT REQUEST HANDLING
    def get_connect_message_for_peer(self, timeout=10):
        """
        Wait for either:
        1. server ACK with target IP, then connect out to peer_port
        2. incoming peer connection already accepted by listener
        """

        self.waiting_for_response = True
        end_time = time.time() + timeout

        while time.time() < end_time:
            # Case 1: incoming peer already connected
            if self.peer_connected_event.is_set():
                self.waiting_for_response = False
                return True

            # Case 2: server replied
            try:
                message = self.message_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            try:
                message_dict = json.loads(message)
            except json.JSONDecodeError:
                continue

            message_dict = self._try_unpack_nested_control(message_dict)
            header = message_dict.get("header", {})
            body = message_dict.get("body", {})
            command = header.get("command")

            # If peer connected while we were parsing, use that
            if self.peer_connected_event.is_set():
                self.waiting_for_response = False
                return True

            if command == "ACK":
                addr = body.get("message", [None, None])

                if isinstance(addr, list) and len(addr) >= 1:
                    client_ip = addr[0]

                    # IMPORTANT:
                    # server returns wrong peer port, so ignore it
                    if client_ip is not None:
                        success = self.tcp_connect_peer(client_ip, self.peer_port)
                        self.waiting_for_response = False
                        return success

            elif command == "ERROR":
                # Even if server complains, maybe the peer already connected in the meantime
                if self.peer_connected_event.is_set():
                    self.waiting_for_response = False
                    return True

                print("Server returned an error:", body)

            else:
                # Process any other message normally
                self.receive_message(message)

            # If peer connected after processing, still accept success
            if self.peer_connected_event.is_set():
                self.waiting_for_response = False
                return True

        self.waiting_for_response = False

        # Final rescue: maybe peer got connected just at the edge of timeout
        if self.peer_connected_event.is_set():
            return True

        print("Timeout waiting for connection grant")
        return False

    def close_connection(self):
        try:
            if self.peer_socket:
                self.peer_socket.close()
        except:
            pass

        try:
            if self.peer_listener_socket:
                self.peer_listener_socket.close()
        except:
            pass

        try:
            if self.client_socket:
                self.client_socket.close()
        except:
            pass

        try:
            if self.udp_socket:
                self.udp_socket.close()
        except:
            pass

        self.peer_connected_event.clear()
        print("Connection is closed")
    
    def offline_data_rec(self, message):
        header = message['header']
        body = message['body']

        off_sender = header.get("senderId", "Unknown")
        off_receiver = self.username
        off_message = body.get("message", "")
        off_timestamp = header.get("timestamp", "")

        new_row_dict = {
            "sender_id": off_sender,
            "receiver_id": off_receiver,
            "offline_data": off_message,
            "time_stamp": off_timestamp
        }

        filename = 'chat_history.csv'
        with open(filename, 'r', newline='') as file:
            reader = csv.reader(file)
            headers = next(reader)

        with open(filename, 'a', newline='') as file:
            writer = csv.writer(file)
            row = [new_row_dict.get(header, '') for header in headers]
            writer.writerow(row)

    def offline_data_send(self, target_user, message):
        header = message['header']
        body = message['body']

        off_sender = self.username
        off_receiver = target_user
        off_message = body.get("message", "")
        off_timestamp = header.get("timestamp", "")

        new_row_dict = {
            "sender_id": off_sender,
            "receiver_id": off_receiver,
            "offline_data": off_message,
            "time_stamp": off_timestamp
        }

        filename = 'chat_history.csv'
        with open(filename, 'r', newline='') as file:
            reader = csv.reader(file)
            headers = next(reader)

        with open(filename, 'a', newline='') as file:
            writer = csv.writer(file)
            row = [new_row_dict.get(header, '') for header in headers]
            writer.writerow(row)
    
    def send_file(self, filepath, type, target):
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)

        body = {"target": target, "fileName": filename, "fileType": type, "fileSize": filesize}
        message = self.send_data("FILE_TRANSFER", body)

        with self.peer_lock:
            receiver_socket = self.peer_socket

        if receiver_socket is None:
            print("Peer disconnected.")
            return
        receiver_socket.sendall((json.dumps(message) + "\n").encode())

        with open(filepath, "rb") as file:
            while True:
                data = file.read(4096)
                if not data:
                    break
                receiver_socket.sendall(data)

        print("File sent successfully")

    def receive_file(self, sock, filename, filesize):
        received_bytes = 0
        with open(f"{filename}", "wb") as file:
            while received_bytes < filesize:
                chunk = sock.recv(min(4096, filesize - received_bytes))

                if not chunk:
                    break

                file.write(chunk)
                received_bytes += len(chunk)
        print(f"Received file {filename}")

def view_online_users(self):
    request_message = self.send_command("VIEW_ONLINE", "")
    self.send_message_tcp(request_message)
    time.sleep(1)

def main():
    client = None

    server_ip = input("Enter server IP address: ").strip()
    server_port = 12000

    def main_menu1():
        print("Main Menu:\n")
        print("1. REGISTER\n2. LOGIN\n")

    def register():
        print("Welcome")
        nonlocal client

        username = input("Enter your username: ").strip()
        password = input("Enter your password: ").strip()

        client = client_application(username)
        client.tcp_connect(server_ip, server_port)
        client.udp_connect(server_ip, server_port)

        register_message = client.send_command(
            "REGISTER",
            {"username": client.username, "password": password}
        )
        client.send_message_tcp(register_message)
        time.sleep(1)

    def login():
        print("Welcome back")
        nonlocal client

        username = input("Enter your username: ").strip()
        password = input("Enter your password: ").strip()

        client = client_application(username)
        client.tcp_connect(server_ip, server_port)
        client.udp_connect(server_ip, server_port)

        login_message = client.send_command(
            "LOGIN",
            {"username": client.username, "password": password}
        )
        client.send_message_tcp(login_message)
        time.sleep(1)

    def main_menu2():
        print("Main Menu:\n")
        print("1. 1-on-1 chat\n2. Group Chat\n3. View Online Users\n4. LOGOUT\n")

    def one_on_one_chat():
        nonlocal client

        if not client.listener_started:
            threading.Thread(target=client.start_peer_listener, daemon=True).start()
            time.sleep(0.5)

        req_or_accept = int(input("1. Request User\n2. Accept Connection\n").strip())
        rec_id = None
        if req_or_accept == 1:
            user = input("Enter the username of the person you want to chat with: ").strip()
            rec_id = user
            if not user:
                print("No username entered.")
                return
        elif req_or_accept == 2:
            #still need to figure out how to get the rec_id for offline data
            #
            #
            print("Waiting for incoming connection...")
            if not client.peer_connected_event.wait(timeout=30):
                print("Timed out waiting for connection.")
                return
            print("Peer connected! Starting chat.")
        # If a peer already connected, just use that
        if client.peer_connected_event.is_set():
            print("A peer is already connected. Starting chat.")
        else:
            connect_request_message = client.send_command(
                "CONNECT_REQUEST",
                {"target_user": user}
            )
            client.send_message_tcp(connect_request_message)

            connected = client.get_connect_message_for_peer(timeout=10)

            if not connected:
                print("Could not establish peer connection.")
                return

        print("You can now chat. Type EXIT_CHAT to leave.")

        while True:
            with client.peer_lock:
                if client.peer_socket is None:
                    print("Chat ended.")
                    break

            message = input("You: ")

            if message == "FILE_TRANSFER":
                filepath = input("Enter the file path: ").strip()
                filetype = input("Enter the file type (images, audios, videos, documents, other): ").strip()

                client.send_file(filepath, filetype, rec_id)
                continue

            data_message = client.send_data("SEND_TEXT", {"message": message})
            sent_ok = client.send_message_peer(data_message)
            client.offline_data_send(rec_id, data_message)

            if not sent_ok:
                print("Message could not be sent.")
                break

            if message == "EXIT_CHAT":
                with client.peer_lock:
                    try:
                        if client.peer_socket:
                            client.peer_socket.close()
                    except:
                        pass
                    client.peer_socket = None
                client.peer_connected_event.clear()
                break

    def create_group(group_name=None):
        nonlocal client
        members = []

        while True:
            member = input("Enter the username of the member you want to add to the group (or type 'done' to finish): ").strip()
            if member == 'done':
                break
            if member:
                members.append(member)

        create_group_message = client.send_command(
            "CREATE_GROUP",
            {"group-name": group_name, "members": members}
        )
        client.send_message_tcp(create_group_message)

        message = input("Enter the message to the group ('done' to finish): ")
        gmessage = client.send_data(
            "GTEXT_MESSAGE",
            {"group-name": group_name, "message": message}
        )
        client.send_message_tcp(gmessage)

        while True:
            message = input("You: ")

            if message == "FILE_TRANSFER":
                filepath = input("Enter the file path: ").strip()
                filetype = input("Enter the file type (images, audios, videos, documents, other): ").strip()

                client.send_file(filepath, filetype, group_name)
                continue

            gmessage = client.send_data(
                "GTEXT_MESSAGE",
                {"group-name": group_name, "message": message}
            )
            client.send_message_tcp(gmessage)

            if message == 'done':
                break
    def GROUP_CHAT():
        nonlocal client
        menu = int(input("1. Create Group\n2. View Groups\n3. Join Group Chat\n").strip())
        if menu == 1:
            group_name = input("Enter the group name: ").strip()
            create_group(group_name)

        elif menu == 2:
            view_group_message = client.send_command("VIEW_GROUP", {})
            client.send_message_tcp(view_group_message)
            print("Request sent. Check above for group list.")
            time.sleep(1)
            
        elif menu == 3:
            group_name = input("Enter the group name to join: ").strip()
            
            print(f"\n=== Joined group: {group_name} ===")
            
            #flag for the chat loop
            in_group_chat = True
            
            while in_group_chat:
                try:
                    message = input("You: ")
                    
                    if message == "FILE_TRANSFER":
                        filepath = input("Enter the file path: ").strip()
                        filetype = input("Enter the file type: ").strip()
                        
                        # For group file transfers, you might need a different command
                        # Check if your server supports GFILE_TRANSFER
                        client.send_file(filepath, filetype, group_name)
                        continue
                        
                    elif message == "EXIT_CHAT":
                        # Send leave notification
                        leave_msg = client.send_data(
                            "GTEXT_MESSAGE",
                            {"group-name": group_name, "message": "left the chat"}
                        )
                        client.send_message_tcp(leave_msg)
                        
                        in_group_chat = False
                        break
                        
                    else:
                        # Send regular message
                        gmessage = client.send_data(
                            "GTEXT_MESSAGE",
                            {"group-name": group_name, "message": message}
                        )
                        client.send_message_tcp(gmessage)
                    time.sleep(0.8) 
                        
                except KeyboardInterrupt:
                    print("\nLeaving group chat...")
                    in_group_chat = False
                    break
                except Exception as e:
                    print(f"Error in group chat: {e}")
                    in_group_chat = False
                    break
            
            print("Returned to main menu.")

    def logout():
        nonlocal client
        logout_message = client.send_command("LOGOUT", "")
        client.send_message_tcp(logout_message)
        time.sleep(0.5)
        client.close_connection()

    main_menu1()
    choice = input("Enter your choice: ").strip()

    if choice == '1':
        register()
        login()
    elif choice == '2':
        login()
    else:
        print("Invalid choice.")
        return
    
    while True:
        main_menu2()
        choice2 = input("Enter your choice: ").strip()

        if choice2 == '1':
            one_on_one_chat()
        elif choice2 == '2':
            GROUP_CHAT()
        elif choice2 == '3':
            view_online_users()
        elif choice2 == '4':
            logout()
            break
        else:
            print("Invalid choice. Please try again.")

    print("Disconnected from server.")


if __name__ == "__main__":
    main()

"""
body {
    "target": "name of person receiving the file",
    "fileName": "name of the file being sent",
    "filetype": "type of the file being sent",
    "fileSize": "size of the file in bytes"}
"""

"""fileTypes:

images
audio
videos
documents
other
"""