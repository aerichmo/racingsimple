// Racing Simple JavaScript

class RacingApp {
    constructor() {
        this.loadRacesBtn = document.getElementById('load-races');
        this.refreshBtn = document.getElementById('refresh-data');
        this.loadingDiv = document.getElementById('loading');
        this.racesListDiv = document.getElementById('races-list');
        this.errorDiv = document.getElementById('error-message');
        
        this.init();
    }
    
    init() {
        this.loadRacesBtn.addEventListener('click', () => this.loadRaces());
        this.refreshBtn.addEventListener('click', () => this.refreshData());
        
        // Load races on page load
        this.loadRaces();
    }
    
    async loadRaces() {
        this.showLoading();
        this.hideError();
        
        try {
            const response = await fetch('/api/races');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.displayRaces(data.data);
            } else {
                throw new Error('Failed to load races');
            }
            
        } catch (error) {
            console.error('Error loading races:', error);
            this.showError('Failed to load races. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    async refreshData() {
        await this.loadRaces();
    }
    
    displayRaces(races) {
        if (!races || races.length === 0) {
            this.racesListDiv.innerHTML = '<p class="no-data">No races available at this time.</p>';
            return;
        }
        
        const racesHTML = races.map(race => this.createRaceCard(race)).join('');
        this.racesListDiv.innerHTML = racesHTML;
    }
    
    createRaceCard(race) {
        const horsesHTML = race.horses.map(horse => `
            <div class="horse-card">
                <div class="horse-name">${horse.name}</div>
                <div class="horse-details">
                    <span>Jockey: ${horse.jockey}</span>
                    <span class="odds">Odds: ${horse.odds}</span>
                </div>
            </div>
        `).join('');
        
        return `
            <div class="race-card">
                <div class="race-header">
                    <div class="race-title">${race.name}</div>
                    <div class="race-info">
                        <span><strong>Time:</strong> ${race.time}</span>
                        <span><strong>Track:</strong> ${race.track}</span>
                        <span><strong>Distance:</strong> ${race.distance}</span>
                    </div>
                </div>
                <div class="horses-grid">
                    ${horsesHTML}
                </div>
            </div>
        `;
    }
    
    showLoading() {
        this.loadingDiv.classList.remove('hidden');
        this.racesListDiv.innerHTML = '';
    }
    
    hideLoading() {
        this.loadingDiv.classList.add('hidden');
    }
    
    showError(message) {
        this.errorDiv.textContent = message;
        this.errorDiv.classList.remove('hidden');
    }
    
    hideError() {
        this.errorDiv.classList.add('hidden');
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new RacingApp();
});