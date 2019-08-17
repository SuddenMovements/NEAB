const app = require('express')();
const http = require('http').Server(app);
const io = require('socket.io')(http);
const Quadtree = require('quadtree-lib');
const shortid = require('shortid');

const gameWidth = 5000;
const gameHeight = 5000;
const simulatedLag = 2; // the number of ticks between receiving a player target and taking that action, needs to be configured
const tickMultiplierFromFramerate = 4;
const splitMass = 35;
// TODO these speeds are currently arbitrary
const splitSpeed = 25 * tickMultiplierFromFramerate;
const maxPlayerSpeed = 6.25 * tickMultiplierFromFramerate;
// assuming the bot could feasibly run at 15fps
// the original clone had speeds of 25 and 6.25 and was intended to run at 60fps
// so multiply by 60/15 = 4

class Player {
	constructor(socketID, playerType) {
		this.id = socketID;
		this.x = Math.round(Math.random() * gameWidth);
		this.y = Math.round(Math.random() * gameHeight);
		this.cells = [];
		this.mass = 0;
		this.hue = Math.round(Math.random() * 360);
		this.type = playerType;
		this.lastTargetUpdate = 0;
		this.targets = [];
		if (this.type === 'player') {
			this.cells.push(new Cell(this, this.x, this.y, 10, { x: 0, y: 0 }, 0));
		} else if (this.type === 'spectator') {
			this.x = gameWidth / 2;
			this.y = gameHeight / 2;
		} else {
			console.log(`[ERROR] user registered with unknown type ${this.type}`);
		}
	}
}

class Cell {
	constructor(player, x, y, mass, target, speed) {
		this.id = shortid.generate();
		this.playerID = player.id;
		this.x = x;
		this.y = y;
		this.mass = mass;
		this.r = massToRadius(this.mass);
		this.target = target;
		this.speed = speed;
		this.hue = player.hue;
	}
}

class Food {
	constructor(x, y) {
		this.id = shortid.generate();
		this.x = x;
		this.y = y;
		this.hue = Math.round(Math.random() * 360);
		this.r = 14;
		this.mass = 1;
	}
}

class Mass {
	constructor(playerID, originCellIndex, x, y, hue, target, speed) {
		this.id = shortid.generate();
		this.playerID = playerID;
		this.originCellIndex = originCellIndex;
		this.x = x;
		this.y = y;
		this.mass = 13;
		this.r = massToRadius(this.mass);
		this.hue = hue;
		this.target = target;
		this.speed = speed;
	}
}

class Virus {
	constructor(x, y, mass, speed, target) {
		this.id = shortid.generate();
		this.x = x;
		this.y = y;
		this.mass = mass;
		this.r = massToRadius(this.mass);
		this.speed = speed;
		this.target = target;
	}
}

// TODO test quadtree removal speeds
// reject vs remove where

var players = {};
var spectators = [];
var food = new Quadtree({ width: gameWidth, height: gameHeight });
var cells = new Quadtree({ width: gameWidth, height: gameHeight });
var masses = new Quadtree({ width: gameWidth, height: gameHeight });
var viruses = new Quadtree({ width: gameWidth, height: gameHeight });

function massToRadius(mass) {
	return Math.sqrt(mass) * 7.5;
}

const slowdownBaseLog = Math.log2(4.5);
function massToSlowdown(mass) {
	return Math.log2(mass / 10) / slowdownBaseLog + 1;
}

function getUniformPosition(points) {
	let bestPos = { x: 0, y: 0 };
	let bestDist = 0;
	for (let i = 0; i < 10; i++) {
		let dist = Infinity;
		let pos = { x: Math.round(Math.random() * gameWidth), y: Math.round(Math.random() * gameHeight) };
		for (let point of points) {
			dist = Math.min(dist, (point.x - pos.x) * (point.x - pos.x) + (point.y - pos.y) * (point.y - pos.y));
		}
		if (dist > bestDist) {
			bestPos = pos;
			bestDist = dist;
		}
	}
	return bestPos;
}

