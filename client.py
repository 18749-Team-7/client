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
        self.rm_ip = ip
        self.rm_port = port
        self.client_id = client_id

        print(GREEN + "Connecting to Replication Manager..." + RESET)
        self.connect_RM() # Connect only once

        time.sleep(10)
        # Disconnect from RM
        self.disconnect_RM()

    def connect_RM(self):
        # Get a socket to connect to the server
        self.s_RM = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # IPv4, TCPIP

        # Connect to RM
        try:
            self.s_RM.connect((self.rm_ip, self.rm_port))
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
        except:
            print(RED + "Connection closed unexpectedly with Replication Manager")
            print("Shutting down client..." + RESET)
            os._exit(1)

        # Close connection with RM
        self.s_RM.close()
        print(RED + "Shutting down client..." + RESET)

        os._exit(1)



    def recv_rm_thread(self):
        while(True):
            try:
                data = self.s.recv(BUF_SIZE)
                if (len(data) != 0):
                    rm_msg = json.loads(data.decode("utf-8"))
                    print(rm_msg)
            except:
                pass

    # def tcp_client(self):
        

        # Log in to chat server
        login_packet = LOGIN_STR + username
        try:
            s.send(login_packet.encode(STR_ENCODING))
        except:
            print(RED + "Error: Connection closed unexpectedly")

        # Spawn thread to handle printing received messages
        threading.Thread(target=receive_thread,args=(s,)).start()

        # Chat!
        # Create a window for the input field for messages
        setup_chat_window(s, ip, port, username)

        # Closing
        logout_packet = LOGOUT_STR + username
        try:
            s.send(logout_packet.encode(STR_ENCODING))
            s.close()
        except: 
            print(RED + "Error: Connection closed unexpectedly")
        return

    def setup_chat_window(self):
        # Create a window
        self.top = tk.Tk()
        self.top.title(self.client_id)

        # Create input text field
        input_user = tk.StringVar()
        input_field = tk.Entry(self.top, text=input_user)
        input_field.pack(side=tk.BOTTOM, fill=tk.X)

        # Inline function
        def send_msg(event = None):
            message = input_field.get()
            input_user.set('')

            if (message):
                print(UP) # Cover input() line with the chat line from the server.
                try:
                    s.send(message.encode(STR_ENCODING))
                except:
                    print(RED + "Error: Connection closed unexpectedly")
            return "break"

        # Create the frame for the text field
        input_field.bind("<Return>", send_msg)

        # Add an escape condition
        def destroy(e):
            self.top.destroy()
        self.top.bind("<Escape>", destroy)

        # Start the chat window
        self.top.mainloop()