
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Activity, Bot, Brain, Check, CheckCircle2, Copy, Cpu,
  FileText, Folder, FolderOpen, HardDrive, MessageSquare, Monitor,
  Plus, RefreshCw, Send, Settings, ShieldCheck, Trash2,
  Wifi, WifiOff, X, Pencil, Sparkles, PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

const API = "http://127.0.0.1:8000";

declare global {
  interface Window {
    pywebview?: {
      api?: {
        select_folder: () => Promise<{ path: string } | null>;
        get_authorized_folders: () => Promise<string[]>;
        revoke_folder: (path: string) => Promise<unknown>;
      };
    };
  }
}

type Message = {
  id?: number;
  role: "user" | "assistant";
  content: string;
  proposals?: Proposal[];
  provider?: string;
};

type Conversation = {
  id: number;
  title: string;
  updated_at: string;
  message_count: number;
};

type Proposal = {
  id: number;
  action: string;
  arguments: Record<string, unknown>;
  status: string;
  summary?: string;
};

type Memory = {
  id: number;
  category: string;
  content: string;
};

type FileItem = {
  name: string;
  type: "file" | "folder";
  size?: number | null;
};

type SystemInfo = {
  computer: string;
  operating_system: string;
  processor: string;
  cpu_cores: number;
  cpu_usage: number;
  ram_total_gb: number;
  ram_used_gb: number;
  ram_percent: number;
  disk_total_gb: number;
  disk_free_gb: number;
};

type HealthResponse = { status: string };
type MemoryResponse = { items: Memory[] };
type FileResponse = { items: FileItem[]; workspace?: string; current_path?: string };
type ChatResponse = { answer: string; provider: string; user_message_id: number; assistant_message_id: number };
type PlanResponse = { summary?: string; proposals?: Proposal[]; user_message_id: number; assistant_message_id: number; provider: string };
type ActionResponse = { result: Record<string, unknown> };

const actionNames: Record<string, string> = {
  list_files: "Consultar arquivos",
  read_file: "Ler arquivo",
  create_file: "Criar arquivo",
  create_folder: "Criar pasta",
  edit_file: "Editar arquivo",
  move_file: "Mover arquivo",
  delete_file: "Enviar para a Lixeira",
  download_file: "Baixar arquivo",
  run_command: "Executar comando",
  search_apps: "Pesquisar aplicativos",
  install_app: "Instalar aplicativo",
};

const styles = {
  app: {
    height: "100vh",
    width: "100%",
    display: "flex",
    overflow: "hidden",
    background: "#0b0d12",
    color: "#ececf1",
    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
  } as React.CSSProperties,
  sidebar: {
    width: 270,
    minWidth: 270,
    background: "#101116",
    borderRight: "1px solid #262830",
    display: "flex",
    flexDirection: "column",
    padding: 14,
    gap: 12,
  } as React.CSSProperties,
  main: {
    flex: 1,
    minWidth: 0,
    display: "flex",
    flexDirection: "column",
    position: "relative",
  } as React.CSSProperties,
  secondary: {
    background: "#15171e",
    border: "1px solid #292c36",
    borderRadius: 12,
    padding: 16,
  } as React.CSSProperties,
  button: {
    border: 0,
    borderRadius: 9,
    padding: "10px 13px",
    color: "#f5f5f7",
    background: "#282a34",
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    fontSize: 13,
    fontWeight: 600,
  } as React.CSSProperties,
  input: {
    width: "100%",
    boxSizing: "border-box",
    background: "#202127",
    border: "1px solid #393b46",
    borderRadius: 13,
    padding: "14px 15px",
    color: "#fff",
    outline: "none",
    font: "inherit",
  } as React.CSSProperties,
  muted: {
    color: "#9295a1",
    fontSize: 12,
  } as React.CSSProperties,
};

function actionResultMessage(action: string, result: Record<string, unknown>): string {
  const path = typeof result.path === "string" ? result.path : "o destino autorizado";

  if (action === "search_apps") {
    const apps = Array.isArray(result.apps) ? result.apps : [];
    if (apps.length === 0) return "Nenhum aplicativo encontrado.";

    const visibleApps = apps.slice(0, 15);
    const lines = visibleApps.map((item) => {
      const app = item as Record<string, unknown>;
      return `- ${String(app.name || "Aplicativo")}\n  ID: ${String(app.id || "Não informado")}\n  Versão: ${String(app.version || "Não informada")}`;
    });

    const hidden = apps.length - visibleApps.length;
    const suffix = hidden > 0 ? `\n\n... e mais ${hidden} aplicativo(s) não exibido(s).` : "";
    return `Pesquisa concluída: ${String(result.count ?? apps.length)} resultado(s).\n\n${lines.join("\n\n")}${suffix}`;
  }

  if (action === "install_app") {
    return typeof result.message === "string"
      ? result.message
      : `Instalação concluída: ${String(result.package_id || "pacote")}.`;
  }

  if (action === "create_file") return `Arquivo criado com sucesso em ${path}.`;
  if (action === "edit_file") return `Arquivo atualizado com sucesso em ${path}.`;
  if (action === "create_folder") return `Pasta criada com sucesso em ${path}.`;
  if (action === "download_file") return `Download concluído em ${path}.`;
  if (action === "delete_file") return "Item enviado para a Lixeira com sucesso.";
  if (action === "move_file") return `Item movido para ${String(result.destination || "o destino solicitado")}.`;
  if (action === "run_command") return result.return_code === 0 ? "Comando autorizado executado com sucesso." : `O comando terminou com código ${String(result.return_code)}. ${String(result.stderr || "Verifique a mensagem de erro.")}`;
  if (action === "read_file") return `Arquivo lido com sucesso: ${path}.`;
  if (action === "list_files") return `Consulta concluída: ${Array.isArray(result.items) ? result.items.length : 0} itens encontrados.`;
  return "Ação concluída com sucesso.";
}

