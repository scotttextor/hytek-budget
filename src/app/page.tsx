// MOTHBALLED 2026-04-22 — retirement notice shown ONLY if the Next.js
// redirect in next.config.ts fails to fire (edge case — browser cache, etc.).
// Normal traffic flow: request arrives → next.config 307 redirect →
// hytek-install.vercel.app/dashboard. This page should basically never render.

export default function RetiredPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-hytek-black text-white">
      <div className="max-w-md text-center">
        <div className="text-5xl font-bold text-hytek-yellow mb-4">HYTEK</div>
        <h1 className="text-2xl font-bold mb-3">This app has been retired.</h1>
        <p className="text-gray-300 mb-6">
          Install budget tracking has moved to the new HYTEK Install app.
          Your logins, data, and history are already there.
        </p>
        <a
          href="https://hytek-install.vercel.app/dashboard"
          className="inline-block bg-hytek-yellow text-hytek-black font-bold rounded-lg px-6 py-3 hover:brightness-95"
        >
          Take me to the new app →
        </a>
        <p className="text-xs text-gray-500 mt-6">
          Mothballed 22 April 2026. See <code className="bg-gray-800 px-1 rounded">hytek-budget/CLAUDE.md</code> for history.
        </p>
      </div>
    </div>
  )
}
