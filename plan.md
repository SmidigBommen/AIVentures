# Hero Wars Web GUI Implementation Plan - FastAPI + HTML (XP/TDD Approach)

## **Project Overview**

This plan outlines the implementation of a Hero Wars-style web GUI for the existing D&D Python game project using modern web technologies and XP/TDD methodologies. The focus is on creating an engaging Battle Arena interface with pure HTML/CSS/JavaScript frontend and FastAPI backend.

### **User Requirements**
- **Frontend**: Pure HTML/CSS/JavaScript (no frameworks)
- **Backend**: FastAPI with uvicorn server
- **Communication**: HTTP polling for real-time updates
- **Storage**: In-memory only (single player)
- **Timeline**: 1-week sprints with incremental delivery
- **Methodology**: XP/Scrum with TDD approach
- **Priority**: Battle Arena with character portraits, health bars, animated combat

## **Architecture Overview**

### **Technology Stack**
- **Backend**: FastAPI with uvicorn server
- **Frontend**: Pure HTML/CSS/JavaScript (no frameworks)
- **Communication**: HTTP polling for real-time updates
- **Storage**: In-memory only (single player)
- **Testing**: TDD with pytest for backend, manual testing for frontend

### **New Project Structure**
```
AIVentures-web/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # Pydantic models
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── game.py          # Game state endpoints
│   │   │   ├── character.py     # Character endpoints
│   │   │   ├── battle.py        # Battle endpoints
│   │   │   └── location.py      # Location endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── game_service.py  # Game logic wrapper
│   │   │   └── session.py       # Session management
│   │   └── tests/
│   │       ├── test_game.py
│   │       ├── test_character.py
│   │       └── test_battle.py
│   ├── existing_game_files/     # Original game code
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── battle.css
│   │   ├── character.css
│   │   └── common.css
│   ├── js/
│   │   ├── api.js               # API communication
│   │   ├── battle.js            # Battle logic
│   │   ├── character.js         # Character management
│   │   └── main.js              # Main application
│   └── assets/
│       └── images/
└── plan-updated.md
```

### **Existing Game Components to Preserve**
- `GameState` - Central state management (singleton)
- `Character` - Player stats, leveling, equipment
- `Monster` - Enemy entities with AI
- `Battle` - Turn-based combat mechanics
- Factory patterns for character/monster/item creation
- All existing game logic and D&D rules

## **XP Scrum Slices (User Stories)**

### **Sprint 1: Foundation & Character Creation**
**Duration**: 1 Week

**User Story 1**: As a player, I want to start a new game and create a character
**Acceptance Criteria**:
- Player can choose race and class from dropdowns
- Character stats are calculated based on D&D rules
- Game session is created and stored in memory
- API returns character sheet data

**TDD Approach**:
```python
# Test-first approach
def test_create_character():
    response = client.post("/api/character/create", json={
        "name": "TestHero",
        "race": "human",
        "class": "fighter"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TestHero"
    assert data["race"] == "human"
    assert data["class"] == "fighter"
    assert data["level"] == 1
    assert "stats" in data
```

**Implementation Tasks**:
- [ ] Set up FastAPI project structure
- [ ] Implement character creation endpoint
- [ ] Create Pydantic models for Character
- [ ] Test character creation (TDD)
- [ ] Build HTML character creation form
- [ ] Connect frontend to character creation API

---

### **Sprint 2: Basic Game State & Navigation**
**Duration**: 1 Week

**User Story 2**: As a player, I want to see my character status and navigate between locations
**Acceptance Criteria**:
- Display current character stats and inventory
- Show current location and available areas
- Allow movement between connected areas
- Game state persists in session

**TDD Approach**:
```python
def test_get_character_stats():
    response = client.get("/api/character/stats")
    assert response.status_code == 200
    data = response.json()
    assert "hp" in data
    assert "stats" in data
    assert "inventory" in data

def test_location_navigation():
    response = client.get("/api/location/current")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "connected_areas" in data
```

