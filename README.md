# Moorchestration-Ollama

Ollamaをローカルリソースで快適に使いたいと思った為、このツールを作りました。

![Main Screenshot](./uI_image_1.jpg)

---

## 🐂 概要 (Overview)

限られたハードウェアリソース（特に VRAM 6GB の RTX 2060 等）で、いかに効率よく LLM と対話するかを目的としています。
Python (Flet) による GUI と、Go によるバックエンド制御を組み合わせ、リソースの動的な管理を実現しています。

### 最大の特徴：CPU/GPU 駆動の柔軟な切り替え
VRAM容量を超えるような大型モデルでも、ワンクリックで **CPU強制モード** に切り替えることで動作可能です。
* **動作確認済み**: `command-r:latest` (18 GB モデル) が CPU 駆動にて快適に動作することを確認済みです。

---

## ✨ 主な機能 (Features)

* **Resource Orchestration**: VRAM の状況に応じ、GPU と CPU モードを動的に切り替え。
* **Hybrid Interpreter Logic**: 「通訳（翻訳）」と「思考（LLM）」の役割を分離し、日本語での快適な対話を実現。
* **Cowsay-Style UI**: ターミナル文化へのリスペクトを込めた AA 表示。
* **Auto Clean-up**: モデル停止時に Go のサイドカープロセスが確実にリソースを解放。

---

## 🛠️ 技術要件 (Tech Stack)

* **Frontend**: Python 3.12+ / Flet
* **Backend**: Go (System resource control)
* **Environment**: Kubuntu 25.10 / Wayland (RTX 2060 動作確認済)
* **AI Core**: Ollama
* **Dependencies**: `trans` (Translate Shell), `cowsay`

---

## 🚀 使い方 (Usage)

### 1. Backendのビルド
```bash
go build -o cow-manager main.go
```

### 2. Python環境のセットアップ
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 実行
```bash
python3 cow_chat.py
```

---

## 🗺️ 開発ビジョンと課題 (Roadmap)

* **Avatar Switching**: AA モードと「ちびキャラ」アバターの切り替え機能。
* **File Injection**: Linux/Wayland 環境でのファイル読み込みの安定化。
* **Windows Support**: Windows へのポータビリティ向上。

---

## ⚖️ ライセンス (License)

Apache License 2.0
