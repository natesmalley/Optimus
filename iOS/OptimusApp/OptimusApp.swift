import SwiftUI
import Combine
import Foundation

// MARK: - Main App
@main
struct OptimusApp: App {
    @StateObject private var appState = AppState()
    
    init() {
        // Use REAL backend, not mock data
        APIManager.shared.enableMockMode(false)
        APIManager.shared.configure(baseURL: "http://localhost:8003")
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .onAppear {
                    // Test backend connection on launch
                    Task {
                        await APIManager.shared.testConnection()
                    }
                }
        }
    }
}

// MARK: - App State
class AppState: ObservableObject {
    @Published var isAuthenticated = false
    @Published var showVoiceInterface = false
    @Published var selectedTab = 2
    @Published var serverURL = "http://localhost:8003"
    @Published var isConnected = false
}

// MARK: - Content View
struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedTab = 2  // Start with Voice tab
    
    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView(selectedTab: $selectedTab)
                .tabItem {
                    Label("Home", systemImage: "house.fill")
                }
                .tag(0)
                .environmentObject(appState)
            
            AgendaView()
                .tabItem {
                    Label("Agenda", systemImage: "calendar")
                }
                .tag(1)
            
            VoiceAssistantView()
                .tabItem {
                    Label("Optimus", systemImage: "mic.circle.fill")
                }
                .tag(2)
                .environmentObject(appState)
            
            TasksView()
                .tabItem {
                    Label("Tasks", systemImage: "checklist")
                }
                .tag(3)
            
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(4)
                .environmentObject(appState)
        }
        .accentColor(.blue)
    }
}

