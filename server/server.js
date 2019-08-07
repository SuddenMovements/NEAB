var express = require('express');
var app = express();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var SAT = require('sat');
// Import game settings.
var c = require('./config.json');

// Import utilities.
var util = require('./util');

// Import quadtree.
var quadtree = require('simple-quadtree');

var tree = quadtree(0, 0, c.gameWidth, c.gameHeight);

var users = [];
var massFood = [];
var food = [];
var virus = [];
var sockets = {};

var leaderboard = [];
var leaderboardChanged = false;

var V = SAT.Vector;
var C = SAT.Circle;
var initMassLog = util.log(c.defaultPlayerMass, c.slowBase);

function addFood(toAdd) {
	// var radius = util.massToRadius(c.foodMass);
	var radius = 14;
	while (toAdd--) {
		var position = c.foodUniformDisposition ? util.uniformPosition(food, radius) : util.randomPosition(radius);
		food.push({
			// Make IDs unique.
			id: (new Date().getTime() + '' + food.length) >>> 0,
			x: position.x,
			y: position.y,
			radius: radius,
			mass: Math.random() + 2,
			hue: Math.round(Math.random() * 360)
		});
	}
}

function addVirus(toAdd) {
	while (toAdd--) {
		// https://agario.fandom.com/wiki/Virus
		// A virus has 100 mass
		// var mass = util.randomInRange(c.virus.defaultMass.from, c.virus.defaultMass.to, true);
		var mass = 100;
		var radius = util.massToRadius(mass);
		var position = c.virusUniformDisposition ? util.uniformPosition(virus, radius) : util.randomPosition(radius);
		virus.push({
			id: (new Date().getTime() + '' + virus.length) >>> 0,
			x: position.x,
			y: position.y,
			radius: radius,
			mass: mass,
			speed: 0,
			fill: c.virus.fill,
			stroke: c.virus.stroke,
			strokeWidth: c.virus.strokeWidth
		});
	}
}

function removeFood(toRem) {
	while (toRem--) {
		food.pop();
	}
}

function movePlayer(player) {
	// https://agario.fandom.com/wiki/Cell
	// Players' cells constantly move in the direction of the cursor with a slight delay.
	var x = 0,
		y = 0;
	for (var i = 0; i < player.cells.length; i++) {
		var target = {
			x: player.x - player.cells[i].x + player.target.x,
			y: player.y - player.cells[i].y + player.target.y
		};
		if (player.cells[i].target !== undefined) {
			target = player.cells[i].target;
			delete player.cells[i].target;
		}
		var dist = Math.sqrt(Math.pow(target.y, 2) + Math.pow(target.x, 2));
		var deg = Math.atan2(target.y, target.x);
		var slowDown = 1;
		if (player.cells[i].speed <= 6.25) {
			slowDown = util.log(player.cells[i].mass, c.slowBase) - initMassLog + 1;
		}

		var deltaY = (player.cells[i].speed * Math.sin(deg)) / slowDown;
		var deltaX = (player.cells[i].speed * Math.cos(deg)) / slowDown;

		if (player.cells[i].speed > 6.25) {
			player.cells[i].speed -= 0.5;
		}
		if (dist < 50 + player.cells[i].radius) {
			deltaY *= dist / (50 + player.cells[i].radius);
			deltaX *= dist / (50 + player.cells[i].radius);
		}
		if (!isNaN(deltaY)) {
			player.cells[i].y += deltaY;
		}
		if (!isNaN(deltaX)) {
			player.cells[i].x += deltaX;
		}
		// Find best solution.
		for (var j = 0; j < player.cells.length; j++) {
			if (j != i && player.cells[i] !== undefined) {
				var distance = Math.sqrt(
					Math.pow(player.cells[j].y - player.cells[i].y, 2) +
						Math.pow(player.cells[j].x - player.cells[i].x, 2)
				);
				var radiusTotal = player.cells[i].radius + player.cells[j].radius;
				if (distance < radiusTotal) {
					// https://agario.fandom.com/wiki/Splitting
					// The cool down time is calculated as 30 seconds plus 2.33% of the cells mass
					if (player.lastSplit > new Date().getTime() - 1000 * (30 + player.cells[i].mass * 0.0233)) {
						if (player.cells[i].x < player.cells[j].x) {
							player.cells[i].x--;
						} else if (player.cells[i].x > player.cells[j].x) {
							player.cells[i].x++;
						}
						if (player.cells[i].y < player.cells[j].y) {
							player.cells[i].y--;
						} else if (player.cells[i].y > player.cells[j].y) {
							player.cells[i].y++;
						}
					} else if (distance < radiusTotal / 1.75) {
						player.cells[i].mass += player.cells[j].mass;
						player.cells[i].radius = util.massToRadius(player.cells[i].mass);
						player.cells.splice(j, 1);
					}
				}
			}
		}
		if (player.cells.length > i) {
			var borderCalc = player.cells[i].radius / 3;
			if (player.cells[i].x > c.gameWidth - borderCalc) {
				player.cells[i].x = c.gameWidth - borderCalc;
			}
			if (player.cells[i].y > c.gameHeight - borderCalc) {
				player.cells[i].y = c.gameHeight - borderCalc;
			}
			if (player.cells[i].x < borderCalc) {
				player.cells[i].x = borderCalc;
			}
			if (player.cells[i].y < borderCalc) {
				player.cells[i].y = borderCalc;
			}
			x += player.cells[i].x;
			y += player.cells[i].y;
		}
	}
	player.x = x / player.cells.length;
	player.y = y / player.cells.length;
}