**Implementation Tasks**:
- [ ] Implement game state endpoints
- [ ] Create character stats display
- [ ] Build location navigation system
- [ ] Test state management (TDD)
- [ ] Create HTML dashboard and navigation

---

### **Sprint 3: Battle System - Basic Combat**
**Duration**: 1 Week

**User Story 3**: As a player, I want to engage in turn-based combat with monsters
**Acceptance Criteria**:
- Combat starts when exploring dangerous areas
- Display player and monster with health bars
- Allow attack and defend actions
- Calculate damage based on D&D rules
- Show victory/defeat results

**TDD Approach**:
```python
def test_battle_start():
    response = client.post("/api/battle/start")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] == True
    assert "monster" in data
    assert "character_hp" in data

def test_attack_action():
    response = client.post("/api/battle/action", json={
        "action": "attack"
    })
    assert response.status_code == 200
    data = response.json()
    assert "damage" in data or "miss" in data
```

**Implementation Tasks**:
- [ ] Implement battle start endpoint
- [ ] Create battle action endpoints
- [ ] Build battle state management
- [ ] Test combat mechanics (TDD)
- [ ] Create HTML battle interface with health bars
- [ ] Implement polling for battle updates

---

### **Sprint 4: Battle Polish & Visual Feedback**
**Duration**: 1 Week

**User Story 4**: As a player, I want visual feedback and animations during combat
**Acceptance Criteria**:
- Damage numbers appear when attacks land
- Health bars animate smoothly
- Character portraits show equipment
- Turn order is clearly displayed
- Battle effects for special abilities

**Implementation Tasks**:
- [ ] Add battle animations with CSS/JS
- [ ] Implement floating damage numbers
- [ ] Create simple character portraits
- [ ] Add turn indicators
- [ ] Polling optimization for battle state
- [ ] Mobile responsive design

---

### **Sprint 5: Items & Equipment**
**Duration**: 1 Week

**User Story 5**: As a player, I want to manage my inventory and equipment
**Acceptance Criteria**:
- View character inventory
- Equip/unequip weapons and armor
- Use healing items during battle
- See equipment reflected on character
- Inventory management UI

**TDD Approach**:
```python
def test_inventory_management():
    response = client.get("/api/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)

def test_equip_item():
    response = client.post("/api/inventory/equip", json={
        "item_id": "sword_001"
    })
    assert response.status_code == 200
```

**Implementation Tasks**:
- [ ] Implement inventory endpoints
- [ ] Create equipment management
- [ ] Build inventory UI
- [ ] Test item usage (TDD)
- [ ] Visual equipment changes on character

---

### **Sprint 6: Level Up & Progression**
**Duration**: 1 Week

**User Story 6**: As a player, I want to level up and become stronger
**Acceptance Criteria**:
- Gain XP from battles
- Level up when XP threshold reached
- Improve stats on level up
- Visual celebration for level up
- Progress tracking

**Implementation Tasks**:
- [ ] Implement XP and leveling system
- [ ] Create level up mechanics
- [ ] Build progression UI
- [ ] Test character advancement (TDD)
- [ ] Add level up animations

## **TDD Testing Strategy**

### **Backend Testing (Pytest)**
```python
# tests/test_game_service.py
class TestGameService:
    def setup_method(self):
        self.game_service = GameService()
        
    def test_new_game_creation(self):
        # Test game initialization
        pass
        
    def test_character_creation_validation(self):
        # Test character creation rules
        pass
```

#### **Integration Testing**
```python
# tests/test_integration.py
def test_full_game_flow():
    # Test complete game journey
    pass
```

#### **Frontend Testing (Manual)**
- Manual testing checklist for each sprint
- Browser compatibility testing
- Mobile responsiveness testing
- User interaction testing

### **REST API Endpoints Design**

