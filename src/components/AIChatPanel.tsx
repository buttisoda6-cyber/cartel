import { useState, useRef, useEffect } from "react";
import { X, Send, Bot, User, Sparkles, Loader2, ChevronDown, ChevronUp, Database, ClipboardList, Sunrise } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { aiService, type SQLAgentResponse } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  sources?: string;
  timestamp: Date;
  title?: string;
  sqlResult?: SQLAgentResponse;
}

interface AIChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

type Mode = "chat" | "sql";

export function AIChatPanel({ isOpen, onClose }: AIChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSourcesFor, setShowSourcesFor] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("chat");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      fetchHistory();
    }
  }, [isOpen]);

  const fetchHistory = async () => {
    try {
      const data = await aiService.history(20);
      if (data && data.length > 0) {
        const history: Message[] = [];
        data.forEach((turn: any) => {
          history.push({
            id: `user-${turn.id}`,
            role: "user",
            content: turn.user_query,
            timestamp: new Date(turn.created_at),
          });
          history.push({
            id: `ai-${turn.id}`,
            role: "ai",
            content: turn.ai_response,
            timestamp: new Date(turn.created_at),
          });
        });
        setMessages(history);
      } else {
        setMessages([
          {
            id: "greeting",
            role: "ai",
            content:
              "Hello! I'm your AI Store Employee. I can answer grounded business questions, generate a morning brief, and run read-only SQL queries when you need structured reports.",
            timestamp: new Date(),
            title: "AI Store Employee",
          },
        ]);
      }
    } catch (error) {
      console.error("Failed to fetch history:", error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const pushUserMessage = (query: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
  };

  const pushAiMessage = (payload: Partial<Message> & Pick<Message, "content">) => {
    const aiMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: "ai",
      content: payload.content,
      title: payload.title,
      sources: payload.sources,
      sqlResult: payload.sqlResult,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, aiMsg]);
  };

  const handleSend = async (query: string = input) => {
    if (!query.trim()) return;

    pushUserMessage(query);
    setInput("");
    setIsLoading(true);

    try {
      if (mode === "sql") {
        const data = await aiService.sql(query);
        const rowCount = data.summary?.row_count ?? 0;
        const sourceLabel = data.source_db?.toUpperCase() || "DATA SOURCE";
        const content = data.error
          ? `**SQL Agent Error**\n\n${data.error}`
          : `**SQL Agent Result**\n\n${data.explanation || "Structured query completed."}\n\nReturned **${rowCount}** rows from **${sourceLabel}**.`;

        pushAiMessage({
          title: "SQL Agent",
          content,
          sqlResult: data,
        });
      } else {
        const data = await aiService.chat(query);
        pushAiMessage({
          title: data.intent ? `Intent: ${data.intent.replace(/_/g, " ")}` : undefined,
          content: data.answer || "Sorry, I couldn't generate a response.",
          sources: data.context_snapshot,
        });
      }
    } catch (error) {
      pushAiMessage({
        content:
          mode === "sql"
            ? "Network error connecting to the SQL agent."
            : "Network error connecting to the AI service.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const runBrief = async (briefType: "morning" | "end_of_day") => {
    setIsLoading(true);
    try {
      const data =
        briefType === "morning"
          ? await aiService.morningBrief()
          : await aiService.endOfDayBrief();

      pushAiMessage({
        title: data.title,
        content: data.answer,
        sources: data.context_snapshot,
      });
    } catch (error) {
      pushAiMessage({
        content: "Network error connecting to the briefing endpoint.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const quickPrompts =
    mode === "sql"
      ? [
          "Show products needing restock.",
          "Show dead stock.",
          "Show category performance.",
          "Show products with declining sales.",
        ]
      : [
          "What products should I reorder today?",
          "Which products are likely to go out of stock next week?",
          "Which items should be promoted?",
          "Compare this month with last month.",
        ];

  const placeholder =
    mode === "sql"
      ? "Ask for a report, like: show products needing restock"
      : "Ask about inventory, forecasts, or sales...";

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-background/40 backdrop-blur-sm z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      <div
        className={`fixed top-0 right-0 h-full w-full sm:w-[420px] md:w-[500px] bg-card border-l border-border shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-sidebar text-sidebar-foreground">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-semibold">AI Store Employee</h2>
              <p className="text-xs text-white/60">Grounded RAG + SQL Agent</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/60 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-4 pt-4">
          <div className="grid grid-cols-2 gap-2 rounded-2xl bg-muted p-1">
            <button
              onClick={() => setMode("chat")}
              className={`rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                mode === "chat" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setMode("sql")}
              className={`rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                mode === "sql" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"
              }`}
            >
              SQL Agent
            </button>
          </div>
        </div>

        <div className="px-4 pt-3 grid grid-cols-2 gap-2">
          <button
            onClick={() => runBrief("morning")}
            className="flex items-center justify-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-xs font-medium hover:bg-muted transition-colors"
          >
            <Sunrise className="w-3.5 h-3.5" />
            Morning Brief
          </button>
          <button
            onClick={() => runBrief("end_of_day")}
            className="flex items-center justify-center gap-2 rounded-xl border border-border bg-background px-3 py-2 text-xs font-medium hover:bg-muted transition-colors"
          >
            <ClipboardList className="w-3.5 h-3.5" />
            End-of-Day
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {mode === "sql" && (
            <div className="rounded-2xl border border-dashed border-border bg-background/60 p-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-2 text-foreground font-medium mb-1">
                <Database className="w-4 h-4" />
                SQL Agent mode
              </div>
              Ask for a structured report. The backend will generate a read-only SQL query, run it, and show you the result.
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} mb-4`}>
              <div className={`flex gap-3 max-w-[92%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                <div className="flex flex-col gap-1 w-full">
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground rounded-tr-sm"
                        : "bg-muted text-foreground border border-border rounded-tl-sm"
                    }`}
                  >
                    {msg.title && (
                      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        {msg.title}
                      </div>
                    )}
                    {msg.role === "user" ? (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <div className="text-sm prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    )}

                    {msg.sqlResult && (
                      <div className="mt-4 space-y-3">
                        <div className="rounded-xl bg-background border border-border p-3">
                          <div className="flex items-center justify-between gap-3 mb-2">
                            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                              <Database className="w-3.5 h-3.5" />
                              Generated SQL
                            </div>
                            <span className="text-[10px] text-muted-foreground">
                              {msg.sqlResult.source_db?.toUpperCase()}
                            </span>
                          </div>
                          <pre className="overflow-x-auto text-[11px] leading-relaxed text-muted-foreground whitespace-pre-wrap">
                            {msg.sqlResult.sql || "No SQL generated."}
                          </pre>
                        </div>

                        {msg.sqlResult.rows && msg.sqlResult.rows.length > 0 ? (
                          <div className="rounded-xl bg-background border border-border overflow-hidden">
                            <div className="px-3 py-2 border-b border-border text-xs font-semibold text-foreground flex items-center justify-between">
                              <span>Result Preview</span>
                              <span className="text-muted-foreground">
                                {msg.sqlResult.summary?.row_count ?? msg.sqlResult.rows.length} rows
                              </span>
                            </div>
                            <div className="overflow-x-auto max-h-64">
                              <table className="min-w-full text-xs">
                                <thead className="sticky top-0 bg-muted">
                                  <tr>
                                    {(msg.sqlResult.summary?.columns || Object.keys(msg.sqlResult.rows[0] || {})).map((col) => (
                                      <th key={col} className="text-left px-3 py-2 font-semibold text-foreground whitespace-nowrap">
                                        {col}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {msg.sqlResult.rows.slice(0, 5).map((row, idx) => (
                                    <tr key={idx} className="border-t border-border/60">
                                      {(msg.sqlResult.summary?.columns || Object.keys(row)).map((col) => (
                                        <td key={col} className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                                          {formatCell(row[col])}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        ) : (
                          <div className="rounded-xl bg-background border border-border p-3 text-xs text-muted-foreground">
                            {msg.sqlResult.error || "Query returned no rows."}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {msg.role === "ai" && msg.sources && (
                    <div className="mt-1">
                      <button
                        onClick={() => setShowSourcesFor(showSourcesFor === msg.id ? null : msg.id)}
                        className="text-xs text-muted-foreground flex items-center gap-1 hover:text-foreground transition-colors"
                      >
                        {showSourcesFor === msg.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        View sources
                      </button>
                      {showSourcesFor === msg.id && (
                        <div className="mt-2 p-3 bg-background border border-border rounded-lg text-xs font-mono text-muted-foreground max-h-40 overflow-y-auto whitespace-pre-wrap">
                          {msg.sources}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start mb-4">
              <div className="flex gap-3 max-w-[85%]">
                <div className="w-8 h-8 rounded-full bg-muted text-muted-foreground flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-muted text-foreground border border-border rounded-tl-sm flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    {mode === "sql" ? "Generating SQL report..." : "Analyzing store data..."}
                  </span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {(messages.length <= 1 || mode === "sql") && (
          <div className="px-4 pb-2">
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground mb-2">
              Example prompts
            </div>
            <div className="flex flex-wrap gap-2">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleSend(prompt)}
                  className="px-3 py-1.5 text-xs bg-muted hover:bg-muted/80 text-foreground border border-border rounded-full transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="p-4 border-t border-white/10 bg-card">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="relative flex items-center"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={placeholder}
              className="w-full bg-background border border-input rounded-full pl-5 pr-12 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-foreground placeholder:text-muted-foreground"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </>
  );
}

function formatCell(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (value instanceof Date) return value.toLocaleString();
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
