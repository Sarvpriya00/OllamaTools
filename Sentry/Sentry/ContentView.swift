import SwiftUI

struct ChatMessage: Identifiable, Codable {
    var id = UUID()
    let role: String
    let content: String
}

struct ChatResponse: Codable {
    let status: String
    let response: String
    let session_id: String
}

struct ContentView: View {
    @State private var inputMessage: String = ""
    @State private var messages: [ChatMessage] = []
    @State private var selectedModel: String = "gemma4:latest"
    @State private var isExecuting: Bool = false
    @State private var researchFiles: [URL] = []
    @State private var scrollProxy: ScrollViewProxy? = nil
    
    let models = ["gemma4:latest", "llama3:latest", "mistral:latest"]
    let projectPath = "/Users/sarvpriyaadarsh/ollama-agent"
    
    var body: some View {
        NavigationSplitView {
            // Sidebar: System Archives
            List(researchFiles, id: \.self) { file in
                NavigationLink {
                    ScrollView {
                        Text((try? String(contentsOf: file)) ?? "Data Unreadable")
                            .padding()
                            .font(.system(.body, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                } label: {
                    Label(file.lastPathComponent, systemImage: "doc.text.fill")
                }
            }
            .navigationTitle("Archives")
            .listStyle(.sidebar)
            .toolbar {
                Button(action: refreshFiles) {
                    Image(systemName: "arrow.clockwise")
                }
            }
        } detail: {
            VStack(spacing: 0) {
                // Glassmorphic Header
                HStack {
                    VStack(alignment: .leading) {
                        Text("Sentry Agent")
                            .font(.system(size: 20, weight: .bold, design: .rounded))
                        Text(selectedModel)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    if isExecuting {
                        ProgressView()
                            .padding(.trailing, 8)
                    }
                    Menu {
                        ForEach(models, id: \.self) { model in
                            Button(model) { selectedModel = model }
                        }
                    } label: {
                        Image(systemName: "cpu")
                    }
                }
                .padding()
                .background(.ultraThinMaterial)
                
                // Chat Timeline
                ScrollViewReader { proxy in
                    ScrollView {
                        VStack(spacing: 20) {
                            if messages.isEmpty {
                                VStack(spacing: 12) {
                                    Image(systemName: "shield.fill")
                                        .font(.system(size: 40))
                                        .foregroundColor(.blue.opacity(0.5))
                                    Text("Autonomous System Ready")
                                        .font(.headline)
                                    Text("Command the agent to write code, research, or run system tasks.")
                                        .font(.subheadline)
                                        .foregroundColor(.secondary)
                                        .multilineTextAlignment(.center)
                                }
                                .padding(.top, 100)
                            }
                            
                            ForEach(messages) { msg in
                                ChatBubble(message: msg)
                            }
                        }
                        .padding()
                    }
                    .onAppear { self.scrollProxy = proxy }
                }
                
                // Input Matrix
                HStack(spacing: 12) {
                    TextField("Send command...", text: $inputMessage, axis: .vertical)
                        .textFieldStyle(.plain)
                        .padding(12)
                        .background(Color.primary.opacity(0.05))
                        .cornerRadius(12)
                        .lineLimit(1...5)
                        .onSubmit(sendMessage)
                    
                    Button(action: sendMessage) {
                        Image(systemName: isExecuting ? "stop.circle.fill" : "arrow.up.circle.fill")
                            .font(.system(size: 30))
                            .foregroundColor(isExecuting ? .red : .blue)
                    }
                    .buttonStyle(.plain)
                    .disabled(inputMessage.isEmpty && !isExecuting)
                }
                .padding()
                .background(.ultraThinMaterial)
            }
        }
        .onAppear(perform: refreshFiles)
    }
    
    func refreshFiles() {
        let path = URL(fileURLWithPath: projectPath)
        researchFiles = (try? FileManager.default.contentsOfDirectory(at: path, includingPropertiesForKeys: nil))?
            .filter { $0.pathExtension == "md" }
            .sorted { $0.lastPathComponent > $1.lastPathComponent } ?? []
    }
    
    func sendMessage() {
        guard !inputMessage.isEmpty else { return }
        let userMsg = ChatMessage(role: "user", content: inputMessage)
        messages.append(userMsg)
        let objective = inputMessage
        inputMessage = ""
        isExecuting = true
        
        // Network Payload
        guard let url = URL(string: "http://127.0.0.1:8000/chat") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: String] = [
            "message": objective,
            "model": selectedModel,
            "session_id": "main_session"
        ]
        request.httpBody = try? JSONEncoder().encode(body)
        
        Task {
            do {
                let (data, _) = try await URLSession.shared.data(for: request)
                if let decoded = try? JSONDecoder().decode(ChatResponse.self, from: data) {
                    DispatchQueue.main.async {
                        messages.append(ChatMessage(role: "assistant", content: decoded.response))
                        isExecuting = false
                        refreshFiles()
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    messages.append(ChatMessage(role: "system", content: "Error: Failed to connect to bridge."))
                    isExecuting = false
                }
            }
        }
    }
}

struct ChatBubble: View {
    let message: ChatMessage
    
    var body: some View {
        HStack {
            if message.role == "user" { Spacer() }
            
            VStack(alignment: message.role == "user" ? .trailing : .leading, spacing: 4) {
                Text(message.role.uppercased())
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.secondary)
                
                Text(message.content)
                    .padding(12)
                    .background(bubbleColor)
                    .foregroundColor(textColor)
                    .cornerRadius(16)
                    .frame(maxWidth: 500, alignment: message.role == "user" ? .trailing : .leading)
            }
            
            if message.role != "user" { Spacer() }
        }
    }
    
    var bubbleColor: Color {
        switch message.role {
        case "user": return .blue
        case "system": return .red.opacity(0.1)
        default: return Color.primary.opacity(0.05)
        }
    }
    
    var textColor: Color {
        message.role == "user" ? .white : .primary
    }
}

#Preview {
    ContentView()
}

#Preview {
    ContentView()
}