function addFood(numberFoodToAdd) {
	// https://www.reddit.com/r/Agario/wiki/cells
	// Food Cells are tiny passive cells that frequently spawn across the realms at random location.
	// When spawned they are the size of 1 Mass and slowly over time they can grow to become up to 5 Mass.
	// Food cells at maximum size can be distinguished by having a dark pulsing outline.
	// All food cells can be eaten by Player Cells of 10 Mass.
	if (numberFoodToAdd <= 0) {
		return [];
	}
	// console.log(`[DEBUG] adding ${numberFoodToAdd} food`);
	let newFood = [];
	for (let i = 0; i < numberFoodToAdd; i++) {
		newFood.push(new Food(Math.floor(Math.random() * gameWidth), Math.floor(Math.random() * gameHeight)));
	}
	food.pushAll(newFood);
	return newFood;
}

function addVirus(numberVirusToAdd) {
	let allViruses = viruses.find(elem => true);
	let newViruses = [];
	for (let i = 0; i < numberVirusToAdd; i++) {
		let pos = getUniformPosition(newViruses.concat(allViruses));
		newViruses.push(new Virus(pos.x, pos.y, 100, 0, null));
	}
	viruses.pushAll(newViruses);
	return newViruses;
}

function generateMap() {
	food.clear();
	cells.clear();
	masses.clear();
	viruses.clear();
	addFood(1000);
	addVirus(50);
}

