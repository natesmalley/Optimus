import SwiftUI
import Combine

// MARK: - Main App
@main
struct OptimusApp: App {
    @StateObject private var appState = AppState()
    
    init() {
        // Configure API Manager to use mock data when server is unavailable
        APIManager.shared.enableMockMode(true)
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
    }
}

// MARK: - App State
class AppState: ObservableObject {
    @Published var isAuthenticated = false
    @Published var showVoiceInterface = false
    @Published var selectedTab = 2
    @Published var serverURL = "http://localhost:8003"
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
        }
        .accentColor(.blue)
    }
}

// MARK: - Placeholder Views
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
    @AppStorage("serverURL") private var serverURL = "http://localhost:8003"
    @State private var showAlert = false
    @State private var alertMessage = ""
    
    var body: some View {
        NavigationView {
            Form {
                Section("Server Configuration") {
                    HStack {
                        Text("API Server")
                        Spacer()
                        Text(serverURL)
                            .foregroundColor(.secondary)
                            .font(.caption)
                    }
                    
                    Button("Test Connection") {
                        alertMessage = "Using mock data - server connection coming soon"
                        showAlert = true
                    }
                }
                
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                    HStack {
                        Text("Build")
                        Spacer()
                        Text("Phase 2")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Settings")
            .alert("Connection Status", isPresented: $showAlert) {
                Button("OK", role: .cancel) { }
            } message: {
                Text(alertMessage)
            }
        }
    }
}

// MARK: - Dashboard View
struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()
    @Binding var selectedTab: Int
    @State private var showAddTask = false
    @State private var showCouncilAlert = false
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Hero Card
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Welcome to Optimus")
                            .font(.largeTitle)
                            .fontWeight(.bold)
                        
                        Text("Your AI-powered life assistant")
                            .font(.title2)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
                    .background(
                        LinearGradient(colors: [.blue.opacity(0.2), .purple.opacity(0.2)],
                                     startPoint: .topLeading,
                                     endPoint: .bottomTrailing)
                    )
                    .cornerRadius(15)
                    
                    // Stats Grid  
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 15) {
                        StatCard(title: "Tasks Today", value: "8", icon: "checklist") {
                            // Navigate to Tasks tab
                            selectedTab = 3
                        }
                        StatCard(title: "Completed", value: "3", icon: "checkmark.circle.fill") {
                            // Navigate to Tasks tab
                            selectedTab = 3
                        }
                        StatCard(title: "Meetings", value: "2", icon: "person.3.fill") {
                            // Navigate to Agenda tab
                            selectedTab = 1
                        }
                        StatCard(title: "Focus Hours", value: "4", icon: "timer") {
                            // Show focus stats
                            selectedTab = 3
                        }
                    }
                    
                    // Quick Actions
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Quick Actions")
                            .font(.headline)
                        
                        HStack(spacing: 15) {
                            QuickActionButton(icon: "mic.fill", title: "Voice", color: .blue) {
                                // Navigate to Voice tab
                                selectedTab = 2
                            }
                            QuickActionButton(icon: "plus.circle.fill", title: "Add Task", color: .green) {
                                // Show add task sheet
                                showAddTask = true
                            }
                            QuickActionButton(icon: "calendar", title: "Schedule", color: .orange) {
                                // Navigate to Agenda tab
                                selectedTab = 1
                            }
                            QuickActionButton(icon: "person.3.fill", title: "Council", color: .purple) {
                                // Navigate to Voice tab for Council
                                selectedTab = 2
                                showCouncilAlert = true
                            }
                        }
                    }
                    
                    Spacer(minLength: 100)
                }
                .padding()
            }
            .navigationTitle("Optimus")
            .sheet(isPresented: $showAddTask) {
                AddTaskSheet()
            }
            .alert("Life Council", isPresented: $showCouncilAlert) {
                Button("Ask Council", role: .cancel) {
                    selectedTab = 2
                }
            } message: {
                Text("Navigate to Voice Assistant to consult with your Life Council")
            }
        }
    }
}

// MARK: - Add Task Sheet
struct AddTaskSheet: View {
    @Environment(\.dismiss) var dismiss
    @State private var taskTitle = ""
    @State private var taskPriority = 1
    
