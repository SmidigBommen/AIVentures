// AIVentures - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize selection cards
    initSelectionCards();
});

function initSelectionCards() {
    const selectionCards = document.querySelectorAll('.selection-card[data-value]');
    const hiddenInput = document.getElementById('selected-value');

    selectionCards.forEach(card => {
        card.addEventListener('click', function() {
            // Remove selected class from all cards
            selectionCards.forEach(c => c.classList.remove('selected'));

            // Add selected class to clicked card
            this.classList.add('selected');

            // Update hidden input if exists
            if (hiddenInput) {
                hiddenInput.value = this.dataset.value;
            }
        });
    });
}

// Auto-refresh for battle pages
function startBattleRefresh(interval = 2000) {
    setInterval(function() {
        if (document.querySelector('.battle-arena')) {
            fetch(window.location.href + '/status')
                .then(response => response.json())
                .then(data => updateBattleUI(data))
                .catch(err => console.log('Battle status check failed'));
        }
    }, interval);
}

function updateBattleUI(data) {
    // Update health bars
    const playerHealth = document.querySelector('.player .health-bar-fill');
    const monsterHealth = document.querySelector('.monster .health-bar-fill');

    if (playerHealth && data.player) {
        const playerPercent = (data.player.current_hp / data.player.max_hp) * 100;
        playerHealth.style.width = playerPercent + '%';
    }

    if (monsterHealth && data.monster) {
        const monsterPercent = (data.monster.current_hp / data.monster.max_hp) * 100;
        monsterHealth.style.width = monsterPercent + '%';
    }
}

// Smooth scroll to battle log bottom
function scrollBattleLog() {
    const log = document.querySelector('.battle-log');
    if (log) {
        log.scrollTop = log.scrollHeight;
    }
}

// Form submission helper
function submitForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.submit();
    }
}