io.on('connection', socket => {
	console.log(`${socket.id} connected!`);
	socket.emit('handshake');
	var currentPlayer = {};
	socket.on('handshake', playerInfo => {
		console.log(`${socket.id} registered as a ${playerInfo.type}`);
		currentPlayer = new Player(socket.id, playerInfo.type);
		for (let playerCell of currentPlayer.cells) {
			cells.push(playerCell);
		}
		if (playerInfo.type === 'player') {
			players[socket.id] = currentPlayer;
		} else {
			spectators.push(currentPlayer);
		}
		socket.emit('playerInfo', currentPlayer);
		// on playerInfo client should store player location and mass

		// maybe emit a new player has joined so clients can start tracking new cells?
		socket.emit('gameSetup', {
			food: food.find(elem => true),
			cells: cells.find(elem => true),
			masses: masses.find(elem => true),
			viruses: viruses.find(elem => true)
		});
		// on gameSetup client should store food, cells, masses and viruses to be rendered
		console.log('Total players: ' + Object.keys(players).length);
	});

	socket.on('disconnect', () => {
		if (players[socket.id] !== undefined) {
			console.log(`${socket.id} disconnected`);
			delete players[socket.id];
			let playerCells = cells.where({ playerID: socket.id });
			for (let playerCell of playerCells) {
				cells.remove(playerCell);
			}
			console.log('Total players: ' + Object.keys(players).length);
			// io.emit('playerLeft', socket.id);
			// on playerLeft client should remove all cells with matching socket.id
			if (Object.values(players).every(val => val.lastTargetUpdate === tickCount)) {
				tick();
			}
		}
	});

	socket.on('move', newTarget => {
		moveFunc(newTarget);
	});

	function moveFunc(newTarget) {
		// newTarget should be an object with {x, y}
		// if (currentPlayer.targets == undefined) {
		// 	setTimeout(() => {
		// 		moveFunc(newTarget);
		// 	}, 100);
		// 	return;
		// }
		currentPlayer.targets.unshift(newTarget);
		currentPlayer.lastTargetUpdate = tickCount;
		if (Object.values(players).every(val => val.lastTargetUpdate === tickCount)) {
			// if we have received moves for every player
			tick();
		} else {
			// for (let player of Object.values(players).filter(val => val.lastTargetUpdate !== tickCount)) {
			// 	console.log(`waiting on player ${player.id}`);
			// }
		}
	}

	socket.on('fire', () => {
		// Fire food.
		// https://agario.fandom.com/wiki/Ejecting
		// The ejected mass can be eaten by any cell that is over 20 mass.
		// Cells lose 18 mass per ejection
		// however, the mass of the ejected piece is only ~72% of that. Consuming the mass only gains 13 mass.
		for (let i = 0; i < currentPlayer.cells.length; i++) {
			if (currentPlayer.cells[i].mass > splitMass) {
				cells.remove(cells.where({ id: currentPlayer.cells[i].id })[0]);
				currentPlayer.cells[i].mass -= 18;
				currentPlayer.cells[i].r = massToRadius(currentPlayer.cells[i].mass);
				currentPlayer.mass -= 18;
				cells.push(currentPlayer.cells[i]);
				// 'ejected mass has an angle of spread, meaning that Viruses created may veer off course by ~20 degrees'
				let target = currentPlayer.cells[i].target;
				let deg = Math.atan2(target.y, target.x);
				let veer = (Math.random() - 0.5) * Math.PI * 2 * (20 / 360);
				let mag = Math.sqrt(target.x * target.x + target.y * target.y);
				target.x = mag * Math.cos(deg + veer);
				target.y = mag * Math.sin(deg + veer);
				let newMass = new Mass(
					currentPlayer.id,
					i,
					currentPlayer.cells[i].x,
					currentPlayer.cells[i].y,
					currentPlayer.hue,
					target,
					splitSpeed
				);
				masses.push(newMass);
			}
		}
	});

	socket.on('split', () => {
		function splitCell(cellIndex) {
			// https://agario.fandom.com/wiki/Splitting
			//  'To be able to split, a cell needs to have at least 35 mass'
			if (currentPlayer.cells.length < 16 && currentPlayer.cells[cellIndex].mass >= 35) {
				cells.remove(cells.where({ id: currentPlayer.cells[cellIndex].id })[0]);
				currentPlayer.cells[cellIndex].mass = currentPlayer.cells[cellIndex].mass / 2;
				currentPlayer.cells[cellIndex].r = massToRadius(currentPlayer.cells[cellIndex].mass);
				cells.push(currentPlayer.cells[cellIndex]);
				let splitCell = new Cell(
					currentPlayer,
					currentPlayer.cells[cellIndex].x,
					currentPlayer.cells[cellIndex].y,
					currentPlayer.cells[cellIndex].mass,
					currentPlayer.cells[cellIndex].target,
					splitSpeed
				);
				currentPlayer.cells.push(splitCell);
				cells.push(splitCell);
				currentPlayer.lastSplit = tickCount;
			}
		}
		let splitCount = currentPlayer.cells.length;
		for (let i = 0; i < splitCount; i++) {
			splitCell(i);
		}
	});

	socket.on('respawn', () => {
		if (players[socket.id] === undefined) {
			currentPlayer = new Player(socket.id, 'player');
			for (let playerCell of currentPlayer.cells) {
				cells.push(playerCell);
			}
			players[socket.id] = currentPlayer;
			socket.emit('playerInfo', currentPlayer);
			socket.emit('gameSetup', {
				food: food.find(elem => true),
				cells: cells.find(elem => true),
				masses: masses.find(elem => true),
				viruses: viruses.find(elem => true)
			});
		}
	});
});

