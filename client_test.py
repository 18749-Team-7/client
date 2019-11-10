import argparse
import socket
import threading
import os
import time
import tkinter as tk
import json
import client

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
    client_obj = client.Client(args.ip, args.port, args.username)

    # Total client up time
    print(RESET + "\nClient up time: {} seconds".format(time.time() - start_time))

    # Exit
    os._exit(1)