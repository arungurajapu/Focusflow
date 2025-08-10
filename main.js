document.addEventListener('DOMContentLoaded', function() {
    const postureStatusEl = document.getElementById('posture-status');
    const postureCardEl = document.getElementById('posture-card');

    const tiltStatusEl = document.getElementById('tilt-status');
    const tiltCardEl = document.getElementById('tilt-card');

    const distanceStatusEl = document.getElementById('distance-status');
    const distanceCardEl = document.getElementById('distance-card');
    
    const blinkStatusEl = document.getElementById('blink-status');

    function updateStatus(element, card, status) {
        if (!element || !card) return;

        element.textContent = status;
        card.classList.remove('status-good', 'status-warn', 'status-bad');

        if (status === 'Good') {
            card.classList.add('status-good');
        } else if (status === 'Warning') {
            card.classList.add('status-bad');
        }
    }

    async function fetchData() {
        try {
            const response = await fetch('/data');
            const data = await response.json();
            
            updateStatus(postureStatusEl, postureCardEl, data.posture);
            updateStatus(tiltStatusEl, tiltCardEl, data.tilt);
            updateStatus(distanceStatusEl, distanceCardEl, data.distance);

            if (blinkStatusEl) {
                blinkStatusEl.textContent = data.blink || '0';
            }

        } catch (error) {
            console.error("Error fetching data:", error);
        }
    }

    setInterval(fetchData, 1000);
});