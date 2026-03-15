# client
import os
from socket import *
import datetime
import time
import json
import threading
import queue
import csv
from app import socketio


class client_application:
    def __init__(self, ip_addr="0.0.0.0", peer_port=8000):
        self.server_ip = "196.47.245.85"
        self.server_port = 12000
        self.username = None
        self.ip_addr = ip_addr
        self.peer_port = peer_port
        self.counter = 0

        self.client_socket = None
        self.udp_socket = None
        self.peer_socket = None
        self.peer_listener_socket = None

        self.message_queue = queue.Queue()
        self.waiting_for_response = False

        self.login_event = threading.Event()
        self.login_success = False
        self.login_response = None
        self.login_error_message = ""

        self.peer_lock = threading.Lock()
        self.listener_started = False
        self.peer_connected_event = threading.Event()

    # TCP / UDP CONNECTIONS
    def tcp_connect(self, server_ip="196.47.245.85", server_port=12000):
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
        print(message_dict)
        header = message_dict.get("header", {})
        body = message_dict.get("body", {})
        command = header.get("command")

        if command == "ACK":
            #print("Continue with the next step")
            pass

        elif command == "ERROR":
            print("Received ERROR message:", body)

        elif command == "LISTEN":
            if not self.listener_started:
                t = threading.Thread(target=self.start_peer_listener, daemon=True)
                t.start()
                time.sleep(0.5)

        elif command == "PING":
            pong_message = self.send_command("PONG", "")
            self.send_message_udp(pong_message)

        elif command == "SEND_TEXT":
            display_message = body.get("message", "")
            sender = header.get("senderId", "Unknown") #added
            print(f"\n{header.get('senderId', 'Unknown')}: {display_message}")
            print("Recieving msg:", display_message)
            socketio.emit(
                "new_message",
                {
                    "chat_name": sender,
                    "message": display_message
                },
                room=self.username
            )
            self.offline_data_rec(message_dict)


        elif command == "FILE_TRANSFER":
            PATH = "app/static/uploads/received" #ADDED BY ME
            os.makedirs(PATH, exist_ok=True)
            name = os.path.basename(body.get("fileName"))
            filename = os.path.normpath(os.path.join(PATH, name)) #CHANGED BY ME

            filesize = body.get("fileSize")
            sender = header.get("senderId", "Unknown")
            print(f"\nReceiving file: {filename} ({filesize} bytes)")

            with self.peer_lock:
                sock = self.peer_socket
            if sock:
                print(f"Sending to {sender} of the file: {filename}")
                self.receive_file(sock, filename, filesize, sender)

        elif command == "GTEXT_MESSAGE":
            print("I was here")
            display_message = body.get("message", "")
            group_name = body.get("group-name", "GROUP")
            sender = header.get('senderId', 'Unknown')
            print(f"{group_name}-{header.get('senderId', 'Unknown')}: {display_message}")

            socketio.emit(
                "new_message",
                {
                    "chat_name": group_name,
                    "sender": sender,
                    "message": display_message
                },
                room=self.username
            )

        elif command == "GFILE_TRANSFER":
            filename = body.get("fileName")
            filesize = body.get("fileSize")

            print(f"\nReceiving file: {filename} ({filesize} bytes)")

            sock = self.client_socket
            if sock:
                self.receive_file(sock, filename, filesize)

        elif command == "VIEW_ONLINE":
            online_users = body.get("users", [])
            print("Online users:", online_users)

        elif command == "VIEW_GROUP":
            groups = body.get("groups", [])
            print("Groups:", groups)

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
                    print("I'm checking conncection to peer")
                    break

                msg = current_peer_socket.recv(2048).decode()
                if msg:
                   buffer+=msg
                

                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    if message.strip():
                        self.receive_message(message)

            except Exception:
                print("Peer disconnected.2")

    def tcp_receive_thread(self):
        buffer = ""

        while True:
            try:
                msg = self.client_socket.recv(2048).decode()

                if not msg:
                    print("Server disconnected.1")
                    break

                buffer += msg

                while '\n' in buffer:
                    msg, buffer = buffer.split('\n', 1)

                    if not msg.strip():
                        continue

                    if self.waiting_for_response:
                        self.message_queue.put(msg)
                    else:
                        #print("Peer from thread",msg)
                        self.receive_message(msg)

            except Exception:
                print("Server disconnected.2")
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
    
    def close_connection_peer(self):
        with self.peer_lock:
            try:
                if self.peer_socket:
                    self.peer_socket.close()
            except:
                pass

            self.peer_socket = None

        self.peer_connected_event.clear()

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
    
    def send_file(self, filepath, filename, type, size, target):
        # filename = os.path.basename(filepath)

        body = {"target": target, "fileName": filename, "fileType": type, "fileSize": size}
        message = self.send_data("FILE_TRANSFER", body)
        print(message)
        with self.peer_lock:
            receiver_socket = self.peer_socket

        if receiver_socket is None:
            print("Peer disconnected.")
            return
        
        receiver_socket.sendall((json.dumps(message) + "\n").encode())


        with open(filepath, "rb") as file:
            while True:
                data = file.read(65536)
                if not data:
                    break
                receiver_socket.sendall(data)


        print("File sent successfully")

    def receive_file(self, sock, filename, filesize, sender):
        received_bytes = 0
        fname = os.path.basename(filename)
        print("Received file: ", fname)
        with open(f"{filename}", "wb") as file:
            while received_bytes < filesize:
                chunk = sock.recv(min(65536, filesize - received_bytes))

                if not chunk:
                    break

                file.write(chunk)
                received_bytes += len(chunk)
        print("File reconstruction completed:", filename)
        socketio.emit(
            "uploaded_files",
            {
                "chat_name": sender,
                "url": filename,
                "name": fname
            },
            room=self.username
        )

        print(f"Received file {filename}")

    def register(self, username, password):
        """Register a new user"""
        self.username = username
        self.tcp_connect(self.server_ip, self.server_port)
        self.udp_connect(self.server_ip, self.server_port)
        
        register_message = self.send_command(
            "REGISTER",
            {"username": username, "password": password}
        )
        self.send_message_tcp(register_message)
        
        self.waiting_for_response = True
        try:
            response = self.message_queue.get(timeout=5)
            response_dict = json.loads(response)
            
            if response_dict["header"]["command"] == "ACK":
                return True, "Registration successful"
            else:
                return False, str(response_dict.get("body", {}))
        except queue.Empty:
            return False, "Registration timeout"
        finally:
            self.waiting_for_response = False

    def is_connected(self):
        """Check if connected to server"""
        return self.client_socket is not None and self.client_socket.fileno() != -1  # CHANGED

    def is_peer_connected(self):
        """Check if peer is connected"""
        return self.peer_socket is not None
        
    def login_thread(self, username, password):
        """thread to handle login process"""
        self.username = username
        
        # Connect to server
        self.tcp_connect(self.server_ip, self.server_port)
        self.udp_connect(self.server_ip, self.server_port)
        
        # Set waiting for response
        self.waiting_for_response = True
        
        # Send login message
        login_message = self.send_command(
            "LOGIN",
            {"username": username, "password": password}
        )
        self.send_message_tcp(login_message)
        
        # Wait for response from queue
        try:
            response = self.message_queue.get(timeout=5)
            response_dict = json.loads(response)
            
            if response_dict["header"]["command"] == "ACK":
                print("Login successful!")
                self.login_success = True
                self.login_response = "ACK"
            else:
                self.login_error_message = str(response_dict.get("body", {}))
                print(f"Login failed: {self.login_error_message}")
                self.login_success = False
                self.login_response = "ERROR"
                
        except queue.Empty:
            self.login_error_message = "Login timeout - server not responding"
            print(self.login_error_message)
            self.login_success = False
            self.login_response = "TIMEOUT"
        except Exception as e:
            self.login_error_message = f"Login error: {e}"
            print(self.login_error_message)
            self.login_success = False
            self.login_response = "ERROR"
        finally:
            self.waiting_for_response = False
            self.login_event.set()
        
        return self.login_success

    def login(self, username, password, timeout=10):
        """Blocking login that waits for result"""
        self.login_event.clear()
        self.login_success = False
        self.login_error_message = ""
        
        login_thread = threading.Thread(
            target=self.login_thread,
            args=(username, password),
            daemon=True
        )
        login_thread.start()
        
        if not self.login_event.wait(timeout=timeout):
            return False, "Login process timed out"
            
        return self.login_success, self.login_error_message

    def login_async(self, username, password, callback=None):
        """Non-blocking login with optional callback"""
        def login_wrapper():
            success, error = self.login(username, password)
            if callback:
                callback(success, error)
        
        threading.Thread(target=login_wrapper, daemon=True).start()
            

    def one_on_one_chat_connection(self, peer_username=None):
        if peer_username is not None:
            req_msg = self.send_command(
                "CONNECT_REQUEST",
                {"target_user": peer_username}
            )
            self.send_message_tcp(req_msg)
            
            connected = self.get_connect_message_for_peer(timeout=10)
            if connected:
                print("Peer connected! Starting chat.")
                return True
            else:
                print("Not connected")
                return False

        else:
            if self.peer_connected_event.wait(timeout=30):
                print("Got connection")
                return True
            else:
                print("Timed out waiting for connection.")
                return False

    def send_message_121(self, message, rec_id):
        with self.peer_lock:
            if self.peer_socket is None:
                return False
            
        data_message = self.send_data("SEND_TEXT", {"message": message})
        sent_ok = self.send_message_peer(data_message)
        
        if message == "EXIT_CHAT" and sent_ok:
            with self.peer_lock:
                try:
                    if self.peer_socket:
                        self.peer_socket.close()
                except:
                    pass
                self.peer_socket = None
            self.peer_connected_event.clear()
            return False
        
        return sent_ok
        
    def send_message_group(self, gmessage, group_name):
        #print("Got here")
        gmessage = self.send_data(
            "GTEXT_MESSAGE",
            {"group-name": group_name, "message": gmessage}
        )
        print("sending msg:", gmessage)
        self.send_message_tcp(gmessage)

        if gmessage == 'done':
            return False
        return True

    def create_group(self, group_name, members):
        create_group_message = self.send_command(
            "CREATE",
            {"user": self.username,"group-name": group_name, "members": members}
        )
        self.send_message_tcp(create_group_message)

        self.waiting_for_response = True

        try:
            response = self.message_queue.get(timeout=5)
            response = json.loads(response)
            header = response.get("header", {})
            status = header.get("command", "")

            if status=="ACK":
                return True
        except:
            print("No server response")

        self.waiting_for_response = False

    def view_online_users(self):

        message = self.send_command("VIEW_ONLINE", {})
        self.send_message_tcp(message)
        self.waiting_for_response = True

        try:
            response = self.message_queue.get(timeout=5)

            response = json.loads(response)  

            print("View online response: ", response)
            body = response.get("body",{})
            self.online_users = body.get("users", [])
            print("users: ", self.online_users)
        except queue.Empty:
            print("Server timeout")
            self.waiting_for_response = False
            return []

        self.waiting_for_response = False

        return self.online_users

    def logout(self):
        logout_message = self.send_command("LOGOUT", "")
        self.send_message_tcp(logout_message)
        time.sleep(0.5)
        self.close_connection()


    def view_groups(self):
        """Request available groups from the server and return them"""

        message = self.send_command("VIEW_GROUPS", {})
        self.send_message_tcp(message)

        self.waiting_for_response = True

        try:
            response = self.message_queue.get(timeout=5)
            response = json.loads(response)

            body = response.get("body", {})
            groups = body.get("groups", [])

        except queue.Empty:
            print("Server timeout")
            self.waiting_for_response = False
            return []

        self.waiting_for_response = False
        return groups