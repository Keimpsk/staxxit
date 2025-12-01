const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*' }
});

const PORT = process.env.PORT || 3000;

// Serve static files
app.use(express.static(__dirname));
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'Staxxit.html'));
});

// Game utilities
const dirs = [
  [1, 0], [1, -1], [0, -1],
  [-1, 0], [-1, 1], [0, 1]
];

function parseKey(key) {
  return key.split(',').map(Number);
}

function cubeDist(aq, ar, bq, br) {
  const as = -aq - ar;
  const bs = -bq - br;
  return Math.max(Math.abs(aq - bq), Math.abs(ar - br), Math.abs(as - bs));
}

function isInner(key) {
  const [q, r] = parseKey(key);
  return cubeDist(0, 0, q, r) <= 5;
}

function isOuter(key) {
  const [q, r] = parseKey(key);
  return cubeDist(0, 0, q, r) === 6;
}

function neighbors(key) {
  const [q, r] = parseKey(key);
  const neigh = [];
  for (let d = 0; d < 6; d++) {
    const nq = q + dirs[d][0];
    const nr = r + dirs[d][1];
    const nkey = `${nq},${nr}`;
    const ns = -nq - nr;
    if (Math.max(Math.abs(nq), Math.abs(nr), Math.abs(ns)) <= 6) {
      neigh.push(nkey);
    }
  }
  return neigh;
}

function pathClear(board, fromKey, dq, dr, k) {
  for (let i = 1; i < k; i++) {
    const [fq, fr] = parseKey(fromKey);
    const iq = fq + i * dq;
    const ir = fr + i * dr;
    const ikey = `${iq},${ir}`;
    if (!isInner(ikey) || (board[ikey] && board[ikey].stack.length > 0)) {
      return false;
    }
  }
  return true;
}

function getCaptureTargets(board, pos, player) {
  const targets = [];
  const st = board[pos] || { stack: [] };
  const h = st.stack.length;
  const [q, r] = parseKey(pos);
  for (let d = 0; d < 6; d++) {
    const dq = dirs[d][0];
    const dr = dirs[d][1];
    const tq = q + h * dq;
    const tr = r + h * dr;
    const tkey = `${tq},${tr}`;
    if (!isInner(tkey)) continue;
    if (!pathClear(board, pos, dq, dr, h)) continue;
    const tst = board[tkey] || { stack: [] };
    if (tst.stack.length > 0 && tst.stack[tst.stack.length - 1] !== player) {
      targets.push(tkey);
    }
  }
  return targets;
}

function getMoveInner(board, pos, player) {
  const targets = [];
  const st = board[pos] || { stack: [] };
  const h = st.stack.length;
  const [q, r] = parseKey(pos);
  for (let d = 0; d < 6; d++) {
    const dq = dirs[d][0];
    const dr = dirs[d][1];
    for (let k = 1; k <= h; k++) {
      const tq = q + k * dq;
      const tr = r + k * dr;
      const tkey = `${tq},${tr}`;
      if (!isInner(tkey)) break;
      if (!pathClear(board, pos, dq, dr, k)) break;
      const tst = board[tkey] || { stack: [] };
      if (tst.stack.length === 0) {
        targets.push(tkey);
      } else {
        break;
      }
    }
  }
  return targets;
}

function getExitTargets(board, pos, player, outerColors) {
  const targets = [];
  const st = board[pos] || { stack: [] };
  const h = st.stack.length;
  const [q, r] = parseKey(pos);
  for (let d = 0; d < 6; d++) {
    const dq = dirs[d][0];
    const dr = dirs[d][1];
    const tq = q + h * dq;
    const tr = r + h * dr;
    const tkey = `${tq},${tr}`;
    if (!isOuter(tkey)) continue;
    if (!pathClear(board, pos, dq, dr, h)) continue;
    const tst = board[tkey] || { stack: [] };
    if (tst.stack.length === 0 && (outerColors[tkey] === player || outerColors[tkey] === 'both')) {
      targets.push(tkey);
    }
  }
  return targets;
}

function getSplitAdjs(board, pos) {
  return neighbors(pos).filter(n => isInner(n) && (!board[n] || board[n].stack.length === 0));
}

