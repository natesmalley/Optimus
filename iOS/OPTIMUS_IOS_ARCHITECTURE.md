# 🏗️ Optimus iOS App Architecture & Design Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Design System](#design-system)
3. [Component Library](#component-library)
4. [API Integration](#api-integration)
5. [Button Actions & Functions](#button-actions--functions)
6. [Navigation Flow](#navigation-flow)
7. [Data Flow](#data-flow)
8. [Voice Integration](#voice-integration)
9. [State Management](#state-management)
10. [Implementation Status](#implementation-status)

---

## Architecture Overview

### Technology Stack
```
┌─────────────────────────────────────┐
│           iOS App (SwiftUI)         │
├─────────────────────────────────────┤
│         Presentation Layer          │
│  • Views (SwiftUI)                  │
│  • ViewModels (ObservableObject)    │
│  • Components (Reusable UI)         │
├─────────────────────────────────────┤
│          Business Logic             │
│  • Managers (Singleton Services)    │
│  • Models (Data Structures)         │
│  • Utilities (Helpers)              │
├─────────────────────────────────────┤
│          Data Layer                 │
│  • APIManager (Network)             │
│  • CoreData (Local Storage)         │
│  • UserDefaults (Settings)          │
└─────────────────────────────────────┘
```

### Project Structure
```
iOS/OptimusApp/
├── Sources/
│   ├── Core/                    # Core systems
│   │   ├── DesignSystem.swift   # Colors, typography, spacing
│   │   ├── AppState.swift       # Global app state
│   │   └── Constants.swift      # App constants
│   │
│   ├── Views/                   # UI Components
│   │   ├── ContentView.swift    # Main tab navigation
│   │   ├── DashboardView.swift  # Home screen
│   │   ├── VoiceAssistantView.swift # Voice interface
│   │   ├── AgendaView.swift     # Calendar/schedule
│   │   ├── TasksView.swift      # Task management
│   │   ├── SettingsView.swift   # App settings
│   │   └── Components/          # Reusable components
│   │       ├── CouncilResponseView.swift
│   │       ├── QuickActionsGrid.swift
│   │       └── LoadingView.swift
│   │
│   ├── ViewModels/              # Business logic
│   │   ├── DashboardViewModel.swift
│   │   ├── VoiceViewModel.swift
│   │   ├── AgendaViewModel.swift
│   │   └── TasksViewModel.swift
│   │
│   ├── Managers/                # Services
│   │   ├── APIManager.swift     # Network calls
│   │   ├── VoiceManager.swift   # Speech services
│   │   ├── NotificationManager.swift
│   │   └── StorageManager.swift # Local storage
│   │
│   ├── Models/                  # Data models
│   │   ├── AssistantModels.swift
│   │   ├── UserModels.swift
│   │   └── CouncilModels.swift
│   │
│   └── OptimusApp.swift        # App entry point
│
├── Resources/
│   ├── Assets.xcassets/        # Images, colors
│   ├── Info.plist              # App configuration
│   └── Localizable.strings     # Translations
│
└── Tests/
    ├── ViewTests/
    ├── ViewModelTests/
    └── ManagerTests/
```

---

## Design System

### Color Palette
| Color Name | Hex Code | Usage | SwiftUI Reference |
|------------|----------|-------|-------------------|
| **Primary Blue** | #007AFF | Main actions, links | `Color.optimusPrimary` |
| **Secondary Purple** | #5856D6 | Accents, special features | `Color.optimusSecondary` |
| **Accent Orange** | #FF9500 | Energy, notifications | `Color.optimusAccent` |
| **Success Green** | #34C759 | Completed, positive | `Color.optimusSuccess` |
| **Warning Orange** | #FF9500 | Alerts, attention | `Color.optimusWarning` |
| **Error Red** | #FF3B30 | Errors, critical | `Color.optimusError` |

### Council Member Colors
| Member | Color | Role | SwiftUI Reference |
|--------|-------|------|-------------------|
| Magnus | Blue | Work & Productivity | `Color.magnusColor` |
| Harmony | Orange | Social & Relationships | `Color.harmonyColor` |
| Vitalis | Green | Health & Wellness | `Color.vitalisColor` |
| Sage | Purple | Growth & Learning | `Color.sageColor` |
| Sentinel | Red | Safety & Security | `Color.sentinelColor` |

### Typography Scale
```swift
// Headers
.largeTitle: 34pt bold      // Main screens
.title: 28pt semibold        // Section headers
.title2: 22pt medium         // Card titles

// Body
.headline: 17pt semibold     // Important text
.body: 17pt regular          // Main content
.callout: 16pt regular       // Secondary content
.footnote: 13pt regular      // Metadata

// Special
.monospaced: 15pt mono       // Stats/numbers
```

### Spacing System
| Name | Value | Usage |
|------|-------|-------|
| `xxs` | 4pt | Minimal spacing |
| `xs` | 8pt | Compact elements |
| `sm` | 12pt | Small gaps |
| `md` | 16pt | Standard spacing |
| `lg` | 20pt | Section spacing |
| `xl` | 24pt | Large gaps |
| `xxl` | 32pt | Major sections |

---

## Component Library

### 1. OptimusAvatarView
**Purpose**: Animated hexagon avatar representing Optimus Prime
```swift
OptimusAvatarView(
    isListening: Bool,      // Shows audio rings when true
    audioLevel: CGFloat     // Controls ring animation (0-1)
)
```
**Features**:
- Rotating hexagon with gradient
- Lightning bolt icon
- Animated audio reaction rings
- 3D rotation effect

### 2. VoiceActivationButton
**Purpose**: Primary voice interaction trigger
```swift
VoiceActivationButton(
    isListening: Binding<Bool>,
    action: () -> Void
)
```
**States**:
- **Default**: Blue circle with mic icon
- **Listening**: Red circle with stop icon
- **Animation**: Scales up when active
- **Haptics**: Medium impact on tap

### 3. CouncilResponseView
**Purpose**: Displays Life Council consensus and member insights
```swift
CouncilResponseView(
    response: AssistantResponse
)
```
**Sections**:
- Confidence badge (color-coded)
- Main consensus text
- Council member cards (expandable)
- Action items (checkable)
- Follow-up suggestions

### 4. QuickActionsGrid
**Purpose**: Common command shortcuts
```swift
QuickActionsGrid(
    actions: [QuickAction],
    onTap: (String) -> Void
)
```
**Default Actions**:
| Icon | Label | Command |
|------|-------|---------|
| 📅 | Today's agenda | "What's on my schedule today?" |
| ➕ | Add task | "I need to add a new task" |
| ✉️ | Check messages | "Do I have any important messages?" |
| 🎯 | Focus mode | "Start a focus session" |

### 5. TranscriptCard
**Purpose**: Shows user's spoken text
```swift
TranscriptCard(
    transcript: String
)
```
**Features**:
- Auto-expanding for long text
- Timestamp display
- Copy to clipboard action

### 6. LoadingStateView
**Purpose**: Unified loading indicator
```swift
LoadingStateView(
    message: String,
    progress: Double?  // Optional progress bar
)
```

---

## API Integration

### Base Configuration
```swift
// Production
baseURL = "https://api.optimus.ai"

// Development
baseURL = "http://localhost:8003"
```

### Endpoints & Functions

#### 1. Mobile Summary
**Endpoint**: `GET /api/mobile/summary`
**Function**: `APIManager.fetchSummary()`
**Response**:
```json
{
  "greeting": "Good morning!",
  "weather": {
    "temp": "72°F",
    "condition": "Sunny",
    "icon": "☀️"
  },
  "next_event": {
    "id": "evt_123",
    "title": "Team Standup",
    "time": "9:00 AM",
    "type": "meeting"
  },
  "urgent_tasks": [...],
  "suggestions": [...],
  "stats": {
    "tasks_today": 5,
    "completed": 2,
    "meetings": 3,
    "focus_hours": 4
  }
}
```

#### 2. Voice Command Processing
**Endpoint**: `POST /api/mobile/voice`
**Function**: `APIManager.processVoiceCommand(_:)`
**Request**:
```json
{
  "transcript": "What's my day look like?",
  "device_info": {
    "model": "iPhone 15 Pro",
    "systemVersion": "17.2",
    "name": "John's iPhone"
  }
}
```
**Response**:
```json
{
  "intent": "schedule_query",
  "response": "You have 3 meetings today...",
  "actions": [
    {
      "type": "show_calendar",
      "data": {...}
    }
  ],
  "audio_response": true
}
```

#### 3. Assistant Query (Life Council)
**Endpoint**: `POST /api/assistant/ask`
**Function**: `APIManager.askAssistant(_:mode:)`
**Request**:
```json
{
  "query": "Should I reschedule my workout?",
  "mode": "AUTO",
  "require_voice": true,
  "device": "ios"
}
```
**Response**:
```json
{
  "answer": "Based on your energy levels...",
  "confidence": 0.87,
  "agents_consulted": [
    "health_guardian",
    "work_orchestrator"
  ],
  "actions": [...],
  "suggestions": [...],
  "voice_text": "Optimized for speech..."
}
```

#### 4. Quick Add
**Endpoint**: `POST /api/mobile/quick-add`
**Function**: `APIManager.quickAdd(_:)`
**Types**: task, event, note, reminder

#### 5. Today's Agenda
**Endpoint**: `GET /api/mobile/today`
**Function**: `APIManager.fetchTodayAgenda()`
**Response Structure**:
- Morning items
- Afternoon items
- Evening items
- Anytime tasks

---

## Button Actions & Functions

### Dashboard View Buttons

| Button | Location | Action | Function | API Call |
|--------|----------|--------|----------|----------|
| **Notification Bell** | Nav Bar Leading | Show notifications | `showNotifications()` | GET `/api/notifications` |
| **Profile** | Nav Bar Trailing | Show profile | `showProfile()` | GET `/api/user/profile` |
| **Refresh** | Pull to refresh | Reload dashboard | `viewModel.refresh()` | GET `/api/mobile/summary` |
| **Continue** | Hero Card | Resume task | `resumeTask(id:)` | POST `/api/tasks/{id}/resume` |
| **Quick Action** | Grid | Various commands | `performQuickAction(_:)` | Context-dependent |

### Voice Assistant View Buttons

| Button | Action | Function | Haptic | Visual Feedback |
|--------|--------|----------|--------|-----------------|
| **Voice Button** | Toggle listening | `toggleListening()` | Medium impact | Color change + scale |
| **Stop** | Stop listening | `stopListening()` | Light impact | Immediate stop |
| **Clear Session** | Reset conversation | `clearSession()` | Light impact | Fade animation |
| **Quick Command** | Execute preset | `handleQuickCommand(_:)` | Light impact | Background flash |

### Council Response Actions

| Button | Purpose | Function | State Management |
|--------|---------|----------|------------------|
| **Expand Member** | Show member details | `expandedMember = id` | Local state |
| **Check Action** | Mark complete | `completeAction(index:)` | Local + API |
| **Read More** | Expand text | `isExpanded.toggle()` | Local state |
| **Follow Suggestion** | Execute suggestion | `executeSuggestion(_:)` | Navigate/API |

### Settings View Actions

| Setting | Type | Function | Storage |
|---------|------|----------|---------|
| **Server URL** | Text Field | `updateServerURL(_:)` | UserDefaults |
| **Voice Settings** | Toggle | `toggleVoiceResponse()` | UserDefaults |
| **Notifications** | Multi-select | `updateNotificationPrefs(_:)` | UserDefaults + System |
| **Theme** | Segmented | `setTheme(_:)` | UserDefaults |

---

## Navigation Flow

### Tab Bar Structure
```
TabView (selectedTab)
├── 🏠 Home (0)
│   └── DashboardView
│       ├── Summary Card
│       ├── Stats Grid
│       ├── Next Event
│       └── Quick Actions
│
├── 📅 Agenda (1)
│   └── AgendaView
│       ├── Calendar
│       ├── Timeline
│       └── Event Details
│
├── 🎤 Optimus (2) [CENTER - PRIMARY]
│   └── VoiceAssistantView
│       ├── Avatar
│       ├── Voice Button
│       ├── Transcript
│       ├── Council Response
│       └── Quick Commands
│
├── ✅ Tasks (3)
│   └── TasksView
│       ├── Active Tasks
│       ├── Completed
│       └── Categories
│
└── ⚙️ Settings (4)
    └── SettingsView
        ├── Server Config
        ├── Personalization
        ├── Notifications
        └── About
```

### Navigation Patterns
1. **Tab Selection**: Direct navigation via tab bar
2. **Deep Links**: `optimus://voice`, `optimus://task/{id}`
3. **Push Navigation**: Detail views within tabs
4. **Modal Sheets**: Voice interface, add forms
5. **Alerts**: Errors, confirmations

---

## Data Flow

### Architecture Pattern: MVVM + Combine
```
View → ViewModel → Manager → API
  ↑                            ↓
  └──── @Published Properties ←┘
```

### State Management Hierarchy
```
App State (Global)
├── User Session
├── Server Configuration
├── Theme Settings
└── Navigation State

View Models (Screen-specific)
├── Dashboard: Summary, stats
├── Voice: Transcript, responses
├── Agenda: Events, calendar
└── Tasks: Lists, filters

Managers (Shared Services)
├── APIManager: Network state
├── VoiceManager: Audio state
├── NotificationManager: Push state
└── StorageManager: Cache state
```

### Data Update Flows

#### Voice Command Flow
```
1. User taps mic button
2. VoiceManager.startListening()
3. Speech → Text conversion
4. Display transcript
5. APIManager.processVoiceCommand()
6. Receive Council response
7. Update UI + Speak response
8. Store in history
```

#### Dashboard Refresh Flow
```
1. Pull to refresh / App launch
2. DashboardViewModel.loadSummary()
3. Parallel API calls:
   - Fetch summary
   - Fetch weather
   - Fetch events
   - Fetch tasks
4. Update @Published properties
5. SwiftUI redraws
6. Cache for offline
```

---

## Voice Integration

### Speech Framework Setup
```swift
import Speech
import AVFoundation

class VoiceManager {
    // Speech Recognition
    private let speechRecognizer = SFSpeechRecognizer()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()
    
    // Speech Synthesis
    private let synthesizer = AVSpeechSynthesizer()
}
```

### Voice Capabilities
| Feature | Implementation | Status |
|---------|---------------|--------|
| Speech-to-Text | Apple Speech Framework | ✅ Active |
| Text-to-Speech | AVSpeechSynthesizer | ✅ Active |
| Wake Word | "Hey Optimus" | 🔄 Planned |
| Continuous Listening | Background mode | 🔄 Planned |
| Voice Profiles | Speaker recognition | 🔄 Future |

### Voice Commands
```swift
// Recognized intents
enum VoiceIntent {
    case scheduleQuery      // "What's my day?"
    case addTask           // "Add task..."
    case setReminder       // "Remind me..."
    case focusMode         // "Start focus"
    case statusCheck       // "How am I doing?"
    case councilAdvice     // "Should I..."
}
```

---

## State Management

### Global App State
```swift
class AppState: ObservableObject {
    @Published var isAuthenticated = false
    @Published var user: User?
    @Published var serverURL = "http://localhost:8003"
    @Published var showVoiceInterface = false
    @Published var theme: Theme = .system
    @Published var selectedTab = 2  // Default to Voice
}
```

### View Model Pattern
```swift
class DashboardViewModel: ObservableObject {
    // Published properties trigger UI updates
    @Published var summary: MobileSummary?
    @Published var isLoading = false
    @Published var error: Error?
    
    // Private properties
    private var cancellables = Set<AnyCancellable>()
    private let apiManager = APIManager.shared
    
    // Public methods
    func loadSummary() async { ... }
    func refresh() async { ... }
}
```

### Error Handling
```swift
enum OptimusError: LocalizedError {
    case networkError(String)
    case authenticationFailed
    case voiceRecognitionFailed
    case apiError(Int, String)
    
    var errorDescription: String? {
        switch self {
        case .networkError(let message):
            return "Network Error: \(message)"
        case .authenticationFailed:
            return "Authentication failed. Please login again."
        case .voiceRecognitionFailed:
            return "Could not understand. Please try again."
        case .apiError(let code, let message):
            return "Error \(code): \(message)"
        }
    }
}
```

---

## Implementation Status

### ✅ Completed Features
- [x] Design System (colors, typography, spacing)
- [x] Voice Assistant View with Life Council
- [x] Council Response Component
- [x] API Manager with all endpoints
- [x] Voice Manager for speech services
- [x] Haptic feedback system
- [x] Loading state management
- [x] Error handling framework

### 🚧 In Progress
- [ ] Dashboard View implementation
- [ ] Agenda View with calendar
- [ ] Tasks View with categories
- [ ] Settings persistence
- [ ] Offline mode support

### 📋 Planned Features
- [ ] Widget Extension
- [ ] Siri Shortcuts
- [ ] Apple Watch App
- [ ] Live Activities
- [ ] Push Notifications
- [ ] Background Refresh
- [ ] CloudKit Sync
- [ ] SharePlay Support

### Known Issues
1. **Button Functionality**: Some quick action buttons need wiring
2. **Layout Polish**: Spacing inconsistencies on smaller devices
3. **Voice Recognition**: Needs permission handling
4. **API Error Recovery**: Implement retry logic
5. **Offline Cache**: Complete implementation

---

## Testing Strategy

### Unit Tests
```swift
// ViewModelTests
func testDashboardLoadsSummary()
func testVoiceProcessingFlow()
func testErrorHandling()

// ManagerTests
func testAPIEndpoints()
func testVoiceRecognition()
func testStoragePersistence()
```

### UI Tests
```swift
// Navigation
func testTabBarNavigation()
func testDeepLinkHandling()

// Voice Flow
func testVoiceCommandExecution()
func testCouncilResponseDisplay()

// Error States
func testNetworkErrorDisplay()
func testEmptyStates()
```

### Integration Tests
- API connection with backend
- Voice services availability
- Push notification delivery
- Widget data updates

---

## Performance Metrics

### Target Metrics
| Metric | Target | Current |
|--------|--------|---------|
| App Launch | < 1s | ~1.2s |
| API Response | < 500ms | ~400ms |
| Voice Recognition | < 2s | ~1.5s |
| Frame Rate | 60 FPS | 58 FPS |
| Memory Usage | < 100MB | ~85MB |
| Battery Impact | Low | Low |

### Optimization Strategies
1. **Lazy Loading**: Load views on demand
2. **Image Caching**: Cache avatar and icons
3. **API Caching**: Store recent responses
4. **Batch Updates**: Combine multiple state changes
5. **Background Processing**: Offload heavy tasks

---

## Security & Privacy

### Data Protection
- Keychain for sensitive data
- Encrypted CoreData
- Certificate pinning for API
- Biometric authentication option

### Privacy Features
- Microphone permission handling
- Location services (optional)
- Analytics opt-out
- Data deletion support

### Compliance
- GDPR compliant
- CCPA compliant
- App Tracking Transparency
- Privacy nutrition label

---

## Deployment

### Build Configuration
```yaml
Targets:
  - OptimusApp (iOS 17.0+)
  - OptimusWidgets (iOS 17.0+)
  - OptimusWatch (watchOS 10.0+)

Schemes:
  - Debug (localhost)
  - Staging (staging API)
  - Release (production API)

Code Signing:
  - Team: Your Team ID
  - Bundle ID: com.yourcompany.optimus
  - Provisioning: Automatic
```

### App Store Preparation
1. App icons (all sizes)
2. Screenshots (all devices)
3. App Store description
4. Privacy policy URL
5. Support URL
6. Marketing materials

---

## Resources & References

### Apple Documentation
- [SwiftUI Documentation](https://developer.apple.com/documentation/swiftui)
- [Speech Framework](https://developer.apple.com/documentation/speech)
- [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)

### Design Resources
- [SF Symbols](https://developer.apple.com/sf-symbols/)
- [Apple Design Resources](https://developer.apple.com/design/resources/)
- [Figma iOS Kit](https://www.figma.com/community/file/1248375255495415511)

### Project Links
- Backend API: `http://localhost:8003`
- Documentation: `/iOS/OPTIMUS_IOS_ARCHITECTURE.md`
- UX Plan: `/iOS/OPTIMUS_UX_IMPROVEMENT_PLAN.md`
- Vision Doc: `/docs/assistant/vision.md`

---

## Appendix: Quick Reference

### Common SwiftUI Modifiers
```swift
.padding()                    // Standard spacing
.cornerRadius(12)            // Rounded corners
.shadow(radius: 10)          // Drop shadow
.animation(.spring())        // Spring animation
.transition(.opacity)        // Fade transition
.sheet(isPresented:)         // Modal presentation
.alert(isPresented:)         // Alert dialog
.task { }                    // Async on appear
.refreshable { }             // Pull to refresh
.searchable(text:)           // Search bar
```

### Debugging Commands
```bash
# View network traffic
xcrun simctl launch --console booted com.yourcompany.optimus

# Reset simulator
xcrun simctl erase all

# Export app for testing
xcodebuild -exportArchive -archivePath ./build/OptimusApp.xcarchive

# Run UI tests
xcodebuild test -scheme OptimusApp -destination 'platform=iOS Simulator,name=iPhone 15'
```

---

*Last Updated: November 2024*
*Version: 1.0.0*
*Maintainer: Optimus Development Team*