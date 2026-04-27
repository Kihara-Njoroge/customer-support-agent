"use client"

import Link from 'next/link';
import { SignInButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs';

const pillars = [
    {
        title: 'First line, enterprise pace',
        body: 'Billing, SSO, usage limits, renewals, onboarding blockers, and outage triage—answered in plain language so your team can move.',
    },
    {
        title: 'Consistent, policy-aware tone',
        body: 'Short answers when you need a fast read; checklists and next steps when you are coordinating across IT, finance, and vendors.',
    },
    {
        title: 'Signed-in, account-ready',
        body: 'Clerk sign-in ties sessions to your org user. Escalate to your CSM or support portal when something needs a human or a contract lookup.',
    },
];

export default function Home() {
    return (
        <div className="landing relative min-h-screen overflow-hidden">
            <div className="landing-aurora" aria-hidden="true" />

            <div className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col px-5 pb-16 pt-8 md:px-10">
                <nav className="flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-3">
                        <div className="chat-logo-mark h-10 w-10" aria-hidden="true" />
                        <div>
                            <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-indigo-600">Desk</p>
                            <p className="font-display desk-heading text-lg font-semibold">Enterprise support</p>
                        </div>
                    </Link>
                    <div className="flex items-center gap-3">
                        <SignedOut>
                            <SignInButton mode="modal">
                                <button type="button" className="chat-btn-ghost px-4 py-2 text-sm">
                                    Sign in
                                </button>
                            </SignInButton>
                        </SignedOut>
                        <SignedIn>
                            <Link href="/product" className="chat-send-btn px-5 py-2.5 text-sm">
                                Open console
                            </Link>
                            <UserButton showName={true} />
                        </SignedIn>
                    </div>
                </nav>

                <section className="mt-16 flex flex-1 flex-col items-center text-center md:mt-24">
                    <p className="desk-eyebrow rounded-full px-4 py-2 text-[10px] font-bold uppercase tracking-[0.22em]">
                        B2B · AI-assisted · Not a binding commitment
                    </p>
                    <h1 className="font-display desk-heading mt-8 max-w-3xl text-balance text-4xl font-semibold leading-[1.15] md:text-6xl md:leading-[1.1]">
                        Customer support that scales with your enterprise accounts.
                    </h1>
                    <p className="desk-body mt-6 max-w-2xl text-pretty text-base leading-relaxed md:text-lg">
                        Desk is an MVP console for AI-assisted enterprise support: triage common questions, draft next steps, and
                        know when to hand off to your account team or ticketing system.
                    </p>

                    <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
                        <SignedOut>
                            <SignInButton mode="modal">
                                <button type="button" className="chat-send-btn px-8 py-3.5 text-sm font-semibold">
                                    Sign in to try it
                                </button>
                            </SignInButton>
                        </SignedOut>
                        <SignedIn>
                            <Link href="/product" className="chat-send-btn px-8 py-3.5 text-sm font-semibold">
                                Go to console
                            </Link>
                        </SignedIn>
                    </div>
                </section>

                <section className="mt-20 grid gap-4 md:mt-28 md:grid-cols-3">
                    {pillars.map((p) => (
                        <article
                            key={p.title}
                            className="desk-card rounded-3xl p-6 text-left transition hover:border-indigo-300"
                        >
                            <h2 className="font-display desk-heading text-lg font-semibold">{p.title}</h2>
                            <p className="desk-body mt-2 text-sm leading-relaxed">{p.body}</p>
                        </article>
                    ))}
                </section>
            </div>
        </div>
    );
}