    var body: some View {
        NavigationView {
            Form {
                Section("Task Details") {
                    TextField("Task title", text: $taskTitle)
                    
                    Picker("Priority", selection: $taskPriority) {
                        Text("Low").tag(3)
                        Text("Medium").tag(2)
                        Text("High").tag(1)
                    }
                }
                
                Section {
                    Button("Add Task") {
                        // Add task logic here
                        dismiss()
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
        }
    }
}

// MARK: - Voice Assistant View
struct VoiceAssistantView: View {
    @State private var isListening = false
    @State private var transcript = ""
    @State private var response = ""
    @State private var showingQuickCommands = false
    @State private var councilConfidence: Double = 0.87
    
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
                    // Avatar
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
                    
                    // Status
                    Text(isListening ? "Listening..." : "Tap to speak")
                        .font(.headline)
                        .foregroundColor(.secondary)
                    
                    // Transcript
                    if !transcript.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("You said:")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Spacer()
                                Button("Clear") {
                                    withAnimation {
                                        transcript = ""
                                        response = ""
                                    }
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
                    
                    // Response
                    if !response.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("Life Council says:")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Spacer()
                                Text("\(Int(councilConfidence * 100))% confidence")
                                    .font(.caption)
                                    .foregroundColor(.green)
                            }
                            
                            Text(response)
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.blue.opacity(0.1))
                                .cornerRadius(10)
                            
                            // Council Members
                            HStack(spacing: 10) {
                                CouncilMember(name: "Magnus", color: .blue)
                                CouncilMember(name: "Harmony", color: .orange)
                                CouncilMember(name: "Vitalis", color: .green)
                                CouncilMember(name: "Sage", color: .purple)
                                CouncilMember(name: "Sentinel", color: .red)
                            }
                            .padding(.horizontal)
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
                        }
                    }
                    .padding(.horizontal)
                    
                    Spacer(minLength: 50)
                }
                .padding(.vertical)
            }
            .navigationTitle("Life Council")
            .navigationBarTitleDisplayMode(.large)
        }
    }
    
    private func toggleListening() {
        withAnimation {
            isListening.toggle()
        }
        
        if isListening {
            // Clear previous
            transcript = ""
            response = ""
            
            // Simulate listening
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                transcript = sampleQuestions.randomElement() ?? "What's my schedule?"
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
        // Generate appropriate response based on question
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            withAnimation {
                councilConfidence = Double.random(in: 0.75...0.95)
                
                if transcript.contains("schedule") {
                    response = "You have 3 meetings today: Team standup at 9 AM, client review at 2 PM, and planning session at 4 PM. I recommend using your 10-12 PM block for deep work on the project proposal."
                } else if transcript.contains("workout") {
                    response = "Based on your energy patterns and schedule, I suggest keeping your workout. You typically have higher productivity after morning exercise, and you have a 90-minute window before your first meeting."
                } else if transcript.contains("prioritize") {
                    response = "Focus on high-impact tasks first: 1) Complete project proposal (2 hours), 2) Review client feedback (30 min), 3) Prepare for tomorrow's presentation (1 hour). Save routine emails for your low-energy period after lunch."
                } else if transcript.contains("energy") {
                    response = "Your energy peaks at 10 AM and 3 PM. You're most creative in the morning and analytical in the afternoon. Schedule creative work before noon and data analysis after 2 PM for optimal performance."
                } else {
                    response = "Based on your current context, I recommend focusing on your most important task first. The Life Council suggests taking advantage of your peak energy hours for deep work."
                }
            }
        }
    }
}

// Council Member Badge
struct CouncilMember: View {
    let name: String
    let color: Color
    
    var body: some View {
        Text(String(name.prefix(1)))
            .font(.caption)
            .fontWeight(.bold)
            .foregroundColor(.white)
            .frame(width: 30, height: 30)
            .background(color)
            .clipShape(Circle())
    }
}

// MARK: - Components
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

// MARK: - View Models
class DashboardViewModel: ObservableObject {
    @Published var isLoading = false
    @Published var summary: MobileSummary?
    
    func loadSummary() async {
        // Load summary data
    }
    
    func refresh() async {
        await loadSummary()
    }
}

// MARK: - API Manager
class APIManager: ObservableObject {
    static let shared = APIManager()
    private var useMockData = false
    
    func enableMockMode(_ enabled: Bool = true) {
        self.useMockData = enabled
    }
    
    func fetchSummary() async throws -> MobileSummary {
        // Return mock data for now
        return MobileSummary(
            greeting: "Good morning!",
            weather: nil,
            nextEvent: nil,
            urgentTasks: [],
            suggestions: [],
            stats: ["tasks_today": 8, "completed": 3]
        )
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
    let id = UUID().uuidString
    let type: String
    let title: String
    let time: String?
    let priority: Int?
    
    init(type: String, title: String, time: String? = nil, priority: Int? = nil) {
        self.type = type
        self.title = title
        self.time = time
        self.priority = priority
    }
}

// MARK: - Voice Manager Placeholder
class VoiceManager {
    static let shared = VoiceManager()
    
    func requestPermissions() {
        // Request permissions
    }
}