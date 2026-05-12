const DEV_MODE = false; // Set to false to connect to real WebSocket

// --- DOM Elements ---
const canvas = document.getElementById('game-canvas');
const ctx = canvas.getContext('2d');
const scoreText = document.getElementById('score-text');
const feedbackText = document.getElementById('feedback-message');
const multiplierDisplay = document.getElementById('multiplier-display');
const statusIndicator = document.getElementById('status-indicator');
const timerDisplay = document.getElementById('timer-display');
const gameOverScreen = document.getElementById('game-over-screen');
const finalScoreDisplay = document.getElementById('final-score-display');

// Focus Segments
const segments = [
    document.getElementById('seg-1'),
    document.getElementById('seg-2'),
    document.getElementById('seg-3'),
    document.getElementById('seg-4'),
    document.getElementById('seg-5')
];

// --- Resize Handling ---
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvas);
// Call once after a slight delay to ensure HUD layout is calculated
setTimeout(resizeCanvas, 100);

// --- Globals & State ---
let currentFocus = 0; // Smoothed focus value (0 to 1)
let targetFocus = 0;  // Target from BCI/Dev mode
let score = 0;
let currentMultiplier = 1;

// Game constants
const DIRECTIONS = ['Up', 'Down', 'Left', 'Right'];
const COLORS = ['Orange', 'Green'];

// Round State
let currentRound = null;
let lastTime = 0;
let leaves = [];
let isGameOver = false;

// Timer State
let timeLeft = 90; // 90 seconds (1:30)
let timerInterval = null;

// --- BCI Data Handling ---

if (DEV_MODE) {
    statusIndicator.textContent = "DEV MODE";
    statusIndicator.className = "status-dev";

    // Simulate data at 10Hz
    setInterval(() => {
        if (isGameOver) return;
        // Sine wave mapped to 0-1
        let val = (Math.sin(Date.now() / 1000) + 1) / 2;
        targetFocus = val;
    }, 100);
} else {
    // Real WebSocket Connection
    let ws = null;
    function connectWS() {
        statusIndicator.textContent = "CONNECTING...";
        statusIndicator.className = "status-offline";

        ws = new WebSocket('ws://localhost:8000/ws/attention');

        ws.onopen = () => {
            statusIndicator.textContent = "CONNECTED";
            statusIndicator.className = "status-connected";
        };

        ws.onmessage = (event) => {
            if (isGameOver) return;
            try {
                const data = JSON.parse(event.data);
                if (data.attention_score !== undefined) {
                    targetFocus = data.attention_score; // Assume 0-1 range from backend
                }
            } catch (e) {
                console.error("JSON parse error:", e);
            }
        };

        ws.onclose = () => {
            statusIndicator.textContent = "DISCONNECTED";
            statusIndicator.className = "status-offline";
            if (!isGameOver) setTimeout(connectWS, 3000); // Reconnect
        };

        ws.onerror = (err) => {
            console.error("WebSocket Error:", err);
            ws.close();
        };
    }
    connectWS();
}

// --- Math Utilities ---
function lerp(start, end, amt) {
    return (1 - amt) * start + amt * end;
}

// Format Score as 6 digits padded with zeros
function formatScore(val) {
    return val.toString().padStart(6, '0');
}

// Format Time as MM:SS
function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// --- Timer Logic ---
function startTimer() {
    timerDisplay.textContent = formatTime(timeLeft);
    timerInterval = setInterval(() => {
        if (isGameOver) return;
        timeLeft--;

        // Update display
        timerDisplay.textContent = formatTime(timeLeft);

        // Alert styling for last 10 seconds
        if (timeLeft <= 10) {
            timerDisplay.classList.add('alert-text');
        } else {
            timerDisplay.classList.remove('alert-text');
        }

        if (timeLeft <= 0) {
            triggerGameOver();
        }
    }, 1000);
}

function triggerGameOver() {
    isGameOver = true;
    clearInterval(timerInterval);
    leaves = []; // Clear leaves
    currentRound = null;

    // Show UI
    finalScoreDisplay.textContent = formatScore(score);
    gameOverScreen.classList.remove('hidden');
}