// MARK: - Dashboard View
struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()
    @Binding var selectedTab: Int
    @State private var showAddTask = false
    @State private var showError = false
    @State private var errorMessage = ""
    
    var body: some View {
        NavigationView {
            ScrollView {
                if viewModel.isLoading {
                    ProgressView("Loading dashboard...")
                        .padding()
                } else {
                    VStack(spacing: 20) {
                        // Greeting Card with REAL data
                        if let summary = viewModel.summary {
                            GreetingCard(
                                greeting: summary.greeting,
                                weather: summary.weather
                            )
                        }
                        
                        // Stats Grid with REAL data
                        if let stats = viewModel.summary?.stats {
                            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 15) {
                                ForEach(Array(stats.keys.sorted()), id: \.self) { key in
                                    StatCard(
                                        title: formatTitle(key),
                                        value: "\(stats[key] ?? 0)",
                                        icon: iconForStat(key)
                                    ) {
                                        handleStatTap(key)
                                    }
                                }
                            }
                        }
                        
                        // Next Event from REAL backend
                        if let nextEvent = viewModel.summary?.nextEvent {
                            NextEventCard(event: nextEvent) {
                                // Real action for continuing event
                                selectedTab = 1 // Go to agenda
                            }
                        }
                        
                        // Urgent Tasks from REAL backend
                        if let tasks = viewModel.summary?.urgentTasks, !tasks.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Urgent Tasks")
                                    .font(.headline)
                                
                                ForEach(tasks, id: \.id) { task in
                                    TaskRow(task: task) {
                                        // Real task action
                                        print("Selected task: \(task.title)")
                                    }
                                }
                            }
                        }
                        
                        // AI Suggestions from REAL backend
                        if let suggestions = viewModel.summary?.suggestions, !suggestions.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("AI Suggestions")
                                    .font(.headline)
                                
                                ScrollView(.horizontal, showsIndicators: false) {
                                    HStack(spacing: 12) {
                                        ForEach(suggestions, id: \.id) { suggestion in
                                            SuggestionCard(suggestion: suggestion) {
                                                // Execute suggestion through backend
                                                Task {
                                                    await executeSuggestion(suggestion)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Quick Actions
                        QuickActionsSection(selectedTab: $selectedTab)
                        
                        Spacer(minLength: 100)
                    }
                    .padding()
                }
            }
            .navigationTitle("Optimus")
            .refreshable {
                await viewModel.refresh()
            }
            .onAppear {
                Task {
                    await viewModel.loadSummary()
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") { }
            } message: {
                Text(errorMessage)
            }
        }
    }
    
    private func formatTitle(_ key: String) -> String {
        key.replacingOccurrences(of: "_", with: " ").capitalized
    }
    
    private func iconForStat(_ key: String) -> String {
        switch key {
        case "tasks_today": return "checklist"
        case "completed": return "checkmark.circle.fill"
        case "meetings": return "person.3.fill"
        case "focus_hours": return "timer"
        default: return "circle"
        }
    }
    
    private func handleStatTap(_ key: String) {
        switch key {
        case "tasks_today", "completed":
            selectedTab = 3
        case "meetings":
            selectedTab = 1
        default:
            break
        }
    }
    
    private func executeSuggestion(_ suggestion: MobileAgendaItem) async {
        // Send suggestion to backend for execution
        do {
            let response = try await APIManager.shared.askAssistant(
                "Execute suggestion: \(suggestion.title)",
                mode: "AUTO"
            )
            print("Suggestion executed: \(response.answer)")
        } catch {
            errorMessage = "Failed to execute suggestion"
            showError = true
        }
    }
}

// MARK: - Voice Assistant View (REAL)
struct VoiceAssistantView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel = VoiceViewModel()
    @State private var isListening = false
    @State private var transcript = ""
    @State private var councilResponse: AssistantResponse?
    @State private var showError = false
    @State private var errorMessage = ""
    
    let sampleQuestions = [
        "What's my schedule for today?",
        "Should I reschedule my workout?", 
        "How should I prioritize my tasks?",
        "What's my energy level pattern?"
    ]
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 30) {
                    // Connection Status
                    HStack {
                        Circle()
                            .fill(appState.isConnected ? Color.green : Color.red)
                            .frame(width: 10, height: 10)
                        Text(appState.isConnected ? "Connected to Life Council" : "Offline Mode")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    
                    // Optimus Avatar
                    OptimusAvatar(isListening: isListening)
                    
                    // Voice Button
                    Button(action: toggleListening) {
                        ZStack {
                            Circle()
                                .fill(isListening ? Color.red : Color.blue)
                                .frame(width: 100, height: 100)
                            
                            Image(systemName: isListening ? "stop.fill" : "mic.fill")
                                .font(.system(size: 40))
                                .foregroundColor(.white)
                        }
                    }
                    .disabled(viewModel.isProcessing)
                    
                    // Status
                    if viewModel.isProcessing {
                        ProgressView("Consulting Life Council...")
                            .padding()
                    } else {
                        Text(isListening ? "Listening..." : "Tap to speak")
                            .font(.headline)
                            .foregroundColor(.secondary)
                    }
                    
                    // Transcript
                    if !transcript.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("You said:")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Spacer()
                                Button("Clear") {
                                    transcript = ""
                                    councilResponse = nil
                                }
                                .font(.caption)
                            }
                            
                            Text(transcript)
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.gray.opacity(0.1))
                                .cornerRadius(10)
                        }
                        .padding(.horizontal)
                    }
                    
                    // REAL Council Response
                    if let response = councilResponse {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Text("Life Council Response")
                                    .font(.headline)
                                Spacer()
                                Text("\(Int(response.confidence * 100))% confidence")
                                    .font(.caption)
                                    .foregroundColor(confidenceColor(response.confidence))
                            }
                            
                            Text(response.answer)
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.blue.opacity(0.1))
                                .cornerRadius(10)
                            
                            // Show which agents were consulted
                            if !response.agentsConsulted.isEmpty {
                                HStack {
                                    Text("Consulted:")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                    
                                    ForEach(response.agentsConsulted, id: \.self) { agent in
                                        Text(agent)
                                            .font(.caption)
                                            .padding(.horizontal, 8)
                                            .padding(.vertical, 2)
                                            .background(Color.purple.opacity(0.2))
                                            .cornerRadius(5)
                                    }
                                }
                            }
                            
                            // Show recommended actions
                            if !response.actions.isEmpty {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Recommended Actions:")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                    
                                    ForEach(response.actions, id: \.type) { action in
                                        HStack {
                                            Image(systemName: "checkmark.circle")
                                                .foregroundColor(.green)
                                            Text(action.type.replacingOccurrences(of: "_", with: " ").capitalized)
                                                .font(.subheadline)
                                        }
                                    }
                                }
                            }
                        }
                        .padding(.horizontal)
                    }
                    
                    // Sample Questions
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Try asking:")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        ForEach(sampleQuestions, id: \.self) { question in
                            Button(action: {
                                askQuestion(question)
                            }) {
                                HStack {
                                    Text(question)
                                        .font(.subheadline)
                                        .foregroundColor(.blue)
                                        .multilineTextAlignment(.leading)
                                    Spacer()
                                    Image(systemName: "arrow.right.circle")
                                        .foregroundColor(.blue.opacity(0.5))
                                }
                                .padding(.vertical, 8)
                                .padding(.horizontal, 12)
                                .background(Color.blue.opacity(0.05))
                                .cornerRadius(8)
                            }
                            .disabled(viewModel.isProcessing)
                        }
                    }
                    .padding(.horizontal)
                    
                    Spacer(minLength: 50)
                }
                .padding(.vertical)
            }
            .navigationTitle("Life Council")
            .alert("Error", isPresented: $showError) {
                Button("OK") { }
            } message: {
                Text(errorMessage)
            }
        }
    }
    
    private func toggleListening() {
        if isListening {
            isListening = false
            // In production: stop actual voice recognition
        } else {
            isListening = true
            transcript = ""
            councilResponse = nil
            
            // Simulate voice input for now (in production: use real speech recognition)
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                transcript = sampleQuestions.randomElement() ?? "What should I focus on?"
                isListening = false
                processTranscript()
            }
        }
    }
    
    private func askQuestion(_ question: String) {
        transcript = question
        processTranscript()
    }
    
    private func processTranscript() {
        Task {
            do {
                viewModel.isProcessing = true
                // REAL API call to Life Council
                let response = try await APIManager.shared.askAssistant(
                    transcript,
                    mode: "AUTO"
                )
                
                await MainActor.run {
                    councilResponse = response
                    viewModel.isProcessing = false
                }
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to reach Life Council: \(error.localizedDescription)"
                    showError = true
                    viewModel.isProcessing = false
                }
            }
        }
    }
    
    private func confidenceColor(_ confidence: Double) -> Color {
        if confidence >= 0.8 {
            return .green
        } else if confidence >= 0.6 {
            return .orange
        } else {
            return .red
        }
    }
}

