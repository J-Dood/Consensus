
"""has ID, current term, log, voted for, vector clock?, client and node data(IP, port, ID), timeout"""


"""Need two threads to listen and send"""
from threading import Thread
from time import sleep
import json
import socket

class Server:

    def __init__(self, identity):
        self.alive = True
        self.id = identity  # Should be an int
        self.leaderID = None
        self.currentTerm = 0  # latest term server has seen
        self.votedFor = None  # candidateID that received vote in current term
        self.log = []
        self.commitIndex = 0  # index of highest log entry known to be committed
        self.lastApplied = 0  # index of highest log entry applied to state machine
        # LEADER ONLY BELOW
        self.leader = False # set to true if node is leader
        self.nextIndex = 0  # index of next log entry to send to server
        self.matchIndex = 0 # index of highest log entry known to be replicated on server
        self.votes = 0
        # Other fields, added by Jordan
        self.s = None

        # MSG RCV INFO
        # TODO hopefully wont need
        self.from_msg_term = 0
        self.from_msg_id = 0

        self.addresses = None
        self.address = None
        self.port = 4000

        try:
            file_path = r"server_addresses.txt"
            file = open(file_path, "r")
            self.from_file(file)
        except IOError:
            self.build_self()
        # Sets up the port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind((self.address, self.port))
        # Start the listening Thread
        self.listener = Thread(target=self.receive, args=())
        self.listener.start()
        # Start the sending Thread
        self.sender = Thread(target=self.run, args=())
        self.sender.start()
        # TODO TIMER HELP
        # Start the time Thread
        self.timer = Thread(target=self.timer, args=())
        self.timer.start()
        self.timeoutReset = None  #TODO not sure what this does, Jordan
        # start election timer thread
        self.election_timer = Thread(target=self.election_timer, args=())
        self.election_timer.start()
        self.electionTimerReset = None  #TODO not sure what this does, Jordan
        # start UI thread
        self.input_loop = Thread(target=self.user_input_loop, args=())
        self.input_loopr.start()

    '''
    Below three functions are used to set up server's ip addresses etc
    '''

    # This method gathers needed network info from the user if file not found.
    def build_self(self):
        print("The start up file was not found, please enter values manually.")
        address_book = []
        for i in range(4):
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
            address = line.strip().split(',')
            if address[0] != str(self.id):
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

    # Method to create start up file for next run
    def to_file(self):
        file = open("server_addresses.txt", 'w+')
        for address in self.addresses:
            line = str(address[0]) + ',' + address[1] + ',' + str(address[2]) + "\n"
            file.write(line)
        line = str(self.id) + ',' + str(self.address) + ',' + str(self.port) + "\n"
        file.write(line)
        file.close()

    '''
    user_input_loop is what is runing everything - way user interacts with server to kill, timeout, restart
    continually calls server loop which calls raft functions
    '''

    # Method to run the UI and the server
    def user_input_loop(self):
        print("Choose:\n[1] Time out\n[2] Crash\n[3] Restart")
        while True:
            choice = input(">").strip().lower()
            if choice == '1':  # Timeout
                self.timer = 0
            elif choice == '2':  # Crash
                self.crash()
            elif choice == '3':  # Restart
                self.alive = True
                # TODO probably need to do more here? like reset timer? and talk to other nodes idk

    # This method runs the main server loop
    def server_loop(self):
        while True:
            if self.alive:
                if self.timeout != 0 or self.leader: #everyone does this
                    if self.commitIndex > self.lastApplied:
                        file = open("log" + str(self.id) + ".txt", "w+")
                        for lines in self.log:
                            file.write(str(lines)+"\n")
                        file.close()
                    if self.from_msg_term > self.currentTerm:
                        self.currentTerm = self.from_msg_term
                        self.leader = False
                        self.leaderID = self.from_msg_id
                if self.leader: #leader only shit
                    # do leader shit
                    if self.heartbeat is 0: # could election timer doubel as heartbeat timer?
                        # TODO - fix timer
                        # TODO - logupdates will either be empty, if its just a heartbeat or will have updates if we got a msg from client
                        logupdates = []
                        msg = {'type': 'append entries', 'term': self.currentTerm, 'leaderID': self.id, 'prevLogIndex': (len(self.log)-1),
                               'prevLogTerm': self.log[(len(self.log)-1)], 'entries': logupdates, 'leaderCommit': self.commitIndex}
                        self.send(msg)
                    # TODO if msg receive from client append entry to local log, respond after entry applied to state machine
                    # TODO if N > commit index.. what is N???
                if self.timeout is 0 and self.alive: #candidate time
                    self.leader_election()
                    if self.electionTimer is 0:
                        self.leader_election()
                        self.electionTimer = 'reset' #TODO TIMER HELP
            else:  # When 'crashed' (not self.alive) this keeps us quiet in the infinite loop
                sleep(1)

    '''
    timer and election timer help tick down the timers, might need fixing
    '''

    # Method to leader heartbeat waiting timer
    def timer(self):
        # leader does not time out, they only die, so we need to be mindful of that
        while True:
            if self.alive:
                if self.timeout != 0:
                    sleep(1)
                    self.timeout -= 1
            else:  # When 'crashed' (not self.alive) this keeps us quiet in the infinite loop
                sleep(1)

    # Method to run election timer
    def election_timer(self):
        while True:
            if self.alive:
                if self.electionTimer != 0:
                    sleep(1)
                    self.electionTimer -= 1
            else:  # When 'crashed' (not self.alive) this keeps us quiet in the infinite loop
                sleep(1)

    '''
    update_log, append_entries, reuqest_vote, and leader_election are the heart of raft
    '''

    def update_log(self, items):
        #might need more robust trimming method - wuu bernstein here?
        for x in items:
            if x not in self.log:
                self.log.append(x)

    def append_entries(self, term, leaderID, prevLogIndex, prevLogTerm, entries, leaderCommit): # For leader, appends entries, heartbeat $$$$$$$$$$$$$$
        #TODO TIMER FIX add heartbeat functionality aka- reset timeout
        success = True
        indexOfLastNewEntry = len(self.log) - 1
        if term < self.currentTerm:
            success = False
        if indexOfLastNewEntry >= prevLogIndex:
            if self.log[prevLogIndex] != prevLogTerm:
                success = False
                for i in range(prevLogIndex, indexOfLastNewEntry):
                    log.remove(i)
        self.update_log(entries)
        if leaderCommit > self.commitIndex:
            self.commitIndex = min(leaderCommit, indexOfLastNewEntry)
        if success:
            self.currentTerm = term
        if not self.leader:
            self.leaderID = leaderID
        return success

    def request_vote(self, term, candidateID, lastLogIndex, lastLogTerm): #$$$$$$$$$$$$$$$$$
        if term < self.currentTerm:
            return False
        if self.votedFor is None or self.votedFor is candidateID:
            try:
                if self.log[lastLogIndex] == lastLogTerm:
                    self.currentTerm = term
                    return True # candidate received vote
                else:
                    return False  # log was not up-to-date
            except IndexError:
                return False # log was not up-to-date

    def leader_election(self):
        self.votes = 1
        self.currentTerm += 1
        self.electionTimer == 'reset' #TODO TIMER actually reset
        msg = {'type':'request vote', 'term': self.currentTerm, 'candidateID': self.id, 'lastLogIndex': (len(self.log)-1), 'lastLogTerm': self.log[(len(self.log)-1)]}
        self.send(msg)
        if self.votes >= 3:
            self.leader = True


    '''
    Following functions are in charge of communication, sending between servers, receving from client, etc
    '''
    #TODO - from dislog - modify for this one
    def send(self, message, toAllServers=True, destination=None):
        #self.log.append(((self.id, self.get_stamp()), "send", None))
        if toAllServers:
            # send to everyone
            pass
        else:
            # send only to leader, or candidate, use 'destination' to determine who
            pass
        for server in self.addresses:
            self.s.sendto(message.encode('utf-8'), (self.nodes[server - 1][1], self.nodes[server - 1][2]))

    def receive(self):
        while True:
            if self.alive:
                packet, address = self.s.recvfrom(1024)
                packet = packet.decode('utf-8')
                packet = json.loads(packet)

                sender = packet['sender']
                if sender is 'client':
                    # Jordan!
                    if not self.leader:
                        self.fwd_to_leader(packet)
                if sender is 'server':
                    type = packet['type']
                    if type is 'append entries':
                        response = self.append_entries(packet['term'], packet['leaderID'], packet['prevLogIndex'], packet['prevLogTerm'], packet['entries'], packet['leaderCommit'])
                        msg = {'type': 'ae response', 'id': self.id, 'response': response}
                        self.send(json.dumps(msg), False, self.leaderID)
                    if type is 'request vote':
                        success = self.request_vote(packet['term'], packet['candidateID'], packet['lastLogIndex'], packet['lastLogTerm'])
                        msg = {'type': 'vote response', 'id': self.id, 'success': success}
                        self.send(json.dumps(msg), False, packet['candidateID'])
                    if type is 'ae response' and self.leader:
                        # TODO if last log index >= next index from follower send them older logs too
                        # TODO if succesful update next index and match index for follower
                        # TODO if not succesful bc of inconsistency decrement next index and retry
                        pass
                    if type is 'vote response':
                        if packet['success']:
                            self.votes += 1
                    if type is 'client fwd' and self.leader: # we are the leader and just got a client msg fwded to us from server
                        pass
            else:  # When 'crashed' (not self.alive) this keeps us quiet in the infinite loop
                sleep(1)


    def talk_to_client(self):
        #leader should tell client msg was recived
       pass

    def fwd_to_leader(self, item): # Send request to leader, we do need , fwd to leader
        # TODO Implement this lol
        pass

    # Method to do the 'crashing' of the server
    def crash(self):
        self.alive = False
        self.log = None
        self.id = None
        self.leaderID = None
        self.currentTerm = 0
        self.votedFor = None
        self.commitIndex = None
        self.lastApplied = None
        self.