function moveMassOrVirus(entity) {
	var deg = Math.atan2(entity.target.y, entity.target.x);
	var deltaY = entity.speed * Math.sin(deg);
	var deltaX = entity.speed * Math.cos(deg);

	entity.speed -= 0.5;
	if (entity.speed < 0) {
		entity.speed = 0;
	}
	if (!isNaN(deltaY)) {
		entity.y += deltaY;
	}
	if (!isNaN(deltaX)) {
		entity.x += deltaX;
	}

	var borderCalc = entity.radius + 5;

	if (entity.x > c.gameWidth - borderCalc) {
		entity.x = c.gameWidth - borderCalc;
		entity.target.x *= -1;
	}
	if (entity.y > c.gameHeight - borderCalc) {
		entity.y = c.gameHeight - borderCalc;
		entity.target.y *= -1;
	}
	if (entity.x < borderCalc) {
		entity.x = borderCalc;
		entity.target.x *= -1;
	}
	if (entity.y < borderCalc) {
		entity.y = borderCalc;
		entity.target.y *= -1;
	}
}

function balanceMass() {
	var totalMass =
		food.length * c.foodMass +
		users
			.map(function(u) {
				return u.massTotal;
			})
			.reduce(function(pu, cu) {
				return pu + cu;
			}, 0);

	var massDiff = c.gameMass - totalMass;
	var maxFoodDiff = c.maxFood - food.length;
	var foodDiff = parseInt(massDiff / c.foodMass) - maxFoodDiff;
	var foodToAdd = Math.min(foodDiff, maxFoodDiff);
	var foodToRemove = -Math.max(foodDiff, maxFoodDiff);

	if (foodToAdd > 0) {
		//console.log('[DEBUG] Adding ' + foodToAdd + ' food to level!');
		addFood(foodToAdd);
		//console.log('[DEBUG] Mass rebalanced!');
	} else if (foodToRemove > 0) {
		//console.log('[DEBUG] Removing ' + foodToRemove + ' food from level!');
		removeFood(foodToRemove);
		//console.log('[DEBUG] Mass rebalanced!');
	}

	var virusToAdd = c.maxVirus - virus.length;

	if (virusToAdd > 0) {
		addVirus(virusToAdd);
	}
}

