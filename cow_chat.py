import flet as ft
import subprocess
import asyncio
import httpx
import atexit
import os
import json # ここに移動
from datetime import datetime

async def main(page: ft.Page):
    page.title = "Cow Manager & Chat"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1100
    page.window_height = 800

    # --- ステート管理 ---
    chat_history = []
    loaded_context_data = {"filename": "", "content": ""}

    os.makedirs("logs", exist_ok=True)

    # --- 終了時クリーンアップ ---
    def cleanup_on_exit():
        print("Cleaning up models on exit...")
        try:
            cmd = "ollama ps | awk 'NR>1 {print $1}' | xargs -r -n 1 ollama stop"
            subprocess.run(cmd, shell=True, check=False)
        except Exception as e:
            print(f"Error during cleanup: {e}")

    atexit.register(cleanup_on_exit)

    # --- UI更新ヘルパー ---
    def show_snack(message, color=ft.Colors.TEAL):
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # --- ファイル操作ロジック ---
    def save_log(e):
        print("Save log button clicked") # デバッグ用
        if not chat_history:
            show_snack("⚠️ 保存する履歴がありません", ft.Colors.RED)
            return

        try:
            history_json = json.dumps(chat_history, ensure_ascii=False)
            
            # Go製の cow-manager バイナリに委譲 (-save-log モード)
            # 絶対パスで指定しておくと安心
            cow_manager_bin = os.path.abspath("cow-manager")
            print(f"Calling cow-manager: {cow_manager_bin}")

            process = subprocess.Popen(
                [cow_manager_bin, "-save-log"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()
            )
            
            stdout, stderr = process.communicate(input=history_json)
            
            print(f"Logger stdout: {stdout}")
            print(f"Logger stderr: {stderr}")

            if process.returncode == 0:
                saved_filename = stdout.strip()
                show_snack(f"💾 ログを保存しました: {saved_filename}")
            else:
                show_snack(f"❌ 保存エラー: {stderr.strip()}", ft.Colors.RED)
                
        except Exception as ex:
            print(f"Exception in save_log: {ex}")
            show_snack(f"❌ 呼び出しエラー: {str(ex)}", ft.Colors.RED)

    # --- Ollama / Subprocess ---
    def get_installed_models():
        try:
            res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            lines = res.stdout.strip().split("\n")
            models = []
            for line in lines[1:]:
                if line and line.split(): models.append(line.split()[0])
            return models
        except: return ["Error"]

    async def get_running_models():
        try:
            proc = await asyncio.create_subprocess_exec("ollama", "ps", stdout=subprocess.PIPE)
            stdout, _ = await proc.communicate()
            lines = stdout.decode().strip().split("\n")
            return "\n".join(lines[1:]) if len(lines) > 1 else "No active models"
        except: return "Status Error"

    async def call_ollama_api(model_name, prompt, system_prompt=None, use_cpu=False):
        url = "http://localhost:11434/api/generate"
        options = {"num_gpu": 0} if use_cpu else {}
        payload = {"model": model_name, "prompt": prompt, "stream": False, "options": options}
        if system_prompt: payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    # --- UI Components ---
    installed_models = get_installed_models()
    translator_options = ["Google Translate (trans)"] + installed_models
    default_trans = "Google Translate (trans)"
    default_think = "mistral-nemo" if "mistral-nemo" in installed_models else (installed_models[0] if installed_models else "")

    # Side Bar
    dd_translator = ft.Dropdown(label="通訳モデル", options=[ft.dropdown.Option(m) for m in translator_options], value=default_trans, text_size=12, expand=True)
    cb_trans_input = ft.Checkbox(label="入力翻訳 (JP->EN)", value=True)
    cb_trans_output = ft.Checkbox(label="出力翻訳 (EN->JP)", value=True)
    sw_trans_cpu = ft.Switch(label="CPU強制モード", value=False)
    
    dd_thinker = ft.Dropdown(label="思考モデル", options=[ft.dropdown.Option(m) for m in installed_models], value=default_think, text_size=12, expand=True)
    sw_think_cpu = ft.Switch(label="CPU強制モード", value=True)
    
    txt_status_monitor = ft.Text("Checking...", size=12, font_family="Monospace")

    # Chat Area
    chat_list = ft.ListView(expand=True, spacing=10, padding=20, auto_scroll=True)
    status_text = ft.Text("", color="yellow")
    txt_input = ft.TextField(hint_text="Ask the Cow...", expand=True, on_submit=lambda e: asyncio.create_task(send_message(e)), border_color="white", multiline=True, max_lines=5)
    
    async def refresh_status(e=None):
        txt_status_monitor.value = await get_running_models()
        page.update()

    async def stop_all_models(e):
        btn_stop.disabled = True; btn_stop.text = "Cleaning..."; page.update()
        cleanup_on_exit()
        await refresh_status()
        status_text.value = "All models stopped."
        btn_stop.disabled = False; btn_stop.text = "🧹 全モデル停止"; page.update()

    async def translate_text(text, target, model, cpu):
        if model == "Google Translate (trans)":
            lang = ":en" if target == "en" else ":ja"
            proc = await asyncio.create_subprocess_exec("trans", "-b", lang, text, stdout=subprocess.PIPE)
            out, _ = await proc.communicate()
            return out.decode().strip()
        else:
            sys_p = "You are a professional translator. Output ONLY the translated text."
            p = f"Translate the following text to {'English' if target=='en' else 'Japanese'}:\n{text}"
            return await call_ollama_api(model, p, sys_p, cpu)

    async def send_message(e):
        user_in = txt_input.value
        if not user_in: return
        
        txt_input.value = ""
        txt_input.disabled = True
        chat_history.append({"role": "User", "text": user_in})
        chat_list.controls.append(ft.Container(ft.Text(f"あなた: {user_in}", size=16), padding=10, bgcolor=ft.Colors.GREY_800, border_radius=10, alignment=ft.Alignment(1,0)))
        page.update()

        try:
            # 1. 翻訳
            en_prompt = user_in
            if cb_trans_input.value:
                status_text.value = "Translation..."
                page.update()
                en_prompt = await translate_text(user_in, "en", dd_translator.value, sw_trans_cpu.value)

            # 2. 思考
            status_text.value = "Thinking..."
            page.update()
            
            final_prompt = en_prompt
            
            en_ans = await call_ollama_api(dd_thinker.value, final_prompt, None, sw_think_cpu.value)

            # 3. 翻訳
            jp_ans = en_ans
            if cb_trans_output.value:
                status_text.value = "Translation..."
                page.update()
                jp_ans = await translate_text(en_ans, "ja", dd_translator.value, sw_trans_cpu.value)

            # 4. Cowsay
            chat_history.append({"role": "Cow", "text": jp_ans})
            proc = await asyncio.create_subprocess_exec("cowsay", "-W", "60", jp_ans, stdout=subprocess.PIPE)
            out, _ = await proc.communicate()
            
            chat_list.controls.append(ft.Container(ft.Text(out.decode(), font_family="Monospace", size=14), padding=10, bgcolor=ft.Colors.GREEN_900, border_radius=10))
            await refresh_status()

        except Exception as err:
            chat_list.controls.append(ft.Text(f"Error: {err}", color="red"))
        
        finally:
            status_text.value = ""
            txt_input.disabled = False
            try:
                await txt_input.focus()
            except:
                pass
            page.update()

    # Layout
    btn_stop = ft.FilledButton("🧹 全モデル停止", icon=ft.Icons.DELETE_FOREVER, style=ft.ButtonStyle(bgcolor=ft.Colors.RED_900, color="white"), on_click=stop_all_models)
    btn_save = ft.FilledButton("💾 ログ保存", icon=ft.Icons.SAVE, style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_800, color="white"), on_click=save_log)
    
    sidebar = ft.Container(content=ft.Column([
        ft.Text("🎮 Cow Cockpit", size=24, weight="bold"), ft.Divider(),
        ft.Text("Interpreter", weight="bold"), dd_translator, 
        ft.Row([cb_trans_input, cb_trans_output]), ft.Row([ft.Icon(ft.Icons.MEMORY), sw_trans_cpu]),
        ft.Divider(),
        ft.Text("Thinker", weight="bold"), dd_thinker, 
        ft.Row([ft.Icon(ft.Icons.MEMORY), sw_think_cpu]),
        ft.Divider(),
        ft.Row([ft.Text("Status"), ft.IconButton(ft.Icons.REFRESH, on_click=refresh_status)]),
        ft.Container(txt_status_monitor, bgcolor=ft.Colors.BLACK54, padding=5, border_radius=5),
        ft.Divider(), btn_stop, ft.Divider(), btn_save
    ]), width=320, padding=20, bgcolor=ft.Colors.BLUE_GREY_900)

    chat_col = ft.Column([
        ft.Container(chat_list, expand=True, border=ft.Border(top=ft.BorderSide(1,"grey"), bottom=ft.BorderSide(1,"grey")), border_radius=10),
        ft.Row([status_text]),
        ft.Row([txt_input, ft.IconButton(ft.Icons.SEND, icon_color="green", on_click=lambda e: asyncio.create_task(send_message(e)))], alignment="spaceBetween")
    ], expand=True)

    page.add(ft.Row([sidebar, ft.VerticalDivider(width=1), ft.Container(chat_col, expand=True, padding=20)], expand=True))
    await refresh_status()

    def win_ev(e):
        if e.data=="close": cleanup_on_exit(); page.window_destroy()
    page.on_window_event = win_ev
    page.window_prevent_close = True

if __name__ == "__main__":
    ft.run(main)