"use client"

import { useAuth } from '@clerk/nextjs';
import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { PricingTable, Protect, SignInButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs';

function parseExtraPlanKeys(raw: string | undefined): `user:${string}`[] {
    if (!raw?.trim()) return [];
    return raw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
        .map((k) =>
            k.startsWith('user:') || k.startsWith('org:') ? k : `user:${k}`,
        ) as `user:${string}`[];
}

const DEFAULT_WORKSPACE_PLAN_KEYS: `user:${string}`[] = [
    'user:pro',
    'user:starter',
    'user:premium_subscription',
];

function workspacePlanCondition(has: (p: { plan: `user:${string}` | `org:${string}` }) => boolean) {
    const planRequired = process.env.NEXT_PUBLIC_CLERK_PLAN_REQUIRED !== 'false';
    if (!planRequired) return true;

    const keys = [...new Set([...DEFAULT_WORKSPACE_PLAN_KEYS, ...parseExtraPlanKeys(process.env.NEXT_PUBLIC_CLERK_ALLOWED_PLANS)])];
    return keys.some((plan) => has({ plan }));
}

type Role = 'user' | 'assistant';

type Msg = { id: string; role: Role; content: string };

const SUGGESTIONS = [
    'How do we request a DPA or security questionnaire?',
    'Invoice copy and billing contact change',
    'SSO / SCIM rollout checklist',
    'API rate limits and error spikes—what to check first',
];

type KbSource = { source: string; chunks: number };

function KnowledgePanel({ getToken }: { getToken: () => Promise<string | null> }) {
    const [sources, setSources] = useState<KbSource[]>([]);
    const [kbLoading, setKbLoading] = useState(false);
    const [kbError, setKbError] = useState('');
    const [uploading, setUploading] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    const refreshSources = useCallback(async () => {
        setKbLoading(true);
        setKbError('');
        try {
            const jwt = await getToken();
            if (!jwt) {
                setKbError('Not signed in.');
                return;
            }
            const res = await fetch('/api/knowledge/sources', {
                headers: { Authorization: `Bearer ${jwt}` },
            });
            if (!res.ok) {
                setKbError(`Could not list sources (${res.status}).`);
                return;
            }
            const data = (await res.json()) as { sources: KbSource[] };
            setSources(data.sources ?? []);
        } catch {
            setKbError('Network error loading knowledge base.');
        } finally {
            setKbLoading(false);
        }
    }, [getToken]);

    useEffect(() => {
        void refreshSources();
    }, [refreshSources]);

    async function onUploadFile(f: File) {
        setKbError('');
        setUploading(true);
        try {
            const jwt = await getToken();
            if (!jwt) {
                setKbError('Not signed in.');
                return;
            }
            const fd = new FormData();
            fd.append('file', f);
            const res = await fetch('/api/knowledge/upload', {
                method: 'POST',
                headers: { Authorization: `Bearer ${jwt}` },
                body: fd,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail ?? res.statusText);
                setKbError(detail || `Upload failed (${res.status}).`);
                return;
            }
            await refreshSources();
            if (fileRef.current) fileRef.current.value = '';
        } catch {
            setKbError('Upload failed.');
        } finally {
            setUploading(false);
        }
    }

    async function removeSource(name: string) {
        setKbError('');
        try {
            const jwt = await getToken();
            if (!jwt) return;
            const res = await fetch(`/api/knowledge/source?source=${encodeURIComponent(name)}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${jwt}` },
            });
            if (!res.ok) {
                setKbError(`Remove failed (${res.status}).`);
                return;
            }
            await refreshSources();
        } catch {
            setKbError('Remove failed.');
        }
    }

    return (
        <aside className="desk-kb-panel flex w-full shrink-0 flex-col border-b-2 border-[var(--desk-accent-border)] bg-[var(--desk-accent-soft)] lg:w-80 lg:border-b-0 lg:border-r-2">
            <div className="border-b border-[var(--desk-accent-border)] px-4 py-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-600">Knowledge base</p>
                <p className="desk-body mt-1 text-xs leading-relaxed">
                    Upload .txt, .md, or .pdf. A <strong>router</strong> agent decides when to query them; a{' '}
                    <strong>KB analyst</strong> summarizes excerpts for the support reply (LangGraph orchestration).
                </p>
            </div>
            <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
                <input
                    ref={fileRef}
                    type="file"
                    accept=".txt,.md,.pdf"
                    className="sr-only"
                    onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) void onUploadFile(f);
                    }}
                />
                <button
                    type="button"
                    disabled={uploading}
                    onClick={() => fileRef.current?.click()}
                    className="chat-send-btn w-full py-2.5 text-sm"
                >
                    {uploading ? 'Uploading…' : 'Upload document'}
                </button>
                <button type="button" onClick={() => void refreshSources()} disabled={kbLoading} className="chat-btn-ghost text-xs">
                    {kbLoading ? 'Refreshing…' : 'Refresh list'}
                </button>
                {kbError && (
                    <p className="text-xs text-red-600" role="alert">
                        {kbError}
                    </p>
                )}
                <ul className="space-y-2 text-left text-sm">
                    {sources.length === 0 && !kbLoading && (
                        <li className="desk-body text-xs">No documents yet. Upload runbooks or FAQs your agents should cite.</li>
                    )}
                    {sources.map((s) => (
                        <li key={s.source} className="desk-card flex items-center justify-between gap-2 rounded-xl px-3 py-2">
                            <span className="min-w-0 flex-1 truncate font-medium text-gray-900" title={s.source}>
                                {s.source}
                            </span>
                            <span className="shrink-0 text-xs text-gray-500">{s.chunks} chunks</span>
                            <button
                                type="button"
                                className="shrink-0 text-xs font-semibold text-red-600 hover:underline"
                                onClick={() => void removeSource(s.source)}
                            >
                                Remove
                            </button>
                        </li>
                    ))}
                </ul>
            </div>
        </aside>
    );
}