io.on('connection', function(socket) {
	console.log('A user connected!', socket.id);

	var radius = util.massToRadius(c.defaultPlayerMass);
	var position =
		c.newPlayerInitialPosition == 'farthest' ? util.uniformPosition(users, radius) : util.randomPosition(radius);

	var cells = [
		{
			mass: c.defaultPlayerMass,
			x: position.x,
			y: position.y,
			radius: radius
		}
	];
	var massTotal = c.defaultPlayerMass;

	var currentPlayer = {
		id: socket.id,
		x: position.x,
		y: position.y,
		w: c.defaultPlayerMass,
		h: c.defaultPlayerMass,
		cells: cells,
		massTotal: massTotal,
		hue: Math.round(Math.random() * 360),
		lastHeartbeat: new Date().getTime(),
		target: {
			x: 0,
			y: 0
		}
	};

	socket.on('gotit', function(player) {
		console.log('[INFO] Player ' + player.name + ' connecting!');

		if (util.findIndex(users, player.id) > -1) {
			console.log('[INFO] Player ID is already connected, kicking.');
			socket.disconnect();
		} else if (!util.validNick(player.name)) {
			socket.emit('kick', 'Invalid username.');
			socket.disconnect();
		} else {
			console.log('[INFO] Player ' + player.name + ' connected!');
			sockets[player.id] = socket;

			var radius = util.massToRadius(c.defaultPlayerMass);
			var position =
				c.newPlayerInitialPosition == 'farthest'
					? util.uniformPosition(users, radius)
					: util.randomPosition(radius);
			position = { x: 100, y: 100 };

			player.x = position.x;
			player.y = position.y;
			player.target.x = 0;
			player.target.y = 0;
			player.cells = [
				{
					mass: c.defaultPlayerMass,
					x: position.x,
					y: position.y,
					radius: radius
				}
			];
			player.massTotal = c.defaultPlayerMass;
			player.hue = Math.round(Math.random() * 360);
			currentPlayer = player;
			currentPlayer.lastHeartbeat = new Date().getTime();
			users.push(currentPlayer);

			io.emit('playerJoin', { name: currentPlayer.name });

			socket.emit('gameSetup', {
				gameWidth: c.gameWidth,
				gameHeight: c.gameHeight
			});
			console.log('Total players: ' + users.length);
		}
	});

	socket.on('windowResized', function(data) {
		currentPlayer.screenWidth = data.screenWidth;
		currentPlayer.screenHeight = data.screenHeight;
	});

	socket.on('respawn', function() {
		if (util.findIndex(users, currentPlayer.id) > -1) {
			users.splice(util.findIndex(users, currentPlayer.id), 1);
		}
		socket.emit('welcome', currentPlayer);
		console.log('[INFO] User ' + currentPlayer.name + ' respawned!');
	});

	socket.on('disconnect', function() {
		if (util.findIndex(users, currentPlayer.id) > -1) users.splice(util.findIndex(users, currentPlayer.id), 1);
		console.log('[INFO] User ' + currentPlayer.name + ' disconnected!');

		socket.broadcast.emit('playerDisconnect', { name: currentPlayer.name });
	});

	// Heartbeat function, update everytime.
	socket.on('0', function(target) {
		currentPlayer.lastHeartbeat = new Date().getTime();
		if (target.x !== currentPlayer.x || target.y !== currentPlayer.y) {
			currentPlayer.target = target;
		}
	});

	socket.on('1', function() {
		// Fire food.
		// https://agario.fandom.com/wiki/Ejecting
		// The ejected mass can be eaten by any cell that is over 20 mass.
		// Cells lose 18 mass per ejection
		// however, the mass of the ejected piece is only ~72% of that. Consuming the mass only gains 13 mass.
		for (var i = 0; i < currentPlayer.cells.length; i++) {
			if (currentPlayer.cells[i].mass >= c.playerSplitMass) {
				// var mass = c.fireFood;
				currentPlayer.cells[i].mass -= 18;
				currentPlayer.massTotal -= 18;
				// 'ejected mass has an angle of spread, meaning that Viruses created may veer off course by ~20 degrees'
				let target = {
					x: currentPlayer.x - currentPlayer.cells[i].x + currentPlayer.target.x,
					y: currentPlayer.y - currentPlayer.cells[i].y + currentPlayer.target.y
				};
				let mag = Math.sqrt(target.x * target.x + target.y * target.y);
				let targetAngle = Math.atan2(target.y, target.x) + (Math.random() - 0.5) * Math.PI * 2 * (20 / 360);
				let spreadTarget = {
					x: Math.cos(targetAngle) * mag,
					y: Math.sin(targetAngle) * mag
				};
				massFood.push({
					id: currentPlayer.id,
					num: i,
					mass: 13,
					hue: currentPlayer.hue,
					target: spreadTarget,
					x: currentPlayer.cells[i].x,
					y: currentPlayer.cells[i].y,
					radius: util.massToRadius(13),
					speed: 25
				});
			}
		}
	});

	socket.on('2', function(virusCell) {
		function splitCell(cell, splitFromVirus) {
			// https://agario.fandom.com/wiki/Splitting
			//  'To be able to split, a cell needs to have at least 35 mass'
			if (currentPlayer.cells.length < c.limitSplit && cell && cell.mass && cell.mass >= c.playerSplitMass) {
				cell.mass = cell.mass / 2;
				cell.radius = util.massToRadius(cell.mass);
				let target = currentPlayer.target;
				if (splitFromVirus) {
					target = {
						x: Math.random() * 2 - 1,
						y: Math.random() * 2 - 1
					};
				}
				currentPlayer.cells.push({
					mass: cell.mass,
					x: cell.x,
					y: cell.y,
					radius: cell.radius,
					speed: 25,
					target: target
				});
				currentPlayer.lastSplit = new Date().getTime();
			}
		}
		if (virusCell !== false) {
			//Split single cell from virus
			// https://agario.fandom.com/wiki/Splitting
			// 'Consuming a virus will cause a player's cell to gain 100 mass'
			// 'The popped cell will gain +100 mass, but will also pop into 8-16 pieces'
			currentPlayer.cells[virusCell].mass += 100;
			let lastCellIndex = currentPlayer.cells.length;
			let splitCount = Math.round(4 + Math.random());
			console.log('splitCount ' + splitCount);
			splitCell(currentPlayer.cells[virusCell], true);
			for (let i = 1; i < splitCount; i++) {
				console.log('split ');
				console.log(i);
				for (let j = lastCellIndex; j < currentPlayer.cells.length; j++) {
					splitCell(currentPlayer.cells[j], true);
				}
				splitCell(currentPlayer.cells[virusCell], true);
			}
		} else {
			//Split all cells
			var numCellsToSplit = currentPlayer.cells.length;
			for (var d = 0; d < numCellsToSplit; d++) {
				splitCell(currentPlayer.cells[d], false);
			}
			// currentPlayer.lastSplit = new Date().getTime();
		}
	});
});