#### **Game State Management**
```
GET  /api/game/state          # Get current game state
POST /api/game/new            # Start new game (character creation)
GET  /api/game/campaign       # Get campaign data
```

#### **Character Management**
```
GET  /api/character           # Get character stats and inventory
POST /api/character/create    # Create new character
PUT  /api/character/rest      # Rest to recover HP
GET  /api/character/stats     # Get detailed character sheet
```

#### **Location & Navigation**
```
GET  /api/location/current    # Get current location/area
GET  /api/location/travel     # Get available travel options
POST /api/location/travel     # Travel to new location
POST /api/location/explore    # Explore current area
GET  /api/location/areas      # Get areas in current location
POST /api/location/move       # Move to connected area
```

#### **Combat System**
```
POST /api/battle/start        # Start battle (triggered by exploration)
GET  /api/battle/status       # Get battle status (HP, turn order)
POST /api/battle/action       # Player action (attack/defend/use item)
GET  /api/battle/turn         # Whose turn is it
DELETE /api/battle            # End battle (victory/defeat)
```

#### **Inventory & Items**
```
GET  /api/inventory           # Get character inventory
POST /api/inventory/use       # Use item (healing potion)
GET  /api/inventory/equipment # Get equipped items
POST /api/inventory/equip     # Equip/unequip items
```

#### **Shop System**
```
GET  /api/shop/inventory      # Get shop inventory
POST /api/shop/buy            # Buy item from shop
POST /api/shop/sell           # Sell item to shop
GET  /api/shop/gold           # Get player gold amount
```

### **XP Practices**

#### **Daily Standup Questions**
1. What did you accomplish yesterday?
2. What will you work on today?
3. Any blockers?

#### **Sprint Review**
- Demo working software each sprint
- Collect feedback
- Adjust backlog priority

#### **Sprint Retrospective**
- What went well?
- What could be improved?
- Action items for next sprint

### **Development Workflow**

#### **TDD Cycle**
1. **Red**: Write failing test
2. **Green**: Write minimum code to pass
3. **Refactor**: Improve code while tests pass

#### **Git Workflow**
```bash
# Each user story on feature branch
git checkout -b feature/character-creation
# Commit with tests first, then implementation
git commit -m "test: Add failing character creation test"
git commit -m "feat: Implement character creation endpoint"
```

## **Technical Implementation Details**

### **HTTP Polling Strategy**
```javascript
// Client-side polling pattern with adaptive frequency
function pollGameState() {
    const pollRate = gameState.isBattle ? 1000 : 3000;
    
    fetch('/api/game/state')
        .then(response => response.json())
        .then(data => {
            updateUI(data);
            setTimeout(pollGameState, pollRate);
        })
        .catch(error => {
            console.error('Polling error:', error);
            setTimeout(pollGameState, 5000); // Backoff on error
        });
}
```

### **Session Management**
```python
# In-memory session storage for single player
sessions = {}

def get_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = GameState()
    return sessions[session_id]
```

### **Data Serialization Strategy**
```python
# Pydantic models for API responses
class CharacterResponse(BaseModel):
    name: str
    race: str
    class_name: str
    level: int
    xp: int
    xp_to_next_level: int
    current_hp: int
    max_hp: int
    armor_class: int
    gold: int
    stats: Dict[str, int]
    inventory: List[ItemResponse]
    weapon_slots: Dict[str, Optional[WeaponResponse]]

class BattleState(BaseModel):
    is_active: bool
    round: int
    turn_order: List[str]
    current_turn: str
    character_hp: int
    monster_hp: int
    monster_name: str
    available_actions: List[str]

class LocationResponse(BaseModel):
    name: str
    description: str
    type: str
    areas: List[AreaResponse]
    current_area: AreaResponse
```

