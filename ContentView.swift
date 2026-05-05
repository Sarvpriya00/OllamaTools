import SwiftUI

// ─────────────────────────────────────────────────────────────
// MARK: — Models
// ─────────────────────────────────────────────────────────────

enum MessageRole {
    case user, agent, tool
}

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: MessageRole
    let content: String
    let timestamp = Date()
}

struct ChatResponse: Codable {
    let status: String
    let response: String
    let session_id: String
}

// ─────────────────────────────────────────────────────────────
// MARK: — ViewModel
// ─────────────────────────────────────────────────────────────

@MainActor
class SentryViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var inputText: String = ""
    @Published var isThinking: Bool = false
    @Published var selectedModel: String = "gemma4:latest"
    @Published var sessionId: String = UUID().uuidString
    @Published var researchFiles: [URL] = []

    let availableModels = [
        "gemma4:latest", "gemma3:latest", "llama3:latest",
        "llama3.1:latest", "mistral:latest", "qwen2.5:latest",
        "deepseek-r1:latest", "phi4:latest"
    ]
    let projectPath = "/Users/sarvpriyaadarsh/ollama-agent"

    init() {
        messages.append(ChatMessage(
            role: .agent,
            content: "### Sentry Online\n\nHigh-performance agent ready. I have access to **14 composable tools** — file system, web research, YouTube analysis, caching, script generation, and orchestration.\n\nWhat are we building today?"
        ))
        refreshFiles()
    }

    func sendMessage() {
        let trimmed = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isThinking else { return }

        messages.append(ChatMessage(role: .user, content: trimmed))
        inputText = ""
        isThinking = true

        Task {
            do {
                let response = try await callAgent(message: trimmed)
                messages.append(ChatMessage(role: .agent, content: response))
                refreshFiles()
            } catch {
                messages.append(ChatMessage(
                    role: .tool,
                    content: "⚠ Network Error: \(error.localizedDescription)\n\nEnsure `uvicorn api:app --port 8000` is running."
                ))
            }
            isThinking = false
        }
    }

    private func callAgent(message: String) async throws -> String {
        guard let url = URL(string: "http://localhost:8000/chat") else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 300

        let body: [String: String] = [
            "message": message,
            "model": selectedModel,
            "session_id": sessionId
        ]
        request.httpBody = try JSONEncoder().encode(body)

        let (data, _) = try await URLSession.shared.data(for: request)
        let decoded = try JSONDecoder().decode(ChatResponse.self, from: data)
        return decoded.response
    }

    func refreshFiles() {
        let path = URL(fileURLWithPath: projectPath)
        let fm = FileManager.default
        if let items = try? fm.contentsOfDirectory(at: path, includingPropertiesForKeys: nil) {
            researchFiles = items
                .filter { ["md", "txt", "json"].contains($0.pathExtension) }
                .sorted { $0.lastPathComponent < $1.lastPathComponent }
        }
    }

    func clearSession() {
        sessionId = UUID().uuidString
        messages = [ChatMessage(
            role: .agent,
            content: "### New Session\n\nSentry reset. All context cleared. Ready."
        )]
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Design Tokens
// ─────────────────────────────────────────────────────────────

extension Color {
    static let sentryYellow   = Color(red: 1.0,  green: 0.84, blue: 0.0)   // #FFD700
    static let sentryDark     = Color(red: 0.07, green: 0.07, blue: 0.09)
    static let sentryPanel    = Color(red: 0.11, green: 0.11, blue: 0.14)
    static let sentryBorder   = Color.white.opacity(0.08)
    static let sentryUserBg   = Color.sentryYellow.opacity(0.15)
    static let sentryAgentBg  = Color.white.opacity(0.05)
    static let sentryToolBg   = Color.orange.opacity(0.08)
}

// ─────────────────────────────────────────────────────────────
// MARK: — Liquid Glass Modifier
// ─────────────────────────────────────────────────────────────

struct LiquidGlass: ViewModifier {
    var cornerRadius: CGFloat = 16
    var intensity: CGFloat = 0.06

    func body(content: Content) -> some View {
        content
            .background(
                ZStack {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .fill(.ultraThinMaterial)
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .fill(Color.white.opacity(intensity))
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .strokeBorder(Color.sentryBorder, lineWidth: 1)
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
    }
}

extension View {
    func liquidGlass(cornerRadius: CGFloat = 16, intensity: CGFloat = 0.06) -> some View {
        self.modifier(LiquidGlass(cornerRadius: cornerRadius, intensity: intensity))
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Content View (Root)
// ─────────────────────────────────────────────────────────────

struct ContentView: View {
    @StateObject private var vm = SentryViewModel()
    @State private var showSidebar: Bool = true

    var body: some View {
        ZStack {
            // Dark base
            Color.sentryDark.ignoresSafeArea()

            // Subtle radial glow
            RadialGradient(
                colors: [Color.sentryYellow.opacity(0.06), .clear],
                center: .topLeading,
                startRadius: 0,
                endRadius: 600
            )
            .ignoresSafeArea()

            HStack(spacing: 0) {
                // Sidebar
                if showSidebar {
                    SidebarView(vm: vm)
                        .frame(width: 240)
                        .transition(.move(edge: .leading).combined(with: .opacity))
                }

                // Main Chat
                ChatView(vm: vm, showSidebar: $showSidebar)
            }
        }
        .frame(minWidth: 820, minHeight: 560)
        .preferredColorScheme(.dark)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Sidebar
// ─────────────────────────────────────────────────────────────

struct SidebarView: View {
    @ObservedObject var vm: SentryViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {

            // Brand Header
            HStack(spacing: 10) {
                ZStack {
                    Circle()
                        .fill(Color.sentryYellow)
                        .frame(width: 32, height: 32)
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.black)
                }
                Text("Sentry")
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }
            .padding(.horizontal, 16)
            .padding(.top, 20)
            .padding(.bottom, 16)

            // Model Picker
            VStack(alignment: .leading, spacing: 6) {
                Label("Model", systemImage: "cpu")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.white.opacity(0.4))
                    .padding(.horizontal, 16)

                Picker("", selection: $vm.selectedModel) {
                    ForEach(vm.availableModels, id: \.self) { m in
                        Text(m).tag(m)
                    }
                }
                .pickerStyle(.menu)
                .tint(Color.sentryYellow)
                .padding(.horizontal, 12)
            }
            .padding(.bottom, 12)

            Divider().background(Color.sentryBorder).padding(.horizontal, 12)

            // Files Section
            HStack {
                Label("Files", systemImage: "doc.text")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.white.opacity(0.4))
                Spacer()
                Button(action: vm.refreshFiles) {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.4))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 6)

            ScrollView {
                LazyVStack(spacing: 2) {
                    ForEach(vm.researchFiles, id: \.self) { file in
                        FileCardRow(file: file)
                    }
                    if vm.researchFiles.isEmpty {
                        Text("No files yet")
                            .font(.system(size: 12))
                            .foregroundColor(.white.opacity(0.25))
                            .padding(.top, 20)
                            .frame(maxWidth: .infinity)
                    }
                }
                .padding(.horizontal, 10)
            }

            Spacer()

            // New Session Button
            Button(action: vm.clearSession) {
                Label("New Session", systemImage: "plus.circle")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(Color.sentryYellow)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .liquidGlass(cornerRadius: 10)
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 12)
            .padding(.bottom, 16)
        }
        .background(Color.sentryPanel.opacity(0.6))
        .overlay(
            Rectangle()
                .fill(Color.sentryBorder)
                .frame(width: 1),
            alignment: .trailing
        )
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — File Card Row
// ─────────────────────────────────────────────────────────────

struct FileCardRow: View {
    let file: URL
    @State private var isHovered = false

    var icon: String {
        switch file.pathExtension {
        case "md":   return "doc.richtext"
        case "json": return "curlybraces"
        case "txt":  return "doc.plaintext"
        default:     return "doc"
        }
    }

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 12))
                .foregroundColor(Color.sentryYellow.opacity(0.8))
                .frame(width: 20)

            Text(file.lastPathComponent)
                .font(.system(size: 12))
                .foregroundColor(.white.opacity(0.75))
                .lineLimit(1)
                .truncationMode(.middle)

            Spacer()

            Button(action: { NSWorkspace.shared.activateFileViewerSelecting([file]) }) {
                Image(systemName: "arrow.forward.circle")
                    .font(.system(size: 11))
                    .foregroundColor(.white.opacity(0.3))
            }
            .buttonStyle(.plain)
            .opacity(isHovered ? 1 : 0)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(isHovered ? Color.white.opacity(0.05) : .clear)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .onHover { isHovered = $0 }
        .animation(.spring(response: 0.2, dampingFraction: 0.8), value: isHovered)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Chat View
// ─────────────────────────────────────────────────────────────

struct ChatView: View {
    @ObservedObject var vm: SentryViewModel
    @Binding var showSidebar: Bool
    @Namespace private var bottomAnchor

    var body: some View {
        VStack(spacing: 0) {

            // Top Bar
            HStack(spacing: 12) {
                Button(action: { withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) { showSidebar.toggle() }}) {
                    Image(systemName: showSidebar ? "sidebar.left" : "sidebar.left")
                        .font(.system(size: 16))
                        .foregroundColor(.white.opacity(0.5))
                }
                .buttonStyle(.plain)

                Spacer()

                // Status pill
                HStack(spacing: 6) {
                    Circle()
                        .fill(vm.isThinking ? Color.orange : Color.green)
                        .frame(width: 7, height: 7)
                        .animation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true), value: vm.isThinking)

                    Text(vm.isThinking ? "Processing…" : "Ready")
                        .font(.system(size: 12, weight: .medium, design: .monospaced))
                        .foregroundColor(.white.opacity(0.5))
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 5)
                .liquidGlass(cornerRadius: 20, intensity: 0.04)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.sentryDark.opacity(0.5))
            .overlay(Rectangle().fill(Color.sentryBorder).frame(height: 1), alignment: .bottom)

            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(vm.messages) { msg in
                            MessageBubble(message: msg)
                                .transition(.asymmetric(
                                    insertion: .move(edge: .bottom).combined(with: .opacity),
                                    removal: .opacity
                                ))
                        }

                        if vm.isThinking {
                            ThinkingIndicator()
                                .transition(.move(edge: .bottom).combined(with: .opacity))
                        }

                        Color.clear.frame(height: 1).id("bottom")
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
                .onChange(of: vm.messages.count) { _ in
                    withAnimation(.spring(response: 0.4)) {
                        proxy.scrollTo("bottom", anchor: .bottom)
                    }
                }
                .onChange(of: vm.isThinking) { _ in
                    withAnimation(.spring(response: 0.4)) {
                        proxy.scrollTo("bottom", anchor: .bottom)
                    }
                }
            }

            // Input Bar
            InputBar(vm: vm)
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Markdown Renderer
// ─────────────────────────────────────────────────────────────

// Block types emitted by the parser
private enum MDBlock {
    case heading(String, Int)    // text, level 1-3
    case paragraph(String)
    case codeBlock(String, String) // code, language
    case divider
    case listItem(String, Int)   // text, indent level
    case blank
}

/// Parses a Markdown string into an ordered list of `MDBlock` values.
private func parseMarkdown(_ raw: String) -> [MDBlock] {
    var blocks: [MDBlock] = []
    var lines = raw.components(separatedBy: "\n")
    var i = 0

    while i < lines.count {
        let line = lines[i]
        let trimmed = line.trimmingCharacters(in: .whitespaces)

        // Fenced code block
        if trimmed.hasPrefix("```") {
            let lang = String(trimmed.dropFirst(3)).trimmingCharacters(in: .whitespaces)
            var codeLines: [String] = []
            i += 1
            while i < lines.count && !lines[i].trimmingCharacters(in: .whitespaces).hasPrefix("```") {
                codeLines.append(lines[i])
                i += 1
            }
            blocks.append(.codeBlock(codeLines.joined(separator: "\n"), lang))
            i += 1
            continue
        }

        // Headings
        if trimmed.hasPrefix("### ") { blocks.append(.heading(String(trimmed.dropFirst(4)), 3)); i += 1; continue }
        if trimmed.hasPrefix("## ")  { blocks.append(.heading(String(trimmed.dropFirst(3)), 2)); i += 1; continue }
        if trimmed.hasPrefix("# ")   { blocks.append(.heading(String(trimmed.dropFirst(2)), 1)); i += 1; continue }

        // Divider
        if trimmed == "---" || trimmed == "***" || trimmed == "___" { blocks.append(.divider); i += 1; continue }

        // Unordered list
        if trimmed.hasPrefix("- ") || trimmed.hasPrefix("* ") {
            let text = String(trimmed.dropFirst(2))
            blocks.append(.listItem(text, 0))
            i += 1; continue
        }
        // Ordered list  e.g. "1. " "2. "
        let orderedPattern = #"^\d+\.\s"#
        if let _ = trimmed.range(of: orderedPattern, options: .regularExpression) {
            if let spaceIdx = trimmed.firstIndex(of: " ") {
                let text = String(trimmed[trimmed.index(after: spaceIdx)...])
                blocks.append(.listItem(text, 0))
            }
            i += 1; continue
        }

        // Blank line
        if trimmed.isEmpty { blocks.append(.blank); i += 1; continue }

        // Paragraph
        blocks.append(.paragraph(trimmed))
        i += 1
    }
    return blocks
}

/// Converts inline Markdown (**bold**, *italic*, `code`) to AttributedString.
private func renderInline(_ text: String) -> AttributedString {
    // Use built-in markdown parsing for inline styles
    let opts = AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace)
    if let attributed = try? AttributedString(markdown: text, options: opts) {
        return attributed
    }
    return AttributedString(text)
}

/// Full block-level Markdown renderer.
struct MarkdownView: View {
    let content: String

    private var blocks: [MDBlock] { parseMarkdown(content) }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(Array(blocks.enumerated()), id: \.offset) { idx, block in
                blockView(for: block, index: idx)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .textSelection(.enabled)
    }

    @ViewBuilder
    private func blockView(for block: MDBlock, index: Int) -> some View {
        switch block {

        case .heading(let text, let level):
            Text(renderInline(text))
                .font(headingFont(level))
                .foregroundColor(level == 3 ? Color.sentryYellow : .white)
                .padding(.top, level <= 2 ? 8 : 4)
                .padding(.bottom, 2)

        case .paragraph(let text):
            Text(renderInline(text))
                .font(.system(size: 13.5))
                .foregroundColor(.white.opacity(0.88))
                .fixedSize(horizontal: false, vertical: true)

        case .codeBlock(let code, let lang):
            VStack(alignment: .leading, spacing: 0) {
                if !lang.isEmpty {
                    Text(lang)
                        .font(.system(size: 10, weight: .semibold, design: .monospaced))
                        .foregroundColor(Color.sentryYellow.opacity(0.7))
                        .padding(.horizontal, 12)
                        .padding(.top, 8)
                }
                Text(code)
                    .font(.system(size: 12.5, design: .monospaced))
                    .foregroundColor(.white.opacity(0.85))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
            .background(
                ZStack {
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color.black.opacity(0.4))
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .strokeBorder(Color.sentryYellow.opacity(0.15), lineWidth: 1)
                }
            )
            .padding(.vertical, 4)

        case .divider:
            Rectangle()
                .fill(Color.white.opacity(0.1))
                .frame(height: 1)
                .padding(.vertical, 6)

        case .listItem(let text, _):
            HStack(alignment: .top, spacing: 8) {
                Circle()
                    .fill(Color.sentryYellow.opacity(0.7))
                    .frame(width: 5, height: 5)
                    .padding(.top, 6)
                Text(renderInline(text))
                    .font(.system(size: 13.5))
                    .foregroundColor(.white.opacity(0.88))
                    .fixedSize(horizontal: false, vertical: true)
            }

        case .blank:
            Color.clear.frame(height: 4)
        }
    }

    private func headingFont(_ level: Int) -> Font {
        switch level {
        case 1: return .system(size: 20, weight: .bold,  design: .rounded)
        case 2: return .system(size: 16, weight: .bold,  design: .rounded)
        default: return .system(size: 14, weight: .semibold)
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Message Bubble
// ─────────────────────────────────────────────────────────────

struct MessageBubble: View {
    let message: ChatMessage
    @State private var isHovered = false

    var bubbleColor: Color {
        switch message.role {
        case .user:  return Color.sentryUserBg
        case .agent: return Color.sentryAgentBg
        case .tool:  return Color.sentryToolBg
        }
    }

    var roleIcon: String {
        switch message.role {
        case .user:  return "person.fill"
        case .agent: return "bolt.fill"
        case .tool:  return "wrench.and.screwdriver.fill"
        }
    }

    var roleColor: Color {
        switch message.role {
        case .user:  return Color.sentryYellow
        case .agent: return .white
        case .tool:  return .orange
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            ZStack {
                Circle()
                    .fill(message.role == .user ? Color.sentryYellow.opacity(0.2) : Color.white.opacity(0.05))
                    .frame(width: 30, height: 30)
                Image(systemName: roleIcon)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(roleColor)
            }

            VStack(alignment: .leading, spacing: 6) {
                // Role label + timestamp
                HStack(spacing: 8) {
                    Text(message.role == .user ? "You" : message.role == .tool ? "System" : "Sentry")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(.white.opacity(0.4))
                    Text(message.timestamp, style: .time)
                        .font(.system(size: 10))
                        .foregroundColor(.white.opacity(0.2))
                }

                // Message content — rendered as Markdown
                MarkdownView(content: message.content)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        ZStack {
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .fill(bubbleColor)
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .strokeBorder(Color.sentryBorder, lineWidth: 1)
                        }
                    )
            }
        }
        .padding(.horizontal, 4)
        .scaleEffect(isHovered ? 1.002 : 1.0)
        .onHover { isHovered = $0 }
        .animation(.spring(response: 0.25, dampingFraction: 0.7), value: isHovered)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Thinking Indicator
// ─────────────────────────────────────────────────────────────

struct ThinkingIndicator: View {
    @State private var phase: Int = 0

    let timer = Timer.publish(every: 0.35, on: .main, in: .common).autoconnect()

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                Circle()
                    .fill(Color.white.opacity(0.05))
                    .frame(width: 30, height: 30)
                Image(systemName: "bolt.fill")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.white)
            }

            HStack(spacing: 5) {
                ForEach(0..<3) { i in
                    Circle()
                        .fill(Color.sentryYellow)
                        .frame(width: 7, height: 7)
                        .scaleEffect(phase == i ? 1.4 : 0.8)
                        .animation(
                            .spring(response: 0.3, dampingFraction: 0.5).delay(Double(i) * 0.1),
                            value: phase
                        )
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .liquidGlass(cornerRadius: 12, intensity: 0.04)
        }
        .padding(.horizontal, 4)
        .onReceive(timer) { _ in
            phase = (phase + 1) % 3
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Input Bar
// ─────────────────────────────────────────────────────────────

struct InputBar: View {
    @ObservedObject var vm: SentryViewModel
    @FocusState private var isFocused: Bool

    var body: some View {
        HStack(spacing: 12) {
            // Text field
            TextField("Ask Sentry anything…", text: $vm.inputText, axis: .vertical)
                .font(.system(size: 14))
                .foregroundColor(.white)
                .lineLimit(1...6)
                .focused($isFocused)
                .textFieldStyle(.plain)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    ZStack {
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(Color.white.opacity(0.04))
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .strokeBorder(
                                isFocused ? Color.sentryYellow.opacity(0.5) : Color.sentryBorder,
                                lineWidth: 1
                            )
                    }
                )
                .animation(.spring(response: 0.25), value: isFocused)
                .onSubmit {
                    if !vm.isThinking { vm.sendMessage() }
                }

            // Send button
            Button(action: vm.sendMessage) {
                ZStack {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(vm.isThinking || vm.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                              ? Color.white.opacity(0.1)
                              : Color.sentryYellow)
                        .frame(width: 42, height: 42)

                    Image(systemName: "arrow.up")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(
                            vm.isThinking || vm.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            ? .white.opacity(0.3)
                            : .black
                        )
                }
            }
            .buttonStyle(.plain)
            .disabled(vm.isThinking || vm.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .animation(.spring(response: 0.2, dampingFraction: 0.7), value: vm.isThinking)
            .keyboardShortcut(.return, modifiers: .command)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(
            Color.sentryDark.opacity(0.8)
                .overlay(Rectangle().fill(Color.sentryBorder).frame(height: 1), alignment: .top)
        )
        .onAppear { isFocused = true }
    }
}