// --- Leaf Entity ---
class Leaf {
    constructor(x, y, color, movementDir, pointingDir) {
        this.x = x;
        this.y = y;
        this.color = color;
        this.movementDir = movementDir;
        this.pointingDir = pointingDir;
        this.speed = 150 + Math.random() * 100; // Increased speed for faster movement
        this.size = 45;
        this.active = true;
        this.timeOffset = Math.random() * 100;
        this.swaySpeed = 1 + Math.random() * 0.5;
        this.swayAmount = 15 + Math.random() * 15;
    }

    update(dt) {
        this.timeOffset += dt;
        let sway = Math.sin(this.timeOffset * this.swaySpeed) * this.swayAmount * dt;

        if (this.movementDir === 'Up') { this.y -= this.speed * dt; this.x += sway; }
        if (this.movementDir === 'Down') { this.y += this.speed * dt; this.x += sway; }
        if (this.movementDir === 'Left') { this.x -= this.speed * dt; this.y += sway; }
        if (this.movementDir === 'Right') { this.x += this.speed * dt; this.y += sway; }

        // Out of bounds check
        const margin = 100;
        if (this.x < -margin || this.x > canvas.width + margin ||
            this.y < -margin || this.y > canvas.height + margin) {
            this.active = false;
        }
    }

    draw(ctx) {
        ctx.save();
        ctx.translate(this.x, this.y);

        // Pointing Rotation
        let angle = 0;
        if (this.pointingDir === 'Right') angle = Math.PI / 2;
        if (this.pointingDir === 'Down') angle = Math.PI;
        if (this.pointingDir === 'Left') angle = -Math.PI / 2;
        ctx.rotate(angle);

        // Draw Stem/Central Vein
        ctx.beginPath();
        ctx.moveTo(0, this.size * 0.5);
        ctx.lineTo(0, this.size * 1.8);
        ctx.strokeStyle = '#ffffff'; // White solid stem for black bg
        ctx.lineWidth = 4;
        ctx.stroke();

        // Draw Leaf Blade (Head)
        ctx.beginPath();
        ctx.moveTo(0, -this.size * 1.5); // Pointy tip (Head)
        // Right side bulging out then coming to the stem base
        ctx.bezierCurveTo(this.size * 1.2, -this.size * 0.5, this.size * 0.8, this.size * 0.5, 0, this.size * 0.8);
        // Left side from stem base back to the tip
        ctx.bezierCurveTo(-this.size * 0.8, this.size * 0.5, -this.size * 1.2, -this.size * 0.5, 0, -this.size * 1.5);

        ctx.fillStyle = this.color === 'Orange' ? '#ff9800' : '#00e676';
        ctx.fill();

        // Clean vector outline
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.stroke();

        // Center vein
        ctx.beginPath();
        ctx.moveTo(0, -this.size * 1.4);
        ctx.lineTo(0, this.size * 0.7);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.restore();
    }
}

// --- Game Logic ---
function startNewRound() {
    if (isGameOver) return;

    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    const moveDir = DIRECTIONS[Math.floor(Math.random() * DIRECTIONS.length)];
    const pointDir = DIRECTIONS[Math.floor(Math.random() * DIRECTIONS.length)];

    currentRound = {
        color: color,
        movementDir: moveDir,
        pointingDir: pointDir,
        correctKey: color === 'Orange' ? moveDir : pointDir
    };

    leaves = [];

    // จำนวนใบไม้ 15-20 ใบ
    const numLeaves = Math.floor(Math.random() * 6) + 15;

    for (let i = 0; i < numLeaves; i++) {
        // สุ่มตำแหน่งให้กระจายทั่วหน้าจอตั้งแต่เริ่มเกม
        let x = Math.random() * canvas.width;
        let y = Math.random() * canvas.height;

        leaves.push(new Leaf(x, y, color, moveDir, pointDir));
    }
}

