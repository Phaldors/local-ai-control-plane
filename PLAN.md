---
title: Local AI Control Plane Plan
created: 2026-10-15
modified: 2026-10-15
type: project
status: active
tags: [project, local-llm, ollama, mlx, eval, routing, llmops]
---

# Local AI Control Plane

Ollama ve MLX-LM üstünde birden fazla yerel modeli servis eden, ölçen ve
(ölçüm gerekçelendirirse) route eden katman. Hedef soru: "Hassas veriyi dışarı
çıkarmadan hangi görevi hangi yerel model, hangi güvenle yapabilir?"

## Sınırlar (Arda'nın kararı)
- Ollama + MLX-LM ortak `LLMClient` arkasında.
- İlk hedef router/dashboard DEĞİL: trace'li iki runtime + golden eval sözleşmesi.
- Tool-call başarısızlıkları gizlenmez, eval raporuna bulgu olarak girer.
- Router, ancak ölçüm sonuçlarıyla gerekçelendirilirse başlar.

## Milestones
- [x] M1a `LLMClient` protokolü, Ollama runtime, JSONL trace, golden eval sözleşmesi, hata taksonomisi
- [x] M1b Golden setler: extraction (CORD validation, 50) + tool_call (25, no-tool vakaları dahil)
- [x] M1c MLX runtime: gerçek `mlx_lm.server` koşusu doğrulandı (Qwen3-8B, Qwen3-30B-A3B)
- [x] M2 Ölçüm: 3 model x iki runtime, golden v2, thinking açık/kapalı (docs/findings-m2.md)
- [x] M3 Karar: router gerekçelendirilmiyor (extraction'da en ucuz konfigürasyon en iyisi). Revisit koşulları findings-m2.md sonunda
- [x] M3b Daha zor görev (çok fişli extraction, 2-16 fiş): güçlü modeller doygun, router yine gerekçelendirilmedi (docs/findings-m3.md)
- [ ] M4 (koşullu, şimdilik askıda) Router: görev tipi + güvene göre kademeli yönlendirme
- [ ] M5 Güvenlik: PII redaction, allow-list'li tool, prompt-injection eval, human escalation
- [ ] M6 Yönetişim: audit trail, regression gate, tek sayfalık token/latency paneli
- [ ] M7 README, rapor, CV, GitHub (`Phaldors/local-ai-control-plane`)

## İlkeler
- validation ile ayar, test split yalnızca final dondurulmuş raporda.
- Ölçüm bug'ı ile model bug'ını ayır (DocuGuard dersleri).
- Her koşu: runtime, model, think/max_tokens, commit, host kayıtlı.
