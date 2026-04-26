(function () {
    'use strict';

    // Milliseconds each out-animation takes before navigation fires
    const DURATIONS = {
        fade:        500,
        ease:        700,
        glue:        800,
        'scale-down': 700,
        'scale-up':   500,
        'move-left':  600,
        'move-right': 600,
        'move-top':   600,
        slide:       1000,
        fold:         700,
        flip:         500,
        room:         800,
        cube:         600,
        carousel:     800,
        newspaper:    500,
        fall:        1000,
    };

    // Weighted pool for clock → other-page transitions.
    // shiny: true adds the sparkle overlay on top of the normal animation.
    const POOL = [
        // ── normal ──────────────────────────────────────────
        { key: 'fade',        weight: 10 },
        { key: 'ease',        weight: 8  },
        { key: 'glue',        weight: 8  },
        { key: 'scale-down',  weight: 8  },
        { key: 'scale-up',    weight: 8  },
        { key: 'move-left',   weight: 8  },
        { key: 'move-right',  weight: 8  },
        { key: 'move-top',    weight: 6  },
        { key: 'flip',        weight: 6  },
        // ── rare ────────────────────────────────────────────
        { key: 'fold',        weight: 3  },
        { key: 'slide',       weight: 3  },
        { key: 'room',        weight: 2  },
        { key: 'carousel',    weight: 2  },
        // ── rarest ──────────────────────────────────────────
        { key: 'newspaper',   weight: 1  },
        { key: 'cube',        weight: 1  },
        // ── shiny (even rarer — sparkles on top) ────────────
        { key: 'newspaper',   weight: 0.5, shiny: true },
        { key: 'cube',        weight: 0.3, shiny: true },
        { key: 'fold',        weight: 0.4, shiny: true },
        { key: 'carousel',    weight: 0.3, shiny: true },
        { key: 'scale-down',  weight: 0.3, shiny: true },
    ];

    function pickRandom() {
        var total = POOL.reduce(function (s, t) { return s + t.weight; }, 0);
        var r = Math.random() * total;
        for (var i = 0; i < POOL.length; i++) {
            r -= POOL[i].weight;
            if (r <= 0) return POOL[i];
        }
        return POOL[0];
    }

    function sparkle() {
        var overlay = document.getElementById('pt-sparkles');
        if (!overlay) return;

        var colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#C39BD3', '#F7DC6F', '#A9DFBF'];
        var count  = 36;

        for (var i = 0; i < count; i++) {
            var el    = document.createElement('div');
            var isStar = Math.random() > 0.45;
            el.className = 'pt-sparkle ' + (isStar ? 'star' : 'dot');

            var size  = 7 + Math.random() * 13;
            var angle = Math.random() * Math.PI * 2;
            var dist  = 90 + Math.random() * 200;

            el.style.width  = size + 'px';
            el.style.height = size + 'px';
            el.style.left   = (10 + Math.random() * 80) + '%';
            el.style.top    = (10 + Math.random() * 80) + '%';
            el.style.setProperty('--dx',    (Math.cos(angle) * dist).toFixed(1) + 'px');
            el.style.setProperty('--dy',    (Math.sin(angle) * dist).toFixed(1) + 'px');
            el.style.setProperty('--color', colors[Math.floor(Math.random() * colors.length)]);
            el.style.setProperty('--delay', (Math.random() * 0.35).toFixed(3) + 's');
            el.style.setProperty('--dur',   (0.65 + Math.random() * 0.5).toFixed(3) + 's');

            overlay.appendChild(el);
        }

        setTimeout(function () { overlay.innerHTML = ''; }, 1600);
    }

    function navigate(url, key, isShiny) {
        document.documentElement.classList.add('pt-out-' + key);
        if (isShiny) sparkle();

        var duration = DURATIONS[key] || 600;
        var dest     = url + '?pt=' + key + (isShiny ? '-shiny' : '');

        setTimeout(function () {
            window.location.href = dest;
        }, duration);
    }

    function applyInTransition() {
        var params  = new URLSearchParams(window.location.search);
        var pt      = params.get('pt');
        if (!pt) return;

        var isShiny = pt.slice(-6) === '-shiny';
        var key     = isShiny ? pt.slice(0, -6) : pt;
        if (!DURATIONS[key]) return;

        // Clean the URL immediately so ?pt= never shows in history
        history.replaceState(null, '', window.location.pathname);

        document.documentElement.classList.add('pt-in-' + key);
        if (isShiny) setTimeout(sparkle, 80);

        setTimeout(function () {
            document.documentElement.classList.remove('pt-in-' + key);
        }, DURATIONS[key] + 100);
    }

    window.ptSparkle = sparkle;

    // ── Public API ───────────────────────────────────────────────────────────
    //
    // ptNavigate(url, mode, delaySecs)
    //
    //   url       - destination path, e.g. '/habits' or '/'
    //   mode      - 'random'  → pick from weighted pool (clock → other page)
    //               'fall'    → always the fall animation  (any page → clock)
    //               any key   → use that specific transition
    //   delaySecs - seconds to wait before starting the out-animation
    //
    // To add budget.html to the loop, call ptNavigate from its template:
    //   ptNavigate('/', 'fall', dwell_time)
    // And point the clock toward '/budget' the same way as '/habits'.
    //
    // forceShiny overrides pool randomness — used by the debug page
    window.ptNavigate = function (url, mode, delaySecs, forceShiny) {
        setTimeout(function () {
            if (mode === 'random') {
                var pick = pickRandom();
                navigate(url, pick.key, forceShiny || pick.shiny || false);
            } else if (mode === 'fall') {
                navigate(url, 'fall', forceShiny || false);
            } else {
                navigate(url, mode, forceShiny || false);
            }
        }, (delaySecs || 0) * 1000);
    };

    // Apply in-transition as soon as the DOM is available
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyInTransition);
    } else {
        applyInTransition();
    }
}());
