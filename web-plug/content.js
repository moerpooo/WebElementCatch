let isRecording = false;
let overlay = null;
let currentTarget = null;

// 1. 创建高亮跟随遮罩层（使用 fixed 绝对定位，彻底解决偏移和滚动问题）
function createOverlay() {
    if (document.getElementById('action-recorder-overlay')) return;
    
    // 如果网页还没加载出 body，先跳过
    if (!document.body) return;

    overlay = document.createElement('div');
    overlay.id = 'action-recorder-overlay';
    
    // 使用 cssText 和 !important 防止被网页自带的 CSS 覆盖干扰
    overlay.style.cssText = `
        position: fixed !important;
        background-color: rgba(52, 152, 219, 0.3) !important;
        border: 2px solid #2980b9 !important;
        z-index: 2147483647 !important;
        pointer-events: none !important;
        transition: all 0.05s ease-out !important;
        box-sizing: border-box !important;
        display: none;
    `;
    document.body.appendChild(overlay);
}

// 2. 生成元素的简易 CSS 选择器
function getCssSelector(el) {
    if (!el) return "";
    if (el.tagName.toLowerCase() === "html" || el.tagName.toLowerCase() === "body") return el.tagName.toLowerCase();
    let str = el.tagName.toLowerCase();
    if (el.id) return `${str}#${el.id}`;
    if (el.className && typeof el.className === 'string') {
        let classes = el.className.trim().split(/\s+/);
        if (classes.length > 0 && classes[0]) str += "." + classes[0];
    }
    return str;
}

// 3. 监听鼠标移动：实时追踪并动态绘制
function onMouseMove(e) {
    if (!isRecording) return;
    
    // 确保遮罩层已创建
    if (!overlay) {
        createOverlay();
        if (!overlay) return; // 等待下一帧
    }

    const target = e.target;
    
    // 如果鼠标移到了新的元素上，更新高亮框
    if (target && target !== currentTarget && target !== overlay) {
        currentTarget = target;
        
        // 忽略网页大背景，防止框住整个屏幕
        if (target.tagName === 'BODY' || target.tagName === 'HTML') {
            overlay.style.display = 'none';
            return;
        }

        const rect = target.getBoundingClientRect();
        
        overlay.style.display = 'block';
        overlay.style.setProperty('top', rect.top + 'px', 'important');
        overlay.style.setProperty('left', rect.left + 'px', 'important');
        overlay.style.setProperty('width', rect.width + 'px', 'important');
        overlay.style.setProperty('height', rect.height + 'px', 'important');
    }
}

// 4. 监听点击事件并记录
function handleRecordingClick(e) {
    if (!isRecording || !e.isTrusted) return;

    const target = e.target;
    const selector = getCssSelector(target);

    // 视觉反馈：点击瞬间框框变成绿色
    if (overlay) {
        overlay.style.setProperty('background-color', 'rgba(46, 204, 113, 0.5)', 'important');
        overlay.style.setProperty('border-color', '#27ae60', 'important');
        setTimeout(() => {
            if (overlay) {
                overlay.style.setProperty('background-color', 'rgba(52, 152, 219, 0.3)', 'important');
                overlay.style.setProperty('border-color', '#2980b9', 'important');
            }
        }, 300);
    }

    // 发送点击动作给后台记录
    chrome.runtime.sendMessage({
        type: 'RECORD_ACTION',
        data: { action: 'click', selector: selector }
    });
}

// 5. 监听输入事件并记录
function handleRecordingInput(e) {
    if (!isRecording || !e.isTrusted) return;
    const target = e.target;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        if (target.type === 'password') return; 
        
        const selector = getCssSelector(target);
        chrome.runtime.sendMessage({
            type: 'RECORD_ACTION',
            data: { action: 'input', selector: selector, value: target.value }
        });
    }
}

// 6. 切换录制状态
function toggleRecordingState(state) {
    isRecording = state;
    if (isRecording) {
        createOverlay();
        // 使用 capture 阶段 (true) 保证比页面自身事件更早拿到元素
        document.addEventListener('mousemove', onMouseMove, true);
        document.addEventListener('click', handleRecordingClick, true);
        document.addEventListener('change', handleRecordingInput, true); 
    } else {
        if (overlay) overlay.style.display = 'none';
        document.removeEventListener('mousemove', onMouseMove, true);
        document.removeEventListener('click', handleRecordingClick, true);
        document.removeEventListener('change', handleRecordingInput, true);
    }
}

// 初始化状态同步
chrome.storage.local.get(['isRecording'], (res) => {
    if (res.isRecording) toggleRecordingState(true);
});

chrome.storage.onChanged.addListener((changes) => {
    if (changes.isRecording) {
        toggleRecordingState(changes.isRecording.newValue);
    }
});