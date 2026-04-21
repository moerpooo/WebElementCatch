import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import mouse, keyboard
import win32gui
import win32con
import win32api

# 导入 pythoncom 用于解决 pywinauto 的多线程 COM 冲突
try:
    import pythoncom
except ImportError:
    pythoncom = None

try:
    import uiautomation as auto
except ImportError:
    auto = None

try:
    from pywinauto import Desktop
except ImportError:
    Desktop = None


# --- 可视化高亮层 ---
class HighlightOverlay:
    def __init__(self, root):
        self.master = root
        self.overlay_win = tk.Toplevel(root)
        self.overlay_win.overrideredirect(True)
        self.overlay_win.attributes("-topmost", True)
        self.overlay_win.attributes("-transparentcolor", "white")
        self.overlay_win.config(bg="white")
        
        # 鼠标点击穿透
        hwnd = win32gui.GetParent(self.overlay_win.winfo_id())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED)
        
        self.canvas = tk.Canvas(self.overlay_win, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.overlay_win.withdraw()

    def draw(self, x, y, w, h, color="#3498db", width=4):
        self.master.after(0, self._draw_internal, x, y, w, h, color, width)

    def _draw_internal(self, x, y, w, h, color, width):
        self.overlay_win.geometry(f"{w}x{h}+{x}+{y}")
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, w, h, outline=color, width=width)
        self.overlay_win.deiconify()

    def hide(self):
        self.master.after(0, self.overlay_win.withdraw)