function tickPlayer(currentPlayer) {
	if (currentPlayer.lastHeartbeat < new Date().getTime() - c.maxHeartbeatInterval) {
		sockets[currentPlayer.id].emit('kick', 'Last heartbeat received over ' + c.maxHeartbeatInterval + ' ago.');
		sockets[currentPlayer.id].disconnect();
	}

	movePlayer(currentPlayer);

	function objectIsWithinCell(f) {
		return SAT.pointInCircle(new V(f.x, f.y), playerCircle);
	}

	function deleteFood(f) {
		food[f] = {};
		food.splice(f, 1);
	}

	function eatMass(m) {
		if (SAT.pointInCircle(new V(m.x, m.y), playerCircle)) {
			if (m.id == currentPlayer.id && m.speed > 0 && z == m.num) return false;
			// 'Any cell that is 10% larger than the ejected mass can consume it'
			if (currentCell.mass > m.mass * 1.1) return true;
		}
		return false;
	}

	function collisionCheck(collision) {
		// https://agario.fandom.com/wiki/Splitting
		// a split cell, unlike a single cell, must be 33% larger than the cell it tries to consume
		// (a single cell only needs to be 25% bigger than its target)
		let multiplier = 1.25;
		if (collision.aCellCount > 1) {
			multiplier = 1.33;
		}
		if (
			collision.aUser.mass > collision.bUser.mass * multiplier &&
			collision.aUser.radius >
				Math.sqrt(
					Math.pow(collision.aUser.x - collision.bUser.x, 2) +
						Math.pow(collision.aUser.y - collision.bUser.y, 2)
				) *
					1.75
		) {
			console.log('[DEBUG] Killing user: ' + collision.bUser.id);
			console.log('[DEBUG] Collision info:');
			console.log(collision);

			var numUser = util.findIndex(users, collision.bUser.id);
			if (numUser > -1) {
				if (users[numUser].cells.length > 1) {
					users[numUser].massTotal -= collision.bUser.mass;
					users[numUser].cells.splice(collision.bUser.num, 1);
				} else {
					users.splice(numUser, 1);
					io.emit('playerDied', { name: collision.bUser.name });
					sockets[collision.bUser.id].emit('RIP');
				}
			}
			currentPlayer.massTotal += collision.bUser.mass;
			collision.aUser.mass += collision.bUser.mass;
		}
	}

	for (var z = 0; z < currentPlayer.cells.length; z++) {
		var currentCell = currentPlayer.cells[z];
		var playerCircle = new C(new V(currentCell.x, currentCell.y), currentCell.radius);

		var foodEaten = food.map(objectIsWithinCell).reduce(function(a, b, c) {
			return b ? a.concat(c) : a;
		}, []);

		foodEaten.forEach(deleteFood);

		var massesEaten = massFood.map(eatMass).reduce(function(a, b, c) {
			return b ? a.concat(c) : a;
		}, []);

		var virusCollisions = virus.map(objectIsWithinCell).reduce(function(a, b, c) {
			return b ? a.concat(c) : a;
		}, []);

		if (virusCollisions.length > 0 && currentCell.mass > virus[virusCollisions[0]].mass) {
			sockets[currentPlayer.id].emit('virusSplit', z);
			virus.splice(virusCollisions[0], 1);
		}

		var totalMassEaten = 0;
		for (var m = 0; m < massesEaten.length; m++) {
			totalMassEaten += massFood[massesEaten[m]].mass;
			massFood[massesEaten[m]] = {};
			massFood.splice(massesEaten[m], 1);
			for (var n = 0; n < massesEaten.length; n++) {
				if (massesEaten[m] < massesEaten[n]) {
					massesEaten[n]--;
				}
			}
		}

		if (typeof currentCell.speed == 'undefined') currentCell.speed = 6.25;
		totalMassEaten += foodEaten.length * c.foodMass;
		currentCell.mass += totalMassEaten;
		currentPlayer.massTotal += totalMassEaten;
		currentCell.radius = util.massToRadius(currentCell.mass);
		playerCircle.r = currentCell.radius;

		var playerCollisions = [];

		// TODO quadtree cleanup, do we even need it?
		// let r = currentCell.radius;
		// tree.clear();
		// users.forEach(tree.put);
		// var worldRectToSearch = {x : currentCell.x - r * 2, y : currentCell.y - r * 2, w : r * 4, h : r * 4}
		// var otherUsers =  tree.get(worldRectToSearch);
		// if (otherUsers) {
		//     console.log(otherUsers);
		// }

		for (let user of users) {
			if (user.id != currentPlayer.id) {
				for (var i = 0; i < user.cells.length; i++) {
					if (user.cells[i].mass > 10 && user.id !== currentPlayer.id) {
						var response = new SAT.Response();
						var collided = SAT.testCircleCircle(
							playerCircle,
							new C(new V(user.cells[i].x, user.cells[i].y), user.cells[i].radius),
							response
						);
						if (collided) {
							response.aUser = currentCell;
							response.aCellCount = currentPlayer.cells.length;
							response.bUser = {
								id: user.id,
								name: user.name,
								x: user.cells[i].x,
								y: user.cells[i].y,
								num: i,
								mass: user.cells[i].mass
							};
							response.bCellCount = user.cells.length;
							playerCollisions.push(response);
						}
					}
				}
			}
		}

		playerCollisions.forEach(collisionCheck);
	}
}

