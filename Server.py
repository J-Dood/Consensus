
"""has ID, current term, log, voted for, vector clock?, client and node data(IP, port, ID), timeout"""

"""Need two threads to listen and send"""

from threading import Thread
from time import sleep
import time
import json

class Server:

    def __init__(self, id):
        self.alive = True
        self.id = id
        self.leaderID = None
        self.currentTerm = 0  # latest term server has seen
        self.votedFor = None  # candidateID that received vote in current term
        self.log = []
        self.commitIndex = 0  # index of highest log entry known to be commited
        self.lastApplied = 0  # index of highest log entry applied to state machine
        # LEADER ONLY BELOW
        self.leader = False # set to true if node is leader
        self.nextIndex = [0, 0, 0, 0, 0]  # index of next log entry to send to server
        self.matchIndex = [0, 0, 0, 0, 0] # index of highest log entry known to be replicated on server
        # for candidates
        self.votes = 0

        # MSG RCV INFO
        # TODO hopefully wont need
        self.from_msg_term = 0
        self.from_msg_id = 0

        self.addresses = None
        self.address = None
        self.port = 4000
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

        # TODO TIMER HELP
        # Start the time Thread
        self.timer = Thread(target=self.timer, args=())
        self.timer.start()
        self.timeoutReset = None
        # start election timer thread
        self.electiontimer = Thread(target=self.timer, args=())
        self.electiontimer.start()
        self.electionTimerReset = None

    '''
    Below three functions are used to set up server's ip addresses etc
    '''
    # This method builds the client from a found file
    def from_file(self, file): # JORDAN!!
        address_book = []
        for line in file:
            address_book.append(line.strip().split(','))
        self.addresses = address_book
        file.close()

    # This method collects and sets the address and port for this client instance
    def self_info(self): # JORDAN!!
        self.address = input("Enter your IP address: ").strip()
        self.port = int(input("Enter your preferred port: ").strip())

    # Method to create start up file for next run
    def to_file(self): # JORDAN!!
        file = open("server_addresses", 'w+')
        for address in self.address:
            line = str(address[0]) + ',' + address[1] + ',' + str(address[2])
            file.write(line)
        file.close()

    '''
    user_input_loop is what is runing everything - way user interacts with server to kill, timeout, restart
    continually calls server loop which calls raft functions
    '''

    # Method to run the ui and the server
    def user_input_loop(self):
        while True:
            choice = input().strip().lower()
            if choice == '1': # Timeout
                self.timer = 0 #
            elif choice == '2': # Crash
                self.alive = False
            elif choice == '3': # Restart
                self.alive = True
                # probably need to do more here? like reset timer? and talk to other nodes idk
                # pull from file to fill log
            self.server_loop()

    def server_loop(self):
        while self.alive:
            if self.timeout != 0 or self.leader: #everyone does this
                if self.commitIndex > self.lastApplied:
                    file = open("log" + str(self.id) + ".txt", "w+")
                    for lines in self.log:
                        file.write(str(lines))
                        file.write("\n")
                    file.close()
           # TODO fix
            if self.leader: #leader only shit
                if self.heartbeat is 0: # could election timer doubel as heartbeat timer?
                    # TODO - fix timer
                    # TODO - logupdates will either be empty, if its just a heartbeat or will have updates if we got a msg from client
                    logupdates = []
                    msg = {'type': 'append entries', 'term': self.currentTerm, 'leaderID': self.id, 'prevLogIndex': (len(self.log)-1),
                           'prevLogTerm': self.log[(len(self.log)-1)], 'entries': logupdates, 'leaderCommit': self.commitIndex}
                    self.send(msg)
                # TODO if N > commit index.. what is N???
            if self.timeout is 0 and self.alive: #candidate time
                self.leader_election()
                if self.electionTimer is 0:
                    self.leader_election()
                    self.electionTimer = 'reset' #TODO TIMER HELP

    '''
    timer and election timer help tick down the timers, might need fixing
    '''

    # TODO TIMER HELP
    def timer(self):
        # leader doesnot time out, they only die, so we need to be mindful of that
        while True:
            if self.timeout != 0:
                time.sleep(1)
                self.timeout -= 1

    def electiontimer(self):
        while True:
            if self.electionTimer != 0:
                time.sleep(1)
                self.electionTimer -= 1

    '''
     append_entries, reuqest_vote, and leader_election are the heart of raft
    '''

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
                    self.log.remove(i)
        for x in entries:
            if x not in self.log:
                self.log.append(x)
        if leaderCommit > self.commitIndex:
            self.commitIndex = min(leaderCommit, indexOfLastNewEntry)
        if success:
            self.currentTerm = term
        if not self.leader:
            self.leaderID = leaderID
        return success

    def request_vote(self, term, candidateID, lastLogIndex, lastLogTerm):
        if self.leader:
            return False
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
        msg = {'sender': 'server', 'type':'request vote', 'term': self.currentTerm, 'candidateID': self.id, 'lastLogIndex': (len(self.log)-1), 'lastLogTerm': self.log[(len(self.log)-1)]}
        self.send(json.dumps(msg))
        while self.electionTimer != 0:
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
            while self.alive:
                packet, address = self.s.recvfrom(1024)
                packet = packet.decode('utf-8')
                packet = json.loads(packet)

                sender = packet['sender']
                if sender is 'client':
                    # Jordan!
                    if not self.leader:
                        self.fwd_to_leader(packet)
                    if self.leader: 
                         # TODO if msg receive from client append entry to local log, respond after entry applied to state machine
                         pass

                if sender is 'server':
                    if packet['term'] > self.currentTerm:
                        self.currentTerm = packet['term']
                        self.leader = False
                        self.leaderID = packet['id']
                    type = packet['type']
                    if type is 'append entries':
                        response = self.append_entries(packet['term'], packet['leaderID'], packet['prevLogIndex'], packet['prevLogTerm'], packet['entries'], packet['leaderCommit'])
                        msg = {'sender': 'server', 'type': 'ae response', 'id': self.id, 'term':self.currentTerm, 'response': response, 'nextIndex': len(self.log), 'commitIndex': self.commitIndex}
                        self.send(json.dumps(msg), False, self.leaderID)
                    if type is 'request vote':
                        success = self.request_vote(packet['term'], packet['candidateID'], packet['lastLogIndex'], packet['lastLogTerm'])
                        if success:
                            msg = {'sender': 'server', 'type': 'vote response', 'id': self.id, 'term':self.currentTerm,'success': success}
                            self.send(json.dumps(msg), False, packet['candidateID'])
                    if type is 'ae response' and self.leader:
                        if len(self.log)-1 >= packet['nextIndex']:
                            if packet['response']:
                                self.nextIndex[packet['id']] += 1
                                self.matchIndex[packet['id']] = packet['commitIndex']
                            if not packet['response']:
                                self.nextIndex[packet['id']] -= 1
                    if type is 'vote response':
                        if packet['success']:
                            self.votes += 1
                    
                    if type is 'client fwd' and self.leader: # we are the leader and just got a client msg fwded to us from server
                          # TODO if msg receive from client append entry to local log, respond after entry applied to state machine
                        pass


    def talk_to_client(self):
        #leader should tell client msg was recived
       pass

    def fwd_to_leader(self, item): # Send request to leader, we do need , fwd to leader
        # TODO Implement this lol
        pass
