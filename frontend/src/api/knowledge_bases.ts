import { api } from '@/api/client'
import type {
  KnowledgeBaseCreate,
  KnowledgeBaseOut,
  KnowledgeBaseUpdate,
  KnowledgeDocumentOut,
  KnowledgeDocumentStatusOut,
  KnowledgeSearchRequest,
  KnowledgeSearchResponse,
} from '@/types/domain'

export async function listKnowledgeBases(): Promise<KnowledgeBaseOut[]> {
  const { data } = await api.get<KnowledgeBaseOut[]>('/api/knowledge_bases')
  return data
}

export async function createKnowledgeBase(
  payload: KnowledgeBaseCreate,
): Promise<KnowledgeBaseOut> {
  const { data } = await api.post<KnowledgeBaseOut>('/api/knowledge_bases', payload)
  return data
}

export async function getKnowledgeBase(id: string): Promise<KnowledgeBaseOut> {
  const { data } = await api.get<KnowledgeBaseOut>(`/api/knowledge_bases/${id}`)
  return data
}

export async function updateKnowledgeBase(
  id: string,
  payload: KnowledgeBaseUpdate,
): Promise<KnowledgeBaseOut> {
  const { data } = await api.patch<KnowledgeBaseOut>(`/api/knowledge_bases/${id}`, payload)
  return data
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  await api.delete(`/api/knowledge_bases/${id}`)
}

export async function listDocuments(kbId: string): Promise<KnowledgeDocumentOut[]> {
  const { data } = await api.get<KnowledgeDocumentOut[]>(
    `/api/knowledge_bases/${kbId}/documents`,
  )
  return data
}

export async function uploadDocument(
  kbId: string,
  file: File,
): Promise<KnowledgeDocumentOut> {
  const fd = new FormData()
  fd.append('file', file, file.name)
  const { data } = await api.post<KnowledgeDocumentOut>(
    `/api/knowledge_bases/${kbId}/documents`,
    fd,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function deleteDocument(kbId: string, docId: string): Promise<void> {
  await api.delete(`/api/knowledge_bases/${kbId}/documents/${docId}`)
}

export async function getDocumentStatus(
  kbId: string,
  docId: string,
): Promise<KnowledgeDocumentStatusOut> {
  const { data } = await api.get<KnowledgeDocumentStatusOut>(
    `/api/knowledge_bases/${kbId}/documents/${docId}/status`,
  )
  return data
}

export async function searchKnowledgeBase(
  kbId: string,
  req: KnowledgeSearchRequest,
): Promise<KnowledgeSearchResponse> {
  const { data } = await api.post<KnowledgeSearchResponse>(
    `/api/knowledge_bases/${kbId}/search`,
    req,
  )
  return data
}
