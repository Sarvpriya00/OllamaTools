import SwiftUI
import Combine

// ─────────────────────────────────────────────────────────────
// MARK: — Models
// ─────────────────────────────────────────────────────────────

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: String   // "user" | "assistant" | "system"
    let content: String
    let timestamp = Date()
}

struct ChatResponse: Codable {
    let status: String
    let response: String
    let session_id: String
}

// ─────────────────────────────────────────────────────────────
// MARK: — Design Tokens
// ─────────────────────────────────────────────────────────────

extension Color {
    static let sentryYellow  = Color(red: 1.0,  green: 0.84, blue: 0.0)
    static let sentryDark    = Color(red: 0.07, green: 0.07, blue: 0.09)
    static let sentryPanel   = Color(red: 0.11, green: 0.11, blue: 0.14)
    static let sentryBorder  = Color.white.opacity(0.08)
}

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
        modifier(LiquidGlass(cornerRadius: cornerRadius, intensity: intensity))
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Markdown Parser & Renderer
// ─────────────────────────────────────────────────────────────

private enum MDBlock {
    case heading(String, Int)
    case paragraph(String)
    case codeBlock(String, String)
    case divider
    case listItem(String)
    case image(String, String)   // alt, src (URL or absolute path)
    case blank
}

private func parseMarkdown(_ raw: String) -> [MDBlock] {
    var blocks: [MDBlock] = []
    let lines = raw.components(separatedBy: "\n")
    var i = 0
    while i < lines.count {
        let line = lines[i]
        let t = line.trimmingCharacters(in: .whitespaces)

        // Fenced code block
        if t.hasPrefix("```") {
            let lang = String(t.dropFirst(3)).trimmingCharacters(in: .whitespaces)
            var codeLines: [String] = []
            i += 1
            while i < lines.count && !lines[i].trimmingCharacters(in: .whitespaces).hasPrefix("```") {
                codeLines.append(lines[i]); i += 1
            }
            blocks.append(.codeBlock(codeLines.joined(separator: "\n"), lang))
            i += 1; continue
        }

        if t.hasPrefix("### ") { blocks.append(.heading(String(t.dropFirst(4)), 3)); i += 1; continue }
        if t.hasPrefix("## ")  { blocks.append(.heading(String(t.dropFirst(3)), 2)); i += 1; continue }
        if t.hasPrefix("# ")   { blocks.append(.heading(String(t.dropFirst(2)), 1)); i += 1; continue }

        if t == "---" || t == "***" || t == "___" { blocks.append(.divider); i += 1; continue }

        if t.hasPrefix("- ") || t.hasPrefix("* ") {
            blocks.append(.listItem(String(t.dropFirst(2)))); i += 1; continue
        }

        let orderedPattern = #"^\d+\.\s"#
        if t.range(of: orderedPattern, options: .regularExpression) != nil {
            if let spaceIdx = t.firstIndex(of: " ") {
                blocks.append(.listItem(String(t[t.index(after: spaceIdx)...])))
            }
            i += 1; continue
        }

        // Image: ![alt](src)
        if t.hasPrefix("![") && t.contains("](") {
            if let closeBracketRange = t.range(of: "]("),
               let closeParenIdx = t.lastIndex(of: ")") {
                let altStart = t.index(t.startIndex, offsetBy: 2)
                let altEnd   = closeBracketRange.lowerBound
                let srcStart = closeBracketRange.upperBound
                let srcEnd   = closeParenIdx
                if altStart <= altEnd, srcStart <= srcEnd {
                    let alt = String(t[altStart..<altEnd])
                    let src = String(t[srcStart..<srcEnd])
                    blocks.append(.image(alt, src))
                    i += 1; continue
                }
            }
        }

        if t.isEmpty { blocks.append(.blank); i += 1; continue }
        blocks.append(.paragraph(t))
        i += 1
    }
    return blocks
}

private func renderInline(_ text: String) -> AttributedString {
    let opts = AttributedString.MarkdownParsingOptions(
        interpretedSyntax: .inlineOnlyPreservingWhitespace
    )
    return (try? AttributedString(markdown: text, options: opts)) ?? AttributedString(text)
}

