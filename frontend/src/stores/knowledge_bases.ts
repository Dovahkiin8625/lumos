import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as kbApi from '@/api/knowledge_bases'
import type {
  KnowledgeBaseCreate,
  KnowledgeBaseOut,
  KnowledgeBaseUpdate,
  KnowledgeDocumentOut,
  KnowledgeSearchRequest,
  KnowledgeSearchResponse,
} from '@/types/domain'

export const useKnowledgeBasesStore = defineStore('knowledge_bases', () => {
  const list = ref<KnowledgeBaseOut[]>([])
  const loading = ref(false)

  // 当前正在查看的 KB 详情（包含 documents）
  const current = ref<KnowledgeBaseOut | null>(null)
  const documents = ref<KnowledgeDocumentOut[]>([])

  async function load() {
    loading.value = true
    try {
      list.value = await kbApi.listKnowledgeBases()
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(kbId: string) {
    current.value = await kbApi.getKnowledgeBase(kbId)
    documents.value = await kbApi.listDocuments(kbId)
  }

  async function create(payload: KnowledgeBaseCreate) {
    const kb = await kbApi.createKnowledgeBase(payload)
    list.value = [kb, ...list.value]
    return kb
  }

  async function update(id: string, payload: KnowledgeBaseUpdate) {
    const kb = await kbApi.updateKnowledgeBase(id, payload)
    list.value = list.value.map((k) => (k.id === id ? kb : k))
    if (current.value?.id === id) current.value = kb
    return kb
  }

  async function remove(id: string) {
    await kbApi.deleteKnowledgeBase(id)
    list.value = list.value.filter((k) => k.id !== id)
    if (current.value?.id === id) {
      current.value = null
      documents.value = []
    }
  }

  async function uploadDocument(kbId: string, file: File) {
    const doc = await kbApi.uploadDocument(kbId, file)
    documents.value = [doc, ...documents.value]
    return doc
  }

  async function removeDocument(kbId: string, docId: string) {
    await kbApi.deleteDocument(kbId, docId)
    documents.value = documents.value.filter((d) => d.id !== docId)
  }

  async function refreshDocuments(kbId: string) {
    documents.value = await kbApi.listDocuments(kbId)
  }

  async function search(kbId: string, req: KnowledgeSearchRequest) {
    return await kbApi.searchKnowledgeBase(kbId, req)
  }

  function resetCurrent() {
    current.value = null
    documents.value = []
  }

  return {
    list, loading, current, documents,
    load, loadDetail, create, update, remove,
    uploadDocument, removeDocument, refreshDocuments, search,
    resetCurrent,
  }
})
