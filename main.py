# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import winsound

# This Method appends the received entries
    def append_entries(self, term, leaderID, prevLogIndex, prevLogTerm, entries,
                       leaderCommit):  # For leader, appends entries, heartbeat
        self.timeout = self.timeoutTime
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
            self.currentTerm = term
        if not self.leader:
            self.leaderID = leaderID
            self.candidate = False  # CONNIE maybe remove
        return success


# Press the green button in the gutter to run the script.
if __name__ == '__main__':