struct MarkdownView: View {
    let content: String
    private var blocks: [MDBlock] { parseMarkdown(content) }

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            ForEach(Array(blocks.enumerated()), id: \.offset) { idx, block in
                blockView(for: block)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .textSelection(.enabled)
    }

    @ViewBuilder
    private func blockView(for block: MDBlock) -> some View {
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
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundColor(.white.opacity(0.85))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
            }
            .background(
                ZStack {
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color.black.opacity(0.45))
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .strokeBorder(Color.sentryYellow.opacity(0.15), lineWidth: 1)
                }
            )
            .padding(.vertical, 4)

        case .divider:
            Rectangle()
                .fill(Color.white.opacity(0.12))
                .frame(height: 1)
                .padding(.vertical, 6)

        case .listItem(let text):
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

        case .image(let alt, let src):
            InlineImageView(alt: alt, src: src)

        case .blank:
            Color.clear.frame(height: 4)
        }
    }

    private func headingFont(_ level: Int) -> Font {
        switch level {
        case 1: return .system(size: 20, weight: .bold, design: .rounded)
        case 2: return .system(size: 16, weight: .bold, design: .rounded)
        default: return .system(size: 14, weight: .semibold)
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Inline Image View
// ─────────────────────────────────────────────────────────────

struct InlineImageView: View {
    let alt: String
    let src: String

    var isRemote: Bool { src.hasPrefix("http://") || src.hasPrefix("https://") }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if isRemote {
                AsyncImage(url: URL(string: src)) { phase in
                    switch phase {
                    case .success(let img):
                        img
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .frame(maxWidth: 480)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                            .overlay(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .strokeBorder(Color.sentryBorder, lineWidth: 1)
                            )
                    case .failure(let error):
                        VStack(spacing: 8) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.system(size: 20))
                                .foregroundColor(.orange.opacity(0.8))
                            Text("Image Failed to Load")
                                .font(.system(size: 12, weight: .bold))
                            Text(error.localizedDescription)
                                .font(.system(size: 10))
                                .foregroundColor(.white.opacity(0.4))
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 20)
                            
                            Text(src)
                                .font(.system(size: 8, design: .monospaced))
                                .foregroundColor(.sentryYellow.opacity(0.6))
                                .lineLimit(1)
                                .truncationMode(.middle)
                                .padding(.horizontal, 10)
                            
                            if let url = URL(string: src) {
                                Link("Open in Browser", destination: url)
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.sentryYellow)
                                    .padding(.top, 4)
                            }
                        }
                        .frame(maxWidth: 480, minHeight: 140)
                        .background(Color.white.opacity(0.03))
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .strokeBorder(Color.white.opacity(0.05), lineWidth: 1)
                        )
                    case .empty:
                        ZStack {
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .fill(Color.white.opacity(0.04))
                                .frame(maxWidth: 480, minHeight: 140)
                            ProgressView()
                                .tint(Color.sentryYellow)
                        }
                    @unknown default:
                        EmptyView()
                    }
                }
            } else {
                if let nsImg = NSImage(contentsOfFile: src) {
                    Image(nsImage: nsImg)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(maxWidth: 480)
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .strokeBorder(Color.sentryBorder, lineWidth: 1)
                        )
                } else {
                    imageErrorView(msg: "Local file not found: \(src)")
                }
            }
            
            if !alt.isEmpty {
                Text(alt)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.white.opacity(0.4))
                    .padding(.horizontal, 4)
            }
        }
        .padding(.vertical, 4)
    }

    private func imageErrorView(msg: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "photo")
                .foregroundColor(.white.opacity(0.3))
            Text(msg)
                .font(.system(size: 11))
                .foregroundColor(.white.opacity(0.3))
        }
        .padding(12)
        .background(Color.white.opacity(0.05))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