function ChatWorkspace() {
    const { getToken } = useAuth();
    const [messages, setMessages] = useState<Msg[]>([]);
    const [input, setInput] = useState('');
    const [streaming, setStreaming] = useState(false);
    const [error, setError] = useState('');
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, streaming]);

    const sendPayload = useCallback(
        async (text: string) => {
            const trimmed = text.trim();
            if (!trimmed || streaming) return;

            const jwt = await getToken();
            if (!jwt) {
                setError('Please sign in again.');
                return;
            }

            setError('');
            const userMsg: Msg = {
                id: crypto.randomUUID(),
                role: 'user',
                content: trimmed,
            };
            const nextThread = [...messages, userMsg];
            setMessages(nextThread);
            setInput('');
            setStreaming(true);

            const assistantId = crypto.randomUUID();
            setMessages((prev) => [...prev, { id: assistantId, role: 'assistant', content: '' }]);

            const controller = new AbortController();
            let assembled = '';

            try {
                await fetchEventSource('/api/chat', {
                    signal: controller.signal,
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${jwt}`,
                    },
                    body: JSON.stringify({
                        messages: nextThread.map((m) => ({ role: m.role, content: m.content })),
                    }),
                    async onopen(response) {
                        if (response.ok) return;
                        setError(`Could not start chat (${response.status}).`);
                        throw new Error(String(response.status));
                    },
                    onmessage(ev) {
                        if (ev.data === '[DONE]') return;
                        try {
                            const parsed = JSON.parse(ev.data) as { delta?: string; error?: string };
                            if (parsed.error) {
                                setError(parsed.error);
                                return;
                            }
                            if (parsed.delta) {
                                assembled += parsed.delta;
                                setMessages((prev) =>
                                    prev.map((m) =>
                                        m.id === assistantId ? { ...m, content: assembled } : m,
                                    ),
                                );
                            }
                        } catch {
                            /* ignore parse noise */
                        }
                    },
                    onclose() {
                        setStreaming(false);
                    },
                    onerror(err) {
                        console.error(err);
                        controller.abort();
                        setStreaming(false);
                        setError('Something went wrong. Try again in a moment.');
                        setMessages((prev) =>
                            prev.filter((m) => !(m.id === assistantId && m.role === 'assistant' && !m.content)),
                        );
                    },
                });
            } catch {
                setStreaming(false);
                setError('Could not reach the assistant.');
                setMessages((prev) =>
                    prev.filter((m) => !(m.id === assistantId && m.role === 'assistant' && !m.content)),
                );
            }
        },
        [getToken, messages, streaming],
    );

    function newChat() {
        if (streaming) return;
        setMessages([]);
        setError('');
        setInput('');
    }

    return (
        <div className="chat-app relative flex min-h-screen flex-col lg:flex-row">
            <KnowledgePanel getToken={getToken} />
            <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
            <div className="chat-aurora" aria-hidden="true" />
            <header className="chat-header relative z-10 flex items-center justify-between gap-4 px-4 py-3 md:px-8">
                <div className="flex min-w-0 items-center gap-3">
                    <div className="chat-logo-mark shrink-0" aria-hidden="true" />
                    <div className="min-w-0">
                        <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-indigo-600">Desk</p>
                        <h1 className="desk-heading truncate text-base font-semibold md:text-lg">Enterprise support console</h1>
                    </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                    <button type="button" onClick={newChat} disabled={streaming} className="chat-btn-ghost text-sm">
                        New thread
                    </button>
                    <UserButton showName={true} />
                </div>
            </header>

            <main className="relative z-10 flex flex-1 flex-col overflow-hidden">
                <div className="chat-disclaimer mx-4 mb-2 rounded-2xl px-4 py-3 text-center text-xs font-medium leading-relaxed md:mx-auto md:max-w-2xl">
                    AI-assisted guidance only—not legal, financial, or contractual advice. For SLA credits, order forms, or
                    security incidents, use your official vendor channels and account team.
                </div>

                <div className="flex-1 overflow-y-auto px-3 pb-4 pt-2 md:px-6">
                    {messages.length === 0 && (
                        <div className="mx-auto mt-6 max-w-xl text-center">
                            <p className="font-display desk-heading text-2xl font-semibold md:text-3xl">How can we help your account?</p>
                            <p className="desk-body mt-3 text-sm leading-relaxed md:text-base">
                                Ask about procurement, access, usage, or escalations. I will suggest practical next steps and flag
                                when a human owner should take over.
                            </p>
                            <div className="mt-8 flex flex-wrap justify-center gap-2">
                                {SUGGESTIONS.map((s) => (
                                    <button
                                        key={s}
                                        type="button"
                                        disabled={streaming}
                                        onClick={() => void sendPayload(s)}
                                        className="chat-chip"
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="mx-auto flex max-w-3xl flex-col gap-4">
                        {messages.map((m) => (
                            <article
                                key={m.id}
                                className={`chat-bubble-wrap flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div className={`chat-bubble ${m.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'}`}>
                                    {m.role === 'assistant' ? (
                                        m.content ? (
                                            <div className="chat-markdown markdown-content">
                                                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{m.content}</ReactMarkdown>
                                            </div>
                                        ) : streaming ? (
                                            <span className="chat-typing">
                                                <span />
                                                <span />
                                                <span />
                                            </span>
                                        ) : null
                                    ) : (
                                        <p className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</p>
                                    )}
                                </div>
                            </article>
                        ))}
                        <div ref={bottomRef} />
                    </div>
                </div>

                {error && (
                    <p className="relative z-10 px-4 pb-2 text-center text-sm text-red-600 md:px-8" role="alert">
                        {error}
                    </p>
                )}

                <div className="chat-composer relative z-10 px-3 py-3 md:px-8 md:py-4">
                    <form
                        className="mx-auto flex max-w-3xl gap-2 md:gap-3"
                        onSubmit={(e) => {
                            e.preventDefault();
                            void sendPayload(input);
                        }}
                    >
                        <label htmlFor="chat-input" className="sr-only">
                            Message
                        </label>
                        <textarea
                            id="chat-input"
                            rows={1}
                            value={input}
                            disabled={streaming}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    void sendPayload(input);
                                }
                            }}
                            placeholder="Describe the customer issue or internal question…"
                            className="chat-input flex-1 resize-none rounded-2xl px-4 py-3 text-sm"
                        />
                        <button type="submit" disabled={streaming || !input.trim()} className="chat-send-btn">
                            {streaming ? '…' : 'Send'}
                        </button>
                    </form>
                </div>
            </main>
            </div>
        </div>
    );
}