function showFeedback(isCorrect) {
    if (isCorrect) {
        score += Math.round(10 * currentMultiplier);
        // Instant clear leaves
        leaves = [];
    } else {
        feedbackText.textContent = "✖";
        feedbackText.className = "feedback-text feedback-wrong show";

        // Shake screen
        const gameContainer = document.getElementById('game-container');
        gameContainer.classList.add('shake');
        setTimeout(() => {
            gameContainer.classList.remove('shake');
        }, 400);

        score = Math.max(0, score - 5);

        setTimeout(() => {
            feedbackText.className = "feedback-text feedback-wrong";
        }, 500);
    }

    scoreText.textContent = formatScore(score);
}

// --- Input Handling ---
window.addEventListener('keydown', (e) => {
    if (isGameOver || !currentRound) return;

    let keyDir = null;
    if (e.key === 'ArrowUp') keyDir = 'Up';
    if (e.key === 'ArrowDown') keyDir = 'Down';
    if (e.key === 'ArrowLeft') keyDir = 'Left';
    if (e.key === 'ArrowRight') keyDir = 'Right';

    if (keyDir) {
        if (keyDir === currentRound.correctKey) {
            showFeedback(true);
        } else {
            showFeedback(false);
        }
        startNewRound(); // Start immediately
    }
});

// --- Rendering & Update Loop ---

function updateHUD() {
    if (isGameOver) return;

    // 1. Lerp smoothing (คงไว้เพื่อให้แถบบาร์ขยับนุ่มนวลตามสัญญาณที่บันทึกใน Log)
    currentFocus = lerp(currentFocus, Math.max(0, Math.min(1, targetFocus)), 0.05);

    // 2. Update Multiplier (คงเดิมตามสูตรคำนวณคะแนน)
    currentMultiplier = 1 + (currentFocus * 3);

    // 3. ปรับระดับ Focus Level 1-5 ตามค่า Engagement Index (EI)
    // โดยอ้างอิงจากความถี่ Beta / (Theta + Alpha) ที่ประมวลผลมา
    let level = 1;
    if (currentFocus >= 0.8) level = 5;      // สภาวะ Deep Focus (จุดสูงสุด)
    else if (currentFocus >= 0.6) level = 4; // สภาวะ High Engagement 
    else if (currentFocus >= 0.4) level = 3; // สภาวะ Normal / Active
    else if (currentFocus >= 0.2) level = 2; // สภาวะ Low Focus
    else level = 1;                          // สภาวะ Inattentive (ระดับเริ่มต้น)

    // 4. แสดงผลแถบบาร์ (Segments) ตามระดับที่คำนวณได้
    segments.forEach((seg) => {
        seg.className = 'segment';
    });

    for (let i = 0; i < level; i++) {
        if (segments[i]) {
            segments[i].classList.add(`active-${i + 1}`);
        }
    }

    // 5. แสดงค่า Multiplier และปรับแต่ง Dynamic Styling
    multiplierDisplay.textContent = currentMultiplier.toFixed(1) + "x";

    if (level === 5) {
        multiplierDisplay.style.color = '#00e676'; // สีเขียวเมื่อถึงจุด Focus สูงสุด
        multiplierDisplay.style.transform = 'scale(1.1)';
    } else {
        multiplierDisplay.style.color = '#333333';
        multiplierDisplay.style.transform = 'scale(1)';
    }
}

function gameLoop(timestamp) {
    if (!lastTime) lastTime = timestamp;
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;

    // 1. Update HUD & State
    updateHUD();

    // 2. Update Game Entities
    if (!isGameOver) {
        let allDead = true;
        leaves.forEach(leaf => {
            if (leaf.active) {
                leaf.update(dt);
                allDead = false;
            }
        });

        // If all leaves float off-screen, start new round automatically
        if (allDead && leaves.length > 0) {
            startNewRound();
        }
    }

    // 3. Render
    // Clear canvas to let CSS background show through
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!isGameOver) {
        leaves.forEach(leaf => {
            if (leaf.active) leaf.draw(ctx);
        });
    }

    requestAnimationFrame(gameLoop);
}

// Init
setTimeout(() => {
    resizeCanvas();
    scoreText.textContent = formatScore(0);
    startTimer();
    startNewRound();
    requestAnimationFrame(gameLoop);
}, 200); // Slight delay to let DOM settle