function moveloop() {
	for (var i = 0; i < users.length; i++) {
		tickPlayer(users[i]);
	}
	for (i = 0; i < massFood.length; i++) {
		if (massFood[i].speed > 0) {
			moveMassOrVirus(massFood[i]);
		}
	}
	for (i = 0; i < virus.length; i++) {
		if (virus[i].speed > 0) {
			moveMassOrVirus(virus[i]);
		}
	}
	// If you eject mass into a virus, the virus will consume the mass and get slightly bigger.
	// If you eject 7 pellets into a virus, a new virus will be shot out in the direction of the last ejected pellet which was fed to the virus
	// and the original virus will immediately shrink back to 100 mass.
	for (i = 0; i < virus.length; i++) {
		let massesInVirus = massFood.filter(food => {
			return (
				Math.pow(food.x - virus[i].x, 2) + Math.pow(food.y - virus[i].y, 2) < virus[i].radius * virus[i].radius
			);
		});
		for (let food of massesInVirus) {
			virus[i].mass += food.mass;
			massFood.splice(massFood.indexOf(food), 1);
			if (virus[i].mass > c.virus.splitMass) {
				console.log('virus should split!!');
				let splitDirection = {
					x: virus[i].x - food.x || Math.random(),
					y: virus[i].y - food.y || Math.random()
				};
				let newVirus = {
					id: (new Date().getTime() + '' + virus.length) >>> 0,
					x: virus[i].x,
					y: virus[i].y,
					radius: util.massToRadius(100),
					mass: 100,
					target: splitDirection,
					speed: 25,
					fill: c.virus.fill,
					stroke: c.virus.stroke,
					strokeWidth: c.virus.strokeWidth
				};
				virus.push(newVirus);
				virus.mass = 100;
			}
		}
	}
}

