import { useState } from 'react';
import { useAgentSession } from '../hooks/useAgentSession';

export default function AgentConsole({ token }: { token: string | null }) {
  const [prompt, setPrompt] = useState('');
  const { connected, output, run, status } = useAgentSession(token);

  return (
    <div className="p-2">
      <textarea
        className="w-full border p-2"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <button
        onClick={() => run(prompt)}
        disabled={!connected}
        className="bg-blue-500 text-white px-2 py-1 mt-2"
      >
        Run
      </button>
      <div className="mt-2 whitespace-pre-wrap border p-2 min-h-[4rem]">
        {output}
      </div>
      <div className="text-sm text-gray-500">Status: {status}</div>
    </div>
  );
}