// MARK: - API Manager (REAL)
class APIManager: ObservableObject {
    static let shared = APIManager()
    
    private var baseURL = "http://localhost:8003"
    private var useMockData = false
    private let session: URLSession
    
    init() {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 10
        self.session = URLSession(configuration: configuration)
    }
    
    func configure(baseURL: String) {
        self.baseURL = baseURL
    }
    
    func enableMockMode(_ enabled: Bool) {
        self.useMockData = enabled
    }
    
    func testConnection() async -> Bool {
        do {
            let url = URL(string: "\(baseURL)/api/mobile/summary")!
            let (_, response) = try await session.data(from: url)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            print("Connection test failed: \(error)")
            return false
        }
    }
    
    func fetchSummary() async throws -> MobileSummary {
        let url = URL(string: "\(baseURL)/api/mobile/summary")!
        let (data, _) = try await session.data(from: url)
        
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(MobileSummary.self, from: data)
    }
    
    func askAssistant(_ query: String, mode: String = "AUTO") async throws -> AssistantResponse {
        let url = URL(string: "\(baseURL)/api/assistant/ask")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody = AssistantRequest(
            query: query,
            mode: mode,
            requireVoice: false
        )
        
        request.httpBody = try JSONEncoder().encode(requestBody)
        
        let (data, _) = try await session.data(for: request)
        
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(AssistantResponse.self, from: data)
    }
    
    func quickAdd(_ item: QuickAddRequest) async throws -> QuickAddResponse {
        let url = URL(string: "\(baseURL)/api/mobile/quick-add")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        request.httpBody = try JSONEncoder().encode(item)
        
        let (data, _) = try await session.data(for: request)
        return try JSONDecoder().decode(QuickAddResponse.self, from: data)
    }
}

// MARK: - Models
struct MobileSummary: Codable {
    let greeting: String
    let weather: Weather?
    let nextEvent: MobileAgendaItem?
    let urgentTasks: [MobileAgendaItem]
    let suggestions: [MobileAgendaItem]
    let stats: [String: Int]
}

struct Weather: Codable {
    let temp: String
    let condition: String
    let icon: String
}

struct MobileAgendaItem: Codable, Identifiable {
    let id: String
    let type: String
    let title: String
    let time: String?
    let priority: Int?
    let energy: Int?
    let icon: String?
    let color: String?
}

struct AssistantRequest: Codable {
    let query: String
    let mode: String
    let requireVoice: Bool
    