function App() {
  const profile = "principal";
  const [provider, setProvider] = useState("hybrid");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [online, setOnline] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [page, setPage] = useState<"chat" | "files" | "memory" | "settings">("chat");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [workspace, setWorkspace] = useState("");
  const [currentFolder, setCurrentFolder] = useState("");
  const [folderRoot, setFolderRoot] = useState("");
  const [folderLoading, setFolderLoading] = useState(false);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [memoryCategory, setMemoryCategory] = useState("Preferência");
  const [memoryContent, setMemoryContent] = useState("");
  const [notice, setNotice] = useState("");
  const [busyAction, setBusyAction] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingText, setEditingText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const api = useCallback(async <T = unknown,>(path: string, options: RequestInit = {}): Promise<T> => {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", "X-Profile": profile, ...(options.headers || {}) },
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({})) as { detail?: string };
      throw new Error(data.detail || `Erro ${response.status}`);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  }, []);

  async function loadConversations() {
    const data = await api<{ items: Conversation[] }>("/api/conversations");
    setConversations(data.items || []);
  }

  async function loadConversation(id: number) {
    setActiveId(id);
    setPage("chat");

    try {
      const data = await api<{ items: Message[] }>(`/api/conversations/${id}`);
      const loaded = data.items || [];
      const pending = await api<{ items: Proposal[] }>(`/api/agent/pending?conversation_id=${id}`);
      const grouped = new Map<number, Proposal[]>();
      (pending.items || []).forEach((proposal) => {
        const source = (proposal as Proposal & { source_message_id?: number }).source_message_id;
        const target = source ? loaded.findIndex((item) => item.id === source) : loaded.length - 1;
        const index = Math.max(0, target >= 0 && loaded[target + 1]?.role === "assistant" ? target + 1 : target);
        grouped.set(index, [...(grouped.get(index) || []), proposal]);
      });
      setMessages(loaded.map((message, index) => ({ ...message, proposals: grouped.get(index) || [] })));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Erro ao abrir conversa.");
    }
  }

  const loadData = useCallback(async () => {
    try {
      const [health, conversationData, memoryData, fileData, systemData] =
        await Promise.all([
          api<HealthResponse>("/api/health"),
          api<{ items: Conversation[] }>("/api/conversations"),
          api<MemoryResponse>("/api/memories"),
          api<FileResponse>(`/api/files?path=${encodeURIComponent(currentFolder || ".")}`),
          api<SystemInfo>("/api/system"),
        ]);

      setOnline(health.status === "online");
      setConversations(conversationData.items || []);
      setMemories(memoryData.items || []);
      setFiles(fileData.items || []);
      setWorkspace(fileData.workspace || "");
      if (!currentFolder) {
        setCurrentFolder(fileData.workspace || "");
        setFolderRoot(fileData.workspace || "");
      }
      setSystem(systemData);
      setNotice("");
    } catch (error) {
      setOnline(false);
      setNotice(error instanceof Error ? error.message : "Backend desconectado.");
    }
  }, [api, currentFolder]);

  async function loadFolder(path: string) {
    if (!path) return;

    setFolderLoading(true);

    try {
      const data = await api<FileResponse>(
        `/api/files?path=${encodeURIComponent(path)}`
      );

      setFiles(data.items || []);
      setCurrentFolder(data.current_path || path);
      setNotice("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Não foi possível abrir a pasta.");
    } finally {
      setFolderLoading(false);
    }
  }

  async function chooseFolder() {
    try {
      const bridge = window.pywebview?.api;

      if (!bridge) {
        setNotice("O seletor de pastas está disponível ao abrir a NOVA pelo aplicativo desktop.");
        return;
      }

      const selected = await bridge.select_folder();

      if (selected?.path) {
        setFolderRoot(selected.path);
        await loadFolder(selected.path);
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Não foi possível selecionar a pasta.");
    }
  }

  async function returnToFolderRoot() {
    if (folderRoot) {
      await loadFolder(folderRoot);
    }
  }

  async function returnToWorkspace() {
    setFolderRoot(workspace);
    await loadFolder(workspace);
  }

  useEffect(() => {
    loadData();
    const timer = window.setInterval(loadData, 12000);
    return () => window.clearInterval(timer);
  }, [profile, currentFolder, loadData]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function newConversation() {
    try {
      const data = await api<{ id: number; title: string }>("/api/conversations", {
        method: "POST",
        body: JSON.stringify({ title: "Nova conversa" }),
      });

      setActiveId(data.id);
      setMessages([]);
      setPage("chat");
      await loadConversations();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Não foi possível criar a conversa.");
    }
  }

  async function deleteConversation(id: number) {
    try {
      await api(`/api/conversations/${id}`, { method: "DELETE" });
      setConversations((current) => current.filter((item) => item.id !== id));

      if (activeId === id) {
        setActiveId(null);
        setMessages([]);
      }

      setDeleteId(null);
      await loadConversations();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Erro ao excluir conversa.");
    }
  }

  async function renameConversation(id: number) {
    if (!renameValue.trim()) return;

    try {
      await api(`/api/conversations/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ title: renameValue.trim() }),
      });
      setRenamingId(null);
      await loadConversations();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Erro ao renomear conversa.");
    }
  }

  function isComputerFileTask(text: string): boolean {
  const normalized = text.trim().toLocaleLowerCase("pt-BR");

  if (/^(como|qual|quais|por que|porque|o que|me explica|me ensina|explique|ensine|gostaria de saber|pode me explicar)\b/.test(normalized)) {
    return false;
  }

  const appAction = /\b(pesquise|pesquisar|procure|buscar|busque|instale|instalar|desinstale|desinstalar|confirmo|autorizo|confirmar|autorizada|prossiga)\b/.test(normalized);
  const appTarget =
    /\b(aplicativo|aplicativos|programa|programas|software|firefox|steam|chrome|vlc|discord|winget|[a-z0-9_-]+\.[a-z0-9._+-]+)\b/.test(normalized)
    || /\b(?:pesquise|pesquisar|procure|buscar|busque|instale|instalar|desinstale|desinstalar)\s+(?:(?:o|a|um|uma|do|da|de|dos|das)\s+)*(?!para\b|por\b|no\b|na\b|me\b|mim\b|meu\b|minha\b)[a-z0-9][a-z0-9._+-]*/.test(normalized);

  if (appAction && appTarget) {
    return true;
  }

  const action = /\b(crie|criar|cria|edite|editar|edita|altere|alterar|modifique|modificar|salve|salvar|exclua|excluir|apague|apagar|delete|deletar|renomeie|renomear|mova|mover|transfira|transferir|copie|copiar|baixe|baixar|download|organize|organizar|liste|listar|abra|abrir|leia|ler)\b/.test(normalized);

  const target = /\b(arquivo|arquivos|pasta|pastas|diret?rio|diretorio|documento|documentos|texto|txt|pdf|docx|xlsx|csv|imagem|imagens|foto|fotos|planilha|relat?rio|relatorio|c?digo|codigo|projeto|download)\b/.test(normalized)
    || /\b[\w.-]+\.(txt|pdf|docx|xlsx|csv|json|html|css|js|ts|tsx|py|zip|png|jpg)\b/i.test(normalized)
    || /https?:\/\//i.test(normalized);

  return action && target;
}

async function sendMessage(event?: FormEvent) {
    event?.preventDefault();
    const text = chatInput.trim();
    if (!text || loading) return;

  if (isComputerFileTask(text)) {
    await sendAgentTask(event);
    return;
  }

    let conversationId = activeId;

    try {
      if (!conversationId) {
        const created = await api<{ id: number }>("/api/conversations", {
          method: "POST",
          body: JSON.stringify({ title: text.slice(0, 55) }),
        });
        conversationId = created.id;
        setActiveId(conversationId);
      }

      const userMessage: Message = { role: "user", content: text };
      const updated = [...messages, userMessage];
      setMessages(updated);
      setChatInput("");
      setLoading(true);

      if (page === "chat") {
        const data = await api<ChatResponse>("/api/chat", {
          method: "POST",
          body: JSON.stringify({
            message: text,
            history: updated.slice(-13, -1),
            provider,
            conversation_id: conversationId,
          }),
        });

        setMessages((current) => [
          ...current.slice(0, -1),
          { ...current[current.length - 1], id: data.user_message_id },
          {
            role: "assistant",
            content: data.answer,
            provider: data.provider,
            id: data.assistant_message_id,
          },
        ]);
      }

      await loadConversations();
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: error instanceof Error ? error.message : "Não foi possível processar a mensagem.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function sendAgentTask(event?: FormEvent) {
    event?.preventDefault();
    const text = chatInput.trim();
    if (!text || loading) return;

    let conversationId = activeId;

    try {
      if (!conversationId) {
        const created = await api<{ id: number }>("/api/conversations", {
          method: "POST",
          body: JSON.stringify({ title: text.slice(0, 55) }),
        });
        conversationId = created.id;
        setActiveId(conversationId);
      }

      setMessages((current) => [...current, { role: "user", content: text }]);
      setChatInput("");
      setLoading(true);

      const data = await api<PlanResponse>("/api/agent/plan", {
        method: "POST",
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
          current_folder: currentFolder || workspace,
          provider,
        }),
      });

      setMessages((current) => [
        ...current.slice(0, -1),
        { ...current[current.length - 1], id: data.user_message_id },
        {
          role: "assistant",
          content: data.summary || "Plano preparado.",
          proposals: data.proposals || [],
          id: data.assistant_message_id,
          provider: data.provider,
        },
      ]);

      await loadConversations();
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: error instanceof Error ? error.message : "Erro ao planejar tarefa.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function approveAction(proposal: Proposal) {
    setBusyAction(proposal.id);

    try {
      const result = await api<ActionResponse>(`/api/agent/execute/${proposal.id}`, {
        method: "POST",
        body: JSON.stringify({ confirm: true }),
      });

      setMessages((current): Message[] => [
  ...current.map((message) => ({
    ...message,
    proposals: message.proposals?.filter((item) => item.id !== proposal.id),
  })),
  {
    role: "assistant",
    content: `Ação concluída: ${actionNames[proposal.action] || proposal.action}\n\nResultado:\n${actionResultMessage(proposal.action, result.result)}`,
  },
]);

      setNotice("Ação executada com sucesso.");
      await loadData();
    } catch (error) {
      setMessages((current) => [
        ...current.map((message) => ({ ...message, proposals: message.proposals?.filter((item) => item.id !== proposal.id) })),
        { role: "assistant", content: `A ação falhou e não foi concluída. ${error instanceof Error ? error.message : "Prepare uma nova proposta."}` },
      ]);
      setNotice(error instanceof Error ? error.message : "Erro ao executar ação.");
    } finally {
      setBusyAction(null);
    }
  }

  async function cancelAction(proposal: Proposal) {
    try {
      await api(`/api/agent/cancel/${proposal.id}`, { method: "POST" });
      setMessages((current): Message[] => [
  ...current.map((message) => ({
    ...message,
    proposals: message.proposals?.filter((item) => item.id !== proposal.id),
  })),
  {
    role: "assistant",
    content: "Ação recusada. Nenhuma alteração foi realizada por essa solicitação.",
  },
]);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Erro ao recusar ação.");
    }
  }

  async function saveEditedMessage(message: Message) {
    if (message.id == null || activeId == null || !editingText.trim()) return;
    setLoading(true);
    try {
      await api(`/api/conversations/${activeId}/edit`, {
        method: "POST",
        body: JSON.stringify({ message_id: message.id, content: editingText.trim(), provider }),
      });
      setEditingIndex(null);
      setEditingText("");
      await loadConversation(activeId);
      await loadConversations();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Não foi possível reenviar a mensagem. A conversa foi preservada.");
    } finally {
      setLoading(false);
    }
  }

  async function addMemory(event: FormEvent) {
    event.preventDefault();
    if (!memoryContent.trim()) return;

    try {
      await api("/api/memories", {
        method: "POST",
        body: JSON.stringify({ category: memoryCategory, content: memoryContent }),
      });
      setMemoryContent("");
      await loadData();
      setNotice("Memória salva.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Erro ao salvar memória.");
    }
  }

  async function removeMemory(id: number) {
    try {
      await api(`/api/memories/${id}`, { method: "DELETE" });
      await loadData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Erro ao apagar memória.");
    }
  }

  function formatBytes(size?: number | null) {
    if (size == null) return "—";
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  const submit = page === "chat" ? sendMessage : sendAgentTask;

  return (
    <div style={styles.app}>
      {sidebarOpen && (
        <aside style={styles.sidebar} className="nova-sidebar">
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 5px 14px" }}>
            <div style={{
              width: 35, height: 35, borderRadius: 11,
              background: "linear-gradient(135deg,#8b78ff,#5744ce)",
              display: "grid", placeItems: "center",
            }}>
              <Bot size={22} color="white" />
            </div>
            <div>
              <strong style={{ fontSize: 17, letterSpacing: ".3px" }}>NOVA AI</strong>
              <div style={styles.muted}>Assistente pessoal</div>
            </div>
            <button
              style={{ ...styles.button, marginLeft: "auto", padding: 7, background: "transparent" }}
              onClick={() => setSidebarOpen(false)}
              title="Recolher barra lateral"
            >
              <PanelLeftClose size={17} />
            </button>
          </div>

          <button
            style={{
              ...styles.button,
              background: "#29234f",
              border: "1px solid #4d4385",
              justifyContent: "flex-start",
              padding: 12,
            }}
            onClick={newConversation}
          >
            <Plus size={17} /> Nova conversa
          </button>

          <div style={{ ...styles.muted, padding: "12px 7px 2px", letterSpacing: 1 }}>
            HISTÓRICO
          </div>

          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                style={{
                  background: activeId === conversation.id ? "#252630" : "transparent",
                  borderRadius: 9,
                  padding: "8px 7px",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  border: activeId === conversation.id ? "1px solid #393b49" : "1px solid transparent",
                }}
              >
                {renamingId === conversation.id ? (
                  <form
                    style={{ display: "flex", flex: 1, gap: 4 }}
                    onSubmit={(event) => { event.preventDefault(); renameConversation(conversation.id); }}
                  >
                    <input
                      autoFocus
                      value={renameValue}
                      onChange={(event) => setRenameValue(event.target.value)}
                      style={{ ...styles.input, padding: 7, fontSize: 12 }}
                    />
                    <button style={{ ...styles.button, padding: 6 }} type="submit"><Check size={14} /></button>
                  </form>
                ) : (
                  <>
                    <button
                      onClick={() => loadConversation(conversation.id)}
                      style={{
                        flex: 1, minWidth: 0, border: 0, background: "transparent",
                        color: activeId === conversation.id ? "#fff" : "#b9bac4",
                        cursor: "pointer", display: "flex", alignItems: "center",
                        gap: 9, textAlign: "left", padding: 3,
                      }}
                    >
                      <MessageSquare size={15} style={{ flexShrink: 0 }} />
                      <span style={{
                        overflow: "hidden", whiteSpace: "nowrap",
                        textOverflow: "ellipsis", fontSize: 12.5,
                      }}>
                        {conversation.title}
                      </span>
                    </button>
                    <button
                      title="Renomear conversa"
                      onClick={() => { setRenamingId(conversation.id); setRenameValue(conversation.title); }}
                      style={{ ...styles.button, background: "transparent", padding: 5, color: "#888" }}
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      title="Excluir conversa"
                      onClick={() => setDeleteId(conversation.id)}
                      style={{ ...styles.button, background: "transparent", padding: 5, color: "#888" }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </>
                )}
              </div>
            ))}

            {conversations.length === 0 && (
              <p style={{ ...styles.muted, padding: 8 }}>Suas conversas aparecerão aqui.</p>
            )}
          </div>

          {deleteId !== null && (
            <div style={{
              ...styles.secondary,
              borderColor: "#8b414b",
              display: "grid",
              gap: 9,
            }}>
              <strong style={{ fontSize: 13 }}>Excluir esta conversa?</strong>
              <span style={styles.muted}>As mensagens dessa conversa também serão apagadas.</span>
              <div style={{ display: "flex", gap: 7 }}>
                <button
                  style={{ ...styles.button, background: "#8b303e", flex: 1 }}
                  onClick={() => deleteConversation(deleteId)}
                >
                  Excluir
                </button>
                <button
                  style={{ ...styles.button, flex: 1 }}
                  onClick={() => setDeleteId(null)}
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}

          <div style={{ borderTop: "1px solid #292b34", paddingTop: 10, display: "grid", gap: 4 }}>
  <button
    style={{ ...styles.button, justifyContent: "flex-start", background: page === "files" ? "#292a35" : "transparent", color: "#c5c5cf" }}
    onClick={() => setPage("files")}
  >
    <Folder size={16} /> Arquivos
  </button>

  <button
    style={{ ...styles.button, justifyContent: "flex-start", background: page === "memory" ? "#292a35" : "transparent", color: "#c5c5cf" }}
    onClick={() => setPage("memory")}
  >
    <Brain size={16} /> Memória
  </button>

  <button
    style={{ ...styles.button, justifyContent: "flex-start", background: page === "settings" ? "#292a35" : "transparent", color: "#c5c5cf" }}
    onClick={() => setPage("settings")}
  >
    <Settings size={16} /> Configurações
  </button>
</div>

          <div style={{ ...styles.muted, display: "flex", alignItems: "center", gap: 7, padding: "5px 3px" }}>
            {online ? <Wifi size={14} color="#42c98b" /> : <WifiOff size={14} color="#e47777" />}
            {online ? "Sistema conectado" : "Sistema desconectado"}
          </div>
        </aside>
      )}

      <main style={styles.main}>
        <header style={{
          height: 58, minHeight: 58, display: "flex", alignItems: "center",
          justifyContent: "space-between", padding: "0 22px",
          borderBottom: "1px solid #242630",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {!sidebarOpen && (
              <button style={{ ...styles.button, background: "transparent", padding: 7 }} onClick={() => setSidebarOpen(true)}>
                <PanelLeftOpen size={19} />
              </button>
            )}
            <div>
              <strong style={{ fontSize: 14 }}>
                {page === "chat" ? "NOVA AI" : page === "files" ? "Arquivos" : page === "memory" ? "Memória" : "Configurações"}
              </strong>
              <div style={styles.muted}>
                {page === "chat" ? "Seu espaço de conversa" : "Gerencie seu assistente"}
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ ...styles.muted, display: "flex", alignItems: "center", gap: 5 }}>
              {online ? <Wifi size={14} color="#42c98b" /> : <WifiOff size={14} />}
              {online ? "Online" : "Offline"}
            </span>
            <button
              style={{ ...styles.button, padding: 8, background: "transparent" }}
              title="Atualizar"
              onClick={loadData}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>

        {notice && (
          <div style={{
            margin: "12px auto 0", maxWidth: 850, width: "calc(100% - 32px)",
            padding: "10px 13px", background: "#29234f",
            border: "1px solid #4d4385", borderRadius: 9,
            fontSize: 12, color: "#d8d0ff",
          }}>
            {notice}
            <button onClick={() => setNotice("")} style={{ float: "right", background: "transparent", border: 0, color: "white", cursor: "pointer" }}>
              <X size={14} />
            </button>
          </div>
        )}

        {page === "chat" && (
          <>
            <div style={{
              flex: 1, overflowY: "auto", padding: "30px 18px 20px",
              userSelect: "text", WebkitUserSelect: "text",
            }}>
              <div style={{ maxWidth: 820, margin: "0 auto", display: "flex", flexDirection: "column", gap: 25 }}>
                {messages.length === 0 && (
                  <div style={{
                    minHeight: "55vh", display: "flex", flexDirection: "column",
                    alignItems: "center", justifyContent: "center", textAlign: "center",
                  }}>
                    <div style={{
                      width: 58, height: 58, borderRadius: 20,
                      background: "linear-gradient(135deg,#8b78ff,#5140c8)",
                      display: "grid", placeItems: "center", marginBottom: 22,
                      boxShadow: "0 10px 45px #6652d533",
                    }}>
                      <Sparkles size={29} color="white" />
                    </div>
                    <h1 style={{ fontSize: 29, fontWeight: 600, margin: "0 0 10px" }}>
                      Como posso ajudar?
                    </h1>
                    <p style={{ color: "#999ba7", fontSize: 14, maxWidth: 440, lineHeight: 1.7 }}>
                      Converse comigo, tire dúvidas ou peça para realizar tarefas no seu computador.
                    </p>
                    <div style={{
                      display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))",
                      gap: 10, width: "100%", maxWidth: 550, marginTop: 25,
                    }}>
                      {[
                        ["Organizar arquivos", "Me ajude a organizar minha área de trabalho."],
                        ["Criar um documento", "Crie um arquivo de texto com minhas anotações."],
                        ["Tirar uma dúvida", "Explique como funciona uma rede local."],
                        ["Planejar uma tarefa", "Analise o que preciso fazer antes de executar."],
                      ].map(([title, prompt]) => (
                        <button
                          key={title}
                          onClick={() => setChatInput(prompt)}
                          style={{
                            ...styles.secondary, textAlign: "left",
                            color: "#e5e5ed", cursor: "pointer",
                          }}
                        >
                          <strong style={{ fontSize: 13 }}>{title}</strong>
                          <p style={{ ...styles.muted, marginBottom: 0, lineHeight: 1.5 }}>{prompt}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((message, index) => (
                  <div key={message.id ?? index} style={{
                    display: "flex", gap: 13,
                    flexDirection: message.role === "user" ? "row-reverse" : "row",
                    alignItems: "flex-start",
                  }}>
                    <div style={{
                      width: 30, height: 30, minWidth: 30, borderRadius: 10,
                      display: "grid", placeItems: "center",
                      background: message.role === "user" ? "#34313f" : "#5546b5",
                    }}>
                      {message.role === "user" ? <span style={{ fontSize: 12 }}>U</span> : <Bot size={18} />}
                    </div>
                    <div style={{
                      maxWidth: "85%", minWidth: 0,
                      background: message.role === "user" ? "#24252d" : "transparent",
                      border: message.role === "user" ? "1px solid #343640" : "1px solid transparent",
                      borderRadius: 14, padding: message.role === "user" ? "12px 15px" : "3px 0",
                      lineHeight: 1.75, fontSize: 14, whiteSpace: "pre-wrap",
                      overflowWrap: "anywhere",
                      userSelect: "text", WebkitUserSelect: "text",
                    }}>
                      {editingIndex === index ? (
                        <div style={{ minWidth: "min(70vw, 560px)" }}>
                          <textarea value={editingText} onChange={(event) => setEditingText(event.target.value)} rows={4} style={{ ...styles.input, resize: "vertical" }} />
                          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
                            <button style={styles.button} disabled={loading} onClick={() => { setEditingIndex(null); setEditingText(""); }}>Cancelar</button>
                            <button style={{ ...styles.button, background: "#705cf6" }} disabled={loading || !editingText.trim()} onClick={() => saveEditedMessage(message)}>{loading ? "Gerando resposta..." : "Salvar e reenviar"}</button>
                          </div>
                        </div>
                      ) : message.role === "assistant" ? (
     <div className="nova-markdown">
       <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
         pre: ({ children }) => <div style={{ position: "relative" }}><button title="Copiar código" onClick={(event) => {
           const code = event.currentTarget.parentElement?.querySelector("code")?.textContent || "";
           if (!navigator.clipboard) { setNotice("A cópia não está disponível nesta janela."); return; }
           void navigator.clipboard.writeText(code).then(() => setNotice("Código copiado.")).catch(() => setNotice("Não foi possível copiar o código."));
         }} style={{ position: "absolute", right: 8, top: 8, zIndex: 1, ...styles.button, padding: "5px 8px", fontSize: 11 }}><Copy size={13} /> Copiar</button>{children}</div>,
       }}>
         {message.content}
       </ReactMarkdown>
       {message.provider && <div style={{ ...styles.muted, marginTop: 8 }}>Respondido por {message.provider === "cloud" ? "Gemini" : "Ollama local"}</div>}
     </div>
   ) : <>
     <div>{message.content}</div>
     {message.id != null && <button title="Editar mensagem" aria-label="Editar mensagem" onClick={() => { setEditingIndex(index); setEditingText(message.content); }} style={{ ...styles.button, padding: 5, marginTop: 7, background: "transparent", color: "#a9aab5" }}><Pencil size={14} /></button>}
   </>}
                      {message.proposals?.map((proposal) => (
                        <div key={proposal.id} style={{
                          ...styles.secondary, marginTop: 15, width: "min(100%,520px)",
                          borderColor: "#51468a",
                        }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                            <ShieldCheck size={19} color="#a99aff" />
                            <strong style={{ fontSize: 13 }}>Autorização necessária</strong>
                            <span style={{ ...styles.muted, marginLeft: "auto" }}>#{proposal.id}</span>
                          </div>
                          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 9 }}>
                            {actionNames[proposal.action] || proposal.action}
                          </div>
                          <div style={{
                            background: "#0c0d12", border: "1px solid #30313b",
                            borderRadius: 8, padding: 11, color: "#bfc1ce",
                            fontSize: 12, whiteSpace: "pre-wrap", overflowWrap: "anywhere",
                          }}>
                            {String(proposal.arguments.query || proposal.arguments.package_id || proposal.arguments.path || proposal.arguments.destination || proposal.arguments.source || proposal.arguments.cwd || (Array.isArray(proposal.arguments.command) ? proposal.arguments.command.join(" ") : "Ação solicitada"))}
                          </div>
                          <p style={{ ...styles.muted, lineHeight: 1.5 }}>{proposal.summary || "Confira os detalhes. A ação só será realizada se você aprovar."}</p>
                          <p style={{ ...styles.muted, lineHeight: 1.5 }}>
                            Confira os detalhes. A ação só será realizada se você aprovar.
                          </p>
                          <div style={{ display: "flex", gap: 8 }}>
                            <button
                              style={{ ...styles.button, background: "#18784f" }}
                              disabled={busyAction !== null}
                              onClick={() => approveAction(proposal)}
                            >
                              <CheckCircle2 size={15} />
                              {busyAction === proposal.id ? "Executando..." : "Executar ação"}
                            </button>
                            <button
                              style={{ ...styles.button, background: "#383943" }}
                              disabled={busyAction !== null}
                              onClick={() => cancelAction(proposal)}
                            >
                              <X size={15} /> Cancelar
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div style={{ color: "#a99aff", fontSize: 13, paddingLeft: 43 }}>
                    NOVA está pensando...
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            </div>

            <div style={{ padding: "12px 18px 18px" }}>
              <form
                onSubmit={submit}
                style={{
                  maxWidth: 820, margin: "0 auto",
                  background: "#191a21", border: "1px solid #393b46",
                  borderRadius: 17, padding: 9,
                  boxShadow: "0 8px 35px #0005",
                }}
              >
                <textarea
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      submit();
                    }
                  }}
                  placeholder="Envie uma mensagem para a NOVA..."
                  rows={2}
                  disabled={!online || loading}
                  style={{
                    ...styles.input, background: "transparent", border: 0,
                    resize: "none", minHeight: 55, maxHeight: 180,
                    padding: "9px 10px", fontSize: 14,
                  }}
                />
                <div style={{
                  display: "flex", justifyContent: "space-between",
                  alignItems: "center", padding: "4px 4px 2px",
                }}>
                  <span style={{ ...styles.muted, paddingLeft: 5 }}>
                    Enter para enviar · Shift + Enter para pular linha
                  </span>
                  <button
                    type="submit"
                    disabled={!online || loading || !chatInput.trim()}
                    style={{
                      ...styles.button, width: 37, height: 37, padding: 0,
                      background: chatInput.trim() ? "#705cf6" : "#343540",
                      opacity: !chatInput.trim() || loading ? .5 : 1,
                    }}
                    title="Enviar mensagem"
                  >
                    <Send size={17} />
                  </button>
                </div>
              </form>
              <p style={{ ...styles.muted, textAlign: "center", margin: "9px 0 0" }}>
                A NOVA pode cometer erros. Confira informações importantes e autorize ações antes da execução.
              </p>
            </div>
          </>
        )}

        {page === "files" && (
          <div style={{ flex: 1, overflowY: "auto", padding: 25 }}>
            <div style={{ maxWidth: 950, margin: "0 auto", display: "grid", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <h2 style={{ marginBottom: 6 }}>Explorador de arquivos</h2>
                  <p style={styles.muted}>A NOVA só acessa pastas escolhidas e autorizadas por você.</p>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button style={styles.button} onClick={returnToWorkspace}>
                    <HardDrive size={15} /> Workspace
                  </button>
                  <button style={{ ...styles.button, background: "#705cf6" }} onClick={chooseFolder}>
                    <FolderOpen size={15} /> Selecionar pasta
                  </button>
                  <button style={styles.button} onClick={() => loadFolder(currentFolder || workspace)} disabled={folderLoading}>
                    <RefreshCw size={15} /> Atualizar
                  </button>
                </div>
              </div>

              <section style={styles.secondary}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                  <Folder size={17} color="#a99aff" />
                  <span style={{ fontSize: 12, overflowWrap: "anywhere" }}>{currentFolder || workspace}</span>
                </div>

                {folderRoot && currentFolder && currentFolder !== folderRoot && (
                  <button style={{ ...styles.button, marginBottom: 12 }} onClick={returnToFolderRoot}>
                    Voltar à pasta selecionada
                  </button>
                )}

                {files.map((file) => (
                  <div key={file.name} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: 12, borderTop: "1px solid #292b34",
                  }}>
                    {file.type === "folder"
                      ? <Folder size={18} color="#a99aff" />
                      : <FileText size={18} />}
                    {file.type === "folder" ? (
                      <button
                        onClick={() => loadFolder(`${currentFolder}\\${file.name}`)}
                        style={{ flex: 1, textAlign: "left", color: "#ececf1", background: "transparent", border: 0, cursor: "pointer", fontSize: 13, padding: 0 }}
                      >
                        {file.name}
                      </button>
                    ) : (
                      <span style={{ flex: 1, fontSize: 13, overflowWrap: "anywhere" }}>{file.name}</span>
                    )}
                    <span style={styles.muted}>
                      {file.type === "folder" ? "Pasta" : formatBytes(file.size)}
                    </span>
                  </div>
                ))}

                {files.length === 0 && (
                  <p style={styles.muted}>
                    {folderLoading ? "Carregando..." : "Nenhum arquivo encontrado nesta pasta."}
                  </p>
                )}
              </section>
            </div>
          </div>
        )}

        {page === "memory" && (
          <div style={{ flex: 1, overflowY: "auto", padding: 25 }}>
            <div style={{ maxWidth: 850, margin: "0 auto", display: "grid", gap: 18 }}>
              <section style={styles.secondary}>
                <h2 style={{ marginTop: 0 }}>Memória da NOVA</h2>
                <p style={styles.muted}>Informações que ajudam a NOVA a responder melhor.</p>
                <form onSubmit={addMemory} style={{ display: "grid", gap: 10 }}>
                  <select style={styles.input} value={memoryCategory} onChange={(event) => setMemoryCategory(event.target.value)}>
                    <option>Preferência</option>
                    <option>Estudo</option>
                    <option>Trabalho</option>
                    <option>Projeto</option>
                    <option>Outra informação</option>
                  </select>
                  <textarea
                    style={{ ...styles.input, minHeight: 90, resize: "vertical" }}
                    value={memoryContent}
                    onChange={(event) => setMemoryContent(event.target.value)}
                    placeholder="O que a NOVA deve lembrar?"
                  />
                  <button style={{ ...styles.button, background: "#705cf6" }} type="submit">Salvar memória</button>
                </form>
              </section>
              <section style={styles.secondary}>
                <h3>Memórias salvas ({memories.length})</h3>
                {memories.map((memory) => (
                  <div key={memory.id} style={{
                    padding: "13px 0", borderTop: "1px solid #292b34",
                    display: "flex", gap: 12, alignItems: "center",
                  }}>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: 13 }}>{memory.category}</strong>
                      <p style={{ fontSize: 13, color: "#c4c5ce" }}>{memory.content}</p>
                    </div>
                    <button style={{ ...styles.button, color: "#ef8b91" }} onClick={() => removeMemory(memory.id)}>
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
                {memories.length === 0 && <p style={styles.muted}>Nenhuma memória salva.</p>}
              </section>
            </div>
          </div>
        )}

        {page === "settings" && (
          <div style={{ flex: 1, overflowY: "auto", padding: 25 }}>
            <div style={{ maxWidth: 850, margin: "0 auto", display: "grid", gap: 18 }}>
              <section style={styles.secondary}>
                <h2 style={{ marginTop: 0 }}>Inteligência artificial</h2>
                <label style={{ ...styles.muted, display: "block", marginBottom: 9 }}>Provedor de conversa</label>
                <select style={styles.input} value={provider} onChange={(event) => setProvider(event.target.value)}>
                  <option value="hybrid">Automático: IA local e nuvem</option>
                  <option value="cloud">Somente Gemini</option>
                  <option value="local">Somente Ollama</option>
                </select>
                <p style={styles.muted}>O modo automático tenta usar a IA local e prioriza o Gemini e utiliza o Ollama como alternativa quando necess?rio.</p>
              </section>

              <section style={styles.secondary}>
                <h2 style={{ marginTop: 0 }}>Computador</h2>
                {system && (
                  <div style={{ display: "grid", gap: 10, fontSize: 13 }}>
                    <div><Monitor size={15} style={{ verticalAlign: "middle", marginRight: 8 }} />{system.computer}</div>
                    <div><Cpu size={15} style={{ verticalAlign: "middle", marginRight: 8 }} />{system.processor}</div>
                    <div><Activity size={15} style={{ verticalAlign: "middle", marginRight: 8 }} />CPU: {system.cpu_usage}%</div>
                    <div><Brain size={15} style={{ verticalAlign: "middle", marginRight: 8 }} />RAM: {system.ram_used_gb} / {system.ram_total_gb} GB ({system.ram_percent}%)</div>
                    <div><HardDrive size={15} style={{ verticalAlign: "middle", marginRight: 8 }} />Disco livre: {system.disk_free_gb} GB</div>
                  </div>
                )}
              </section>

              <section style={styles.secondary}>
                <h2 style={{ marginTop: 0 }}>Segurança</h2>
                <p style={{ color: "#b6b8c4", fontSize: 13, lineHeight: 1.7 }}>
                  As ferramentas desta versão trabalham dentro da pasta workspace autorizada. As ações do agente exigem aprovação individual. Não aprove operações que você não reconheça.
                </p>
                <div style={{ display: "flex", gap: 8, alignItems: "center", color: "#65d6a0", fontSize: 13 }}>
                  <ShieldCheck size={18} /> Proteção básica ativa
                </div>
              </section>

              <section style={styles.secondary}>
                <h2 style={{ marginTop: 0 }}>Sobre</h2>
                <p style={styles.muted}>NOVA AI · Versão 3.0 · Assistente desktop para Windows</p>
              </section>
            </div>
          </div>
        )}
      </main>

      <style>{`
        * { box-sizing: border-box; }
        button:disabled { cursor: not-allowed !important; }
        button:hover:not(:disabled) { filter: brightness(1.12); }
        textarea::placeholder, input::placeholder { color: #858794; }
        @media (max-width: 760px) {
          .nova-sidebar {
            position: absolute;
            z-index: 20;
            height: 100%;
            width: min(270px, calc(100vw - 56px)) !important;
            min-width: 0 !important;
            box-shadow: 15px 0 40px #0008;
          }
        }
        @media (max-width: 480px) {
          .nova-chat-area { padding-left: 12px !important; padding-right: 12px !important; }
          .nova-proposal-actions { flex-wrap: wrap; }
        }
      `}</style>
    </div>
  );
}

export default App;
