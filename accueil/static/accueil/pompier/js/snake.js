"use strict";

/* =========================================================
   SAUVE QUI PEUT — MOTEUR DU SERPENT
   - 1 bonne réponse
   - 3 mauvaises réponses
   - 4 petits cadres
   - aucune réponse unique ou partie bloquée
========================================================= */

class SnakeGame {
    constructor(options = {}) {
        if (!options.canvas) {
            throw new Error("SnakeGame : canvas introuvable.");
        }

        this.canvas = options.canvas;
        this.ctx = this.canvas.getContext("2d");

        if (!this.ctx) {
            throw new Error(
                "SnakeGame : contexte 2D indisponible."
            );
        }

        this.cellSize = options.cellSize || 30;
        this.speed = options.speed || 220;

        this.columns = Math.floor(
            this.canvas.width / this.cellSize
        );

        this.rows = Math.floor(
            this.canvas.height / this.cellSize
        );

        this.onCorrect =
            typeof options.onCorrect === "function"
                ? options.onCorrect
                : () => {};

        this.onWrong =
            typeof options.onWrong === "function"
                ? options.onWrong
                : () => {};

        this.onSnakeCollision =
            typeof options.onSnakeCollision === "function"
                ? options.onSnakeCollision
                : () => {};

        this.snake = [];
        this.answers = [];

        this.direction = { x: 1, y: 0 };
        this.nextDirection = { x: 1, y: 0 };

        this.running = false;
        this.paused = false;
        this.finished = false;
        this.timer = null;

        this.resetSnake();
        this.draw();
    }

    shuffle(items) {
        const result = [...items];

        for (
            let index = result.length - 1;
            index > 0;
            index -= 1
        ) {
            const randomIndex = Math.floor(
                Math.random() * (index + 1)
            );

            [result[index], result[randomIndex]] = [
                result[randomIndex],
                result[index]
            ];
        }

        return result;
    }

    resetSnake() {
        const startY = Math.floor(this.rows / 2);

        this.snake = [
            { x: 7, y: startY },
            { x: 6, y: startY },
            { x: 5, y: startY }
        ];

        this.direction = { x: 1, y: 0 };
        this.nextDirection = { x: 1, y: 0 };
    }

    changeDirection(x, y) {
        const reverse =
            x === -this.direction.x &&
            y === -this.direction.y;

        if (reverse) {
            return;
        }

        this.nextDirection = { x, y };
    }

    setAnswers(correctAnswer, wrongAnswers) {
        if (
            !correctAnswer ||
            !Array.isArray(wrongAnswers) ||
            wrongAnswers.length < 3
        ) {
            console.error(
                "SnakeGame : il faut une bonne réponse et trois mauvaises réponses."
            );

            this.answers = [];
            this.draw();
            return;
        }

        const selectedWrongAnswers =
            this.shuffle(wrongAnswers).slice(0, 3);

        const answers = this.shuffle([
            {
                text: correctAnswer,
                correct: true
            },
            ...selectedWrongAnswers.map((text) => ({
                text,
                correct: false
            }))
        ]);

        /*
           Canvas actuel : 450 × 270.
           Avec des cases de 30 px :
           15 colonnes × 9 lignes.
        */
        const boxWidth = 5;
        const boxHeight = 2;

        const positions = [
            { x: 0, y: 0 },
            { x: this.columns - boxWidth, y: 0 },
            { x: 0, y: this.rows - boxHeight },
            {
                x: this.columns - boxWidth,
                y: this.rows - boxHeight
            }
        ];

        this.answers = answers.map((answer, index) => ({
            ...answer,
            x: positions[index].x,
            y: positions[index].y,
            width: boxWidth,
            height: boxHeight
        }));

        this.draw();
    }

    getTouchedAnswer(head) {
        return this.answers.find((answer) => {
            return (
                head.x >= answer.x &&
                head.x < answer.x + answer.width &&
                head.y >= answer.y &&
                head.y < answer.y + answer.height
            );
        });
    }

    move() {
        if (
            !this.running ||
            this.paused ||
            this.finished
        ) {
            return;
        }

        this.direction = this.nextDirection;

        const head = {
            x: this.snake[0].x + this.direction.x,
            y: this.snake[0].y + this.direction.y
        };

        /*
           Le serpent traverse les bords.
        */
        if (head.x < 0) {
            head.x = this.columns - 1;
        }

        if (head.x >= this.columns) {
            head.x = 0;
        }

        if (head.y < 0) {
            head.y = this.rows - 1;
        }

        if (head.y >= this.rows) {
            head.y = 0;
        }

        const touchesItself = this.snake.some(
            (part, index) => {
                return (
                    index > 0 &&
                    part.x === head.x &&
                    part.y === head.y
                );
            }
        );

        if (touchesItself) {
            this.resetSnake();
            this.onSnakeCollision();
            this.draw();
            return;
        }

        this.snake.unshift(head);

        const touchedAnswer =
            this.getTouchedAnswer(head);

        if (!touchedAnswer) {
            this.snake.pop();
            this.draw();
            return;
        }

        if (touchedAnswer.correct) {
            /*
               Le serpent grandit après une bonne réponse.
            */
            this.onCorrect(touchedAnswer);
        } else {
            /*
               Après une mauvaise réponse :
               retour au centre et appel du gestionnaire.
            */
            this.snake.pop();
            this.resetSnake();
            this.onWrong(touchedAnswer);
        }

        this.draw();
    }