function moveAndDecayPlayer(player) {
	if (player.targets.length <= simulatedLag) {
		return;
	}
	var x = 0;
	var y = 0;
	let currentTarget = player.targets[simulatedLag];
	for (var i = 0; i < player.cells.length; i++) {
		// decay
		// TODO find source for this supposed decay rate
		// if (tickCount % 15 == 0) {
		player.cells[i].mass *= 1 - 0.002;
		if (player.cells[i].mass < 10) {
			player.cells[i].mass = 10;
		}
		// }

		// movement
		let cellTargetX = player.x + currentTarget.x - player.cells[i].x;
		let cellTargetY = player.y + currentTarget.y - player.cells[i].y;
		cells.remove(cells.where({ id: player.cells[i].id })[0]);
		let target = { x: cellTargetX, y: cellTargetY };
		player.cells[i].target = target;
		var dist = Math.pow(target.y, 2) + Math.pow(target.x, 2);
		var deg = Math.atan2(target.y, target.x);
		var slowDown = 1;
		if (player.cells[i].speed <= maxPlayerSpeed) {
			if (dist < 10 * 10) {
				player.cells[i].speed = 0;
			} else {
				player.cells[i].speed = maxPlayerSpeed * Math.min(1, (dist - 100) / 5000);
			}
			slowDown = massToSlowdown(player.cells[i].mass);
		}

		var deltaY = (player.cells[i].speed * Math.sin(deg)) / slowDown;
		var deltaX = (player.cells[i].speed * Math.cos(deg)) / slowDown;

		if (player.cells[i].speed > maxPlayerSpeed) {
			// player.cells[i].speed -= 0.5 * 4;
			player.cells[i].speed *= 0.8;
		}

		deltaX = Math.round(deltaX);
		deltaY = Math.round(deltaY);

		if (!isNaN(deltaY) && !isNaN(deltaX)) {
			player.cells[i].y += deltaY;
			player.cells[i].x += deltaX;
		}

		for (var j = 0; j < player.cells.length; j++) {
			if (j != i && player.cells[i] !== undefined) {
				var distance = Math.sqrt(
					Math.pow(player.cells[j].y - player.cells[i].y, 2) +
						Math.pow(player.cells[j].x - player.cells[i].x, 2)
				);
				var radiusTotal = player.cells[i].r + player.cells[j].r;
				if (distance < radiusTotal) {
					// https://agario.fandom.com/wiki/Splitting
					// The cool down time is calculated as 30 seconds plus 2.33% of the cells mass
					// todo update the multiplier to work with tick rate
					if (player.lastSplit > tickCount - 15 * (30 + player.cells[i].mass * 0.0233)) {
						if (player.cells[i].x < player.cells[j].x) {
							player.cells[i].x -= tickMultiplierFromFramerate;
						} else if (player.cells[i].x > player.cells[j].x) {
							player.cells[i].x += tickMultiplierFromFramerate;
						}
						if (player.cells[i].y < player.cells[j].y) {
							player.cells[i].y -= tickMultiplierFromFramerate;
						} else if (player.cells[i].y > player.cells[j].y) {
							player.cells[i].y += tickMultiplierFromFramerate;
						}
					} else if (distance < radiusTotal / 1.75) {
						player.cells[i].mass += player.cells[j].mass;
						player.cells[i].r = massToRadius(player.cells[i].mass);
						cells.remove(cells.where({ id: player.cells[j].id })[0]);
						player.cells.splice(j, 1);
						if (j < i) {
							i--;
						}
						j--;
					}
				}
			}
		}

		if (player.cells[i].x < 0) {
			player.cells[i].x = 0;
		} else if (player.cells[i].x > gameWidth) {
			player.cells[i].x = gameWidth;
		}
		if (player.cells[i].y < 0) {
			player.cells[i].y = 0;
		} else if (player.cells[i].y > gameHeight) {
			player.cells[i].y = gameHeight;
		}

		x += player.cells[i].x;
		y += player.cells[i].y;
		cells.push(player.cells[i]);
	}
	player.x = Math.round(x / player.cells.length);
	player.y = Math.round(y / player.cells.length);
	player.targets.pop();
}

function eatFoodPellets() {
	// gets all food pellets eaten by players and removes them
	// returns a list of id's of food objects to be eaten
	let foodEaten = [];
	for (let player of Object.values(players)) {
		for (let i = 0; i < player.cells.length; i++) {
			let nearbyFood = food.colliding({
				x: player.cells[i].x - player.cells[i].r,
				y: player.cells[i].y - player.cells[i].r,
				width: player.cells[i].r * 2,
				height: player.cells[i].r * 2
			});
			if (nearbyFood.length > 0) {
				// console.log(`[DEBUG] ${player.id} colliding with food ${nearbyFood[0].id}`);
				// for (let f of nearbyFood) {
				let f = nearbyFood[0];
				{
					if (
						(f.x - player.cells[i].x) * (f.x - player.cells[i].x) +
							(f.y - player.cells[i].y) * (f.y - player.cells[i].y) <
						player.cells[i].r * player.cells[i].r
					) {
						foodEaten.push(f.id);
						cells.remove(cells.where({ id: player.cells[i].id })[0]);
						player.cells[i].mass += f.mass;
						player.cells[i].r = massToRadius(player.cells[i].mass);
						player.mass += f.mass;
						cells.push(player.cells[i]);
						food.remove(food.where({ id: f.id })[0]);
					}
				}
			}
		}
	}
	return foodEaten;
}

