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
- [~] M1c MLX runtime: kod + mock testleri hazır, gerçek `mlx_lm.server` koşusu model indirme onayı bekliyor
- [ ] M2 Ölçüm: >=3 model x iki runtime, kalite/gecikme/tok-s/RAM tablosu, thinking açık/kapalı etkisi
- [ ] M3 Karar noktası: ölçüm router'ı gerekçelendiriyor mu? Hayırsa durup raporla
- [ ] M4 (koşullu) Router: görev tipi + güvene göre kademeli yönlendirme
- [ ] M5 Güvenlik: PII redaction, allow-list'li tool, prompt-injection eval, human escalation
- [ ] M6 Yönetişim: audit trail, regression gate, tek sayfalık token/latency paneli
- [ ] M7 README, rapor, CV, GitHub (`Phaldors/local-ai-control-plane`)

## İlkeler
- validation ile ayar, test split yalnızca final dondurulmuş raporda.
- Ölçüm bug'ı ile model bug'ını ayır (DocuGuard dersleri).
- Her koşu: runtime, model, think/max_tokens, commit, host kayıtlı.
