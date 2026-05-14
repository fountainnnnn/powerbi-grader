import { useState, useCallback } from 'react';
import { Rubric } from '../types/api';
import { apiClient } from '../services/api';

export function useRubric() {
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRubric = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.getRubric();
      setRubric(response.rubric);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load rubric');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const uploadRubric = useCallback(async (file: File) => {
    setError(null);
    setIsLoading(true);
    try {
      const newRubric = await apiClient.uploadRubric(file);
      setRubric(newRubric);
      return newRubric;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to upload rubric';
      setError(errorMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteRubric = useCallback(async () => {
    setError(null);
    try {
      await apiClient.deleteRubric();
      setRubric(null);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete rubric';
      setError(errorMsg);
      throw err;
    }
  }, []);

  return {
    rubric,
    isLoading,
    error,
    loadRubric,
    uploadRubric,
    deleteRubric,
  };
}
