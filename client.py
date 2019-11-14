import argparse
import socket
import threading
import os
import time
import tkinter as tk
import json

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

    def __init__(self, ip, port, client_id, verbose=True):
        if ip == "NO_INPUT":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            host_ip = s.getsockname()[0] 
        else:
            host_ip = ip

        self.rm_ip = host_ip
        self.rm_port = port
        self.client_id = client_id
        self.replica_IPs = []
        self.rp_msg_counter = 0 # Counts how many messages have been sent to replica
        self.rm_msg_counter = 0
        

        # Replica parameters
        self.replica_port = 5000
        self.replica_mutex = threading.Lock()
        self.replica_sockets = {}
        self.replica_socket_mutex = threading.Lock()
        self.replica_msg_proc = 0
        self.replica_msg_proc_mutex = threading.Lock()

        print(GREEN + "Connecting to Replication Manager..." + RESET)
        self.connect_RM() # Connect only once

        self.setup_chat_window()

        # Disconnect from RM
        self.disconnect_RM()

    def connect_RM(self):
        # Get a socket to connect to the server
        self.s_RM = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IPv4, TCPIP

        # Connect to RM
        try:
            self.s_RM.connect((self.rm_ip, self.rm_port))
            # Spawn the listening thread for RM
            threading.Thread(target=self.recv_rm_thread).start()
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

            # Initiate a client listening thread
            # threading.Thread(target=client_service_thread, args=(conn,addr, logfile, verbose)).start()
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
        os._exit(1)



    def recv_rm_thread(self):
        while(True):
            try:
                data = self.s_RM.recv(BUF_SIZE)                    
            except:
                print(RED + "Connection from RM closed unexpectedly" + RESET)

            rm_msg = json.loads(data.decode("utf-8"))

            # Print Message received from RM
            print(YELLOW + "(RECV) -> RM:", rm_msg, RESET)

            if rm_msg["type"] == "new_replica_IPs":
                self.replica_mutex.acquire()
                self.replica_IPs = rm_msg["ip_list"]
                self.replica_mutex.release()

                self.connect_to_replica_IPs(rm_msg["ip_list"])


            if rm_msg["type"] == "update_replica_IPs":
                self.replica_mutex.acquire()
                diff_ip_list = []
                for ip in rm_msg["ip_list"]:
                    if ip not in self.replica_IPs:
                        diff_ip_list.append(ip)
                self.replica_IPs = rm_msg["ip_list"]
                self.replica_mutex.release()

                print("New list:", self.replica_IPs)

                self.connect_to_replica_IPs(diff_ip_list)




    def connect_to_replica_IPs(self, ip_list):
        for addr in ip_list:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            s.settimeout(5)

            s.connect((addr, self.replica_port))

            self.replica_socket_mutex.acquire()
            self.replica_sockets[addr] = s
            self.replica_socket_mutex.release()

            ################

            
            # Spawn recv thread
            threading.Thread(target=self.recv_replica_thread, args=(s, addr)).start()

            ################

            # Send login packet
            msg = {}
            msg["type"] = "login"
            msg["username"] = self.client_id
            msg["clock"] = self.rp_msg_counter

            login_data = json.dumps(msg)

            try:
                # Send login message
                s.send(login_data.encode("utf-8"))
            except:
                print(RED+"Connection with Replica {} closed unexpectedly".format(addr) + RESET)
                os._exit()

        # First message sent
        self.rp_msg_counter += 1
            


    def recv_replica_thread(self, s, addr):
        while True:
            try:
                data = s.recv(1024)
            except socket.error:
                self.replica_mutex.acquire()
                if addr not in self.replica_IPs:
                    self.replica_mutex.release()
                    print("Timeout error: Replica {} died".format(addr) + RESET)
                    break

                self.replica_mutex.release()
            except:
                print(RED+"Unknown Error: Connection with Replica {} closed unexpectedly".format(addr) + RESET)
            if len(data) == 0:
                continue

            msg = json.loads(data.decode("utf-8"))

            # Print Message received by replica
            print(YELLOW +"(RECV) -> Replica ({}):".format(addr), msg, RESET)

            # Duplicate detection
            self.replica_msg_proc_mutex.acquire()
            if msg["clock"] < self.replica_msg_proc:
                print(RED + "Duplicate message detected from {}: clock = {}".format(addr, msg["clock"]) + RESET)
                continue
            else:
                self.replica_msg_proc += 1
            self.replica_msg_proc_mutex.release()

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

            data = ""
            
    def send_msg(self, event = None):
        message = self.input_field.get()
        self.input_user.set('')

        # Create the message packet
        msg = {}
        msg["type"] = "send_message"
        msg["username"] = self.client_id
        msg["text"] = message
        msg["clock"] = self.rp_msg_counter

        data = json.dumps(msg)

        if (msg):
            print(UP) # Cover input() line with the chat line from the server.

            self.replica_socket_mutex.acquire()
            # Send message to every replica
            for addr, s in self.replica_sockets.items():
                try:
                    s.send(data.encode("utf-8"))
                except:
                    print(RED + "Error: Connection closed unexpectedly from Replica {}".format(addr) + RESET)

            self.rp_msg_counter += 1
            self.replica_socket_mutex.release()

        return "break"

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

        # Start the chat window
        self.top.mainloop()

    def logout_client(self, event = None):
        # Send login packet
        msg = {}
        msg["type"] = "logout"
        msg["username"] = self.client_id
        msg["clock"] = self.rp_msg_counter

        logout_data = json.dumps(msg)

        self.replica_socket_mutex.acquire()
        # Send message to every replica
        for addr, s in self.replica_sockets.items():
            try:
                s.send(logout_data.encode("utf-8"))
            except:
                print(RED + "Error: Connection closed unexpectedly from Replica {}".format(addr) + RESET)
        self.rp_msg_counter += 1
        self.replica_socket_mutex.release()
        
        self.top.destroy()


def get_args():
    parser = argparse.ArgumentParser()

    # IP, PORT, Username
    parser.add_argument('-ip', '--ip', help="Replication Manager IP Address", default="NO_INPUT")
    parser.add_argument('-p', '--port', help="Replication Manager Port", type=int, default=6666)
    parser.add_argument('-u', '--username', help="Chat user/display name (needs to be unique)", required=True) # Used as client_id
    
    # Parse the arguments
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    start_time = time.time()

    # Extract Arguments from the 
    args = get_args()

    # Create Client object
    client_obj = Client(args.ip, args.port, args.username)

    # Total client up time
    print(RESET + "\nClient up time: {} seconds".format(time.time() - start_time))

    # Exit
    os._exit(1)