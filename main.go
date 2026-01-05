package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// ログデータの構造体（JSON受け取り用）
type LogEntry struct {
	Role string `json:"role"`
	Text string `json:"text"`
}

func main() {
	gpuFlag := flag.Bool("gpu", false, "GPUモードで起動")
	stopFlag := flag.Bool("stop", false, "全モデル停止＆VRAM解放")
	saveLogFlag := flag.Bool("save-log", false, "標準入力からJSONを受け取ってログ保存")

	flag.Parse()

	// --- 1. ログ保存モード (-save-log) ---
	if *saveLogFlag {
		if err := runSaveLog(); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(1)
		}
		return // ログ保存だけして終了
	}

	// --- 2. 停止モード (-stop) ---
	if *stopFlag {
		fmt.Println("🧹 Cow-Manager: VRAMクリーンアップを開始します...")
		stopCmd := exec.Command("sh", "-c", "ollama stop $(ollama ps | awk 'NR>1 {print $1}')")
		if err := stopCmd.Run(); err != nil {
			fmt.Println("✅ モデルは既に停止しているか、空っぽだもー。")
		} else {
			fmt.Println("✨ VRAMが綺麗になったもー！")
		}
		return
	}

	// --- 3. 起動モード (デフォルト / -gpu) ---
	fmt.Println("🐂 Cow-Manager: Ollamaリソース調整起動...")
	
	// 既存プロセス停止
	_ = exec.Command("pkill", "ollama").Run()
	time.Sleep(500 * time.Millisecond)

	// Ollama起動
	cmd := exec.Command("ollama", "serve")
	cmd.Env = os.Environ()

	if *gpuFlag {
		fmt.Println("🔥 モード: GPU (RTX 2060)")
	} else {
		fmt.Println("🧊 モード: CPU (i7-12700K)")
		cmd.Env = append(cmd.Env, "CUDA_VISIBLE_DEVICES=")
	}

	if err := cmd.Start(); err != nil {
		fmt.Printf("❌ 起動失敗: %v\n", err)
		return
	}
	fmt.Printf("✨ Ollama起動完了！ (PID: %d)\n", cmd.Process.Pid)
}

// ログ保存の実処理
func runSaveLog() error {
	// 1. 標準入力から読み込み
	inputData, err := io.ReadAll(os.Stdin)
	if err != nil {
		return fmt.Errorf("failed to read stdin: %w", err)
	}

	// 2. JSONパース
	var history []LogEntry
	if err := json.Unmarshal(inputData, &history); err != nil {
		return fmt.Errorf("invalid json: %w", err)
	}
	if len(history) == 0 {
		return fmt.Errorf("empty chat history")
	}

	// 3. ディレクトリ作成
	logDir := "logs"
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return fmt.Errorf("failed to create log dir: %w", err)
	}

	// 4. ファイル名生成
	filename := filepath.Join(logDir, fmt.Sprintf("chat_%s.txt", time.Now().Format("20060102-150405")))

	// 5. 書き込み
	file, err := os.Create(filename)
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	defer file.Close()

	for _, entry := range history {
		if _, err := fmt.Fprintf(file, "[%s]\n%s\n\n%s\n\n", entry.Role, entry.Text, "========================================"); err != nil {
			return err
		}
	}

	// 6. 成功したらファイル名を標準出力へ (Python側で受け取る)
	fmt.Print(filename)
	return nil
}