import argparse
import socket
import threading
import os
import time
import tkinter as tk
import json
import multiprocessing
import sys
import random

BUF_SIZE = 1024

BLACK =     "\u001b[30m"
RED =       "\u001b[31m"
GREEN =     "\u001b[32m"
YELLOW =    "\u001b[33m"
BLUE =      "\u001b[34m"
MAGENTA =   "\u001b[35m"
CYAN =      "\u001b[36m"
WHITE =     "\u001b[37m"
RESET =     "\u001b[0m"
UP =        "\033[A"

class Client():
    """
    Alien Tech. for client
    """

    def __init__(self, ip, port, client_id, ai):
        if ip == "NO_INPUT":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            host_ip = s.getsockname()[0] 
        else:
            host_ip = ip

        self.rm_ip = host_ip
        self.rm_port = port
        self.client_id = client_id
        self.rp_msg_counter = 1 # Counts how many messages have been sent to replica
        self.rm_msg_counter = 0

        self.is_logged_on = False

        # Set AI flag
        self.use_ai = ai

        self.queue = multiprocessing.Queue()
        

        # Replica parameters
        self.replica_port = 5000
        self.replica_sockets = multiprocessing.Manager().dict()
        self.replica_msg_proc = 0
        self.replica_msg_proc_mutex = threading.Lock()

        print(GREEN + "Connecting to Replication Manager..." + RESET)
        self.connect_RM() # Connect only once

        threading.Thread(target=self.proc_queue, daemon=True).start()

        self.setup_chat_window()

        # Disconnect from RM
        self.disconnect_RM()
        return

    def connect_RM(self):
        # Get a socket to connect to the server
        self.s_RM = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IPv4, TCPIP

        # Connect to RM
        try:
            self.s_RM.connect((self.rm_ip, self.rm_port))
            # Spawn the listening thread for RM
            threading.Thread(target=self.recv_rm_thread, daemon=True).start()
        except:
            print(RED + "Connection failed with Replication Manager")
            print("Shutting down client..." + RESET)
            os._exit(1)

        # Create client->RM packet for informing to get replica IPs
        rm_info_msg = {}
        rm_info_msg["type"] = "add_client_rm"
        rm_info_msg["client_id"] = self.client_id
        rm_info_msg = json.dumps(rm_info_msg)

        try:
            self.s_RM.send(rm_info_msg.encode("utf-8"))
            self.rm_msg_counter += 1
        except:
            print(RED + "Connection closed unexpectedly with Replication Manager")
            print("Shutting down client..." + RESET)
            os._exit(1)

    def disconnect_RM(self):
        # Create client->RM packet for informing that it is disconnecting
        rm_info_msg = {}
        rm_info_msg["type"] = "del_client_rm"
        rm_info_msg["client_id"] = self.client_id
        rm_info_msg = json.dumps(rm_info_msg)

        # Send packet to RM
        try:
            self.s_RM.send(rm_info_msg.encode("utf-8"))
            self.rm_msg_counter += 1
        except:
            print(RED + "Connection closed unexpectedly with Replication Manager")
            print("Shutting down client..." + RESET)
            os._exit(1)

        # Close connection with RM
        print(RED + "Shutting down client..." + RESET)


    def recv_rm_thread(self):
        while(True):
            try:
                data = self.s_RM.recv(BUF_SIZE)                 
            except:
                print(RED + "Connection from RM closed unexpectedly" + RESET)

            try:
                rm_msg = json.loads(data.decode("utf-8"))
            except:
                # Client has mostly shutdown
                return

            # Print Message received from RM
            print(YELLOW + "(RECV) -> RM:", rm_msg, RESET)

            # Message says to add replicas
            if rm_msg["type"] == "add_replicas":
                self.connect_replicas(rm_msg["ip_list"])

            # MEssage says to remove replicas
            if rm_msg["type"] == "del_replicas":
                self.disconnect_replicas(rm_msg["ip_list"])

    def connect_replicas(self, ip_list):
        for addr in ip_list:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            s.settimeout(5)

            s.connect((addr, self.replica_port))

            self.replica_sockets[addr] = s

            ################

            # Spawn recv thread
            threading.Thread(target=self.recv_replica_thread, args=(s, addr), daemon=True).start()

            ################
            # Send login packet
            msg = {}
            msg["type"] = "login"
            msg["username"] = self.client_id
            msg["clock"] = 0

            login_data = json.dumps(msg)

            try:
                # Send login message
                s.send(login_data.encode("utf-8"))
            except:
                print(RED+"Connection with Replica {} closed unexpectedly".format(addr) + RESET)
                os._exit()
            
    def disconnect_replicas(self, ip_list):
        # Close all socket connections in the ip_list given
        for addr in ip_list:
            self.replica_sockets[addr].close() # Close the socket
            del self.replica_sockets[addr]

    def recv_replica_thread(self, s, addr):
        while True:
            # Check if replica is still in the sockets dict
            try:
                replica_is_alive = addr in self.replica_sockets
            except:
                # Client has mostly shut down
                return

            if not replica_is_alive:
                return

            try:
                data = s.recv(1024)
            except socket.timeout:
                continue
            except:
                print(RED+"Unknown Error: Connection with Replica {} closed unexpectedly".format(addr) + RESET)
            if len(data) == 0:
                continue

            msg = json.loads(data.decode("utf-8"))
            msg["ip"] = addr
            msg["socket"] = s
            self.queue.put(msg)

            # Print Message received by replica

            data = ""

    
    def client_msg_box_control(self, msg):
        if msg == "$count":
            print(MAGENTA + "CLIENT -> Number of messages processed: {}".format(self.replica_msg_proc) + RESET)
            return "break"

        if msg == "$help":
            print(MAGENTA + "CLIENT -> Hi this is the client of {}".format(self.client_id) + RESET)
            print(MAGENTA + "CLIENT -> $count : Gives number of messages that have been processed " + RESET)
            print(MAGENTA + "CLIENT -> $replica : Number of replicas connected " + RESET)
            print(MAGENTA + "CLIENT -> $reset_count : Clears the number of messages that have been processed (useful when all replicas) " + RESET)
            return "break"
        
        elif msg == "$replica":
            print(MAGENTA + "CLIENT -> Number of Replicas connected: {}".format(len(self.replica_sockets)) + RESET)

        elif msg == "$reset_count":
            print(MAGENTA + "CLIENT -> Clearing messages processed count")
            self.replica_msg_proc = 0
            print(MAGENTA + "CLIENT -> Number of messages processed: {}".format(self.replica_msg_proc) + RESET)

        else:
            print(MAGENTA + "CLIENT -> Error: Not an internal command")
        


    def proc_queue(self):
        # Duplicate detection
        while True:
            msg = self.queue.get()
            addr = msg["ip"]
            s = msg["socket"]

            del msg["socket"]
            del msg["ip"]

            print(YELLOW +"(RECV) -> Replica ({}):".format(addr), msg, RESET)

            if "clock" in msg.keys():
                rp_clock_value = msg["clock"]
            else:
                rp_clock_value = msg["replica_clock"]

            # Check if its your login message, sync your clock to replicas
            if (msg["type"] == "login_success") and (msg["username"] == self.client_id) and (self.replica_msg_proc == 0):
                    self.replica_msg_proc = rp_clock_value + 1
                    self.is_logged_on = True
            else:
                if rp_clock_value < self.replica_msg_proc:
                    print(RED + "Duplicate message detected from {}: clock = {}".format(addr, rp_clock_value) + RESET)
                    continue
                else:
                    self.replica_msg_proc += 1

            # Handle messages
            ####################
            if msg["type"] == "error":
                print(RED + "ERROR: {}".format(msg["text"] + RESET))
                s.close()
                return

            if msg["type"] == "login_success":
                print(GREEN + "{} has logged in".format(msg["username"]) + RESET)

            if msg["type"] == "logout_success":
                print(GREEN + "{} has logged out".format(msg["username"]) + RESET)

            if msg["type"] == "receive_message":
                username = msg["username"]
                text = msg["text"]

                print("{}: {}".format(username, text))

    def send_msg(self, event = None):
        message = self.input_field.get()
        self.input_user.set('')
        if message == "":
            return "break"
        if (message[0] == "$"):
            self.client_msg_box_control(message)
            return "break"

        if self.use_ai:
            return "break"

        # Create the message packet
        msg = {}
        msg["type"] = "send_message"
        msg["username"] = self.client_id
        msg["text"] = message
        msg["clock"] = self.rp_msg_counter

        data = json.dumps(msg)

        if (msg):
            print(UP) # Cover input() line with the chat line from the server.

            # Send message to every replica
            for addr, s in self.replica_sockets.items():
                try:
                    s.send(data.encode("utf-8"))
                except:
                    print(RED + "Error: Connection closed unexpectedly from Replica {}".format(addr) + RESET)

            self.rp_msg_counter += 1

        return "break"

    def ai_send_thread(self):
        lionel_ritchie = "Hello, is it me you're looking for? Cause I wonder where you are And I wonder what you do Are you somewhere feeling lonely, or is someone loving you?"
        lionel_ritchie = lionel_ritchie.split()
        len_lyric = len(lionel_ritchie)
        file_string = "{} {}"
        msg_count = 0

        while(not self.is_logged_on):
            pass

        while True:
            while self.use_ai:
                # Create the message packet
                msg = {}
                msg["type"] = "send_message"
                msg["username"] = self.client_id
                msg["text"] = file_string.format(lionel_ritchie[msg_count % len_lyric], msg_count)
                msg["clock"] = self.rp_msg_counter

                data = json.dumps(msg)

                # Send message to every replica
                for addr, s in self.replica_sockets.items():
                    try:
                        s.send(data.encode("utf-8"))
                        # print("Sent message")
                    except:
                        print(RED + "Error: Connection closed unexpectedly from Replica {}".format(addr) + RESET)

                self.rp_msg_counter += 1

                t = random.random()
                time.sleep(1.5 + t)

                msg_count += 1

    def setup_chat_window(self):
        # Create a window
        self.top = tk.Tk()
        self.top.title(self.client_id)

        # Create input text field
        self.input_user = tk.StringVar()
        self.input_field = tk.Entry(self.top, text=self.input_user)
        self.input_field.pack(side=tk.BOTTOM, fill=tk.X)

        # Create the frame for the text field
        self.input_field.bind("<Return>", self.send_msg)

        self.top.bind("<Escape>", self.logout_client)

        if self.use_ai:
            threading.Thread(target=self.ai_send_thread, daemon=True).start()

        # Start the chat window
        self.top.mainloop()

    def logout_client(self, event = None):
        # Send login packet
        msg = {}
        msg["type"] = "logout"
        msg["username"] = self.client_id
        msg["clock"] = self.rp_msg_counter

        logout_data = json.dumps(msg)

        # Send message to every replica
        for addr, s in self.replica_sockets.items():
            try:
                s.send(logout_data.encode("utf-8"))
            except:
                print(RED + "Error: Connection closed unexpectedly from Replica {}".format(addr) + RESET)
        self.rp_msg_counter += 1
        
        self.top.destroy()


def get_args():
    parser = argparse.ArgumentParser()

    # IP, PORT, Username
    parser.add_argument('-ip', '--ip', help="Replication Manager IP Address", default="NO_INPUT")
    parser.add_argument('-p', '--port', help="Replication Manager Port", type=int, default=6666)
    parser.add_argument('-u', '--username', help="Chat user/display name (needs to be unique)", required=True) # Used as client_id
    parser.add_argument('-ai', '--use_ai', help="Uses Alien Tech AI to send messages", action='store_true')
    
    # Parse the arguments
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    start_time = time.time()

    # Extract Arguments from the 
    args = get_args()

    # Create Client object
    client_obj = Client(args.ip, args.port, args.username, args.use_ai)

    # Total client up time
    print(RESET + "Client up time: {} seconds".format(time.time() - start_time))

    # Exit
    sys.exit(1)