function gameloop() {
	if (users.length > 0) {
		users.sort(function(a, b) {
			return b.massTotal - a.massTotal;
		});

		var topUsers = [];

		for (var i = 0; i < Math.min(10, users.length); i++) {
			topUsers.push({
				id: users[i].id,
				name: users[i].name
			});
		}
		if (isNaN(leaderboard) || leaderboard.length !== topUsers.length) {
			leaderboard = topUsers;
			leaderboardChanged = true;
		} else {
			for (i = 0; i < leaderboard.length; i++) {
				if (leaderboard[i].id !== topUsers[i].id) {
					leaderboard = topUsers;
					leaderboardChanged = true;
					break;
				}
			}
		}
		for (i = 0; i < users.length; i++) {
			for (var z = 0; z < users[i].cells.length; z++) {
				// https://agario.fandom.com/wiki/Cell
				// Cells lose mass over time, at a rate of 0.2% of their mass per second
				// in config.json massLossRate is recorded as 0.002
				let newMass = users[i].cells[z].mass * (1 - c.massLossRate);
				if (newMass > c.defaultPlayerMass) {
					users[i].massTotal -= users[i].cells[z].mass - newMass;
					users[i].cells[z].mass = newMass;
				}
			}
		}
	}
	balanceMass();
}

function sendUpdates() {
	users.forEach(function(u) {
		// center the view if x/y is undefined, this will happen for spectators
		u.x = u.x || c.gameWidth / 2;
		u.y = u.y || c.gameHeight / 2;
		let visibleWidth = (u.screenWidth * u.massTotal) / c.defaultPlayerMass + 200;
		let visibleHeight = (u.screenHeight * u.massTotal) / c.defaultPlayerMass + 200;
		var visibleFood = food
			.map(function(f) {
				if (
					f.x > u.x - visibleWidth / 2 - 20 &&
					f.x < u.x + visibleWidth / 2 + 20 &&
					f.y > u.y - visibleHeight / 2 - 20 &&
					f.y < u.y + visibleHeight / 2 + 20
				) {
					return f;
				}
			})
			.filter(function(f) {
				return f;
			});

		var visibleVirus = virus
			.map(function(f) {
				if (
					f.x > u.x - visibleWidth / 2 - f.radius &&
					f.x < u.x + visibleWidth / 2 + f.radius &&
					f.y > u.y - visibleHeight / 2 - f.radius &&
					f.y < u.y + visibleHeight / 2 + f.radius
				) {
					return f;
				}
			})
			.filter(function(f) {
				return f;
			});

		var visibleMass = massFood
			.map(function(f) {
				if (
					f.x + f.radius > u.x - visibleWidth / 2 - 20 &&
					f.x - f.radius < u.x + visibleWidth / 2 + 20 &&
					f.y + f.radius > u.y - visibleHeight / 2 - 20 &&
					f.y - f.radius < u.y + visibleHeight / 2 + 20
				) {
					return f;
				}
			})
			.filter(function(f) {
				return f;
			});

		var visibleCells = users
			.map(function(f) {
				for (var z = 0; z < f.cells.length; z++) {
					if (
						f.cells[z].x + f.cells[z].radius > u.x - visibleWidth / 2 - 20 &&
						f.cells[z].x - f.cells[z].radius < u.x + visibleWidth / 2 + 20 &&
						f.cells[z].y + f.cells[z].radius > u.y - visibleHeight / 2 - 20 &&
						f.cells[z].y - f.cells[z].radius < u.y + visibleHeight / 2 + 20
					) {
						z = f.cells.lenth;
						if (f.id !== u.id) {
							return {
								id: f.id,
								x: f.x,
								y: f.y,
								cells: f.cells,
								massTotal: Math.round(f.massTotal),
								hue: f.hue,
								name: f.name
							};
						} else {
							//console.log("Nombre: " + f.name + " Es Usuario");
							return {
								x: f.x,
								y: f.y,
								cells: f.cells,
								massTotal: Math.round(f.massTotal),
								hue: f.hue
							};
						}
					}
				}
			})
			.filter(function(f) {
				return f;
			});

		sockets[u.id].emit('serverTellPlayerMove', visibleCells, visibleFood, visibleMass, visibleVirus, {
			x: u.x,
			y: u.y,
			totalMass: u.massTotal,
			defaultMass: c.defaultPlayerMass
		});
		// console.log(visibleVirus);
		if (leaderboardChanged) {
			sockets[u.id].emit('leaderboard', {
				players: users.length,
				leaderboard: leaderboard
			});
		}
	});
	leaderboardChanged = false;
}

setInterval(moveloop, 1000 / 60);
setInterval(gameloop, 1000);
setInterval(sendUpdates, 1000 / c.networkUpdateFactor);

// Don't touch, IP configurations.
var ipaddress = process.env.OPENSHIFT_NODEJS_IP || process.env.IP || c.host;
var serverport = process.env.OPENSHIFT_NODEJS_PORT || process.env.PORT || c.port;
http.listen(serverport, ipaddress, function() {
	console.log('[DEBUG] Listening on ' + ipaddress + ':' + serverport);
});
