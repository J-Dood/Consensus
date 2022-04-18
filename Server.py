# Written by Connie Bernard and Jordan Dood
# April 14th 2022
# This project is to implement the RAFT algorithm as the foundation for a Rock 'Em Sock 'Em Robots Game.
# This class is responsible for:
#   1) Running the RAFT server functionality
#   2) Communicating with the client nodes
#   3) Saving the Server Node data and Log to disc
#   4) Running a UI capable of causing 'crash', 'restore', and 'timeout' functions

# we are getting msg from followers but still running elections, do something about that

# Imports
from os.path import exists
from threading import Thread
from time import sleep
import json
import socket
import random


# Static Methods
# Method to get a random offset between 1 - 1000 ms
def rand_offset():
    return random.randint(1, 10)


# The Class that acts as a server Node
class Server:
    # --------------------------------------------------------------------------------------------
    # Methods for initializing and constructing the server node object
    # Initializing Method
    def __init__(self):
        # Node Fields
        self.alive = True
        # self.id = None  # Should be an int
        self.leaderID = None
        self.currentTerm = 0  # latest term server has seen
        self.votedFor = None  # candidateID that received vote in current term
        self.log = []
        self.commitIndex = 0  # index of highest log entry known to be committed
        self.lastApplied = 1  # index of highest log entry applied to state machine
        self.timeout = random.randint(1, 10)
        self.electionTime = 6
        self.timeoutTime = 3 + rand_offset()
        self.heartbeatTime = 1
        self.candidate = False
        # Leader Only Fields
        self.leader = False  # set to true if node is leader
        self.nextIndex = [0, 0, 0, 0, 0]  # index of next log entry to send to server
        self.matchIndex = [0, 0, 0, 0, 0]  # index of highest log entry known to be replicated on server
        # For Candidates
        self.votes = 0
        # Communication Fields
        self.s = None
        self.addresses = None
        self.address = None
        self.port = 4000
        # Game State Fields
        self.clients_clock_red = 0  # Start as None until client contact made
        self.clients_clock_blue = 0
        self.client_alive_red = True
        self.client_alive_blue = True
        self.has_player = False
        self.client_count_red = 0
        self.client_count_blue = 0
        self.red_left_blocking = False
        self.red_right_blocking = False
        self.blue_left_blocking = False
        self.blue_right_blocking = False

        # Code to try and read in network info from saved file
        # If file exists use information within
        self.id = input("Enter the process ID: ").strip()
        try:
            file_path = "server_addresses" + str(self.id) + ".txt"
            file = open(file_path, "r")
            self.from_file(file)
            file.close()
        # If no file found then collect network info
        except IOError:
            self.build_self()

        # Sets up the port for messaging
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind((self.address, self.port))

        # Set up of the Treads
        # Start the listening Thread
        self.listener = Thread(target=self.receive_loop, args=())
        self.listener.start()
        # Start the time Thread
        self.time_keeper = Thread(target=self.timer, args=())
        self.time_keeper.start()
        # start UI thread
        self.input_loop = Thread(target=self.user_input_loop, args=())
        self.input_loop.start()
        # Start the sending Thread
        self.server = Thread(target=self.server_loop, args=())
        self.server.start()

    # This method gathers needed network info from the user if file not found
    def build_self(self):
        print("The start up file was not found, please enter values manually.")
        address_book = []
        # self.id = "Enter Personal ID number 1-5:"
        personal_info = self.personal_info()
        for i in range(4):
            server_id = int(input("Enter Server ID number 1-5: ").strip())
            server_address = input("Enter Server address: ").strip()
            server_port = input("Enter Port address: ").strip()
            address_book.append([server_id, server_address, server_port])
        self.addresses = address_book
        self.addresses.append(personal_info)
        self.to_file()

    # This method collects and sets the address and port for this client instance
    def personal_info(self):
        self.address = input("Enter your IP address: ").strip()
        self.port = int(input("Enter your preferred port: ").strip())
        self.id = int(input("Enter which process you are: ").strip())
        return [self.id, self.address, self.port]

    # --------------------------------------------------------------------------------------------
    # The Loop Methods used to run the Server UI, Main Server, and Listener
    # Loop Method to run the server UI
    def user_input_loop(self):
        print("Choose:\n[1] Timeout\n[2] Crash\n[3] Restart")
        while True:
            choice = input(">").strip().lower()
            if choice == '1':  # Timeout
                self.timeout = 0
            elif choice == '2':  # Crash
                self.to_json()
                self.crash()
            elif choice == '3':  # Restart
                self.revive()
            else:
                print("Option not recognized, try again.\n")
                print("Choose:\n[1] Timeout\n[2] Crash\n[3] Restart")

    # Loop Method to run the main server
    def server_loop(self):
        while True:
            if self.alive:
                self.to_json()
                # sleep(.1)
                # if self.timeout > 0 or self.leader:  # everyone does this
                # if self.commitIndex > self.lastApplied:
                # self.to_log()
                if self.leader:  # leader only shit
                    # CONNIE HERE - check are we sending heartbeats, do we need to modify timeouts so leader can do shit for a bit
                    if self.timeout <= 0:
                        try:
                            prevlogterm = self.log[min(self.nextIndex)]
                            entries = self.log[min(self.nextIndex): (len(self.log) - 1)]
                        except IndexError:
                            prevlogterm = None
                            entries = None
                        msg = {'type': 'append entries', 'term': self.currentTerm, 'id': self.id,
                               'prevLogIndex': min(self.nextIndex),
                               'prevLogTerm': prevlogterm,
                               'entries': entries,
                               'leaderCommit': self.commitIndex,
                               'sender': 'server',
                               'addresses': self.addresses,
                               'state': self.get_game_state()
                               }
                        # print('trying to send')   TEST CODE
                        self.send(json.dumps(msg))
                        # print('tried to send')    TEST CODE
                    self.leader_commit_index()
                if self.timeout <= 0 and self.alive and not self.leader:  # candidate time
                    # print('i am running for election')    TEST CODE
                    self.candidate = True
                    self.leader_election()
            else:  # When 'crashed' (not self.alive) this keeps us quiet in the infinite loop
                sleep(1)

    # Loop Method to handle incoming messages
    def receive_loop(self):
        while True:
            if self.alive:
                packet, address = self.s.recvfrom(1024)
                packet = packet.decode('utf-8')
                packet = json.loads(packet)

                self.receive(packet, address)
            else:  # When 'crashed' (not self.alive) this keeps us quiet in the infinite loop
                sleep(1)

    # Method to handle the receiving and processing of messages
    def receive(self, packet, address):
        sender = packet['sender']
        if sender == 'client':
            self.handle_request(packet, address)
        elif sender == 'server':
            type = packet['type']
            #  TODO this if statement might break everything.. not sure
            if packet['term'] > self.currentTerm and type == 'append entries':
                # print('I INCREMENTED TERM 4')
                self.currentTerm = packet['term']
                self.leader = False
                self.leaderID = packet['id']
            if type == 'append entries':
                # print('hey i got an append entries!')
                response = self.append_entries(packet['term'], packet['id'], packet['prevLogIndex'],
                                               packet['prevLogTerm'], packet['entries'], packet['leaderCommit'])
                msg = {'sender': 'server', 'type': 'ae response', 'id': self.id, 'term': self.currentTerm,
                       'response': response, 'nextIndex': len(self.log), 'commitIndex': self.commitIndex}
                self.send(json.dumps(msg), False, self.leaderID)
                if response:
                    self.addresses = packet['addresses']
                    self.update_game_state(packet['state'])
            elif type == 'request vote':
                success = self.request_vote(packet['term'], packet['id'],
                                            packet['lastLogIndex'], packet['lastLogTerm'])
                if success:
                    # print(str(packet['id']) + 'wanted a vote I said YES')
                    msg = {'sender': 'server', 'type': 'vote response', 'id': self.id, 'term': self.currentTerm,
                           'success': success}
                    self.send(json.dumps(msg), False, packet['id'])
            elif type == 'ae response' and self.leader:
                # print('i go t ae response')
                if len(self.log) - 1 >= packet['nextIndex']:
                    if packet['response']:
                        self.nextIndex[packet['id']] += 1
                        self.matchIndex[packet['id']] = packet['commitIndex']
                    if not packet['response']:
                        self.nextIndex[packet['id']] -= 1
            elif type == 'vote response':
                # print(packet['success'])
                if packet['success']:
                    # print('i got voted for!!')
                    self.votes += 1
            else:  # Error Condition
                print("Invalid message type passed to receive()")
        else:  # Error Condition
            print("Invalid message sender passed to receive()")

    # --------------------------------------------------------------------------------------------
    # The Timer Methods
    # Method to leader heartbeat waiting timer
    def timer(self):
        # leader does not time out, they only die, so we need to be mindful of that
        while True:
            if self.alive:
                if self.timeout > 0:
                    sleep(0.1)
                    self.timeout -= 0.1
            else:  # When 'crashed' (not self.alive) this keeps us quiet in the infinite loop
                sleep(1)

    # --------------------------------------------------------------------------------------------
    # Methods To Assist Server Function
    # This Method appends the received entries
    def append_entries(self, term, leaderID, prevLogIndex, prevLogTerm, entries,
                       leaderCommit):  # For leader, appends entries, heartbeat $$$$$$$$$$$$$$
        self.timeout = self.timeoutTime
        #print('im in append entreis')
        # print(self.timeout)
        success = True
        indexOfLastNewEntry = len(self.log) - 1
        if term < self.currentTerm:  # What is this doing? -JORDAN
            success = False
        if indexOfLastNewEntry >= prevLogIndex:
            if self.log[prevLogIndex] != prevLogTerm:  # Probably need to index in further? -JORDAN
                success = False
                for i in range(prevLogIndex, indexOfLastNewEntry):  # Probably need to index +1 to get last -JORDAN
                    self.log.remove(i)  # Probably should slice, otherwise indexing may not work -JORDAN
        for x in entries:
            if x not in self.log:
                self.log.append(x)
        if leaderCommit > self.commitIndex:
            self.commitIndex = min(leaderCommit, indexOfLastNewEntry)
        if success:
            # print('I INCREMENTED TERM 3')
            # print(str(term) + 'TERM')
            # print(str(self.currentTerm) + 'SELF.CURRENTTERM')
            self.currentTerm = term
        if not self.leader:
            self.leaderID = leaderID
            self.candidate = False  # CONNIE maybe remove
        return success

    # Method to request a vote
    def request_vote(self, term, candidate_ID, lastLogIndex, lastLogTerm):
        # print('am I a leader?' + str(self.leader))  TEST CODE
        if self.leader:
            # print(str(candidate_ID) + "wanted vote, I said no bc I am LEADER")
            return False
        if self.candidate:
            if term > self.currentTerm:
                # print(str(candidate_ID) + "wanted vote, I said YES bc I am CANDIDATE but their term is higher")
                return True
            # print(str(candidate_ID) + "wanted vote, I said no bc I am CANDIDATE")
            return False
        if term < self.currentTerm:
            # print(str(candidate_ID) + "wanted vote, I said no bc their term is not upto date")
            return False
        if self.votedFor is None or self.votedFor == candidate_ID:
            try:
                if self.log[lastLogIndex][0] == lastLogTerm:
                    self.timeout = self.timeoutTime
                    # print('I INCREMENTED TERM 2')
                    self.currentTerm = term
                    self.votedFor = candidate_ID
                    return True  # candidate received vote
                else:
                    # print(str(candidate_ID) + "wanted vote, I said no bc their LOG is not upto date")
                    return False  # log was not up-to-date
            except IndexError:
                if len(self.log) == 0:  # We are just starting up, there is no leader yet
                    # print('i said true')
                    self.timeout = self.timeoutTime
                    # print('I INCREMENTED TERM 1')
                    self.currentTerm = term
                    self.votedFor = candidate_ID
                    return True
                # print(self.leaderID)
                # print(str(candidate_ID) + "wanted vote, I said no bc their LOG is not upto date HERE")
                return False  # log was not up-to-date

    # Method to run a leader election
    def leader_election(self):
        # print('hey leader election')
        self.votes = 1
        self.currentTerm += 1
        self.timeout = self.electionTime
        if bool(self.log):
            lastlogterm = self.log[self.commitIndex][0]
        else:
            lastlogterm = None
        msg = {'sender': 'server', 'type': 'request vote', 'term': self.currentTerm, 'id': self.id,
               'lastLogIndex': self.commitIndex, 'lastLogTerm': lastlogterm}
        self.send(json.dumps(msg))
        while self.timeout > 0:
            # print(self.votes)
            # print(self.currentTerm)
            if self.votes >= 3:
                # print('I AM LEADER\a')
                self.leader = True
                self.candidate = False
                break
        if self.timeout <= 0:
            self.candidate = False

    # Method to determine committed values
    def leader_commit_index(self):
        for n in range(self.commitIndex, self.commitIndex + 10):
            a, b, c = False, False, False
            counter = 0
            if n > self.commitIndex:
                a = True
            for i in self.matchIndex:
                if self.matchIndex[i] >= n:
                    counter += 1
            if counter >= 3:
                b = True
            try:
                if self.log[n][0] == self.currentTerm:
                    c = True
            except IndexError:
                if len(self.log) == 0:
                    c = True
            if a and b and c:
                # print(n)
                self.commitIndex = n
                break

    # --------------------------------------------------------------------------------------------
    # Methods to handle sending and receiving messages in support of Receiving Loop (above)
    def send(self, message, to_all_servers=True, destination=None):
        # self.log.append(((self.id, self.get_stamp()), "send", None))
        if to_all_servers:
            for node in self.addresses:
                if node[0] == 'red' or node[0] == 'blue' or node[0] == self.id:
                    continue
                else:
                    # tempSensorSocket.sendto(tempString.encode(), ("127.0.0.1",7070))
                    self.s.sendto(message.encode('utf-8'), (node[1], int(node[2])))
                    # print('sent to everyone!')
        else:
            for node in self.addresses:
                if int(node[0]) == int(destination):
                    self.s.sendto(message.encode('utf-8'), (node[1], int(node[2])))
                    # print('sent!')
                    break

    # Method to handle the messaging to clients if we are leader
    def talk_to_client(self, name):
        clock = [0, self.commitIndex]
        game = True
        if not self.client_alive_red or not self.client_alive_blue:
            game = False
        if name == 'red':
            knows = self.clients_clock_red
            alive = self.client_alive_red
        elif name == 'blue':
            knows = self.clients_clock_blue
            alive = self.client_alive_blue
        else:  # Error Condition
            print("Invalid Username passed to talk_to_client()")
            return
        log = self.get_log(knows)
        info = {'time': clock,
                'action': None,
                'name': name,
                'alive': alive,
                'game': game,
                'log': log,
                'sender': "server"
                }
        message = json.dumps(info)
        self.send_to_client(name, message)

    # Method to forward a given message from the client to the leader
    def fwd_to_leader(self, item):  # Send request to leader, we do need , fwd to leader
        message = json.dumps(item)
        identity = self.leaderID
        self.send(json.dumps(message), False, identity)

    # Method to return all committed parts of a log back to some number
    def get_log(self, knows):
        if self.commitIndex > knows:
            log = []
            for i in range(knows, self.commitIndex + 1):
                log.append(self.log[i])
            return log
        else:
            return None

    # Method to handle incoming requests
    def handle_request(self, packet, address):
        if self.leader:
            name = packet['name']
            clock = packet['time']
            if not self.seen(name, clock[0]):
                action = packet['action']
                if name == "red":
                    self.client_count_red = clock[0]
                    self.clients_clock_red = clock[1]
                    self.game_logic(name, action)
                    self.talk_to_client(name)
                    self.talk_to_client("blue")
                elif name == "blue":
                    self.client_count_blue = clock[0]
                    self.clients_clock_blue = clock[1]
                    self.game_logic(name, action)
                    self.talk_to_client(name)
                    self.talk_to_client("red")
                else:  # You get here if name is None
                    self.handle_startup(address)
            else:
                pass  # Done if message is duplicate
        else:
            self.fwd_to_leader(packet)

    # Method to handle first contact with client
    def handle_startup(self, address):
        if self.has_player:
            self.client_alive_blue = True
            self.addresses.append(["blue", address[0], address[1]])
            self.send_comms("red", True)
            self.send_comms("blue", True)
        else:
            self.has_player = True
            self.client_alive_red = True
            self.addresses.append(["red", address[0], address[1]])
            self.send_comms("red", False)

    # Method to handle sending communications to clients
    def send_comms(self, name, game=True, alive=True):
        info = {'time': [0, self.commitIndex],
                'action': None,
                'name': name,
                'alive': alive,
                'game': game,
                'log': None,
                'sender': "server"
                }
        message = json.dumps(info)
        self.send_to_client(name, message)

    # Method to send messages to client
    def send_to_client(self, name, message):
        for address in self.addresses:
            if address[0] == name:
                self.s.sendto(message.encode('utf-8'), (address[1], address[2]))
                break

    # Method to decide if a message has been seen previously
    def seen(self, name, request):
        if name == "red":
            return request <= self.client_count_red
        elif name == "blue":
            return request <= self.client_count_blue
        elif name is None:
            return False
        else:
            print("Error: name sent to seen() not valid")
            return True

    # --------------------------------------------------------------------------------------------
    # Methods to do the game logic
    # Method to handle the game logic on the server side
    def game_logic(self, player, action):
        self.log.append([self.currentTerm, player, action, self.lastApplied])
        self.lastApplied += 1
        if player == "red":  # Player "red" did.....
            # Block
            if action == "block_left":
                self.red_left_blocking = True
            elif action == "block_right":
                self.red_right_blocking = True
            # Strike
            elif action == "strike_left":
                self.red_left_blocking = False
                result = self.strike("blue", self.blue_right_blocking, False)
                if result == "stunned":
                    self.log.append([self.currentTerm, 'red', 'stunned', self.lastApplied])
                    self.lastApplied += 1
                else:
                    self.log.append([self.currentTerm, 'blue', 'hit_right', self.lastApplied])
                    self.lastApplied += 1
            elif action == "strike_right":
                self.red_right_blocking = False
                result = self.strike("blue", self.blue_left_blocking, True)
                if result == "stunned":
                    self.log.append([self.currentTerm, 'red', 'stunned', self.lastApplied])
                    self.lastApplied += 1
                else:
                    self.log.append([self.currentTerm, 'blue', 'hit_left', self.lastApplied])
                    self.lastApplied += 1
            else:  # Should never get here
                print("Invalid Move passed to game_logic()")
        elif player == "blue":  # Player "blue" did.....
            # Block
            if action == "block_left":
                self.blue_left_blocking = True
            elif action == "block_right":
                self.blue_right_blocking = True
            # Strike
            elif action == "strike_left":
                self.blue_left_blocking = False
                result = self.strike("red", self.red_right_blocking, False)
                if result == "stunned":
                    self.log.append([self.currentTerm, 'blue', 'stunned', self.lastApplied])
                    self.lastApplied += 1
                else:
                    self.log.append([self.currentTerm, 'red', 'hit_right', self.lastApplied])
                    self.lastApplied += 1
            elif action == "strike_right":
                self.blue_right_blocking = False
                result = self.strike("red", self.red_left_blocking, True)
                if result == "stunned":
                    self.log.append([self.currentTerm, 'blue', 'stunned', self.lastApplied])
                    self.lastApplied += 1
                else:
                    self.log.append([self.currentTerm, 'red', 'hit_left', self.lastApplied])
                    self.lastApplied += 1
            else:  # Should never get here
                print("Invalid Move passed to game_logic()")
        else:  # Should never get here
            print("Invalid Username passed to game_logic()")
        self.to_log()  # Where log gets saved to file once updated

    # Method to decide outcome of a strike
    def strike(self, name, blocking, left):
        # If you are blocked you get stunned
        if blocking:
            return "stunned"
        else:
            if random.randint(0, 10) == 5:  # One in ten chance of kill
                if name == "red":
                    self.client_alive_red = False
                else:
                    self.client_alive_blue = False
            if left:
                return "hit_left"
            else:
                return "hit_right"

    # Method to compile the game state in a dictionary
    def get_game_state(self):
        dictionary = {
            'last': self.lastApplied,
            'clients_clock_red': self.clients_clock_red,
            'clients_clock_blue': self.clients_clock_blue,
            'client_alive_red': self.client_alive_red,
            'client_alive_blue': self.client_alive_blue,
            'has_player': self.has_player,
            'client_count_red': self.client_count_red,
            'client_count_blue': self.client_count_blue,
            'red_left_blocking': self.red_left_blocking,
            'red_right_blocking': self.red_right_blocking,
            'blue_left_blocking': self.blue_left_blocking,
            'blue_right_blocking': self.blue_right_blocking
        }
        return dictionary

    # Method to update the game state from a dictionary
    def update_game_state(self, dictionary):
        self.lastApplied = dictionary['last']
        self.clients_clock_red = dictionary['clients_clock_red']
        self.clients_clock_blue = dictionary['clients_clock_blue']
        self.client_alive_red = dictionary['client_alive_red']
        self.client_alive_blue = dictionary['client_alive_blue']
        self.has_player = dictionary['has_player']
        self.client_count_red = dictionary['client_count_red']
        self.client_count_blue = dictionary['client_count_blue']
        self.red_left_blocking = dictionary['red_left_blocking']
        self.red_right_blocking = dictionary['red_right_blocking']
        self.blue_left_blocking = dictionary['blue_left_blocking']
        self.blue_right_blocking = dictionary['blue_right_blocking']

    # --------------------------------------------------------------------------------------------
    # Methods to do the fake crash and revive options
    # Method to do the 'crashing' of the server
    def crash(self):
        self.alive = False
        sleep(10)  # Keeps the values from clearing until all threads have 'likely' stopped
        self.log = None
        self.leaderID = None
        self.currentTerm = 0
        self.votedFor = None
        self.commitIndex = None
        self.lastApplied = None
        self.leader = None
        self.nextIndex = None
        self.votes = 0
        self.addresses = None
        self.address = None
        self.port = None
        self.timeout = 0
        self.clients_clock_red = None
        self.clients_clock_blue = None
        self.client_alive_red = None
        self.client_alive_blue = None
        self.has_player = None
        self.client_count_red = None
        self.client_count_blue = None
        self.red_left_blocking = None
        self.red_right_blocking = None
        self.blue_left_blocking = None
        self.blue_right_blocking = None

    # Method to do the 'reviving' of the server
    def revive(self):
        self.votes = 0
        self.leader = False
        self.timeout = 0
        self.from_json()
        sleep(10)  # Gets the values in before all threads start back up
        self.alive = True

    # --------------------------------------------------------------------------------------------
    # File IO Methods
    # A Method to write to a json File
    def to_json(self):
        dictionary = {
            'log': self.log,
            'leaderID': self.leaderID,
            'currentTerm': self.currentTerm,
            'votedFor': self.votedFor,
            'commitIndex': self.commitIndex,
            'lastApplied': self.lastApplied,
            'nextIndex': self.nextIndex,
            'addresses': self.addresses,
            'address': self.address,
            'port': self.port,
            'clients_clock_red': self.clients_clock_red,
            'clients_clock_blue': self.clients_clock_blue,
            'client_alive_red': self.client_alive_red,
            'client_alive_blue': self.client_alive_blue,
            'has_player': self.has_player,
            'client_count_red': self.client_count_red,
            'client_count_blue': self.client_count_blue,
            'red_left_blocking': self.red_left_blocking,
            'red_right_blocking': self.red_right_blocking,
            'blue_left_blocking': self.blue_left_blocking,
            'blue_right_blocking': self.blue_right_blocking
        }
        json_object = json.dumps(dictionary)
        # Try Catch for opening the file, should never fail
        try:
            with open('nodeStorage' + str(self.id) + '.json', 'w') as outfile:
                outfile.write(json_object)
                outfile.close()
        except IOError:
            print("Something went wrong opening nodeStorage" + str(self.id) + ".json")

    # Method to restore a node from json file
    def from_json(self):
        if exists('nodeStorage' + str(self.id) + '.json'):
            with open('nodeStorage' + str(self.id) + '.json') as json_file:
                dictionary = json.load(json_file)
                self.log = dictionary['log']
                self.leaderID = dictionary['leaderID']
                self.currentTerm = dictionary['currentTerm']
                self.votedFor = dictionary['votedFor']
                self.commitIndex = dictionary['commitIndex']
                self.lastApplied = dictionary['lastApplied']
                self.nextIndex = dictionary['nextIndex']
                self.addresses = dictionary['addresses']
                self.address = dictionary['address']
                self.port = dictionary['port']
                self.clients_clock_red = dictionary['clients_clock_red']
                self.clients_clock_blue = dictionary['clients_clock_blue']
                self.client_alive_red = dictionary['client_alive_red']
                self.client_alive_blue = dictionary['client_alive_blue']
                self.has_player = dictionary['has_player']
                self.client_count_red = dictionary['client_count_red']
                self.client_count_blue = dictionary['client_count_blue']
                self.red_left_blocking = dictionary['red_left_blocking']
                self.red_right_blocking = dictionary['red_right_blocking']
                self.blue_left_blocking = dictionary['blue_left_blocking']
                self.blue_right_blocking = dictionary['blue_right_blocking']
            json_file.close()
        else:
            print("Node Restoration Failed!")

    # A method to write the log to a human readable file
    def to_log(self):
        file = open("server_log" + str(self.id) + ".txt", 'w+')
        for item in self.log:
            line = str(item) + "\n"
            file.write(line)
        file.close()

    # This method builds the client from a found file
    def from_file(self, file):
        address_book = []
        for line in file:
            address = line.strip().split(',')
            if address[0] == str(self.id):
                self.address = address[1]
                self.port = int(address[2])
            address_book.append([address[0], address[1], address[2]])
        self.addresses = address_book

    # Method to create start up file for next run
    def to_file(self):
        file = open("server_addresses" + str(self.id) + ".txt", 'w+')
        for address in self.addresses:
            line = str(address[0]) + ',' + address[1] + ',' + str(address[2]) + "\n"
            file.write(line)
        line = str(self.id) + ',' + str(self.address) + ',' + str(self.port) + "\n"
        file.write(line)
        file.close()


if __name__ == '__main__':
    # TEST CODE
    add = ("3.4.55.666", 4000)
    mess = {'sender': 'server', 'type': 'ae response', 'id': "1", 'term': 6,
                       'response': response, 'nextIndex': 7, 'commitIndex': 4}
    server = Server()
    server.leader = True
    server.receive(mess, add)