const paywallFallback = (
    <div className="chat-app relative min-h-screen px-4 py-12">
        <div className="chat-aurora" aria-hidden="true" />
        <div className="relative z-10 mx-auto max-w-4xl">
            <header className="desk-card mb-8 rounded-3xl p-8 text-center">
                <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-indigo-600">Desk</p>
                <h1 className="desk-heading mt-2 font-display text-3xl font-semibold">Subscribe to use the console</h1>
                <p className="desk-body mx-auto mt-3 max-w-xl text-sm">
                    Pick a plan to access the enterprise support assistant. If your org uses Clerk Billing with different plan
                    ids, add them to{' '}
                    <code className="rounded-md border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-xs text-gray-900">NEXT_PUBLIC_CLERK_ALLOWED_PLANS</code> in{' '}
                    <code className="rounded-md border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-xs text-gray-900">.env.local</code>{' '}
                    (supports <code className="rounded-md border border-indigo-200 bg-indigo-50 px-1.5 py-0.5 text-xs">org:</code> keys).
                </p>
            </header>
            <div className="desk-card rounded-3xl p-4 md:p-6">
                <PricingTable />
            </div>
        </div>
    </div>
);

export default function Product() {
    return (
        <>
            <SignedOut>
                <div className="chat-app relative flex min-h-screen flex-col items-center justify-center px-4">
                    <div className="chat-aurora" aria-hidden="true" />
                    <div className="relative z-10 max-w-md text-center">
                        <div className="chat-logo-mark mx-auto mb-6 h-14 w-14" aria-hidden="true" />
                        <h1 className="font-display desk-heading text-2xl font-semibold">Sign in to open the console</h1>
                        <p className="desk-body mt-3 text-sm">Secure access for your team’s AI-assisted support workspace.</p>
                        <SignInButton mode="modal">
                            <button type="button" className="chat-send-btn mt-8 px-8 py-3">
                                Sign in
                            </button>
                        </SignInButton>
                    </div>
                </div>
            </SignedOut>
            <SignedIn>
                <Protect condition={workspacePlanCondition} fallback={paywallFallback}>
                    <ChatWorkspace />
                </Protect>
            </SignedIn>
        </>
    );
}
