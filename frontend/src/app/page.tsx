export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold text-center mb-8">
          RealtorAgentAI
        </h1>
        <p className="text-xl text-center text-muted-foreground mb-8">
          Multi-Agent Real Estate Contract Platform
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-12">
          <div className="p-6 border rounded-lg">
            <h2 className="text-lg font-semibold mb-2">Document Intake</h2>
            <p className="text-sm text-muted-foreground">
              Upload and process real estate documents with AI-powered extraction
            </p>
          </div>
          <div className="p-6 border rounded-lg">
            <h2 className="text-lg font-semibold mb-2">Contract Generator</h2>
            <p className="text-sm text-muted-foreground">
              Generate standardized contracts from templates and extracted data
            </p>
          </div>
          <div className="p-6 border rounded-lg">
            <h2 className="text-lg font-semibold mb-2">Signature Tracking</h2>
            <p className="text-sm text-muted-foreground">
              Track multi-party signatures with audit trails and notifications
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
