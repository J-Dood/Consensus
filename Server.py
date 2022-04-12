
"""has ID, current term, log, voted for, vector clock?, client and node data(IP, port, ID), timeout"""

"""Need two threads to listen and send"""

from threading import Thread
from time import sleep
import time

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
        self.nextIndex = 0  # index of next log entry to send to server
        self.matchIndex = 0 # index of highest log entry known to be replicated on server

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
                if self.from_msg_term > self.currentTerm:
                    self.currentTerm = self.from_msg_term
                    self.leader = False
                    self.leaderID = self.from_msg_id
            if self.leader: #leader only shit
                # do leader shit
                # TODO send initial empty append entries to each server, repeat to prevent timeouts
                # msg = term, leaderID, prevLogIndex, prevLogTerm, entries, leaderCommit
                self.send(msg)
                # TODO if last log index >= next index from follower send them older logs too
                    # TODO if succesful update next index and match index for follower
                    # TODO if not succesful bc of inconsistency decrement next index and retry
                # TODO if msg receive from client append entry to local log, respond after entry applied to state machine
                # TODO if N > commit index.. what is N???
                pass
            else: #followerrr
                # TODO respond to msgs from candidates and leaders
                # we will probably do this in recive msg
                # TODO send responses....
                pass
            pass
            if self.timeout is 0 and self.alive: #candidate time
                self.leader_election()
                if self.electionTimer is 0:
                    # TODO lets think about this, might also need to do in recive... or not if we have globals...
                    self.leader_election()
                    self.electionTimer = 'reset' #TODO TIMER HELP




    '''
    timer and election timer help tick down the timers, might need fixing
    '''

    # TODO TIMER HELP
    def timer(self):
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
    update_log, append_entries, reuqest_vote, and leader_election are the heart of raft
    '''

    def update_log(self, items):
        #might need more robust trimming method - wuu bernstein here?
        for x in items:
            if x not in self.log:
                self.log.append(x)

    def append_entries(self, term, leaderID, prevLogIndex, prevLogTerm, entries, leaderCommit): # For leader, appends entries, heartbeat $$$$$$$$$$$$$$
        #TODO add heartbeat functionality - reset timeout
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
        votes = 1
        self.currentTerm += 1
        self.electionTimer == 'reset' #TODO actually reset

        # TODO send request vote to all other servers
        if votes >= 3:
            self.leader = True

        pass

    '''
    Following functions are in charge of communication, sending between servers, receving from client, etc
    '''
    #TODO - from dislog - modify for this one
    def send(self, message):
        #self.log.append(((self.id, self.get_stamp()), "send", None))
        for server in self.addresses:
            self.s.sendto(message.encode('utf-8'), (self.nodes[server - 1][1], self.nodes[server - 1][2]))

        # Method to receive msg

    #TODO - from dislog - modify for this one, combine with severloop probably honestly
    def receive(self):
        while True:
            packet, address = self.s.recvfrom(1024)
            packet = packet.decode('utf-8')
            packet = json.loads(packet)

            received_array = packet['array']
            received_log = packet['log']
            sender = None
            for i in range(len(self.nodes)):
                if address[0] in self.nodes[i] and address[1] in self.nodes[i]:
                    sender = self.nodes[i][0]
            info = "from " + str(sender)
            event = ((self.id, self.get_stamp()), "received", None, info, None)
            self.log.append(event)

            self.update_clock(received_array, sender)
            self.update_log(received_log)
            self.wb_trim()

    def talk_to_client(self):
        #leader should tell client msg was recived
       pass

    def request(self, item): # Send request to leader, we do need , fwd to leader
        pass
