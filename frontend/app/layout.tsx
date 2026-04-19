import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'MedRAG — Clinical Decision Support',
  description: 'Multi-agent clinical AI system with anti-hallucination pipeline',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="bg-white">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased min-h-screen bg-surface-50 text-ink-900">{children}</body>
    </html>
  )
}
