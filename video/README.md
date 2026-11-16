# 🎬 Vídeo — A Última Live (pipeline de produção)

Gera os dois vídeos verticais (1080×1920, 30 fps, 60 s cada) do projeto a partir de
[`PART_1_SCRIPT.md`](../PART_1_SCRIPT.md) e [`PART_2_SCRIPT.md`](../PART_2_SCRIPT.md),
mais o corte completo de 2 min para TikTok/Reels/Shorts.

> **O que é (e o que não é):** é uma animação **procedural** em estilo found footage — um corredor 3D
> renderizado quadro a quadro em Python, com personagens 2D, HUD de gravação, chat da live, legendas,
> vozes sintetizadas e efeitos sonoros sintetizados. **Não é filmagem fotorrealista gerada por IA de vídeo.**
> Para uma versão fotorrealista, os roteiros em `PART_*_SCRIPT.md` já estão escritos como prompts de
> produção por plano (câmera, luz, som, atuação) para usar em um gerador de vídeo.

## Saídas (`../output/`)
| Arquivo | Conteúdo |
| :--- | :--- |
| `A_Ultima_Live_Parte1.mp4` | Parte 1 — A Situação (60 s, HUD `02:43 AM 🔴 REC`, termina em `CONTINUA NA PARTE 2 ▶`) |
| `A_Ultima_Live_Parte2.mp4` | Parte 2 — O Desfecho (60 s, HUD `03:01 AM 🔴 REC`, bateria travada em 1%) |
| `A_Ultima_Live_COMPLETO_2min.mp4` | Parte 1 + Parte 2 em sequência |

## Como rodar
```bash
cd video
python -m venv venv && ./venv/bin/pip install -r requirements.txt   # precisa de ffmpeg (libx264 + rubberband)
PATH=$PWD/venv/bin:$PATH ./run_all.sh
```
`gen_tts.py` usa o `edge-tts` (internet). Se o ambiente tiver proxy com CA própria, aponte `SSL_CERT_FILE`
para o bundle de certificados. O render usa 4 processos (≈7 min por parte em 4 núcleos).

## Estrutura
| Arquivo | Função |
| :--- | :--- |
| `lines.py` / `gen_tts.py` | Falas do roteiro → vozes pt-BR (Antonio / Francisca) com ajuste de velocidade e tom |
| `cues.py` | Linha do tempo das falas (início de cada cena) e mensagens do chat da live |
| `textures.py`, `world.py` | Texturas procedurais (azulejos, mofo, portas, cadeado, tijolos) e montagem dos 2 cenários |
| `engine.py` | Raycaster do corredor, luzes fluorescentes/lanternas, sprites, pós (grão, bloom, glitch, tearing) |
| `sprites.py` | Lucas, Clara, Marcos (visual de `CHARACTERS.md`), armário, mão pálida, correntes |
| `part1.py`, `part2.py` | Câmera, personagens, luz e efeitos de cada segundo das partes |
| `hud.py`, `compose.py` | HUD (hora, REC, bateria, AO VIVO), chat, legendas estilo TikTok, tela final |
| `audio_mix.py` | Mixagem: vozes tratadas (sussurro, voz possuída, coro metálico), estrondos, passos, correntes, estática |
| `render_video.py`, `mux.sh` | Render paralelo, encode H.264 e montagem com áudio AAC |

## Mapeamento roteiro → vídeo (Parte 1)
`0:03` armário bate (apagão + salto de câmera) → sussurro no canal esquerdo → `0:05–0:35` câmera vira para Clara e Marcos
(lanternas 5600K, pegadas de lama no chão) → `0:35–0:50` close no cadeado arrombado de dentro para fora, sangue seco, mão do Marcos
recua → `0:50` porta bate, bateria 100% → 1%, som corta, estática de rádio, `CONTINUA NA PARTE 2 ▶`.

## Mapeamento roteiro → vídeo (Parte 2)
`0:00–0:15` câmera no chão, luz azul da tela, Clara encolhida chorando → `0:15–0:35` Marcos de costas diante da parede de tijolos,
cabeça gira 180° com zoom, olhos leitosos → `0:35–0:50` fuga até a porta de ferro, que lacra com correntes enferrujadas e tilintar seco →
`0:50–1:00` celular cai, lanterna pisca duas vezes e apaga, mão pálida de Marcos pega o aparelho, rosto de Lucas possuído (Clara ao fundo),
voz metálica, corte seco para o preto.
