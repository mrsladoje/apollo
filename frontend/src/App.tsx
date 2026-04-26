import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import './index.css'
import { ChatProvider } from '@/hooks/useChatContext'
import { LandingScreen } from '@/components/landing/LandingScreen'
import { ChatScreen } from '@/components/chat-screen/ChatScreen'

type Screen = 'landing' | 'chat'

function App() {
  const [screen, setScreen] = useState<Screen>('landing')

  return (
    <ChatProvider>
      <div>
        <AnimatePresence mode='wait'>
          {screen === 'landing' ? (
            <LandingScreen key='landing' onAsk={() => setScreen('chat')} />
          ) : (
            <ChatScreen key='chat' />
          )}
        </AnimatePresence>
      </div>
    </ChatProvider>
  )
}

export default App