    start() {
        if (this.finished) {
            return;
        }

        this.running = true;
        this.paused = false;

        window.clearInterval(this.timer);

        this.timer = window.setInterval(
            () => this.move(),
            this.speed
        );

        this.draw();
    }

    togglePause() {
        if (!this.running || this.finished) {
            return false;
        }

        this.paused = !this.paused;
        this.draw();

        return this.paused;
    }

    stop() {
        this.running = false;
        this.paused = false;

        window.clearInterval(this.timer);
        this.timer = null;

        this.draw();
    }

    finish(message) {
        this.finished = true;
        this.running = false;
        this.paused = false;

        window.clearInterval(this.timer);
        this.timer = null;

        this.draw();
        this.drawOverlay(message);
    }

    reset() {
        window.clearInterval(this.timer);

        this.timer = null;
        this.running = false;
        this.paused = false;
        this.finished = false;
        this.answers = [];

        this.resetSnake();
        this.draw();
    }

    setSpeed(newSpeed) {
        if (
            !Number.isFinite(newSpeed) ||
            newSpeed < 70
        ) {
            return;
        }

        this.speed = newSpeed;

        if (this.running && !this.paused) {
            window.clearInterval(this.timer);

            this.timer = window.setInterval(
                () => this.move(),
                this.speed
            );
        }
    }

    drawGrid() {
        this.ctx.fillStyle = "#f8f5ea";

        this.ctx.fillRect(
            0,
            0,
            this.canvas.width,
            this.canvas.height
        );

        this.ctx.strokeStyle = "#e4ddcf";
        this.ctx.lineWidth = 1;

        for (
            let x = 0;
            x <= this.canvas.width;
            x += this.cellSize
        ) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }

        for (
            let y = 0;
            y <= this.canvas.height;
            y += this.cellSize
        ) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    drawWrappedText(
        text,
        centerX,
        centerY,
        maxWidth,
        lineHeight
    ) {
        const words = String(text).split(" ");
        const lines = [];
        let currentLine = "";

        words.forEach((word) => {
            const testLine = currentLine
                ? `${currentLine} ${word}`
                : word;

            if (
                this.ctx.measureText(testLine).width >
                    maxWidth &&
                currentLine
            ) {
                lines.push(currentLine);
                currentLine = word;
            } else {
                currentLine = testLine;
            }
        });

        if (currentLine) {
            lines.push(currentLine);
        }

        /*
           Maximum trois lignes pour éviter
           que le texte déborde des petits cadres.
        */
        const displayedLines = lines.slice(0, 3);

        const totalHeight =
            (displayedLines.length - 1) * lineHeight;

        displayedLines.forEach((line, index) => {
            this.ctx.fillText(
                line,
                centerX,
                centerY -
                    totalHeight / 2 +
                    index * lineHeight
            );
        });
    }

    drawAnswers() {
        this.answers.forEach((answer) => {
            const x = answer.x * this.cellSize;
            const y = answer.y * this.cellSize;
            const width =
                answer.width * this.cellSize;
            const height =
                answer.height * this.cellSize;

            this.ctx.fillStyle = "#ffffff";
            this.ctx.strokeStyle = "#b5303d";
            this.ctx.lineWidth = 3;

            this.ctx.fillRect(
                x + 3,
                y + 3,
                width - 6,
                height - 6
            );

            this.ctx.strokeRect(
                x + 3,
                y + 3,
                width - 6,
                height - 6
            );

            this.ctx.fillStyle = "#222222";
            this.ctx.font = "bold 12px Arial";
            this.ctx.textAlign = "center";
            this.ctx.textBaseline = "middle";

            this.drawWrappedText(
                answer.text,
                x + width / 2,
                y + height / 2,
                width - 18,
                14
            );
        });
    }

    drawSnake() {
        this.snake.forEach((part, index) => {
            this.ctx.fillStyle =
                index === 0
                    ? "#174f73"
                    : "#2d9b62";

            this.ctx.fillRect(
                part.x * this.cellSize + 3,
                part.y * this.cellSize + 3,
                this.cellSize - 6,
                this.cellSize - 6
            );
        });

        const head = this.snake[0];

        if (!head) {
            return;
        }

        const centerX =
            head.x * this.cellSize +
            this.cellSize / 2;

        const centerY =
            head.y * this.cellSize +
            this.cellSize / 2;

        this.ctx.fillStyle = "#ffffff";

        this.ctx.beginPath();
        this.ctx.arc(
            centerX - 5,
            centerY - 4,
            2.5,
            0,
            Math.PI * 2
        );
        this.ctx.fill();

        this.ctx.beginPath();
        this.ctx.arc(
            centerX + 5,
            centerY - 4,
            2.5,
            0,
            Math.PI * 2
        );
        this.ctx.fill();
    }

    drawOverlay(text) {
        const width = Math.min(
            340,
            this.canvas.width - 30
        );

        const height = 70;
        const x = (this.canvas.width - width) / 2;
        const y = (this.canvas.height - height) / 2;

        this.ctx.fillStyle =
            "rgba(11,48,72,.88)";

        this.ctx.fillRect(x, y, width, height);

        this.ctx.fillStyle = "#ffffff";
        this.ctx.font = "bold 19px Arial";
        this.ctx.textAlign = "center";
        this.ctx.textBaseline = "middle";

        this.ctx.fillText(
            text,
            this.canvas.width / 2,
            this.canvas.height / 2
        );
    }

    draw() {
        this.drawGrid();
        this.drawAnswers();
        this.drawSnake();

        if (this.paused && !this.finished) {
            this.drawOverlay("PAUSE");
        }
    }
}

window.SnakeGame = SnakeGame;