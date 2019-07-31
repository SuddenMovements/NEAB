#Server Readme File
##Socket Hooks that need to be implemented

connection => waiting screen for user, user needs to create a player object

user creates a player object with properties:
name, id
for now maybe we just say name = id

once player object is created send socket message 'gotit', player
then a global emit 'playerJoin' is sent with only the player's name
then in response to the player, another message 'gameSetup' is sent with gameWidth, gameHeight

server has a 'windowResized' hook that takes {screenWidth, screenHeight}, could be important

sever has a 'respawn' function that takes no parameters which re-emits the ('welcome', currentPlayer) message back to the socket

server has a '0' function, this is the heartbeat function and takes a target variable, {x, y}

server has a '1' function, the fire food function which takes no parameters

sever has a '2' function, apparently this is the split cell function, but it takes a parameter virusCell
So the virus cell thing is called when the user is split due to contact with a virus or just because the player wanted to split. If the player splits then virusCell = false

if you look at line 470 you can see where the playersplit is called by the server, need to implement a clientside hook 'virusSplit' which i guess just sends virusSplit back to the server?

the most important clientside hook is the serverTellPlayerMove hook
it sends:
visibleCells, visibleFood, visibleMass, visibleVirus
These objects (i think) are centered on the player

also if the leaderboard changes then the socket sends 'leaderboard' with {players, leaderboard}