function moveMasses() {
	let movingMasses = masses.find(elem => elem.speed > 0);
	for (let mass of movingMasses) {
		masses.remove(masses.where({ id: mass.id })[0]);
		let deg = Math.atan2(mass.target.y, mass.target.x);
		// TODO change masses to only use degrees
		let deltaX = mass.speed * Math.cos(deg);
		let deltaY = mass.speed * Math.sin(deg);

		mass.speed *= 0.8;
		mass.speed -= 0.5;
		if (mass.speed < 0) {
			mass.speed = 0;
		}

		if (!isNaN(deltaX) && !isNaN(deltaY)) {
			mass.x += deltaX;
			mass.y += deltaY;
		}

		mass.x = Math.round(mass.x);
		mass.y = Math.round(mass.y);
		masses.push(mass);
	}
	return movingMasses;
}

function eatMasses() {
	// returns a list of id's of mass objects to be eaten
	let massEaten = [];
	for (let player of Object.values(players)) {
		for (let i = 0; i < player.cells.length; i++) {
			let nearbyMass = masses.colliding({
				x: player.cells[i].x - player.cells[i].r,
				y: player.cells[i].y - player.cells[i].r,
				width: player.cells[i].r * 2,
				height: player.cells[i].r * 2
			});
			if (nearbyMass.length > 0) {
				// console.log(`[DEBUG] ${player.id} colliding with mass ${nearbyMass[0].id}`);
				for (let m of nearbyMass) {
					if (
						(m.x - player.cells[i].x) * (m.x - player.cells[i].x) +
							(m.y - player.cells[i].y) * (m.y - player.cells[i].y) <
						player.cells[i].r * player.cells[i].r
					) {
						// to make sure we don't eat the mass we just ejected
						if (m.playerID === player.id) {
							if (m.originCellIndex === i && m.speed > 0) {
								continue;
							}
						}
						massEaten.push(m.id);
						cells.remove(cells.where({ id: player.cells[i].id })[0]);
						player.cells[i].mass += m.mass;
						player.mass += m.mass;
						player.cells[i].r = massToRadius(player.cells[i].mass);
						cells.push(player.cells[i]);
						masses.remove(m);
					}
				}
			}
		}
	}

	for (let virus of viruses.find(elem => true)) {
		let nearbyMass = masses.colliding({
			x: virus.x - virus.r,
			y: virus.y - virus.r,
			width: virus.r * 2,
			height: virus.r * 2
		});
		if (nearbyMass.length > 0) {
			// console.log(`[DEBUG] ${player.id} colliding with mass ${nearbyMass[0].id}`);
			for (let m of nearbyMass) {
				if ((m.x - virus.x) * (m.x - virus.x) + (m.y - virus.y) * (m.y - virus.y) < virus.r * virus.r) {
					viruses.remove(viruses.where({ id: virus.id })[0]);
					virus.mass += m.mass;
					virus.r = massToRadius(virus.mass);
					virus.target = { x: virus.x - m.x, y: virus.y - m.y };
					viruses.push(virus);
					updatedViruses[virus.id] = virus;
					masses.remove(m);
					massEaten.push(m.id);
				}
			}
		}
	}
	return massEaten;
}