extension View {
    @ViewBuilder
    func `if`<Content: View>(_ condition: Bool, transform: (Self) -> Content) -> some View {
        if condition { transform(self) } else { self }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Content View
// ─────────────────────────────────────────────────────────────

struct ContentView: View {
    @State private var inputMessage: String = ""
    @State private var messages: [ChatMessage] = []
    @State private var selectedModel: String = "gemma4:latest"
    @State private var isExecuting: Bool = false
    @State private var researchFiles: [URL] = []

    let availableModels = [
        "gemma4:latest", "gemma3:latest", "llama3:latest",
        "llama3.1:latest", "mistral:latest", "qwen2.5:latest",
        "deepseek-r1:latest", "phi4:latest"
    ]
    let projectPath = "/Users/sarvpriyaadarsh/ollama-agent"

    var body: some View {
        ZStack {
            Color.sentryDark.ignoresSafeArea()
            RadialGradient(
                colors: [Color.sentryYellow.opacity(0.05), .clear],
                center: .topLeading, startRadius: 0, endRadius: 600
            ).ignoresSafeArea()

            NavigationSplitView {
                SidebarView(
                    files: researchFiles,
                    selectedModel: $selectedModel,
                    availableModels: availableModels,
                    onRefresh: refreshFiles,
                    onNewSession: newSession
                )
            } detail: {
                ChatDetailView(
                    messages: $messages,
                    inputMessage: $inputMessage,
                    isExecuting: $isExecuting,
                    onSend: sendMessage
                )
            }
        }
        .preferredColorScheme(.dark)
        .onAppear(perform: refreshFiles)
    }

    func refreshFiles() {
        let path = URL(fileURLWithPath: projectPath)
        researchFiles = (try? FileManager.default.contentsOfDirectory(
            at: path, includingPropertiesForKeys: nil))?
            .filter { ["md", "txt", "json"].contains($0.pathExtension) }
            .sorted { $0.lastPathComponent < $1.lastPathComponent } ?? []
    }

    func newSession() {
        messages = [ChatMessage(
            role: "assistant",
            content: "### New Session\n\nContext cleared. Sentry is ready."
        )]
    }

    func sendMessage() {
        let trimmed = inputMessage.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isExecuting else { return }
        messages.append(ChatMessage(role: "user", content: trimmed))
        inputMessage = ""
        isExecuting = true

        guard let url = URL(string: "http://127.0.0.1:8000/chat") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 300

        let body: [String: String] = [
            "message": trimmed,
            "model": selectedModel,
            "session_id": "main_session"
        ]
        request.httpBody = try? JSONEncoder().encode(body)

        Task {
            do {
                let (data, _) = try await URLSession.shared.data(for: request)
                if let decoded = try? JSONDecoder().decode(ChatResponse.self, from: data) {
                    await MainActor.run {
                        messages.append(ChatMessage(role: "assistant", content: decoded.response))
                        isExecuting = false
                        refreshFiles()
                    }
                }
            } catch {
                await MainActor.run {
                    messages.append(ChatMessage(
                        role: "system",
                        content: "⚠ **Connection Error**\n\nCould not reach the Sentry backend.\n\nRun: `uvicorn api:app --port 8000`"
                    ))
                    isExecuting = false
                }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Sidebar
// ─────────────────────────────────────────────────────────────

struct SidebarView: View {
    let files: [URL]
    @Binding var selectedModel: String
    let availableModels: [String]
    let onRefresh: () -> Void
    let onNewSession: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Brand
            HStack(spacing: 10) {
                ZStack {
                    Circle().fill(Color.sentryYellow).frame(width: 28, height: 28)
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(.black)
                }
                Text("Sentry")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }
            .padding(.horizontal, 16)
            .padding(.top, 16)
            .padding(.bottom, 12)

            // Model Picker
            VStack(alignment: .leading, spacing: 4) {
                Text("MODEL")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundColor(.white.opacity(0.35))
                    .padding(.horizontal, 16)

                Picker("", selection: $selectedModel) {
                    ForEach(availableModels, id: \.self) { Text($0).tag($0) }
                }
                .pickerStyle(.menu)
                .tint(Color.sentryYellow)
                .padding(.horizontal, 10)
            }
            .padding(.bottom, 12)

            Divider().background(Color.sentryBorder).padding(.horizontal, 12)

            // Files
            HStack {
                Text("FILES")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundColor(.white.opacity(0.35))
                Spacer()
                Button(action: onRefresh) {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 10))
                        .foregroundColor(.white.opacity(0.3))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 6)

            List(files, id: \.self) { file in
                NavigationLink {
                    FileDetailView(file: file)
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: fileIcon(file))
                            .font(.system(size: 11))
                            .foregroundColor(Color.sentryYellow.opacity(0.8))
                            .frame(width: 16)
                        Text(file.lastPathComponent)
                            .font(.system(size: 12))
                            .foregroundColor(.white.opacity(0.75))
                            .lineLimit(1)
                    }
                }
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)

            Spacer()

            // New Session
            Button(action: onNewSession) {
                Label("New Session", systemImage: "plus.circle")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(Color.sentryYellow)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .liquidGlass(cornerRadius: 10)
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 12)
            .padding(.bottom, 16)
        }
        .background(Color.sentryPanel.opacity(0.7))
    }

    private func fileIcon(_ url: URL) -> String {
        switch url.pathExtension {
        case "md": return "doc.richtext"
        case "json": return "curlybraces"
        default: return "doc.plaintext"
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — File Detail
// ─────────────────────────────────────────────────────────────

struct FileDetailView: View {
    let file: URL
    var body: some View {
        ScrollView {
            Text((try? String(contentsOf: file, encoding: .utf8)) ?? "Unable to read file.")
                .font(.system(size: 12, design: .monospaced))
                .foregroundColor(.white.opacity(0.8))
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .textSelection(.enabled)
        }
        .background(Color.sentryDark)
        .navigationTitle(file.lastPathComponent)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Chat Detail
// ─────────────────────────────────────────────────────────────

struct ChatDetailView: View {
    @Binding var messages: [ChatMessage]
    @Binding var inputMessage: String
    @Binding var isExecuting: Bool
    let onSend: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Top Bar
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Sentry Agent")
                        .font(.system(size: 15, weight: .semibold, design: .rounded))
                        .foregroundColor(.white)
                }
                Spacer()
                HStack(spacing: 6) {
                    Circle()
                        .fill(isExecuting ? Color.orange : Color.green)
                        .frame(width: 7, height: 7)
                    Text(isExecuting ? "Processing…" : "Ready")
                        .font(.system(size: 11, weight: .medium, design: .monospaced))
                        .foregroundColor(.white.opacity(0.45))
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .liquidGlass(cornerRadius: 20, intensity: 0.04)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 12)
            .background(Color.sentryDark.opacity(0.8))
            .overlay(Rectangle().fill(Color.sentryBorder).frame(height: 1), alignment: .bottom)

            // Messages
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 14) {
                        if messages.isEmpty {
                            EmptyStateView()
                        }
                        ForEach(messages) { msg in
                            ChatBubble(message: msg)
                                .id(msg.id)
                        }
                        if isExecuting {
                            ThinkingView()
                        }
                        Color.clear.frame(height: 1).id("bottom")
                    }
                    .padding(.horizontal, 18)
                    .padding(.vertical, 16)
                }
                .onChange(of: messages.count) {
                    withAnimation(.spring(response: 0.4)) {
                        proxy.scrollTo("bottom", anchor: .bottom)
                    }
                }
                .onChange(of: isExecuting) {
                    withAnimation(.spring(response: 0.4)) {
                        proxy.scrollTo("bottom", anchor: .bottom)
                    }
                }
            }

            // Input Bar
            InputBarView(
                inputMessage: $inputMessage,
                isExecuting: isExecuting,
                onSend: onSend
            )
        }
        .background(Color.sentryDark)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Chat Bubble (uses MarkdownView)
// ─────────────────────────────────────────────────────────────

struct ChatBubble: View {
    let message: ChatMessage

    var isUser: Bool { message.role == "user" }
    var isSystem: Bool { message.role == "system" }

    var bubbleFill: Color {
        if isUser   { return Color.sentryYellow.opacity(0.13) }
        if isSystem { return Color.orange.opacity(0.08) }
        return Color.white.opacity(0.04)
    }

    var roleLabel: String {
        if isUser   { return "You" }
        if isSystem { return "System" }
        return "Sentry"
    }

    var roleIcon: String {
        if isUser   { return "person.fill" }
        if isSystem { return "exclamationmark.triangle.fill" }
        return "bolt.fill"
    }

    var iconColor: Color {
        if isUser   { return .sentryYellow }
        if isSystem { return .orange }
        return .white
    }

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            ZStack {
                Circle()
                    .fill(isUser ? Color.sentryYellow.opacity(0.15) : Color.white.opacity(0.05))
                    .frame(width: 28, height: 28)
                Image(systemName: roleIcon)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(iconColor)
            }

            VStack(alignment: .leading, spacing: 5) {
                // Label row
                HStack(spacing: 8) {
                    Text(roleLabel)
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundColor(.white.opacity(0.35))
                    Text(message.timestamp, style: .time)
                        .font(.system(size: 10))
                        .foregroundColor(.white.opacity(0.18))
                }

                // ← MarkdownView renders the content
                MarkdownView(content: message.content)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 11)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        ZStack {
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .fill(bubbleFill)
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .strokeBorder(Color.sentryBorder, lineWidth: 1)
                        }
                    )
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Thinking Indicator
// ─────────────────────────────────────────────────────────────

struct ThinkingView: View {
    @State private var phase = 0
    let timer = Timer.publish(every: 0.35, on: .main, in: .common).autoconnect()

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                Circle().fill(Color.white.opacity(0.05)).frame(width: 28, height: 28)
                Image(systemName: "bolt.fill")
                    .font(.system(size: 11, weight: .semibold)).foregroundColor(.white)
            }
            HStack(spacing: 5) {
                ForEach(0..<3) { i in
                    Circle()
                        .fill(Color.sentryYellow)
                        .frame(width: 7, height: 7)
                        .scaleEffect(phase == i ? 1.5 : 0.8)
                        .animation(.spring(response: 0.3, dampingFraction: 0.5).delay(Double(i) * 0.1), value: phase)
                }
            }
            .padding(.horizontal, 14).padding(.vertical, 12)
            .liquidGlass(cornerRadius: 12, intensity: 0.04)
        }
        .onReceive(timer) { _ in phase = (phase + 1) % 3 }
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Empty State
// ─────────────────────────────────────────────────────────────

struct EmptyStateView: View {
    var body: some View {
        VStack(spacing: 14) {
            ZStack {
                Circle().fill(Color.sentryYellow.opacity(0.1)).frame(width: 64, height: 64)
                Image(systemName: "bolt.fill")
                    .font(.system(size: 28, weight: .semibold))
                    .foregroundColor(Color.sentryYellow.opacity(0.7))
            }
            Text("Sentry Agent Online")
                .font(.system(size: 17, weight: .bold, design: .rounded))
                .foregroundColor(.white.opacity(0.8))
            Text("14 composable tools loaded. Ask anything.")
                .font(.system(size: 13))
                .foregroundColor(.white.opacity(0.35))
        }
        .padding(.top, 80)
        .frame(maxWidth: .infinity)
    }
}

// ─────────────────────────────────────────────────────────────
// MARK: — Input Bar
// ─────────────────────────────────────────────────────────────

struct InputBarView: View {
    @Binding var inputMessage: String
    let isExecuting: Bool
    let onSend: () -> Void
    @FocusState private var isFocused: Bool

    var body: some View {
        HStack(spacing: 12) {
            TextField("Send command…", text: $inputMessage, axis: .vertical)
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
                                isFocused ? Color.sentryYellow.opacity(0.45) : Color.sentryBorder,
                                lineWidth: 1
                            )
                    }
                )
                .animation(.spring(response: 0.25), value: isFocused)
                .onSubmit { if !isExecuting { onSend() } }

            Button(action: onSend) {
                ZStack {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(
                            isExecuting || inputMessage.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            ? Color.white.opacity(0.08)
                            : Color.sentryYellow
                        )
                        .frame(width: 40, height: 40)
                    Image(systemName: "arrow.up")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(
                            isExecuting || inputMessage.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                            ? .white.opacity(0.25)
                            : .black
                        )
                }
            }
            .buttonStyle(.plain)
            .disabled(isExecuting || inputMessage.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .animation(.spring(response: 0.2, dampingFraction: 0.7), value: isExecuting)
            .keyboardShortcut(.return, modifiers: .command)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(
            Color.sentryDark.opacity(0.9)
                .overlay(Rectangle().fill(Color.sentryBorder).frame(height: 1), alignment: .top)
        )
        .onAppear { isFocused = true }
    }
}

#Preview {
    ContentView()
}