function hasAnyCapture(board, player) {
  for (let key in board) {
    if (!isInner(key)) continue;
    const st = board[key] || { stack: [] };
    if (st.stack.length > 0 && st.stack[st.stack.length - 1] === player && getCaptureTargets(board, key, player).length > 0) {
      return true;
    }
  }
  return false;
}

function getValidPlaces(board, occupied, piecesLeft, player) {
  let valids = [];
  if (piecesLeft[player] === 18) {
    if (player === 'W') {
      valids = ['0,0'];
    } else {
      if (occupied.has('0,0')) {
        valids = neighbors('0,0').filter(p => isInner(p) && !board[p]);
      }
    }
  } else {
    const cands = new Set();
    for (let occ of occupied) {
      for (let n of neighbors(occ)) {
        if (isInner(n) && !board[n]) {
          cands.add(n);
        }
      }
    }
    valids = Array.from(cands);
  }
  return valids;
}

// Precompute outer colors
let outerColors = {};
let dualKeys = new Set(['6,0', '0,6', '-6,6', '0,-6', '6,-6', '-6,0']);
let outerHexes = [];
for (let q = -6; q <= 6; q++) {
  for (let r = -6; r <= 6; r++) {
    const s = -q - r;
    const d = Math.max(Math.abs(q), Math.abs(r), Math.abs(s));
    if (d === 6) {
      outerHexes.push([q, r]);
    }
  }
}
let sortedOuter = outerHexes.slice().sort((a, b) => getAngle(a[0], a[1]) - getAngle(b[0], b[1]));
let startIdx = sortedOuter.findIndex(p => p[0] === 6 && p[1] === 0);
if (startIdx !== -1) {
  sortedOuter = sortedOuter.slice(startIdx).concat(sortedOuter.slice(0, startIdx));
}
let colorToggle = 'W';
for (let i = 0; i < 36; i++) {
  const p = sortedOuter[i];
  const key = `${p[0]},${p[1]}`;
  if (dualKeys.has(key)) {
    outerColors[key] = 'both';
  } else {
    outerColors[key] = colorToggle;
    colorToggle = colorToggle === 'W' ? 'B' : 'W';
  }
}
function getAngle(q, r) {
  const x = Math.sqrt(3) * q + (Math.sqrt(3) / 2) * r;
  const y = (3 / 2) * r;
  return Math.atan2(y, x);
}

// Games: roomId -> game state
const games = new Map();

function generateRoomId() {
  return Math.random().toString(36).substr(2, 6).toUpperCase();
}