    enum CodingKeys: String, CodingKey {
        case query, mode
        case requireVoice = "require_voice"
    }
}

struct AssistantResponse: Codable {
    let answer: String
    let confidence: Double
    let actions: [AssistantAction]
    let suggestions: [[String: String]]
    let queryType: String
    let modeUsed: String
    let agentsConsulted: [String]
    let riskFlags: [String]
    let audioUrl: String?
    let voiceText: String?
    
    enum CodingKeys: String, CodingKey {
        case answer, confidence, actions, suggestions
        case queryType = "query_type"
        case modeUsed = "mode_used"
        case agentsConsulted = "agents_consulted"
        case riskFlags = "risk_flags"
        case audioUrl = "audio_url"
        case voiceText = "voice_text"
    }
}

struct AssistantAction: Codable {
    let type: String
    let params: [String: String]
    let confidence: Double
    let requiresConfirmation: Bool
    
    enum CodingKeys: String, CodingKey {
        case type, params, confidence
        case requiresConfirmation = "requires_confirmation"
    }
}

struct QuickAddRequest: Codable {
    let type: String
    let content: String
    let priority: Int?
}

struct QuickAddResponse: Codable {
    let success: Bool
    let type: String
    let id: String
    let message: String
}

// MARK: - View Models
class DashboardViewModel: ObservableObject {
    @Published var summary: MobileSummary?
    @Published var isLoading = false
    @Published var error: Error?
    
    func loadSummary() async {
        await MainActor.run {
            isLoading = true
        }
        
        do {
            let summary = try await APIManager.shared.fetchSummary()
            await MainActor.run {
                self.summary = summary
                self.error = nil
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.error = error
                self.isLoading = false
                print("Failed to load summary: \(error)")
            }
        }
    }
    
    func refresh() async {
        await loadSummary()
    }
}

class VoiceViewModel: ObservableObject {
    @Published var isProcessing = false
    @Published var currentResponse: AssistantResponse?
    @Published var error: Error?
}

// MARK: - UI Components

struct GreetingCard: View {
    let greeting: String
    let weather: Weather?
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(greeting)
                .font(.title2)
                .fontWeight(.bold)
            
            if let weather = weather {
                HStack {
                    Text(weather.icon)
                    Text("\(weather.temp) - \(weather.condition)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(
            LinearGradient(colors: [.blue.opacity(0.2), .purple.opacity(0.2)],
                         startPoint: .topLeading,
                         endPoint: .bottomTrailing)
        )
        .cornerRadius(15)
    }
}

struct NextEventCard: View {
    let event: MobileAgendaItem
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Next Event")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(event.title)
                        .font(.headline)
                    if let time = event.time {
                        Text(time)
                            .font(.subheadline)
                            .foregroundColor(.blue)
                    }
                }
                Spacer()
                if let icon = event.icon {
                    Text(icon)
                        .font(.largeTitle)
                }
            }
            .padding()
            .background(Color.blue.opacity(0.1))
            .cornerRadius(10)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

struct TaskRow: View {
    let task: MobileAgendaItem
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack {
                if let icon = task.icon {
                    Text(icon)
                }
                Text(task.title)
                    .foregroundColor(.primary)
                Spacer()
                if let priority = task.priority {
                    Text("P\(priority)")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(priorityColor(priority))
                        .foregroundColor(.white)
                        .cornerRadius(5)
                }
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 12)
            .background(Color.gray.opacity(0.1))
            .cornerRadius(8)
        }
    }
    
    private func priorityColor(_ priority: Int) -> Color {
        switch priority {
        case 1: return .red
        case 2: return .orange
        default: return .blue
        }
    }
}

struct SuggestionCard: View {
    let suggestion: MobileAgendaItem
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading) {
                if let icon = suggestion.icon {
                    Text(icon)
                        .font(.title2)
                }
                Text(suggestion.title)
                    .font(.caption)
                    .foregroundColor(.primary)
                    .multilineTextAlignment(.leading)
            }
            .padding()
            .frame(width: 150)
            .background(Color.orange.opacity(0.1))
            .cornerRadius(10)
        }
    }
}

struct QuickActionsSection: View {
    @Binding var selectedTab: Int
    @State private var showAddTask = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Quick Actions")
                .font(.headline)
            
