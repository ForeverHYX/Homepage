(function () {
    const cards = Array.from(document.querySelectorAll(".home-liquid-card"));
    if (!cards.length) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    const lerp = (from, to, t) => from + (to - from) * t;
    const defaults = {
        lightX: 18,
        lightY: 12,
        shiftX: 0,
        shiftY: 0,
        lift: 0,
    };

    const states = cards.map((card) => ({
        card,
        current: { ...defaults },
        target: { ...defaults },
        active: false,
    }));

    let rafId = 0;

    function applyState(state) {
        const { card, current } = state;
        card.style.setProperty("--liquid-light-x", `${current.lightX.toFixed(2)}%`);
        card.style.setProperty("--liquid-light-y", `${current.lightY.toFixed(2)}%`);
        card.style.setProperty("--liquid-rim-shift-x", `${(current.shiftX * 1.05).toFixed(2)}px`);
        card.style.setProperty("--liquid-rim-shift-y", `${(current.shiftY * 1.05).toFixed(2)}px`);
        card.style.setProperty("--liquid-shoulder-shift-x", `${(current.shiftX * 0.72).toFixed(2)}px`);
        card.style.setProperty("--liquid-shoulder-shift-y", `${(current.shiftY * 0.72).toFixed(2)}px`);
        card.style.setProperty("--liquid-base-shift-x", `${(current.shiftX * 0.28).toFixed(2)}px`);
        card.style.setProperty("--liquid-base-shift-y", `${(current.shiftY * 0.28).toFixed(2)}px`);
        card.style.setProperty("--liquid-lift", current.lift.toFixed(3));
    }

    function scheduleFrame() {
        if (!rafId) {
            rafId = window.requestAnimationFrame(frame);
        }
    }

    function frame() {
        rafId = 0;
        let needsAnotherFrame = false;

        states.forEach((state) => {
            state.current.lightX = lerp(state.current.lightX, state.target.lightX, 0.16);
            state.current.lightY = lerp(state.current.lightY, state.target.lightY, 0.16);
            state.current.shiftX = lerp(state.current.shiftX, state.target.shiftX, 0.18);
            state.current.shiftY = lerp(state.current.shiftY, state.target.shiftY, 0.18);
            state.current.lift = lerp(state.current.lift, state.target.lift, 0.15);
            applyState(state);

            const delta =
                Math.abs(state.current.lightX - state.target.lightX) +
                Math.abs(state.current.lightY - state.target.lightY) +
                Math.abs(state.current.shiftX - state.target.shiftX) +
                Math.abs(state.current.shiftY - state.target.shiftY) +
                Math.abs(state.current.lift - state.target.lift);

            if (delta > 0.08) {
                needsAnotherFrame = true;
            }
        });

        if (needsAnotherFrame) {
            scheduleFrame();
        }
    }

    function resetState(state) {
        state.active = false;
        state.target = { ...defaults };
        scheduleFrame();
    }

    states.forEach((state) => {
        applyState(state);

        if (reduceMotion.matches) return;

        state.card.addEventListener("pointermove", (event) => {
            const rect = state.card.getBoundingClientRect();
            const x = clamp(((event.clientX - rect.left) / rect.width) * 100, 6, 94);
            const y = clamp(((event.clientY - rect.top) / rect.height) * 100, 6, 94);
            const dx = (x - 50) / 50;
            const dy = (y - 50) / 50;

            state.active = true;
            state.target.lightX = x;
            state.target.lightY = y;
            state.target.shiftX = dx * 3.2;
            state.target.shiftY = dy * 2.4;
            state.target.lift = 1;
            scheduleFrame();
        });

        state.card.addEventListener("pointerleave", () => resetState(state));
        state.card.addEventListener("pointercancel", () => resetState(state));
    });

    const handleMotionChange = () => {
        if (reduceMotion.matches) {
            states.forEach((state) => {
                state.current = { ...defaults };
                resetState(state);
                applyState(state);
            });
        }
    };

    if (typeof reduceMotion.addEventListener === "function") {
        reduceMotion.addEventListener("change", handleMotionChange);
    } else if (typeof reduceMotion.addListener === "function") {
        reduceMotion.addListener(handleMotionChange);
    }
})();
