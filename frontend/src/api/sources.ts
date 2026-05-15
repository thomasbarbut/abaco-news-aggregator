import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api';
import type { NewsSource } from '@/types';

export const sourceKeys = {
  all: ['sources'] as const,
  lists: () => [...sourceKeys.all, 'list'] as const,
};

export function useSources() {
  return useQuery({
    queryKey: sourceKeys.lists(),
    queryFn: async () => {
      const { data } = await apiClient.get<NewsSource[]>('/sources');
      return data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes – sources don't change often
  });
}
