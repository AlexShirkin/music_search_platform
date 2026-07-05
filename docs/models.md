# Models

## MVP stack

| Роль | Модель | Лицензия | Размерность |
|------|--------|----------|-------------|
| Audio similarity | MusiCNN ONNX (v5.0.0-model) | **ISC** | 200 |
| Text ↔ audio | `laion/larger_clap_music` (этап 4+) | CC-BY 4.0 | 512 |

## MusiCNN preprocessing

Реализация: `libs/music_platform/audio/spectrogram.py` → `prepare_spectrogram_patches()`.

```
audio (16 kHz mono)
  → mel-spectrogram (96 bands, hop=256, n_fft=512)
  → log10(1 + 10000 * mel)
  → patches 96×187, step 187 (~3 s each)
  → ONNX embedding per patch
  → mean → L2 normalize → vector (200,)
```

### Параметры mel

| Параметр | Значение |
|----------|----------|
| `SAMPLE_RATE` | 16000 |
| `N_FFT` | 512 |
| `HOP_LENGTH` | 256 |
| `MEL_BANDS` | 96 |
| `PATCH_FRAMES` | 187 |

## Загрузка весов

```bash
make download-models
# → models/musicnn/musicnn_embedding.onnx
# → models/musicnn/musicnn_prediction.onnx
```

Источник: [AudioMuse-AI v5.0.0-model](https://github.com/NeptuneHub/AudioMuse-AI/releases/tag/v5.0.0-model).

## Smoke test

```bash
pip install -e ".[dev,inference]"
make download-models
make smoke-musicnn
```

## Лицензии — что не использовать

| Модель | Причина |
|--------|---------|
| DCLAP (AudioMuse) | AGPL-3.0 |
| MERT | CC-BY-NC (non-commercial) |
| Код AudioMuse-AI | AGPL-3.0 — не копировать в закрытый продукт |