io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`);

  socket.on('createGame', (callback) => {
    const roomId = generateRoomId();
    const game = {
      board: {},
      phase: 'place',
      currentPlayer: 'W',
      piecesLeft: { W: 18, B: 18 },
      occupied: new Set(),
      players: { [socket.id]: 'W' },
      aiPlayer: null,
      outerColors,
      lastAction: null  // New: Store last move for replay
    };
    games.set(roomId, game);
    socket.join(roomId);
    callback({ roomId, color: 'W' });
    io.to(roomId).emit('gameUpdate', getSerializableGame(game));
  });

  socket.on('joinGame', (roomId, callback) => {
    const game = games.get(roomId);
    if (!game || Object.keys(game.players).length >= 2) {
      return callback({ error: 'Invalid or full room' });
    }
    game.players[socket.id] = 'B';
    socket.join(roomId);
    callback({ color: 'B' });
    io.to(roomId).emit('gameUpdate', getSerializableGame(game));
    io.to(roomId).emit('gameStart');
  });

  socket.on('makeMove', (data) => {
    const { roomId, action } = data;
    const game = games.get(roomId);
    if (!game || game.players[socket.id] !== game.currentPlayer) return;

    let valid = false;
    let tempLastAction = { ...action, player: game.currentPlayer };  // Temp store for lastAction

    if (game.phase === 'place') {
      const valids = getValidPlaces(game.board, game.occupied, game.piecesLeft, game.currentPlayer);
      if (valids.includes(action.pos)) {
        game.board[action.pos] = { stack: [game.currentPlayer] };
        game.occupied.add(action.pos);
        game.piecesLeft[game.currentPlayer]--;
        if (game.piecesLeft.W + game.piecesLeft.B === 0) {
          game.phase = 'play';
        }
        valid = true;
        tempLastAction.type = 'place';
        tempLastAction.pos = action.pos;
      }
    } else {
      const from = action.from;
      const to = action.to;
      const player = game.currentPlayer;
      if (!isInner(from) || !game.board[from] || game.board[from].stack[game.board[from].stack.length - 1] !== player) return;

      const mandatory = hasAnyCapture(game.board, player);
      let targets = [];
      if (mandatory) {
        targets = getCaptureTargets(game.board, from, player);
      } else {
        targets = [
          ...getMoveInner(game.board, from, player),
          ...getExitTargets(game.board, from, player, game.outerColors)
        ];
        if (game.board[from].stack.length > 11) {
          targets = targets.concat(getSplitAdjs(game.board, from));
        }
      }
      if (!targets.includes(to)) return;

      const stFrom = game.board[from];
      const h = stFrom.stack.length;
      if (getCaptureTargets(game.board, from, player).includes(to)) {
        const stTo = game.board[to] || { stack: [] };
        game.board[to] = { stack: stTo.stack.concat(stFrom.stack) };
        tempLastAction.type = 'capture';
      } else if (getMoveInner(game.board, from, player).includes(to) || getExitTargets(game.board, from, player, game.outerColors).includes(to)) {
        game.board[to] = { stack: stFrom.stack };
        tempLastAction.type = 'move';
      } else {
        if (h > 11) {
          const h1 = action.splitH1;
          if (h1 >= 1 && h1 < h) {
            game.board[to] = { stack: stFrom.stack.splice(h1) };
            game.occupied.add(to);
            tempLastAction.type = 'split';
            tempLastAction.splitH1 = h1;
          } else {
            return;
          }
        } else {
          return;
        }
      }
      delete game.board[from];
      valid = true;
    }

    if (valid) {
      const prevPlayer = game.currentPlayer;
      game.currentPlayer = game.currentPlayer === 'W' ? 'B' : 'W';
      game.lastAction = tempLastAction;  // Store after validation
      io.to(roomId).emit('gameUpdate', getSerializableGame(game));
      checkEnd(roomId, game);
    }
  });

  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.id}`);
    for (let [roomId, game] of games) {
      if (game.players[socket.id]) {
        delete game.players[socket.id];
        if (Object.keys(game.players).length === 0) {
          games.delete(roomId);
        } else {
          io.to(roomId).emit('playerLeft');
        }
      }
    }
  });
});

function checkEnd(roomId, game) {
  if (game.phase === 'place') return;
  let boardW = 0, boardB = 0;
  let outerStaxW = 0, outerPiecesW = 0;
  let outerStaxB = 0, outerPiecesB = 0;
  for (let key in game.board) {
    const st = game.board[key];
    if (st.stack.length === 0) continue;
    const [q, r] = parseKey(key);
    const d = cubeDist(0, 0, q, r);
    const isOut = d === 6;
    const owner = st.stack[st.stack.length - 1];
    const height = st.stack.length;
    if (owner === 'W') {
      if (isOut) {
        outerStaxW++;
        outerPiecesW += height;
      } else {
        boardW++;
      }
    } else if (owner === 'B') {
      if (isOut) {
        outerStaxB++;
        outerPiecesB += height;
      } else {
        boardB++;
      }
    }
  }
  if (boardW === 0 || boardB === 0) {
    let winner = null;
    if (outerStaxW > outerStaxB) {
      winner = 'W';
    } else if (outerStaxB > outerStaxW) {
      winner = 'B';
    } else if (outerPiecesW > outerPiecesB) {
      winner = 'W';
    } else if (outerPiecesB > outerPiecesW) {
      winner = 'B';
    }
    io.to(roomId).emit('gameEnd', { winner });
  }
}

// Serialization helper: Convert Set to array for JSON
function getSerializableGame(game) {
  return {
    ...game,
    occupied: Array.from(game.occupied)
  };
}

server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});