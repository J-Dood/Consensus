# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
# TODO for append_entries(), make minor object to allow value tests


class Tester:
    timeout = 0
    timeoutTime = 0
    log = None
    currentTerm = 0
    commitIndex = 0
    leader = False
    candidate = False

    def __init__(self):
        self.timeout = 0
        self.timeoutTime = 7
        self.log = [[3, "red", "block_left", 1],
               [3, "blue", "block_right", 2],
               [4, "red", "strike_right", 4],
               [4, "blue", "hit_left", 5]]
        self.currentTerm = 3
        self.commitIndex = 2
        self.leader = False
        self.candidate = False
        self.leaderID = None

# This Method appends the received entries
    def append_entries(self, term, leaderID, prevLogIndex, prevLogTerm, entries,
                       leaderCommit):
        self.timeout = self.timeoutTime
        success = True
        indexOfLastNewEntry = len(self.log) - 1
        if term < self.currentTerm:
            success = False
        if indexOfLastNewEntry >= prevLogIndex:
            if self.log[prevLogIndex][0] != prevLogTerm:
                success = False
                self.log = self.log[0:prevLogIndex]
        if bool(entries):
            for x in entries:
                if x not in self.log:
                    self.log.append(x)
        if leaderCommit > self.commitIndex:
            self.commitIndex = min(leaderCommit, indexOfLastNewEntry)
        if success:
            self.currentTerm = term
        if not self.leader:
            self.leaderID = leaderID
            self.candidate = False
        return success


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    term = 6
    leaderID = "catdog"
    prevLogIndex = 2
    prevLogTerm = 3
    entries = [[4, "red", "strike_left", 7],
               [4, "red", "stunned", 8],
               [5, "blue", "block_left", 9],
               [6, "blue", "block_right", 10]]
    leaderCommit = 2
    test = Tester()
    print(test.append_entries(term, leaderID, prevLogIndex, prevLogTerm, entries, leaderCommit))
    print("LOG:")
    for i in test.log:
        print(i)
    print("LEADER:")
    print(test.leaderID)
    print("CANDIDATE:")
    print(test.candidate)
    print("TERM:")
    print(test.currentTerm)