### **Frontend Architecture**
```javascript
// Modular JavaScript approach
class GameAPI {
    async getGameState() {
        return fetch('/api/game/state').then(r => r.json());
    }
    
    async createCharacter(characterData) {
        return fetch('/api/character/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(characterData)
        }).then(r => r.json());
    }
    
    async performBattleAction(action) {
        return fetch('/api/battle/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        }).then(r => r.json());
    }
}

class BattleUI {
    constructor() {
        this.api = new GameAPI();
        this.pollInterval = null;
    }
    
    render(battleState) {
        // Update battle interface
        this.updateHealthBars(battleState);
        this.updateTurnIndicator(battleState);
        this.updateActionButtons(battleState.available_actions);
    }
    
    startPolling() {
        this.pollInterval = setInterval(() => {
            this.api.getGameState().then(state => {
                if (state.battle) {
                    this.render(state.battle);
                }
            });
        }, 1000);
    }
}
```

### **Key Design Principles**
1. **Preserve Existing Logic** - All game rules remain unchanged
2. **API as Interface Layer** - Clean separation between frontend and backend
3. **Stateless Backend** - All game state stored in sessions
4. **Progressive Enhancement** - Start with basic functionality, enhance gradually
5. **Test-First Development** - Write tests before implementation

### **Performance Considerations**
- Implement adaptive polling (faster in battle, slower normally)
- Cache static game data (races, classes, items) on frontend
- Use efficient JSON responses with minimal data
- Implement proper error handling and retry logic
- Monitor response times and optimize bottlenecks

### **Visual Design Strategy**
Since using pure HTML/CSS/JavaScript without frameworks:
- **CSS Grid/Flexbox** for responsive layouts
- **CSS animations** for health bars and combat effects
- **SVG graphics** for simple character portraits
- **CSS variables** for consistent theming
- **Mobile-first responsive design**
- **Progressive enhancement** for browser compatibility

## **Continuous Integration & Deployment**

### **CI/CD Pipeline**
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          pytest --cov=app tests/
      - name: Upload coverage
        uses: codecov/codecov-action@v1

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to staging
        run: echo "Deploy to staging server"
```

### **Code Quality Tools**
```bash
# Backend code quality
pip install black flake8 mypy pytest pytest-cov
black app/                    # Code formatting
flake8 app/                   # Linting
mypy app/                     # Type checking
pytest --cov=app tests/       # Test coverage

