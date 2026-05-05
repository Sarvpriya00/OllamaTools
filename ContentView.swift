import SwiftUI

struct ResearchResponse: Codable {
    let status: String
    let response: String
    let session_id: String
}

struct ContentView: View {
    @State private var objective: String = ""
    @State private var selectedModel: String = "gemma4:latest"
    @State private var statusMessage: String = "System Idle"
    @State private var isExecuting: Bool = False
    @State private var researchFiles: [URL] = []
    
    let models = ["gemma4:latest", "llama3:latest", "mistral:latest"]
    let projectPath = "/Users/sarvpriyaadarsh/ollama-agent" # Update if path changes
    
    var body: some View {
        NavigationSplitView {
            # Sidebar: Local Research Files
            List(researchFiles, id: \.self) { file in
                NavigationLink(file.lastPathComponent) {
                    ScrollView {
                        Text(try? String(contentsOf: file) ?? "Unable to read file")
                            .padding()
                            .font(.system(.body, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
            .navigationTitle("Archives")
            .listStyle(.sidebar)
            .toolbar {
                Button(action: refreshFiles) {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
            }
        } detail: {
            # Main Dashboard
            VStack(spacing: 0) {
                # Glassmorphic Header
                HStack {
                    Text("Sentry Research")
                        .font(.system(size: 24, weight: .bold, design: .rounded))
                    Spacer()
                    if isExecuting {
                        ProgressView()
                            .scaleEffect(0.8)
                            .shadow(color: .blue, radius: 10)
                    }
                }
                .padding()
                .background(.ultraThinMaterial)
                
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        # Input Section
                        VStack(alignment: .leading) {
                            Text("Research Objective")
                                .font(.headline)
                            TextField("e.g., Impact of Quantum Computing on Cryptography", text: $objective, axis: .vertical)
                                .textFieldStyle(.plain)
                                .padding()
                                .background(Color.primary.opacity(0.05))
                                .cornerRadius(12)
                                .lineLimit(3...10)
                        }
                        
                        # Configuration Section
                        HStack {
                            VStack(alignment: .leading) {
                                Text("Model Source")
                                    .font(.headline)
                                Picker("", selection: $selectedModel) {
                                    ForEach(models, id: \.self) { model in
                                        Text(model).tag(model)
                                    }
                                }
                                .pickerStyle(.menu)
                                .frame(width: 200)
                            }
                            Spacer()
                            
                            Button(action: triggerResearch) {
                                Text(isExecuting ? "Executing..." : "Start Research")
                                    .fontWeight(.semibold)
                                    .padding(.horizontal, 24)
                                    .padding(.vertical, 12)
                                    .background(isExecuting ? Color.gray : Color.blue)
                                    .foregroundColor(.white)
                                    .cornerRadius(12)
                            }
                            .buttonStyle(.plain)
                            .disabled(isExecuting || objective.isEmpty)
                        }
                        
                        Divider()
                        
                        # Console View
                        VStack(alignment: .leading) {
                            Text("Real-time Output")
                                .font(.headline)
                            Text(statusMessage)
                                .font(.system(.subheadline, design: .monospaced))
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.black.opacity(0.1))
                                .cornerRadius(8)
                        }
                    }
                    .padding()
                }
            }
            .frame(minWidth: 600, minHeight: 500)
            .background(Color(NSColor.windowBackgroundColor))
        }
        .onAppear {
            refreshFiles()
        }
    }
    
    # Refresh the list of .md files in the agent directory
    func refreshFiles() {
        let fileManager = FileManager.default
        let path = URL(fileURLWithPath: projectPath)
        
        do {
            let items = try fileManager.contentsOfDirectory(at: path, includingPropertiesForKeys: nil)
            researchFiles = items.filter { $0.pathExtension == "md" }.sorted { $0.lastPathComponent > $1.lastPathComponent }
        } catch {
            print("Error reading directory: \(error)")
        }
    }
    
    # Networking Call to api.py
    func triggerResearch() {
        guard let url = URL(string: "http://localhost:8000/chat") else { return }
        
        isExecuting = true
        statusMessage = "[Initiating] Objective sent to Python Bridge..."
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: String] = ["message": objective, "model": selectedModel]
        request.httpBody = try? JSONEncoder().encode(body)
        
        Task {
            do {
                let (data, _) = try await URLSession.shared.data(for: request)
                if let decoded = try? JSONDecoder().decode(ResearchResponse.self, from: data) {
                    DispatchQueue.main.async {
                        self.statusMessage = decoded.response
                        # Automatically refresh files
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                            self.refreshFiles()
                            self.isExecuting = false
                        }
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    self.statusMessage = "Network Error: Ensure api.py is running on port 8000."
                    self.isExecuting = false
                }
            }
        }
    }
}
