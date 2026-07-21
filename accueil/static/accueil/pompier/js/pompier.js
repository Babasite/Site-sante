"use strict";

/* =========================================================
   SAUVE QUI PEUT — GESTION GÉNÉRALE
========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    const canvas =
        document.getElementById("gameCanvas");

    const pauseButton =
        document.getElementById("pauseButton");

    const restartButton =
        document.getElementById("restartButton");

    const questionElement =
        document.getElementById("question");

    const scoreElement =
        document.getElementById("score");

    const livesElement =
        document.getElementById("lives");

    const questionNumberElement =
        document.getElementById("questionNumber");

    const questionTotalElement =
        document.getElementById("questionTotal");

    const feedbackElement =
        document.getElementById("feedback");

    const upButton =
        document.getElementById("up");

    const downButton =
        document.getElementById("down");

    const leftButton =
        document.getElementById("left");

    const rightButton =
        document.getElementById("right");

    if (
        !canvas ||
        !pauseButton ||
        !restartButton ||
        !questionElement ||
        !scoreElement ||
        !livesElement ||
        !questionNumberElement ||
        !feedbackElement
    ) {
        console.error(
            "Sauve qui peut : des éléments HTML sont manquants."
        );
        return;
    }

    if (typeof window.SnakeGame !== "function") {
        console.error(
            "Sauve qui peut : snake.js n'est pas chargé."
        );
        return;
    }

    if (
        !Array.isArray(
            window.SAUVE_QUI_PEUT_QUESTIONS
        ) ||
        window.SAUVE_QUI_PEUT_QUESTIONS.length === 0
    ) {
        console.error(
            "Sauve qui peut : questions.js est vide ou absent."
        );
        return;
    }

    const questions = [
        ...window.SAUVE_QUI_PEUT_QUESTIONS
    ];

    let score = 0;
    let lives = 3;
    let questionIndex = 0;
    let bestScore = Number(
        localStorage.getItem(
            "sauveQuiPeutBestScore"
        )
    ) || 0;

    function shuffle(items) {
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

    function updateHud() {
        scoreElement.textContent = score;

        livesElement.textContent =
            "❤️ ".repeat(lives).trim();

        questionNumberElement.textContent =
            Math.min(
                questionIndex + 1,
                questions.length
            );

        if (questionTotalElement) {
            questionTotalElement.textContent =
                questions.length;
        }
    }

    function saveBestScore() {
        if (score <= bestScore) {
            return;
        }

        bestScore = score;

        localStorage.setItem(
            "sauveQuiPeutBestScore",
            String(bestScore)
        );
    }

    function loadQuestion() {
        if (questionIndex >= questions.length) {
            finishGame(true);
            return;
        }

        const currentQuestion =
            questions[questionIndex];

        questionElement.textContent =
            currentQuestion.question;

        game.resetSnake();

        game.setAnswers(
            currentQuestion.bonneReponse,
            currentQuestion.mauvaisesReponses
        );

        updateHud();
    }

    function goToNextQuestion(message) {
        feedbackElement.textContent = message;

        questionIndex += 1;

        if (questionIndex >= questions.length) {
            finishGame(true);
            return;
        }

        /*
           On affiche immédiatement une nouvelle question.
           Le joueur n'est donc jamais bloqué.
        */
        loadQuestion();
    }

    function loseLife(message) {
        lives -= 1;
        updateHud();

        if (lives <= 0) {
            feedbackElement.textContent = message;
            finishGame(false);
            return;
        }

        /*
           Même après une mauvaise réponse,
           on passe à la question suivante.
        */
        goToNextQuestion(message);
    }

    const game = new window.SnakeGame({
        canvas,
        cellSize: 30,
        speed: 220,

        onCorrect: () => {
            const currentQuestion =
                questions[questionIndex];

            score += 10;
            saveBestScore();

            goToNextQuestion(
                "✅ Bonne réponse ! " +
                currentQuestion.explication
            );
        },

        onWrong: (answer) => {
            loseLife(
                `❌ Mauvaise réponse : ${answer.text}`
            );
        },

        onSnakeCollision: () => {
            loseLife(
                "❌ Le serpent a touché son propre corps."
            );
        }
    });

    function startGame() {
        if (game.finished) {
            resetGame();
        }

        feedbackElement.textContent =
            "Dirige le serpent vers la bonne réponse.";

        pauseButton.textContent = "⏸ Pause";

        game.start();
    }

    function togglePause() {
        const paused = game.togglePause();

        pauseButton.textContent = paused
            ? "▶ Reprendre"
            : "⏸ Pause";
    }

    function finishGame(victory) {
        saveBestScore();

        if (victory) {
            questionElement.textContent =
                "Bravo, tu as terminé la série !";

            feedbackElement.textContent =
                `🏆 Score final : ${score} points.`;

            game.finish(
                `BRAVO ! ${score} POINTS`
            );
        } else {
            questionElement.textContent =
                "Partie terminée.";

            feedbackElement.textContent =
                "Tu n'as plus de vie. Clique sur Recommencer.";

            game.finish("FIN DE PARTIE");
        }
    }

    function resetGame() {
        score = 0;
        lives = 3;
        questionIndex = 0;

        const shuffledQuestions =
            shuffle(questions);

        questions.splice(
            0,
            questions.length,
            ...shuffledQuestions
        );

        game.reset();

        pauseButton.textContent = "⏸ Pause";

        feedbackElement.textContent =
            "Utilise les flèches pour diriger le serpent.";

        loadQuestion();
        updateHud();
        startGame();
    }

    function changeDirection(x, y) {
        game.changeDirection(x, y);
    }

    pauseButton.addEventListener(
        "click",
        togglePause
    );

    restartButton.addEventListener(
        "click",
        resetGame
    );

    document.addEventListener(
        "keydown",
        (event) => {
            const controlledKeys = [
                "ArrowUp",
                "ArrowDown",
                "ArrowLeft",
                "ArrowRight",
                " "
            ];

            /*
               La page reste défilable tant que
               la partie n'est pas active.
            */
            if (
                game.running &&
                !game.paused &&
                controlledKeys.includes(event.key)
            ) {
                event.preventDefault();
            }

            if (event.key === "ArrowUp") {
                changeDirection(0, -1);
            }

            if (event.key === "ArrowDown") {
                changeDirection(0, 1);
            }

            if (event.key === "ArrowLeft") {
                changeDirection(-1, 0);
            }

            if (event.key === "ArrowRight") {
                changeDirection(1, 0);
            }

            if (
                event.key === " " &&
                game.running
            ) {
                togglePause();
            }
        }
    );

    if (upButton) {
        upButton.addEventListener(
            "click",
            () => changeDirection(0, -1)
        );
    }

    if (downButton) {
        downButton.addEventListener(
            "click",
            () => changeDirection(0, 1)
        );
    }

    if (leftButton) {
        leftButton.addEventListener(
            "click",
            () => changeDirection(-1, 0)
        );
    }

    if (rightButton) {
        rightButton.addEventListener(
            "click",
            () => changeDirection(1, 0)
        );
    }

    resetGame();
});