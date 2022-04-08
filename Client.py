"""This is responsable for running the UI, tracking penalties and wait times, and talking to the server"""
"""State, wait time, list of server nodes, alive bool, messaging info(IP, port, ID), pending move queue?"""
# Written by Jordan Dood and Connie Bernard
# April 7th 2022
# This project is to implement the RAFT algorithm as the foundation for a Rock 'Em Sock 'Em Robots Game.
# This class is responsible for:
#   1) Running the interface and providing the user feedback
#   2) Sending the users moves to the central server and ensuring delivery
#   3) Tacking the local game state, specifically penalties

# Imports
from threading import Thread
from time import sleep


# Static Functions
# Function to print instructions
def instructions():
    print("When the game starts you can use these keys: ")
    print("use [Q] to punch with left")
    print("use [W] to punch with right")
    print("use [A] to block with left")
    print("use [S] to block with right")
    print(">You can only strike once per second")
    print(">You can block on either or both sides, but block ends after a strike")
    print(">If you strike a block and fail you are unable to strike for 3 seconds")


# Function to count down to the fight
def count_down():
    print("Fight in 3...")
    # TODO bell sound
    sleep(1)
    print("Fight in 2...")
    # TODO bell sound
    sleep(1)
    print("Fight in 1...")
    # TODO bell sound
    sleep(1)
    print("Fight!!!\n")
    # TODO bell sound


# Function to print the game result
def game_result(alive):
    if alive:
        print("\nYOU WIN!!!\n")
    else:
        print("\nYOU DIED!!!\n")


# The class for running the UI and handling the game state and messaging the server
class Client:
    # Class Fields
    addresses = None
    Id = None
    address = None
    port = 4000
    can_strike = True
    penalties = 0
    blocking_left = False
    blocking_right = False
    ready = False
    alive = True

    # Class functions
    # This method creates the game client object and gathers needed networking info
    def __init__(self):
        try:
            file_path = r"server_addresses"
            file = open(file_path, "r")
            self.from_file(file)
        except IOError:
            self.build_self()
        # Start the listening Thread
        self.listener = Thread(target=self.receive, args=())
        self.listener.start()
        # Start the sending Thread
        self.sender = Thread(target=self.run, args=())
        self.sender.start()
        # Start the sending Thread
        self.timer = Thread(target=self.timer, args=())
        self.timer.start()

    # This method gathers needed network info from the user if file not found.
    def build_self(self):
        print("The start up file was not found, please enter values manually.")
        address_book = []
        for i in range(5):
            server_id = int(input("Enter Server ID number 1-5: ").strip())
            server_address = input("Enter Server address: ").strip()
            server_port = 4000
            address_book.append([server_id, server_address, server_port])
        self.addresses = address_book
        self.client_info()
        self.to_file()

    # This method builds the client from a found file
    def from_file(self, file):
        address_book = []
        for line in file:
            address_book.append(line.strip().split(','))
        self.addresses = address_book
        file.close()

    # This method collects and sets the address and port for this client instance
    def client_info(self):
        self.address = input("Enter your IP address: ").strip()
        self.port = int(input("Enter your preferred port: ").strip())

    # Method to create start up file for next run
    def to_file(self):
        file = open("server_addresses", 'w+')
        for address in self.address:
            line = str(address[0]) + ',' + address[1] + ',' + str(address[2])
            file.write(line)
        file.close()

    # Method to run the main game loop
    def run(self):
        instructions()
        sleep(10)
        print("\nPlease wait while we connect you....\n")
        # Contact cluster
        while not self.ready:
            sleep(1)
        count_down()
        self.game_loop()
        game_result(self.alive)

    # Method to run the game loop
    def game_loop(self):
        while self.alive:
            choice = input().strip().lower()
            if choice == 'q' and self.can_strike:
                self.strike_left()
            elif choice == 'w' and self.can_strike:
                self.strike_right()
            elif choice == 'a':
                self.block_left()
            elif choice == 's':
                self.block_right()
            else:
                pass # TODO Put bell sound here

    # A method to decide if a player can strike based on a passed penalty (wait) time
    def timer(self):
        while True:
            wait_time = self.penalties
            if wait_time != 0:
                self.penalties = 0
                self.can_strike = False
                sleep(wait_time)
                self.can_strike = True

    # A method to strike left
    def strike_left(self):
        self.penalties = 1
        self.blocking_left = False
        # TODO Send Message Here

    # A method to strike right
    def strike_right(self):
        self.penalties = 1
        self.blocking_right = False
        # TODO send message here

    # A method to block left
    def block_left(self):
        if not self.blocking_left:
            self.blocking_left = True
            # TODO send message here

    # A method to block right
    def block_right(self):
        if not self.blocking_right:
            self.blocking_right = True
            # TODO send message here

    def send_move(self): # Send relevant data to
        pass

    def receive(self): # Respond to incoming log, may update leader info
        pass

