
"""has ID, current term, log, voted for, vector clock?, client and node data(IP, port, ID), timeout"""

"""Need two threads to listen and send"""

from threading import Thread
from time import sleep

class Server:

    def __init__(self, id):
        self.candidateID = id
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

    def time_out(self):  #$2
        pass

    def crash(self): #$2
        pass

    def restart(self): #$2
        pass

    def request(self, item): # Send request to leader, maybe need
        pass

    def update_log(self, items): # Given log items $$$$$$$$$$$$$$$
        pass

    def append_entries(self, term, leaderID, prevLogIndex, prevLogTerm, entries, leaderCommit): # For leader, appends entries, heartbeat $$$$$$$$$$$$$$
        success = True
        indexOfLastNewEntry = len(self.log) - 1

        if term < self.currentTerm:
            success = False

        if indexOfLastNewEntry >= prevLogIndex:
            if self.log[prevLogIndex] != prevLogTerm:
                success = False
                for i in range(prevLogIndex, indexOfLastNewEntry):
                    log.remove(i)

        for x in entries:
            if x not in self.log:
                self.log.append(x)
        # might need to swap this for calling update log

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



    def talk_to_client(self):
        pass

