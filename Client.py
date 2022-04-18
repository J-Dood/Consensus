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
import json
import socket


# Static Functions
# Function to print strike image
def strike(person, side):
    if person == "other":
        if side == "left":
            print("  _        _\n |_| o  o |_|\n  |\/oo__\/|\n"
                  + "  |\/      |\n / \      / \\\n/_  \_  _/  _\\\n")
        elif side == "right":
            print("  _        _\n |_| oo___|_|\n  |\/o  o  |\n"
                  + "  |\/    \/|\n / \      / \\\n/_  \_  _/  _\\\n")
        else:  # Error condition, should never reach
            print("Error, invalid side passed to strike")
    elif person == "me":
        if side == "left":
            print("  _        _\n |_|___oo |_|\n  |  o  o\/|\n"
                  + "  |\/    \/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif side == "right":
            print("  _        _\n |_| o  o |_|\n  |\/__oo\/|\n  |      \/|\n"
                  + " / \      / \\\n/_  \_  _/  _\\\n")
        else:  # Error condition, should never reach
            print("Error, invalid side passed to strike")
    else:  # Error condition, should never reach
        print("Error, invalid person passed to strike")


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
def count_down(player):
    print("Fight in 3...\a")
    sleep(1)
    print("Fight in 2...\a")
    sleep(1)
    print("Fight in 1...\a")
    sleep(1)
    print(str(player) + " Player, Fight!!!\n\a")


# Function to print the game result
def game_result(alive):
    if alive:
        # Victory End Game
        print("       _      _\n      (_)    | |\n"
              + "__   ___  ___| |_ ___  _ __ _   _\n"
              + "\ \ / / |/ __| __/ _ \| '__| | | |\n"
              + " \ V /| | (__| || (_) | |  | |_| |\n"
              + "  \_/ |_|\___|\__\___/|_|   \__, |\n"
              + "                             __/ |\n"
              + "                            |___/ "
              + "\n          YOU WIN!\n\a")
    else:
        # Loss End Game
        print("\n    ___\n   |RIP|\n   |   |\n ##|___|##\n YOU DIED!\n\a")


# A function to draw action frames for hits
def kapow(who, side):
    if who == "me":
        if side == "left":
            print("             _\n  _____   o |_|\n |LEFT |o__\/|"
                  + "\n | HIT!|     |\n |_____|    / \\\n          _/  _\\\n")
        elif side == "right":
            print(" _____      _\n|RIGHT|o___|_|\n| HIT!|  o  |"
                  + "\n|_____|   \/|\n           / \\\n         _/  _\\\n")
        else:
            print("I don’t know if we’ll ever get back home.")  # Error Message
    elif who == "other":
        if side == "left":
            print("   _      _____\n  |_| o  |LEFT |\n   |\/__o| HIT!|\n"
                  + "   |     |_____|\n  / \\\n /_  \_\n")
        elif side == "right":
            print("   _      _____\n  |_|___o|RIGHT|\n   |  o  | HIT!|\n"
                  + "   |\/   |_____|\n  / \\\n /_  \_\n")
        else:
            print("I don’t know if we’ll ever get back home.")  # Error Message
    else:
        print("Sometimes I feel like I’m just like a boat upon a winding river, "
              + "twisting toward an endless black sea. Further and further, drifting "
              + "away from where I want to be. Who I want to be.")  # Error Message


# A function to draw stunned action
def stunned(who):
    if who == "me":
        print(" _            _\n|_| o o    o |_|\n  \\_|/     o\/|\n   \        \/|\n"
              + "   / \       / \\\n  /_  \_   _/  _\\\n")
    elif who == "other":
        print("   _           _\n  |_| o   o o |_|\n   |\/o    \|_/\n"
              + "   |\/       /\n  / \      / \\\n /_  \_  _/  _\\\n")
    else:
        print("You shouldn't be here.")  # Error Message
    sleep(3)


# A function to draw the player stances
def stance(red_left, red_right, blue_left, blue_right):
    if red_left:
        if blue_left:  # red blocking left and blue blocking left
            print("  _        _\n |_|o  o  |_|\n  |\|o  \o/|\n  |\/  "
                  + "  |/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif blue_right:  # red blocking left and blue blocking right
            print("  _        _\n |_|o    o|_|\n  |\|o  o|/|\n  |\/  "
                  + "  \/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif blue_left and blue_right:  # red blocking left and blue blocking both
            print("  _        _\n |_|o   o |_|\n  |\|o  |o/|\n  |\/ "
                  + "   |/|\n / \      / \\\n/_  \_  _/  _\\\n")
        else:  # red blocking left, only block
            print("  _        _\n |_|o   o |_|\n  |\|o  o\/|\n  |\/    \/|\n"
                  + " / \      / \\\n/_  \_  _/  _\\\n")
    elif red_right:
        if blue_left:  # red blocking right and blue blocking left
            print("  _        _\n |_|  o o |_|\n  |\o/  \o/|\n  |\|  "
                  + "  |/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif blue_right:  # red blocking right and blue blocking right
            print("  _        _\n |_|  o  o|_|\n  |\o/  o|/|\n "
                  + " |\|    \/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif blue_left and blue_right:  # red blocking right and blue blocking both
            print("  _        _\n |_|  o  o|_|\n  |\o/  |o/|\n  |\|  "
                  + "  |/|\n / \      / \\\n/_  \_  _/  _\\\n")
        else:  # red blocking right, only block
            print("  _        _\n |_|  o o |_|\n  |\o/  o\/|\n  |\|  "
                  + "  \/|\n / \      / \\\n/_  \_  _/  _\\\n")
    elif red_left and red_right:
        if blue_left:  # red blocking both and blue blocking left
            print("  _        _\n |_| o  o |_|\n  |\o|  \o/|\n  |\|  "
                  + "  |/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif blue_right:  # red blocking both and blue blocking right
            print("  _        _\n |_| o   o|_|\n  |\o|  o|/|\n  |\| "
                  + "   \/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif blue_left and blue_right:  # red blocking both and blue blocking both
            print("  _        _\n |_| o  o |_|\n  |\o|  |o/|\n  |\| "
                  + "   |/|\n / \      / \\\n/_  \_  _/  _\\\n")
        else:  # red blocking both, only blocks
            print("  _        _\n |_| o  o |_|\n  |\o|  o\/|\n"
                  + "  |\|    \/|\n / \      / \\\n/_  \_  _/  _\\\n")
    else:
        if blue_left:  # blue blocking left, only block
            print("  _        _\n |_| o  o |_|\n  |\o|  \o/|\n  |\|  "
                  + "  |/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif blue_right:  # blue blocking right, only block
            print("  _        _\n |_| o   o|_|\n  |\/o  o|/|\n"
                  + "  |\/    \/|\n / \      / \\\n/_  \_  _/  _\\\n")
        elif blue_left and blue_right:  # blue blocking both
            print("  _        _\n |_| o  o |_|\n  |\/o  |o/|\n  |\/  "
                  + "  |/|\n / \      / \\\n/_  \_  _/  _\\\n")
        else:  # no blocks
            print("  _        _\n |_| o  o |_|\n  |\/o  o\/|\n"
                  + "  |\/    \/|\n / \      / \\\n/_  \_  _/  _\\\n")


# The class for running the UI and handling the game state and messaging the server
class Client:
    # Class Fields
    addresses = None
    Id = None
    address = None
    port = 4000
    penalties = 0
    can_strike = True
    blocking_left = False
    blocking_right = False
    other_blocking_left = False
    other_blocking_right = False
    ready = False  # Does double duty tracking if other player is alive
    alive = True
    clock = [1, 0]  # (local count, server count)
    known = 0
    s = None

    # Class functions
    # This method creates the game client object and gathers needed networking info
    def __init__(self):
        server_id = input("Enter a client ID number 1 or 2: ").strip()
        try:
            file_path = "client_addresses" + str(server_id) + ".txt"
            file = open(file_path, "r")
            self.from_file(file)
        except IOError:
            self.build_self(server_id)
        # Sets up the port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind((self.address, self.port))
        # Start the listening Thread
        self.listener = Thread(target=self.receive, args=())
        self.listener.start()
        # Start the sending Thread
        self.sender = Thread(target=self.run, args=())
        self.sender.start()
        # Start the sending Thread
        self.time_keeper = Thread(target=self.timer, args=())
        self.time_keeper.start()

    # This method gathers needed network info from the user if file not found.
    def build_self(self, server):
        print("The start up file was not found, please enter values manually.")
        address_book = []
        for i in range(5):
            server_id = int(input("Enter Server ID number 1-5: ").strip())
            server_address = input("Enter Server address: ").strip()
            server_port = int(input("Enter a Port: ").strip())
            address_book.append([server_id, server_address, server_port])
        self.addresses = address_book
        self.client_info()
        self.to_file(server)

    # This method builds the client from a found file
    def from_file(self, file):
        address_book = []
        for line in file:
            address = line.strip().split(',')
            if address[0] != '0':
                address_book.append([int(address[0]), address[1], int(address[2])])
            else:
                self.address = address[1]
                self.port = int(address[2])
        self.addresses = address_book
        file.close()

    # This method collects and sets the address and port for this client instance
    def client_info(self):
        self.address = input("Enter your IP address: ").strip()
        self.port = int(input("Enter your preferred port: ").strip())
        self.address1 = input("Enter your public IP address: ").strip()

    # Method to create start up file for next run
    def to_file(self, server_id):
        file = open("client_addresses" + str(server_id) + ".txt", 'w+')
        for address in self.addresses:
            line = str(address[0]) + ',' + address[1] + ',' + str(address[2]) + "\n"
            file.write(line)
        line = "0" + ',' + str(self.address) + ',' + str(self.port) + "\n"
        file.write(line)
        file.close()

    # Method to run the main game loop
    def run(self):
        instructions()
        sleep(10)
        print("\nPlease wait while we connect you....\n")
        # Contact cluster
        while not self.ready:
            sleep(5)
            self.send_move()
        count_down(self.Id)
        self.game_loop()
        game_result(self.alive)

    # Method to run the game loop
    def game_loop(self):
        while self.alive and self.ready:
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
                print("\a")

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
        self.clock[0] += 1
        self.send_move("strike_left")

    # A method to strike right
    def strike_right(self):
        self.penalties = 1
        self.clock[0] += 1
        self.send_move("strike_right")

    # A method to block left
    def block_left(self):
        if not self.blocking_left:
            self.clock[0] += 1
            self.send_move("block_left")

    # A method to block right
    def block_right(self):
        if not self.blocking_right:
            self.clock[0] += 1
            self.send_move("block_right")

    # A method to send a move to the server
    def send_move(self, action=None):  # Send relevant data to
        message = {'time': self.clock,
                   'action': action,
                   'name': self.Id,
                   'alive': self.alive,
                   'game': self.ready,
                   'log': None,
                   'sender': "client"
                   }
        message = json.dumps(message)
        # Send message to all server nodes if game still on
        if self.alive or self.ready:
            for i in range(5):
                self.s.sendto(message.encode('utf-8'), (self.addresses[i][1], self.addresses[i][2]))

    # A method to receive an process incoming info
    def receive(self):  # Respond to incoming log, may update leader info
        while True:
            packet, address = self.s.recvfrom(1024)
            packet = packet.decode('utf-8')
            packet = json.loads(packet)
            self.receive_inner(packet)  # Can insert any 'message' (dictionary) here for testing

    # Method to take a message and process it, once received
    def receive_inner(self, packet):
        if not packet['alive']:
            self.alive = False
        if self.Id is None:
            self.Id = packet['name']
        self.ready = packet['game']
        self.clock[1] = packet['time'][1]
        self.update_log(packet['log'])

    # A method to update the game for this players moves
    def take_action(self, action):
        if action == "block_left":
            self.blocking_left = True
        elif action == "block_right":
            self.blocking_right = True
        elif action == "strike_left":
            self.blocking_left = False
            strike("me", "left")
        elif action == "strike_right":
            self.blocking_right = False
            strike("me", "right")
        elif action == "hit_left":
            kapow("me", "left")
        elif action == "hit_right":
            kapow("me", "right")
        elif action == "stunned":
            self.penalties = 3
            stunned("me")
        else:  # Error Condition
            print("Something is very wrong, you shouldn't be here!")
        # Prints the image of the stance
        stance(self.blocking_left, self.blocking_right, self.other_blocking_left, self.other_blocking_right)

    # A method to update the game for this players moves
    def others_action(self, action):
        if action == "block_left":
            self.other_blocking_left = True
        elif action == "block_right":
            self.other_blocking_right = True
        elif action == "hit_left":
            kapow("other", "left")
        elif action == "hit_right":
            kapow("other", "right")
        elif action == "stunned":
            stunned("other")
        elif action == "strike_left":
            self.other_blocking_left = False
            strike("other", "left")
        elif action == "strike_right":
            self.other_blocking_right = False
            strike("other", "right")
        else:  # Error Condition
            print("Something is very wrong, you shouldn't be here!")
        # Prints the image of the stance
        stance(self.blocking_left, self.blocking_right, self.other_blocking_left, self.other_blocking_right)

    # A method to update the local game from a received log
    def update_log(self, log):
        if log is not None:
            for item in log:
                if self.known >= item[3]:
                    pass
                else:
                    if item[1] == self.Id:
                        self.take_action(item[2])
                    else:
                        self.others_action(item[2])
                    self.known = item[3]


# The test driver
if __name__ == '__main__':
    # act = "strike_right"
    # log = [[3, 'red', 'hit_left', 4],
    #     [3, 'blue', 'stunned', 5],
    #     [3, 'blue', 'block_left', 6]]
    # pack1 = {
    #     'time': [0, 100],
    #     'action': None,
    #     'name': 'red',
    #     'alive': True,
    #     'game': True,
    #     'log': log,
    #     'sender': 'server'
    # }
    # pack2 = {
    #     'time': [0, 100],
    #     'action': None,
    #     'name': 'red',
    #     'alive': True,
    #     'game': False,
    #     'log': log,
    #     'sender': 'server'
    # }
    client = Client()
    client.receive_inner(pack1)
    #sleep(20)
    #client.receive_inner(pack2)
    #client.send_move(act)