# --- 主控制面板 ---
class MultiEngineRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("桌面自动化录制器 (悬停修复版)")
        self.root.geometry("450x620")
        self.root.attributes("-topmost", True)
        
        self.is_recording = False
        self.overlay = HighlightOverlay(root)
        self.recorded_lines = []
        self.current_hover_rect = None 
        
        self._setup_ui()
        
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.mouse_listener.start()
        
        # 启动悬停探测线程
        threading.Thread(target=self.hover_inspector_loop, daemon=True).start()

    def _setup_ui(self):
        engine_frame = ttk.LabelFrame(self.root, text=" 自动化引擎 ", padding=10)
        engine_frame.pack(fill="x", padx=10, pady=5)
        
        self.engine_var = tk.StringVar(value="uiautomation")
        ttk.Radiobutton(engine_frame, text="uiautomation (主力推荐)", value="uiautomation", variable=self.engine_var).pack(anchor="w")
        ttk.Radiobutton(engine_frame, text="pywinauto (UIA 模式)", value="pywinauto_uia", variable=self.engine_var).pack(anchor="w")
        ttk.Radiobutton(engine_frame, text="pywinauto (Win32 模式 - 专杀老软件)", value="pywinauto_win32", variable=self.engine_var).pack(anchor="w")

        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x")
        self.start_btn = ttk.Button(btn_frame, text="▶ 开始录制", command=self.toggle_record)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_frame, text="🗑️ 清空代码", command=self.clear_code).pack(side="left", expand=True, fill="x", padx=2)

        self.status_label = ttk.Label(self.root, text="状态: 就绪", foreground="gray")
        self.status_label.pack(pady=2)

        self.code_text = tk.Text(self.root, height=18, font=("Consolas", 9), bg="#f4f4f4")
        self.code_text.pack(fill="both", expand=True, padx=10, pady=5)
        ttk.Button(self.root, text="💾 保存代码", command=self.save_to_file).pack(fill="x", padx=10, pady=10)

    def toggle_record(self):
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.start_btn.config(text="⏹ 停止录制")
            self.status_label.config(text="🔴 正在录制 (鼠标悬停预览，点击录制)", foreground="red")
            
            engine = self.engine_var.get()
            header = ""
            if engine == "uiautomation" and "import uiautomation" not in "".join(self.recorded_lines):
                header = "import uiautomation as auto\nimport time\n"
            elif "pywinauto" in engine and "from pywinauto import Desktop" not in "".join(self.recorded_lines):
                header = "from pywinauto import Desktop\nimport time\n"
            
            if header:
                self.recorded_lines.append(header)
                self.code_text.insert(tk.END, header)
        else:
            self.start_btn.config(text="▶ 开始录制")
            self.status_label.config(text="状态: 已停止", foreground="gray")
            self.overlay.hide()

    def clear_code(self):
        self.recorded_lines = []
        self.code_text.delete(1.0, tk.END)

    def hover_inspector_loop(self):
        # 初始化子线程的 COM 组件 (解决 pywinauto 闪退核心)
        if pythoncom:
            pythoncom.CoInitialize()

        last_x, last_y = -1, -1
        while True:
            time.sleep(0.05)
            if not self.is_recording: continue

            x, y = win32api.GetCursorPos()
            if (x, y) != (last_x, last_y):
                self.overlay.hide()
                last_x, last_y = x, y
                
                # 停顿 0.3 秒探测 (pywinauto探测较慢，增加一点防抖时间)
                time.sleep(0.3)
                nx, ny = win32api.GetCursorPos()
                if (nx, ny) == (x, y):
                    self.inspect_and_highlight(nx, ny)

    def inspect_and_highlight(self, x, y):
        try:
            hwnd = win32gui.WindowFromPoint((x, y))
            if win32gui.GetParent(self.root.winfo_id()) == hwnd: return
        except: pass

        engine = self.engine_var.get()
        try:
            rect = None
            if engine == "uiautomation" and auto:
                control = auto.ControlFromPoint(x, y)
                if control and control.Name != '桌面': 
                    rect = control.BoundingRectangle
            
            elif engine == "pywinauto_uia" and Desktop:
                elem = Desktop(backend="uia").from_point(x, y)
                if elem: rect = elem.rectangle()
                
            elif engine == "pywinauto_win32" and Desktop:
                elem = Desktop(backend="win32").from_point(x, y)
                if elem: rect = elem.rectangle()

            if rect:
                self.current_hover_rect = rect
                # pywinauto 的 rectangle 对象属性调用和 uiautomation 稍有不同，需要兼容兼容处理
                w = rect.width() if callable(rect.width) else rect.width
                h = rect.height() if callable(rect.height) else rect.height
                self.overlay.draw(rect.left, rect.top, w, h, color="#3498db")
        except Exception as e:
            # 静默处理悬停错误，不打扰用户
            pass

    def on_click(self, x, y, button, pressed):
        if self.is_recording and pressed and button == mouse.Button.left:
            try:
                hwnd = win32gui.WindowFromPoint((int(x), int(y)))
                if win32gui.GetParent(self.root.winfo_id()) == hwnd: return
            except: pass
            
            if self.current_hover_rect:
                r = self.current_hover_rect
                w = r.width() if callable(r.width) else r.width
                h = r.height() if callable(r.height) else r.height
                self.overlay.draw(r.left, r.top, w, h, color="#2ecc71", width=5)
            
            threading.Thread(target=self.generate_code, args=(int(x), int(y))).start()

    def generate_code(self, x, y):
        # 再次初始化子线程的 COM 组件
        if pythoncom:
            pythoncom.CoInitialize()
            
        engine = self.engine_var.get()
        code_line = ""
        try:
            if engine == "uiautomation":
                control = auto.ControlFromPoint(x, y)
                prop = f"AutomationId='{control.AutomationId}'" if control.AutomationId else f"Name='{control.Name}'"
                if not prop: prop = f"ClassName='{control.ClassName}'"
                code_line = f"auto.{control.ControlTypeName}({prop}).Click()"
                
            elif engine == "pywinauto_uia":
                if Desktop is None: 
                    raise Exception("未安装 pywinauto！请在终端运行: pip install pywinauto")
                    
                elem = Desktop(backend="uia").from_point(x, y)
                info = elem.element_info
                props = []
                
                # 安全获取 name
                if getattr(info, 'name', None): 
                    props.append(f"title='{info.name}'")
                    
                # 💡 核心修复：读取时叫 automation_id，生成代码时叫 auto_id
                automation_id = getattr(info, 'automation_id', None)
                if automation_id: 
                    props.append(f"auto_id='{automation_id}'")
                    
                # 安全获取 control_type
                control_type = getattr(info, 'control_type', None)
                if control_type: 
                    props.append(f"control_type='{control_type}'")
                    
                code_line = f"Desktop(backend='uia').window({', '.join(props)}).click_input()"
                
            elif engine == "pywinauto_win32":
                elem = Desktop(backend="win32").from_point(x, y)
                info = elem.element_info
                props = []
                if info.name: props.append(f"title='{info.name}'")
                if info.class_name: props.append(f"class_name='{info.class_name}'")
                if hasattr(info, 'control_id') and info.control_id: props.append(f"control_id={info.control_id}")
                code_line = f"Desktop(backend='win32').window({', '.join(props)}).click_input()"

            if code_line:
                self.recorded_lines.append(code_line)
                self.root.after(0, self._update_ui_text, code_line)
                
        except Exception as e:
            # 💡 这里是关键：如果抓取报错，把错误直接打到面板上！
            error_msg = f"# ⚠️ 抓取失败 ({engine}): {str(e)}"
            self.root.after(0, self._update_ui_text, error_msg)

    def _update_ui_text(self, text):
        if "⚠️" in text:
            self.code_text.insert(tk.END, text + "\n", "error")
            self.code_text.tag_config("error", foreground="red")
        else:
            self.code_text.insert(tk.END, text + "\n")
        self.code_text.see(tk.END)

    def save_to_file(self):
        if not self.recorded_lines: return
        with open("multi_engine_script.py", "w", encoding="utf-8") as f:
            f.write("\n".join(self.recorded_lines))
        messagebox.showinfo("成功", "保存成功!")

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    root = tk.Tk()
    app = MultiEngineRecorderApp(root)
    root.mainloop()