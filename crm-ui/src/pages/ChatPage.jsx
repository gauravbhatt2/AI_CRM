import Layout from "../components/Layout.jsx";
import AIChatbot from "../components/AIChatbot.jsx";

export default function ChatPage() {
  return (
    <Layout>
      <div className="flex h-[calc(100vh-7rem)] max-h-[calc(100vh-7rem)] flex-col py-2">
        <header className="mb-4 shrink-0">
          <span className="text-[10px] font-bold uppercase tracking-widest text-secondary">Agents</span>
          <h1 className="font-headline text-4xl font-extrabold tracking-tighter text-primary">Deal assistant</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-on-surface-variant">
            Choose a CRM record, then ask questions. Responses use the Agents API and your ingested transcripts and fields.
          </p>
        </header>
        <div className="flex min-h-0 flex-1 flex-col">
          <AIChatbot />
        </div>
      </div>
    </Layout>
  );
}
