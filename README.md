# Consensus

Messages from the client to the server and vise versa should take the following form
dictionary 

  time: the lamport stamp from the client and the log entry number         # This allows both sides to keep track of who knows what
  action: the action                 # strike_left, strike_right, block_left, block_right, hit_left, hit_right, stuned
  name: the name of the client this is for or from         # Starts as None, then given name by server so can be 'red' or 'blue'
  alive: the boolean Lets the player know if they are still alive     # server can ignor, player checks if they are still alive
  game: a boolean to track if the game is active      # Starts False but becomes True when second player enters and upon recive of False when local state is True mean end
  log: a series of player Log Number, Name, and Move
  
  I am thinking we may want to assume multiple copies of messages may make it to the server since they might so we should be ready for redundancy 
