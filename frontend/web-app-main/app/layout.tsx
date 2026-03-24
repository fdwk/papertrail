import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono, Manrope, Newsreader } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { ThemeProvider } from '@/components/theme-provider'
import { AuthProvider } from '@/lib/auth-context'
import { Toaster } from '@/components/ui/sonner'
import './globals.css'

const newsreader = Newsreader({ subsets: ['latin'], variable: '--font-newsreader' })
const manrope = Manrope({ subsets: ['latin'], variable: '--font-manrope' })
const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' })

export const metadata: Metadata = {
  title: 'Papertrail - Academic Paper Learning Trails',
  description: 'Create structured learning paths through academic papers with interactive DAG visualizations.',
}

export const viewport: Viewport = {
  themeColor: '#002147',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const fontVariables = `${newsreader.variable} ${manrope.variable} ${inter.variable} ${jetbrainsMono.variable}`

  return (
    <html lang="en" className={fontVariables} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <AuthProvider>
            {children}
          </AuthProvider>
          <Toaster richColors position="bottom-right" />
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  )
}