# Frontend validation
npm install -g eslint
eslint frontend/js/           # JavaScript linting
```

### **Development Environment Setup**
```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (simple HTTP server)
cd frontend
python -m http.server 3000
# or
npx serve .
```

### **Local Development Workflow**
1. **Start backend**: `uvicorn app.main:app --reload`
2. **Start frontend**: `python -m http.server 3000`
3. **Run tests**: `pytest --cov=app tests/`
4. **Code formatting**: `black app/`
5. **Type checking**: `mypy app/`

## **Success Metrics**

### **Per Sprint Metrics**
- [ ] All user stories completed
- [ ] Test coverage > 80%
- [ ] Working demo each sprint
- [ ] Code review passed
- [ ] Performance benchmarks met

### **Technical Success Criteria**
- [ ] All existing D&D mechanics work via API
- [ ] Battle animations provide clear feedback
- [ ] Character progression is visually rewarding
- [ ] Response time < 200ms for all endpoints
- [ ] Mobile responsive design
- [ ] Code remains maintainable and extensible

### **User Experience Goals**
- [ ] Intuitive battle controls
- [ ] Clear visual feedback for all actions
- [ ] Responsive interface with no lag
- [ ] Engaging visual presentation
- [ ] Smooth transitions between game states
- [ ] Cross-browser compatibility

### **Code Quality Standards**
- [ ] 80%+ test coverage
- [ ] All linting rules passed
- [ ] Type checking with mypy
- [ ] Documentation for all API endpoints
- [ ] Git commit messages follow conventional format

## **Risk Assessment & Mitigation**

### **Technical Risks**
- **Performance**: HTTP polling may cause unnecessary network traffic
  - *Mitigation*: Implement adaptive polling rates, efficient JSON responses
- **Integration**: Existing game code may not integrate cleanly with web API
  - *Mitigation*: Create wrapper service layer, minimize changes to core classes
- **Session Management**: In-memory storage limits scalability
  - *Mitigation*: For single-player this is acceptable, document limitations
- **Frontend Complexity**: Vanilla JavaScript may become unwieldy
  - *Mitigation*: Use modular design patterns, document architecture

### **Development Risks**
- **Timeline**: 6 sprints may be insufficient for full implementation
  - *Mitigation*: Focus on MVP features first, defer nice-to-haves
- **Testing Coverage**: TDD may slow initial development
  - *Mitigation*: Focus on critical paths, add edge case tests later
- **Browser Compatibility**: Vanilla JS may have cross-browser issues
  - *Mitigation*: Test on major browsers, use modern JS features cautiously

### **Business Risks**
- **User Experience**: Web interface may feel less responsive than native
  - *Mitigation*: Optimize polling rates, add visual feedback immediately
- **Feature Creep**: Scope may expand beyond Hero Wars battle interface
  - *Mitigation*: Strict sprint scope management, prioritize core features

### **Mitigation Strategies**
- **Regular Sprint Reviews**: Demo working software each sprint
- **Automated Testing**: Comprehensive test suite to prevent regressions
- **Incremental Delivery**: Each sprint delivers usable functionality
- **Technical Debt Management**: Reserve 20% of each sprint for refactoring
- **Documentation**: Maintain clear API docs and code comments

## **Future Enhancements**

### **Post-Sprint Features**
- Sound effects and background music (Web Audio API)
- Advanced particle effects for combat animations
- Character skins and customization options
- Smooth screen transitions and animations
- Game state persistence (local storage)
- Settings and options menu

### **Long-term Vision**
- Full Hero Wars-style interface with all screens
- Multiplayer capabilities (WebSockets instead of polling)
- Custom campaign editor and sharing
- Achievement and progression systems
- Guild/social features
- Mobile app wrapper (Cordova/Capacitor)

## **Getting Started - Sprint 1 Setup**

### **Prerequisites**
- Python 3.11+
- Node.js 18+ (for frontend tools)
- Git

### **Initial Setup Commands**
```bash
# Clone repository and switch to feature branch
git clone https://github.com/SmidigBommen/AIVentures.git
cd AIVentures
git checkout hero-wars-gui

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn pytest

# Frontend setup
cd ../frontend
# No build tools needed for vanilla HTML/CSS/JS

# Initial directory structure
mkdir -p backend/app/{api,core,tests}
mkdir -p frontend/{css,js,assets/images}
```

### **First Development Tasks**
1. **Write failing test** for character creation endpoint
2. **Implement minimal FastAPI app** to pass test
3. **Create basic HTML page** with character creation form
4. **Connect frontend to backend** API
5. **Demo working character creation** at end of Sprint 1

## **Conclusion**

This updated implementation plan provides a structured, XP/TDD approach to building a Hero Wars-style web GUI for the existing D&D game. The sprint-based delivery ensures incremental value while maintaining high code quality through test-driven development.

The modern web architecture (FastAPI + pure HTML/CSS/JS) provides several advantages over the original pygame approach:
- **Easier deployment** - Web-based vs desktop application
- **Better maintainability** - Standard web technologies
- **Mobile compatibility** - Responsive design works on all devices
- **Scalable architecture** - API-first design allows for future enhancements
- **Testing approach** - Robust testing with industry-standard tools

Each sprint delivers working software, allowing for early feedback and course corrections. The focus on core game mechanics ensures the underlying D&D experience remains intact while providing an engaging Hero Wars-style interface.

**Ready to start Sprint 1: Foundation & Character Creation?**

**Immediate Next Steps**:
1. Set up project structure as outlined
2. Write first failing test for character creation
3. Begin TDD cycle implementation
4. Schedule Sprint 1 demo session