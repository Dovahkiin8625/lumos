"""Lumos 知识库模块。

文档解析（Docling）和分片（recursive markdown chunker）由 vector-service 提供；
本模块只负责：
  - vector-service HTTP 客户端
  - KB / 文档的持久化与编排
  - 检索（embed query → search → rerank → 引用格式化）
  - 后台索引任务（基于 vector-service /v1/ingest 的原子化端点）
"""
from __future__ import annotations
