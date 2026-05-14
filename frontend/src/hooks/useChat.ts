import { useState, useCallback } from 'react';
import { ChatMessage } from '../types/api';
import { apiClient } from '../services/api';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.getChatHistory();
      setMessages(response.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chat history');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendMessage = useCallback(async (message: string, dashboardId?: string, pbixId?: string, studentName?: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const response = await apiClient.sendMessage(message, dashboardId, pbixId, studentName);
      setMessages(prev => [...prev, response]);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    loadHistory,
    sendMessage,
    clearChat,
  };
}