function updateViruses() {
	// let updatedViruses = [];
	let locallyUpdatedViruses = [];
	let movingViruses = viruses.find(elem => elem.speed > 0);
	for (let virus of movingViruses) {
		viruses.remove(viruses.where({ id: virus.id })[0]);
		let deg = Math.atan2(virus.target.y, virus.target.x);
		let deltaX = virus.speed * Math.cos(deg);
		let deltaY = virus.speed * Math.sin(deg);

		virus.speed *= 0.8;
		virus.speed -= 0.5;
		if (virus.speed < 0) {
			virus.speed = 0;
		}

		if (!isNaN(deltaX)) {
			virus.x += deltaX;
		}
		if (!isNaN(deltaY)) {
			virus.y += deltaY;
		}

		virus.x = Math.round(virus.x);
		virus.y = Math.round(virus.y);
		viruses.push(virus);
	}
	locallyUpdatedViruses = locallyUpdatedViruses.concat(movingViruses);

	let fullViruses = viruses.find(elem => elem.mass > 190);
	for (let virus of fullViruses) {
		let newVirus = new Virus(virus.x, virus.y, 100, splitSpeed, virus.target);
		locallyUpdatedViruses.push(newVirus);
		viruses.push(newVirus);
		viruses.remove(viruses.where({ id: virus.id })[0]);
		virus.mass = 100;
		virus.r = 75;
		virus.target = { x: 0, y: 0 };
		viruses.push(virus);
		locallyUpdatedViruses.push(virus);
	}

	return locallyUpdatedViruses;
}

function eatViruses() {
	function virusSplitCell(player, cell) {
		if (player.cells.length < 16 && cell.mass >= 35) {
			let target = {
				x: (Math.random() * 2 - 1) * 500,
				y: (Math.random() * 2 - 1) * 500
			};
			cells.remove(cells.where({ id: cell.id })[0]);
			cell.mass = cell.mass / 2;
			cell.r = massToRadius(cell.mass);
			cell.target = target;
			cells.push(cell);
			target = {
				x: (Math.random() * 2 - 1) * 500,
				y: (Math.random() * 2 - 1) * 500
			};
			let splitCell = new Cell(player, cell.x, cell.y, cell.mass, target, splitSpeed);
			player.cells.push(splitCell);
			cells.push(splitCell);
			player.lastSplit = tickCount;
		}
	}
	// returns a list of id's of virus objects to be eaten
	let virusEaten = [];
	for (let player of Object.values(players)) {
		for (let i = 0; i < player.cells.length; i++) {
			let nearbyViruses = viruses.colliding({
				x: player.cells[i].x - player.cells[i].r,
				y: player.cells[i].y - player.cells[i].r,
				width: player.cells[i].r * 2,
				height: player.cells[i].r * 2
			});
			if (nearbyViruses.length > 0) {
				// console.log(`[DEBUG] ${player.id} colliding with mass ${nearbyViruses[0].id}`);
				for (let v of nearbyViruses) {
					if (
						(v.x - player.cells[i].x) * (v.x - player.cells[i].x) +
							(v.y - player.cells[i].y) * (v.y - player.cells[i].y) <
						player.cells[i].r * player.cells[i].r
					) {
						if (v.mass < player.cells[i].mass) {
							virusEaten.push(v.id);
							cells.remove(cells.where({ id: player.cells[i].id })[0]);
							player.cells[i].mass += 100;
							player.cells[i].r = massToRadius(player.cells[i].mass);
							player.mass += 100;
							cells.push(player.cells[i]);

							let lastCellIndex = player.cells.length;
							let splitCount = Math.round(4 + Math.random());
							virusSplitCell(player, player.cells[i]);
							for (let j = 1; j < splitCount; j++) {
								let splitRound = player.cells.length;
								for (let k = lastCellIndex; k < splitRound; k++) {
									virusSplitCell(player, player.cells[k]);
								}
								virusSplitCell(player, player.cells[i]);
							}
							viruses.remove(viruses.where({ id: v.id })[0]);
						}
					}
				}
			}
		}
	}
	return virusEaten;
}