            HStack(spacing: 15) {
                QuickActionButton(icon: "mic.fill", title: "Voice", color: .blue) {
                    selectedTab = 2
                }
                QuickActionButton(icon: "plus.circle.fill", title: "Add Task", color: .green) {
                    showAddTask = true
                }
                QuickActionButton(icon: "calendar", title: "Schedule", color: .orange) {
                    selectedTab = 1
                }
                QuickActionButton(icon: "person.3.fill", title: "Council", color: .purple) {
                    selectedTab = 2
                }
            }
        }
        .sheet(isPresented: $showAddTask) {
            AddTaskSheet()
        }
    }
}

struct OptimusAvatar: View {
    let isListening: Bool
    
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 20)
                .fill(LinearGradient(colors: [.blue, .purple],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing))
                .frame(width: 150, height: 150)
            
            Image(systemName: "bolt.fill")
                .font(.system(size: 60))
                .foregroundColor(.white)
        }
        .scaleEffect(isListening ? 1.1 : 1.0)
        .animation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true), value: isListening)
    }
}

// Remaining views...
struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: icon)
                        .foregroundColor(.blue)
                    Spacer()
                }
                Text(value)
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.primary)
                Text(title)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.gray.opacity(0.1))
            .cornerRadius(10)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

struct QuickActionButton: View {
    let icon: String
    let title: String
    let color: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundColor(.white)
                Text(title)
                    .font(.caption)
                    .foregroundColor(.white)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 70)
            .background(color)
            .cornerRadius(10)
        }
    }
}

struct AddTaskSheet: View {
    @Environment(\.dismiss) var dismiss
    @State private var taskTitle = ""
    @State private var taskPriority = 2
    @State private var showError = false
    @State private var errorMessage = ""
    
    var body: some View {
        NavigationView {
            Form {
                Section("Task Details") {
                    TextField("Task title", text: $taskTitle)
                    
                    Picker("Priority", selection: $taskPriority) {
                        Text("High").tag(1)
                        Text("Medium").tag(2)
                        Text("Low").tag(3)
                    }
                }
                
                Section {
                    Button("Add Task") {
                        Task {
                            await addTask()
                        }
                    }
                    .disabled(taskTitle.isEmpty)
                }
            }
            .navigationTitle("New Task")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") { }
            } message: {
                Text(errorMessage)
            }
        }
    }
    
    private func addTask() async {
        do {
            let request = QuickAddRequest(
                type: "task",
                content: taskTitle,
                priority: taskPriority
            )
            
            let response = try await APIManager.shared.quickAdd(request)
            
            if response.success {
                await MainActor.run {
                    dismiss()
                }
            } else {
                await MainActor.run {
                    errorMessage = response.message
                    showError = true
                }
            }
        } catch {
            await MainActor.run {
                errorMessage = "Failed to add task: \(error.localizedDescription)"
                showError = true
            }
        }
    }
}

// Placeholder views
struct AgendaView: View {
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Image(systemName: "calendar")
                    .font(.system(size: 60))
                    .foregroundColor(.blue)
                Text("Your Schedule")
                    .font(.largeTitle)
                Text("Coming Soon")
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Agenda")
        }
    }
}

struct TasksView: View {
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Image(systemName: "checklist")
                    .font(.system(size: 60))
                    .foregroundColor(.green)
                Text("Your Tasks")
                    .font(.largeTitle)
                Text("Coming Soon")
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Tasks")
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @State private var showConnectionTest = false
    @State private var connectionMessage = ""
    
    var body: some View {
        NavigationView {
            Form {
                Section("Server Configuration") {
                    HStack {
                        Text("API Server")
                        Spacer()
                        Text(appState.serverURL)
                            .foregroundColor(.secondary)
                            .font(.caption)
                    }
                    
                    Button("Test Connection") {
                        Task {
                            await testConnection()
                        }
                    }
                }
                
                Section("Status") {
                    HStack {
                        Text("Connection")
                        Spacer()
                        Circle()
                            .fill(appState.isConnected ? Color.green : Color.red)
                            .frame(width: 10, height: 10)
                    }
                }
                
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
            .alert("Connection Test", isPresented: $showConnectionTest) {
                Button("OK") { }
            } message: {
                Text(connectionMessage)
            }
        }
    }
    
    private func testConnection() async {
        let connected = await APIManager.shared.testConnection()
        await MainActor.run {
            appState.isConnected = connected
            connectionMessage = connected ? "Successfully connected to Optimus backend!" : "Failed to connect. Check server is running."
            showConnectionTest = true
        }
    }
}