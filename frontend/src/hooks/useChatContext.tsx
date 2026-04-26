import { createContext, useContext } from 'react'
import { useChat } from './useChat'

type ChatContextValue = ReturnType<typeof useChat>
const ChatContext = createContext<ChatContextValue | null>(null)

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const value = useChat()
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

// Hook export is paired with the provider by design.
// eslint-disable-next-line react-refresh/only-export-components
export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChatContext must be used inside <ChatProvider>')
  return ctx
}