function playerCollisions() {
	for (let player of Object.values(players)) {
		// https://agario.fandom.com/wiki/Splitting
		// a split cell, unlike a single cell, must be 33% larger than the cell it tries to consume
		// (a single cell only needs to be 25% bigger than its target)
		let multiplier = 1.25;
		if (player.cells.length > 1) {
			multiplier = 1.33;
		}
		for (let i = 0; i < player.cells.length; i++) {
			let nearbyCells = cells.colliding({
				x: player.cells[i].x - player.cells[i].r,
				y: player.cells[i].y - player.cells[i].r,
				width: player.cells[i].r * 2,
				height: player.cells[i].r * 2
			});
			for (let otherCell of nearbyCells) {
				if (otherCell.playerID === player.id) {
					continue;
				}
				if (player.cells[i].mass > multiplier * otherCell.mass) {
					if (
						(player.cells[i].x - otherCell.x) * (player.cells[i].x - otherCell.x) +
							(player.cells[i].y - otherCell.y) * (player.cells[i].y - otherCell.y) <
						player.cells[i].r * player.cells[i].r * 1.1
					) {
						cells.remove(cells.where({ id: player.cells[i].id })[0]);
						player.cells[i].mass += otherCell.mass;
						player.cells[i].r = massToRadius(player.cells[i].mass);
						player.mass += otherCell.mass;
						cells.push(player.cells[i]);
						players[otherCell.playerID].cells.splice(
							players[otherCell.playerID].cells.indexOf(otherCell),
							1
						);
						if (players[otherCell.playerID].cells.length === 0) {
							io.to(otherCell.playerID).emit('dead');
							delete players[otherCell.playerID];
						}
						cells.remove(cells.where({ id: otherCell.id })[0]);
					}
				}
			}
		}
	}
}

let tickCount = 0;
let foodDeleted = [];
let foodAdded = {};
let massesDeleted = [];
let updatedMasses = {};
let virusesDeleted = [];
let updatedViruses = {};

function tick() {
	// in tick
	// move all players
	for (let player of Object.values(players)) {
		moveAndDecayPlayer(player);
	}
	// eat food
	foodDeleted = foodDeleted.concat(eatFoodPellets());

	// move and eat masses
	for (let m of moveMasses()) {
		updatedMasses[m.id] = m;
	}
	massesDeleted = massesDeleted.concat(eatMasses());

	// move and eat viruses
	for (let v of updateViruses()) {
		updatedViruses[v.id] = v;
	}
	virusesDeleted = virusesDeleted.concat(eatViruses());

	// and finally check for player on player collisions and eat appropriately
	playerCollisions();

	// now that we have updated all masses, sum the total mass of the game and split it amongst new viruses and new food
	let totalMass = 0;
	cells.each(elem => (totalMass += elem.mass));
	food.each(elem => (totalMass += elem.mass));
	masses.each(elem => (totalMass += elem.mass));
	viruses.each(elem => (totalMass += elem.mass));

	let missingMass = 20000 - totalMass;
	let newFoodCount = Math.min(1000, missingMass * 0.8);
	for (let f of addFood(newFoodCount)) {
		foodAdded[f.id] = f;
	}
	let newVirusCount = Math.min(50, (missingMass - newFoodCount) / 100);
	for (let v of addVirus(newVirusCount)) {
		updatedViruses[v.id] = v;
	}

	tickCount++;
	console.log(`[DEBUG] tickCount: ${tickCount}`);
	sendGameUpdatesToAllPlayers();
}

function sendGameUpdatesToAllPlayers() {
	function sendGameUpdates(player) {
		io.to(player.id).emit('gameUpdate', {
			playerCoords: { x: player.x, y: player.y },
			playerMass: player.mass,
			cells: cells.find(elem => true),
			deleteFood: foodDeleted,
			addFood: foodAdded,
			deleteMass: massesDeleted,
			updateMass: updatedMasses,
			deleteVirus: virusesDeleted,
			updateVirus: updatedViruses
		});
	}
	// any masses or viruses that get added will be included in update dictionaries

	// send players new information
	for (let player of Object.values(players)) {
		sendGameUpdates(player);
	}
	for (let spectator of spectators) {
		sendGameUpdates(spectator);
	}
	foodDeleted = [];
	foodAdded = {};
	massesDeleted = [];
	updatedMasses = {};
	virusesDeleted = [];
	updatedViruses = {};
}

generateMap();

// Don't touch, IP configurations.
var ipaddress = 'localhost';
var serverport = 3000;
http.listen(serverport, ipaddress, function() {
	console.log('[DEBUG] Listening on ' + ipaddress + ':' + serverport);
});
